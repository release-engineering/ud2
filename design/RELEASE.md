# Release Push/Sync Design Specification

This document specifies the design for the Release feature: a schema and workflow
for idempotently associating a collection of repository files with a version on a
product, plus CLI commands to check and push release manifests.


## Overview

A **Release** bundles:

- A product reference (by ID or lookup key)
- A version (by ID or natural key within the product)
- A collection of repository (file) definitions

Operations are idempotent: repeated pushes with the same manifest produce the
same server state. Safe searches and matching heuristics determine whether to
create or update each resource. Write-back of server-assigned IDs into the
manifest assists subsequent syncs.


## Pydantic Schema

### Release

The top-level manifest type.

```python
from typing import List, Optional, Union
from pydantic import BaseModel, Field


class ProductRef(BaseModel):
    """
    Product reference for lookup or identification.

    When ``id`` is present and valid, it is used directly.
    Otherwise, ``eng_id`` and ``name`` are used to search.
    """

    id: Optional[int] = None
    eng_id: Optional[int] = Field(None, alias='engId')
    name: Optional[str] = None


class VersionRef(BaseModel):
    """
    Version reference within a product.

    When ``id`` is present and valid, it is used directly.
    Otherwise, ``version`` is used with the resolved product for lookup.
    Natural key: (product, version).
    """

    id: Optional[int] = None
    version: str
    architecture: Optional[str] = None
    cpe: Optional[str] = None
    platform: Optional[str] = None
    visibility: Optional[str] = None


class RepositoryEntry(BaseModel):
    """
    A single repository (file) entry in the release manifest.

    Mapped to ``RepositoryCreate`` for API calls. Optional ``id`` from prior
    push enables fast-path lookup. When ``path`` is present and ``--upload``
    is used, the upload utility is invoked to obtain/confirm file metadata
    before metadata is pushed.
    """

    id: Optional[int] = None
    description: str  # title; used for user presentation and matching fallback
    file_name: str = Field(..., alias='fileName')
    file_size: int = Field(..., alias='fileSize')
    sha256: str
    md5: str
    issues: List[str] = Field(default_factory=list)
    visibility: str
    classifier: List[str] = Field(default_factory=list)
    content_types: List[str] = Field(default_factory=list, alias='contentTypes')
    installation: Optional[str] = None
    long_description: Optional[str] = Field(None, alias='longDescription')

    # Optional: local file path for --upload flow. When set and --upload used,
    # upload utility reads from this path and may override sha256/md5/file_size.
    path: Optional[str] = None


class ReleaseSyncMetadata(BaseModel):
    """
    Write-back metadata from a successful push.

    Populated by the push operation; used to accelerate subsequent syncs.
    """

    product_id: int = Field(..., alias='productId')
    version_id: int = Field(..., alias='versionId')
    file_ids: List[int] = Field(default_factory=list, alias='fileIds')


class Release(BaseModel):
    """
    Release manifest: product, version, and collection of repository files.
    """

    product: ProductRef
    version: VersionRef
    repositories: List[RepositoryEntry] = Field(default_factory=list)
    _sync: Optional[ReleaseSyncMetadata] = Field(None, alias='_sync')
```

**Note:** `RepositoryEntry` aligns with `RepositoryCreate`; all required fields
(`description`, `file_name`, `file_size`, `sha256`, `md5`, `issues`, `visibility`,
`classifier`) must be present or defaulted. The optional `path` is a manifest-only
hint for the upload flow and is not sent to the API.


## Heuristic Search Helpers

### Product Lookup

```
resolve_product(client, product_ref: ProductRef) -> Optional[Product]
```

1. If `product_ref.id` is present: `client.get_product(product_ref.id)`.
   - On success, return the product.
   - On 404 or other error, fall through to search.
2. If `product_ref.eng_id` and `product_ref.name` are present: iterate
   `client.iter_products()`, match where `p.eng_id == product_ref.eng_id` and
   `p.name == product_ref.name` (case-sensitive or per policy).
3. Return `None` if no match.

### Version Lookup

```
resolve_version(client, product: Product, version_ref: VersionRef) -> Optional[Version]
```

1. If `version_ref.id` is present: `client.get_product_version(version_ref.id)`.
   - If returned `version.product_id == product.id`, return it.
   - Otherwise (wrong product) or on error, fall through.
2. Fetch `client.list_product_versions(product.id)` and match by
   `version.version == version_ref.version`. Natural key is `(product, version)`.
3. Return `None` if no match.

### Repository Lookup (per file)

```
resolve_repository(
    client,
    product_version_id: int,
    entry: RepositoryEntry,
    existing: List[Repository],
) -> Tuple[Optional[Repository], Optional[MatchKind], Optional[RepoMatchError]]
```

Match order: ID → sha256+filename → title (description). Returns
`(repository_or_none, match_kind, error_or_none)`.

