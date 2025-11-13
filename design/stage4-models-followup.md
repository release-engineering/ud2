# Stage 4 Models Follow-up

## Objective

Capture ancillary improvements to the Stage 1 Pydantic models that can be pursued after the core client and CLI work. These ideas reinforce data quality and ergonomics without overlapping the planned Stage 2 (client) and Stage 3 (CLI) deliverables.

## Candidates

### 1. Formal Pagination Types

- Introduce dedicated pagination models (e.g., `PaginatedProducts`, `PaginatedRepositories`) composed of `PaginationMeta` plus resource payloads.
- Encapsulate shared fields (`limit`, `page`, `total`, `total_pages`) and enforce `extra='forbid'`.
- Benefits: clearer typing for list responses, better reuse in client helpers, simplifies serialization for future CLI/table rendering.

### 2. Enumerations for Well-Known Values

- Model swagger-described free-form strings with enums where backend behavior is stable (`Visibility`, `Architecture`, `Platform`).
- Provide `from_str` fallbacks or use `Enum` with custom validation to keep compatibility with unknown future values.
- Benefits: catches upstream regressions early and improves IDE assistance for callers building payloads.

### 3. Temporal Field Normalization

- Parse repository date fields (`publish_date`, `update_date`) to `datetime` using Pydantic validators while preserving original aliases.
- Add optional serialization helpers to emit ISO 8601 strings when sending data back.
- Benefits: avoids string parsing duplication in client/CLI layers and enables richer comparisons in future tooling.

### 4. Data Hygiene Validators

- Add validators for checksum length (`sha256`), minimum `file_size`, and optional normalization (trim whitespace, enforce uppercase product codes).
- Keep validation failures descriptive to aid CLI ergonomics.
- Benefits: prevents malformed payloads from leaving the client and documents expectations explicitly.

### 5. Model Factories for Testing

- Provide lightweight factory helpers (e.g., `Product.stub()`) under a `ud2/models/testing.py` module for unit tests.
- Use default realistic values with override support to streamline Stage 2/3 test setup without polluting production modules.
- Benefits: encourages consistent fixtures and reduces duplication across upcoming test suites.

### 6. Documentation Sync

- Generate ReST snippets for the new models (using `pydantic` schema export) and integrate them into project documentation.
- Highlight alias mapping tables to align internal contributors and future API partners.
- Benefits: keeps docs in lockstep with model evolution and lowers onboarding cost.

<!-- The end. -->
