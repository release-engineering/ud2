======================================
Release Manifest Quickstart
======================================

This guide walks through the release manifest workflow: authoring a manifest that
bundles product reference, version, and repository (file) entries; checking it
against the server; and pushing changes. Use this workflow when you want to
idempotently sync a collection of files with a version on an existing product,
or when composing releases from multiple artifacts in a single declarative file.

For individual product, version, and repository CRUD operations, see
:doc:`cli_quickstart`.


Prerequisites
=============

* ``ud2`` is installed and available on your ``PATH`` (``ud2 --version`` should
  succeed).
* Your UD2 configuration file is accessible (defaults to
  ``~/.config/ud2/config.ini``). Use ``--config`` or ``--env`` if you need to
  override the defaults.
* You can reach the Unified Downloads API from the machine running the CLI.

All examples below use the default "friendly" output. Add ``--yaml`` to render
results as YAML for scripting or piping to tools like ``yq`` or ``jq``.


Manifest Path
=============

Release commands accept ``RELEASEFILE`` as either a file path (for example
``release.yaml``) or a directory. If you pass a directory, the CLI looks for
``ud-release.yml`` inside it. This lets you run commands from the project root
with ``ud2 release check .`` or ``ud2 release push .``.


Creating a Manifest
===================

You can build a manifest from scratch using the authoring commands, or craft the
YAML by hand.

Authoring workflow (recommended)
----------------------------------

1. Initialize a new manifest. Specify the product using **exactly one** of
   ``--product-id``, ``--product-eng-id``, ``--product-name``, or
   ``--product-code``. With ``--product-id``, the manifest stores that numeric
   id. With any of the other three, the manifest stores that engineering id,
   name, or product code (no API call during ``init``). ``ud2 release check``
   and ``ud2 release push`` then resolve the product id against the configured
   API (case-insensitive match on name or product code; exact match on
   engineering id). If several products match, the CLI uses the largest product
   id and prints a warning. Use ``--force`` to overwrite an existing file.

   .. code-block:: bash

      ud2 release init release.yaml --product-eng-id 4001 \\
          --version 1.0 --architecture x86_64 --platform linux

   Or by name or code (stored in the manifest; resolved at check/push time):

   .. code-block:: bash

      ud2 release init release.yaml --product-name "Project Atlas" --version 1.0

   Or with a known product id (stored as-is in the manifest):

   .. code-block:: bash

      ud2 release init release.yaml --product-id 4001 --version 1.0 --platform linux --force

2. Add repository entries. Use ``--file`` with ``--desc`` to have the CLI
   derive ``fileName``, ``fileSize``, ``sha256``, and ``md5`` from the artifact.
   The path is stored in the manifest for the ``--upload`` flow; use
   ``--no-path`` to omit it.

   .. code-block:: bash

      ud2 release add release.yaml --file ./dist/atlas-1.0-ga.iso --desc "Atlas 1.0 GA ISO"
      ud2 release add release.yaml --file ./dist/checksums.txt --desc "Checksums" --no-path

   Alternatively, add entries in explicit mode by providing all of ``--desc``,
   ``--file-name``, ``--file-size``, ``--sha256``, and ``--md5`` (for example
   when the file is not yet on disk). Optional fields include ``--visibility``,
   ``--content-type``, ``--issues``, ``--classifier``, ``--installation``,
   ``--long-desc``, and ``--long-desc-file``.

3. Edit entries with ``ud2 release edit``. Identify the entry by ``--file-name``
   or ``--by-index``. Override any field (``--desc``, ``--new-file-name``,
   ``--file`` to recompute from disk, etc.). Use ``--path`` or ``--clear-path``
   to set or clear the upload path. Use ``--dry-run`` to preview changes without
   writing.

   .. code-block:: bash

      ud2 release edit release.yaml --file-name atlas-1.0-ga.iso --desc "Atlas 1.0 GA ISO (GA)"
      ud2 release edit release.yaml --by-index 1 --dry-run

4. Remove entries with ``ud2 release remove``. Identify by ``--file-name`` or
   ``--by-index``. Use ``--dry-run`` to preview.

   .. code-block:: bash

      ud2 release remove release.yaml --file-name checksums.txt --dry-run
      ud2 release remove release.yaml --file-name checksums.txt

Hand-written manifest
---------------------

Create the manifest YAML directly:

.. code-block:: yaml

   product:
     engId: 4001
     name: "Project Atlas"

   version:
     version: "1.0"
     architecture: x86_64
     platform: linux
     visibility: public

   repositories:
     - description: "Atlas 1.0 GA ISO"
       fileName: atlas-1.0-ga.iso
       fileSize: 734003200
       sha256: "1f2d3c4b5a69788766554433221100ffeeddccbbaa99887766554433221100ff"
       md5: "abc123def456"
       issues: []
       visibility: visible
       classifier: []


Checking the Manifest
=====================

Check the manifest against the server without making changes:

.. code-block:: bash

   ud2 release check release.yaml

This reports whether the product and version exist, and for each repository
whether it would be created or updated. It also surfaces errors such as
filename/sha256 mismatches (when the same title and filename would point to
different content).

Exit codes:

* ``0``: No errors, manifest is in sync (no differences).
* ``1``: Errors present (product not found, filename mismatch, etc.).
* ``2``: Differences present but no hard errors (would create or update).


Pushing the Release
===================

Push the release to apply changes:

.. code-block:: bash

   ud2 release push release.yaml

This creates the version if missing, creates or updates repositories as needed,
and writes back IDs (``_sync``) into the manifest for faster subsequent syncs.

Options:

* ``--force-filename``: Override the filename/sha256 safety check when
  intentionally replacing content under the same filename.
* ``--upload``: Invoke file upload utilities before pushing metadata. This
  option is not yet implemented; use it when upload support is added.

See `design/RELEASE.md` in the source tree for the full release schema and
matching heuristics.


Next Steps
==========

* Use ``ud2 release --help`` and command-specific ``--help`` flags (for example
  ``ud2 release add --help``) to discover all options.
* Add ``--yaml`` to ``check`` or ``push`` for machine-readable output in
  automation or CI pipelines.

.. The end.