Sha256 alone is **not** identity. Identical content under a new download
path (`file_name`) must create a new repository entry, not update the old one.

1. **ID**: If `entry.id` is present, find in `existing` where `r.id == entry.id`.
   - If found, return `(r, MatchKind.ID, None)`.
   - If not found in list, `client.get_repository(entry.id)`; on success and
     if that repository belongs to this version, return it.
   - On 404 or wrong version, treat as no match and continue.

2. **sha256 + file_name**: Find in `existing` where `r.sha256 == entry.sha256`
   **and** `r.file_name == entry.file_name`.
   - If found, return `(r, MatchKind.SHA256, None)`.
   - Same sha256 with a different `file_name` is not a match (fall through).

3. **Title**: Find in `existing` where `r.description == entry.description`.
   - If found:
     - If `r.sha256 == entry.sha256` and `r.file_name != entry.file_name`:
       Skip this repo (same bytes, new download name → would create).
     - If `r.sha256 == entry.sha256`: return `(r, MatchKind.TITLE, None)`.
     - If `r.sha256 != entry.sha256` and `r.file_name == entry.file_name`:
       Return `(r, None, RepoMatchError.FILENAME_MISMATCH)` unless
       `force_filename` is set.
     - If `r.sha256 != entry.sha256` and `r.file_name != entry.file_name`:
       Content replace with new filename; return `(r, MatchKind.TITLE, None)`.
   - If not found, return `(None, None, None)` (would create).

**MatchKind** (enum): `ID`, `SHA256`, `TITLE`.

**RepoMatchError**: `FILENAME_MISMATCH` — same title, different sha256, same
filename; forbidden unless `--force-filename`.


## Ensure (Create/Update) Functions

### ensure_product

Not typically needed; release assumes product exists. Lookup only.

### ensure_version

```
ensure_version(
    client,
    product: Product,
    version_ref: VersionRef,
) -> Version
```

1. Call `resolve_version(client, product, version_ref)`.
2. If found, return it (no update for now; version metadata updates could be
   added later if desired).
3. If not found, build `VersionCreate` from `version_ref` and call
   `client.create_product_version(product.id, payload)`.
4. Return the created version.

### ensure_repository

```
ensure_repository(
    client,
    product_version_id: int,
    entry: RepositoryEntry,
    existing: List[Repository],
    force_filename: bool = False,
) -> Repository
```

1. Call `resolve_repository(client, product_version_id, entry, existing)`.
2. If `RepoMatchError.FILENAME_MISMATCH`: raise `ReleaseError` (or equivalent)
   unless `force_filename` is True.
3. If repository found (any match kind): build `RepositoryCreate` from `entry`,
   call `client.update_repository(repo.id, payload)`, return result.
4. If not found: build `RepositoryCreate`, call
   `client.create_repository(product_version_id, payload)`, return result.


## Write-Back

After a successful push:

1. Resolve product and version (now guaranteed to exist).
2. Resolve each repository (create or update completed).
3. Build `ReleaseSyncMetadata` with `product_id`, `version_id`, and the list
   of `file_ids` in manifest order.
4. Merge into the manifest under `_sync` (or a companion metadata file, per
   implementation choice). When the manifest is loaded for a subsequent run,
   these IDs accelerate lookups.


## CLI Commands

### Authoring Commands (manifest on disk only)

The following commands create and modify the release manifest YAML on disk
without API calls. They enable compose-style interactive authoring before push.

- **ud2 release init RELEASEFILE** — Create a new manifest. Requires
  `--product-id` or both `--product-eng-id` and `--product-name`; requires
  `--version`. Optional: `--architecture`, `--platform`, `--visibility`,
  `--cpe`. Use `--force` to overwrite an existing file.

- **ud2 release add RELEASEFILE** — Add a repository entry. Either use
  `--file PATH` with `--desc` (computes sha256, md5, file_size, file_name from
  the artifact), or provide all of `--desc`, `--file-name`, `--file-size`,
  `--sha256`, `--md5`. Optional: `--visibility`, `--content-type`, `--issues`,
  `--classifier`, `--installation`, `--long-desc`. Use `--no-path` to omit the
  path field when using `--file`.

- **ud2 release list RELEASEFILE** — List repository entries in the manifest.
  Prints index, file name, and title (short description) for each entry. With
  `--yaml`, outputs a YAML list of `index`, `fileName`, and `description`.

- **ud2 release edit RELEASEFILE** — Edit an existing entry. Identify it with
  `--file-name FILENAME` or `--by-index N`. Override any fields (`--desc`,
  `--file`, `--visibility`, etc.). Use `--dry-run` to preview without writing.

- **ud2 release remove RELEASEFILE** — Remove an entry. Identify with
  `--file-name` or `--by-index`. Use `--dry-run` to preview.


### ud2 release check RELEASEFILE

**Synopsis:** `ud2 release check RELEASEFILE [OPTIONS]`

