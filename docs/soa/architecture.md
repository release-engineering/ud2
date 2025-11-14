# UD2 Architecture Overview

## High-Level Description

`ud2` provides a local CLI and Python client (`UDClient`) that orchestrate workflows against the Unified Downloads REST API. Operators configure the CLI via INI profiles that specify endpoints, certificate paths, and timeouts. The CLI parses user commands, loads configuration, instantiates `UDClient`, and issues HTTPS requests (mutual TLS) to the remote API. Responses are validated with Pydantic models before data is returned to the user.

## Diagram

```{mermaid}
flowchart LR
    subgraph "Local Workstation"
        U[User]
        CLI["ud2 CLI (Click)"]
        CFG["Config Loader\nUDConfig + certs"]
        CLIENT["UDClient\nrequests.Session"]
    end

    subgraph "Remote Service"
        API[Unified Downloads REST API]
    end

    U -->|Commands| CLI
    CLI -->|Reads profiles| CFG
    CFG -->|UDConfig instance| CLIENT
    CLI -->|Invokes methods| CLIENT
    CLIENT -->|HTTPS mTLS| API
    API -->|JSON responses| CLIENT
    CLIENT -->|Pydantic models| CLI
    CLI -->|Output/logs| U
```

## Component Responsibilities

- User/CLI: Accepts commands, handles input validation, displays output or errors.
- Configuration loader: Reads profile INI files, resolves paths for certificates, CA bundle, and base URL.
- `UDClient`: Wraps `requests.Session`, enforces headers, mutual TLS setup, pagination helpers, and request logging.
- Unified Downloads API: Authoritative source of products, versions, repository metadata, and access control.

## Trust Zones & Interfaces

- Local workstation: CLI, config files, certificates, private keys.
- Remote service: Unified Downloads API.
- Boundary: HTTPS with mutual TLS; CLI never stores API credentials beyond the local certificate material.
- Logging defaults to local machine; sensitive payloads should be redacted when necessary.

## Operational Notes

- Timeouts, retries, and verification flags are configurable via `UDConfig`.
- CLI commands rely on `ud2.models.*` for schema validation; any contract drift will surface as validation errors.
- Errors from the API are surfaced to the user with HTTP status context; CLI should distinguish transport vs. business logic failures.

<!-- The end. -->
