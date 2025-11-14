# UD2 Data Flow (List Products)

This diagram captures the `ud2 products list` command, which exercises configuration resolution, CLI parsing, `UDClient` pagination helpers, HTTPS transport, and model validation.

```{mermaid}
sequenceDiagram
    participant User
    participant ["CLI as ud2 CLI (Click)"]
    participant ["CFG as Config Loader<br/>UDConfig"]
    participant ["Client as UDClient<br/>requests.Session"]
    participant [API as Unified Downloads API]

    User->>CLI: Run `ud2 products list`
    CLI->>CFG: Load profile config<br/>paths, certs, base_url, timeout
    CFG-->>CLI: UDConfig object
    CLI->>Client: Instantiate with UDConfig<br/>set mTLS certs, headers, timeout
    CLI->>Client: call `iter_products(limit=None)`
    loop Paginated fetch
        Client->>API: HTTPS GET /products?page=N<br/>with certificates
        API-->>Client: JSON payload<br/>{ page, data, total_pages, ... }
        Client->>Client: Validate with `PaginatedProducts`
        Client-->>CLI: `Product` model instances
    end
    CLI-->>User: Render table/list output
```

## Notes

- Authentication: Mutual TLS using user-supplied client certificate and key; optional CA bundle overrides.
- Validation: Responses parsed through Pydantic models in `ud2.models.product` and `ud2.models.pagination`.
- Error pathways:
  - Config errors (missing profile, bad cert paths) stop before network calls.
  - Transport failures propagate `requests` exceptions; CLI surfaces user-facing message.
  - Schema mismatches raise Pydantic errors, signaling contract drift with the API.

<!-- The end. -->