**Description:** Check-only mode. Compares the release manifest to server state,
reports differences, and surfaces errors. Performs no API writes.

**Arguments:**

- `RELEASEFILE`: Path to the release manifest (YAML).

**Options:**

- `--config PATH`: Path to ud2 configuration (inherited from main).
- `--env PROFILE`: Configuration profile (inherited from main).
- `--yaml`: Output report as YAML (inherited from main).

**Behavior:**

1. Load and validate the manifest as a `Release`.
2. Resolve product; if not found, report error and exit non-zero.
3. Resolve version; report "would create" if not found.
4. For each repository: resolve using the heuristic; report:
   - Would create
   - Would update (by ID / sha256+filename / title)
   - ERROR: filename mismatch (same title, different sha256, same filename)
5. Emit a summary of planned actions and any errors.

**Exit codes:**

- `0`: No errors, manifest is in sync (no differences).
- `1`: Errors present (product not found, filename mismatch, etc.).
- `2`: Differences present but no hard errors (e.g. would create/update).

Exact exit code semantics may be refined; the important distinction is
"success / differences only / errors".

---

### ud2 release push RELEASEFILE

**Synopsis:** `ud2 release push RELEASEFILE [OPTIONS]`

**Description:** Push the release to the server. Resolves product and version,
creates or updates repositories as needed, and optionally uploads file binaries.
Writes back sync metadata on success.

**Arguments:**

- `RELEASEFILE`: Path to the release manifest (YAML).

**Options:**

- `--config PATH`: Path to ud2 configuration (inherited from main).
- `--env PROFILE`: Configuration profile (inherited from main).
- `--yaml`: Output as YAML (inherited from main).
- `--force-filename`: Allow replacing file content when matched by title and
  filename is unchanged (overrides the filename/sha256 safety check).
- `--upload`: Invoke file upload utilities before pushing metadata.
  - For each `RepositoryEntry` with a `path` set, the upload utility is called
    to upload the binary. The utility is responsible for:
    - Reading the file at `path`
    - Uploading to the appropriate storage backend (out-of-scope for this spec)
    - Returning or otherwise providing the final `sha256`, `md5`, `file_size`,
      and `file_name` to use in the metadata payload.
  - Entries without `path` use manifest metadata as-is (no upload).
  - **Implementation note:** The upload utility interface and implementation
    are not yet built. This option is a placeholder that will call out to
    as-yet-not-built file uploading utilities. The design assumes:
    - A callable or subprocess interface that accepts (path, manifest_entry?)
      and returns/resolves metadata for the uploaded file.
    - Metadata from the upload (sha256, etc.) overrides manifest values when
      `--upload` is used for that entry.
  - Until the upload utility exists, `--upload` may be rejected with a clear
    "not implemented" message.

**Behavior:**

1. Load and validate the manifest.
2. If `--upload`: for each entry with `path`, invoke the upload utility and
   update entry metadata from the result.
3. Resolve product; if not found, error and exit.
4. Ensure version (create if missing).
5. List existing repositories for the version.
6. For each repository entry: call `ensure_repository` with `force_filename`
   from `--force-filename`. On `FILENAME_MISMATCH` without `--force-filename`,
   error and exit.
7. On success, write back `ReleaseSyncMetadata` into the manifest (or companion
   file).


## Example Manifest

```yaml
product:
  id: 123
  # Or: engId: 4001, name: "Project Atlas"

version:
  id: 456
  version: "1.2.3"
  architecture: x86_64
  platform: linux
  visibility: public

repositories:
  - id: 789
    description: "Project Atlas 1.2.3 Installer"
    fileName: "atlas-1.2.3-installer.zip"
    fileSize: 104857600
    sha256: "abc123..."
    md5: "def456..."
    issues: []
    visibility: visible
    classifier: []
    # path: ./dist/atlas-1.2.3-installer.zip  # for --upload

# _sync: written back after push
# _sync:
#   productId: 123
#   versionId: 456
#   fileIds: [789]
```


## Error Handling

- **Product not found:** Hard failure; nothing can proceed.
- **Version not found:** Create during push; report "would create" during check.
- **Repository filename mismatch:** Error unless `--force-filename`. Message
  should identify the entry (by title) and state that the filename must change
  when content (sha256) changes.
- **Upload utility missing:** When `--upload` is used and the utility is not
  available, fail with a clear "upload support not yet implemented" message.


## Future Considerations

- Version metadata updates (ensure_version could update existing version
  fields if manifest differs).
- Deletion: removing entries from the manifest could optionally delete
  corresponding repositories (dangerous; would need explicit flag).
- Structured report format for `check` (e.g. JSON) for scripting.
- Companion metadata file (e.g. `releasefile.yml.sync`) instead of
  in-manifest `_sync` to avoid modifying the canonical manifest.

<!-- The end. -->
