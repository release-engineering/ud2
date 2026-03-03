# UD2 System Design

## Goals

- Provide a repeatable CLI experience for managing products, versions, and repository artifacts in the Unified Downloads platform.
- Offer a Python client (`UDClient`) that can be embedded into automation without duplicating REST plumbing.
- Enforce API contracts at the edge using typed Pydantic models and centralized configuration to limit operator error.

## Scope & Assumptions

- UD2 owns the local CLI, configuration handling, request orchestration, and output formatting.
- The Unified Downloads REST API is authoritative for persistence, authorization, and audit logging.
- Deployment footprint is a single operator workstation; CI/CD and downstream services are out of scope.
- Users provision client certificates/keys and CA bundles out-of-band and store them locally.

## Component Responsibilities

- `ud2.cli.*`: Click commands handling argument parsing, profile selection, and user feedback. Includes `release check` and `release push` for release manifest workflows.
- `ud2.config.UDConfig`: Parses INI profiles, resolves certificates, CA bundle, base URL, timeout, and verification flags.
- `ud2.client.UDClient`: Wraps `requests.Session`, binds configuration, exposes CRUD helpers, pagination iterators, and logging.
- `ud2.models.*`: Pydantic definitions for products, versions, repositories, release manifests, pagination envelopes, and response collections.
- `ud2.release`: Release push/sync logic (resolve, ensure, check, apply) for idempotently syncing release manifests.
- External API: Validates auth, enforces RBAC, persists metadata and binary artifacts, returns JSON conforming to shared schema.

## Data Contracts

- Request payloads use the JSON schema defined by `ProductCreate`, `VersionCreate`, `RepositoryCreate`, etc.
- Responses are mapped to `Product`, `Version`, `Repository`, `PaginatedProducts`, and `ResponseVersions`.
- Pagination envelopes include `page`, `limit`, `total_pages`, `data`, ensuring consistent iteration semantics.
- Schema changes on the server must be coordinated with corresponding model updates to avoid validation failures.

## Operational Considerations

- Configuration: CLI defaults to `~/.config/ud2/config.ini`; `--config` and `--env` override location/profile.
- Authentication: Mutual TLS via `requests.Session.cert`, optional CA override using `UDConfig.ca_cert`, fallback to `verify` flag.
- Logging: `UDClient` logs request metadata at debug level (no payloads by default); CLI should expose verbose flags when needed.
- Pagination: `iter_*` helpers lazily traverse pages; `list_*` collects all data in memory—use with caution for large datasets.
- Timeouts/Retries: Timeout configured per profile; retries rely on upstream tooling (none built-in beyond `requests` behavior).
- Error Handling: Distinguish configuration errors, transport issues (`requests` exceptions), HTTP status failures, and validation errors.

## Security & Compliance

- Certificates and private keys remain on the workstation; ensure filesystem permissions restrict access.
- HTTPS with mutual TLS protects data in transit; server identity validated via CA bundle or system trust store.
- CLI should avoid writing sensitive material to stdout/stderr or logs unless explicitly requested.

## Extensibility

- New resources can be supported by adding corresponding Pydantic models, client helpers, and CLI commands.
- Shared pagination/serialization utilities in `ud2.client` and `ud2.models` minimize duplication for future endpoints.
- Config profiles allow targeting multiple environments without code changes.

## Open Questions / Follow-Ups

- Should retries/backoff be standardized rather than left to upstream tooling?
- Do we need offline caching of metadata for audit scenarios?
- What telemetry (if any) should the CLI emit to aid support without leaking sensitive data?

<!-- The end. -->
