# Stage 3: Implement CLI Workflows

## Objective

Build a Click-based CLI in `ud2/cli.py` that orchestrates configuration resolution, initializes `UDClient`, and exposes user-friendly commands for managing products, product versions, and repositories. Support both YAML and "friendly" human-readable output modes for list and detail operations.

## Entry Point & Structure

- Entry function `main()` exported via `console_scripts` entry point (`ud2 = ud2.cli:main`).
- Use a top-level Click group `@click.group()` named `cli`.
- Provide global options:
  - `--config PATH` (default: `~/.config/ud2/config.ini`)
  - `--env TEXT` (default: `default`)
  - `--output [friendly|yaml]` (default: `friendly`)
  - `--debug / --no-debug` to toggle verbose logging.
- Resolve configuration once in a `click.pass_context` decorated initializer that stores `UDClient` and the chosen output mode in `ctx.obj`.

## Command Layout

```
ud2 products list [--page INT --limit INT --sort asc|desc]
ud2 products get <product-id>
ud2 products create --file payload.yaml
ud2 products update <product-id> --file payload.yaml
ud2 products delete <product-id>

ud2 versions list <product-id>
ud2 versions get <product-id> <version-id>
ud2 versions create <product-id> --file payload.yaml
ud2 versions update <product-id> <version-id> --file payload.yaml
ud2 versions delete <product-id> <version-id>

ud2 repositories list <product-version-id> [--page INT --limit INT --sort asc|desc]
ud2 repositories get <product-version-id> <repository-id>
ud2 repositories create <product-version-id> --file payload.yaml
ud2 repositories update <product-version-id> <repository-id> --file payload.yaml
ud2 repositories delete <product-version-id> <repository-id>
```

- Use nested Click groups (`@cli.group()`) for `products`, `versions`, and `repositories`.
- For create/update actions, load payloads from YAML via `yaml.safe_load`, validate with the Stage 1 Pydantic create models, and pass model instances to the client.
- For list commands, accept pagination flags and forward them to the client request.

## Output Modes

- Implement an `emit(data, ctx)` helper that checks `ctx.obj["output"]`.
- `yaml` mode: serialize with `yaml.safe_dump(data, sort_keys=False)`.
- `friendly` mode:
  - For lists, print tabular summaries using `tabulate`-like formatting or manual string formatting (prefer avoiding new dependencies; simple column widths suffice).
  - For detail views, print key/value pairs with labels (e.g., `Name: Red Hat Enterprise Linux`).
- Ensure CLI gracefully handles `None` responses (e.g., delete operations) by acknowledging success with concise text.

## Error Handling

- Catch `UDConfig` `ConfigurationError` and surface a Click-friendly message (`click.ClickException`).
- Wrap HTTP errors (`requests.HTTPError`) to present status code and body snippet.
- Validate file paths and payload schema; present validation errors (`pydantic.ValidationError`) with actionable messaging.

## Testing Considerations

- Plan unit tests that exercise each command using Click's `CliRunner`, injecting a fake client.
- Mock file interactions for payload-based commands.
- Verify both output modes via fixtures/snapshots.

## Deliverables

- New `ud2/cli.py` implementing the grouping and commands above.
- Helper utilities for loading payloads and rendering output.
- No direct changes to `ud2/client.py` or models in this stage (consume outputs from previous stages).

## Open Questions

- Determine whether to expose additional filters (e.g., search) once the API supports them.
- Decide if repository payloads should allow inline file uploads or only metadata creation.

<!-- The end. -->
