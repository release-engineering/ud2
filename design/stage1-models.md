# Stage 1: Populate Pydantic Models

## Objective

Translate the API schema in `reference/swagger.yaml` into concrete Pydantic models living under `ud2/models`. Reuse the existing placeholders where possible while introducing shared mixins or helper base classes only when they reduce duplication across product, version, and repository payloads.

## Source Material

- `reference/swagger.yaml`
  - `models.ProductInput` / `models.ProductResponse`
  - `models.ProductVersionInput` / `models.ProductVersionResponse`
  - `models.RepositoryInput` / `models.RepositoryResponse`
- Existing skeletons: `ud2/models/product.py`, `ud2/models/version.py`, `ud2/models/repository.py`
- Export surface: `ud2/models/__init__.py`

## Model Strategy

1. Create dedicated request/response shapes per resource that reflect the swagger definitions:
   - `ProductCreate` and `Product` (response) in `product.py`
   - `VersionCreate` and `Version` in `version.py`
   - `RepositoryCreate` and `Repository` in `repository.py`
2. Keep the exported names in `ud2/models/__init__.py` aligned with the response classes (`Product`, `Version`, `Repository`) because the client primarily consumes response data.
3. Use optional fields where swagger omits `required`, and enforce required attributes with explicit type hints (e.g., `eng_id: int`).
4. Reuse common pagination fields (limit, page, total, total_pages) by introducing a small shared `Pagination` model if needed; prefer composition over inheritance.

## Field Mapping Guidelines

| Swagger Definition | Target Class | Notes |
| --- | --- | --- |
| `models.ProductInput` | `ProductCreate` | Required: `eng_id`, `name`. Optional: `arch`, `category`, `product_code`, `product_group`, `product_group_name`. |
| `models.ProductResponse` | `Product` | All fields optional except `id`, `eng_id`, `name`. Response retains `id`. |
| `models.ProductVersionInput` | `VersionCreate` | Required: `version`. Optional: `architecture`, `cpe`, `platform`, `visibility`. |
| `models.ProductVersionResponse` | `Version` | Includes `id` and `product_id` (via swagger `productId`). Use `Field(alias='productId')` with `serialization_alias` to expose `product_id`. |
| `models.RepositoryInput` | `RepositoryCreate` | Required: `description`, `fileName`, `fileSize`, `sha256`. Normalize field names to snake_case using aliases (e.g., swagger `fileName` -> attribute `file_name`). |
| `models.RepositoryResponse` | `Repository` | Includes `id`, optional metadata such as `installation`, `productName`, `publishDate`. Map camelCase keys to snake_case attributes using aliases and configure `model_config = ConfigDict(populate_by_name=True)` for bidirectional conversion. |

## Implementation Steps

1. For each module (`product.py`, `version.py`, `repository.py`):
   - Replace the placeholder class with the request/response pair.
   - Import `Field` and `ConfigDict` from Pydantic as needed.
   - Document required fields using ReST-style docstrings.
   - Provide helper constructors (`@classmethod from_api`) only if it reduces repetitive alias handling (otherwise rely on `model_validate`).
2. Update `ud2/models/__init__.py` exports to include both create/request models and responses as needed by later stages (e.g., export `ProductCreate` alongside `Product` if CLI will instantiate payloads).
3. Ensure each module ends with `# The end.` per project convention.

## Validation & Defaults

- Apply strict field typing; avoid `Optional` for required swagger fields.
- Use `ConfigDict(extra='forbid')` to catch unexpected keys from API payloads and prompt explicit handling.
- Respect swagger examples when introducing sensible defaults, but prefer explicit required typing over default values.

## Deliverables

- Updated `product.py`, `version.py`, and `repository.py` populated with concrete models.
- Adjusted `ud2/models/__init__.py` exporting request/response classes.
- No client or CLI changes performed in this stage.

## Open Questions

- Confirm whether pagination responses should be formalized into dedicated models or handled ad hoc by the client.
- Determine if visibility/platform enumerations should be expressed via `Enum` types (swagger lists them as free-form strings).

<!-- The end. -->
