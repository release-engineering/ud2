# ud2

`ud2` (Unified Downloads v2) is a release-engineering toolkit for interacting with
the Unified Downloads REST API. It provides:

- A Click-powered CLI for managing products, product versions, and repository files.
- A typed Python client (`ud2.client.UDClient`) for automation or integration with
  other tooling.
- Validated Pydantic models covering the API schema.

The project targets API-driven distribution publishing workflows and aims to make
common release tasks scriptable, auditable, and easy to repeat.

## Quick Start

Install from source (requires Python 3.7+):

```bash
python3 -m pip install --user .
ud2 --help
```

By default the CLI reads configuration from `~/.config/ud2/config.ini`. Override
with `--config` and select profiles with `--env`.

- Create a product: `ud2 products create --file product.yaml`
- Add a version: `ud2 versions create <product-id> --file version.yaml`
- Attach release files: `ud2 repositories create <version-id> --file repo.yaml`

See `docs/cli_quickstart.rst` for detailed, copy/paste friendly walkthroughs and
`docs/configuration_reference.rst` for configuration file guidance.

For programmatic access, build a client from configuration:

```python
from ud2.client import UDClient
from ud2.config import load_config

config = load_config(pathlib.Path("~/.config/ud2/config.ini").expanduser(), "default")
client = UDClient(config=config)
products = client.list_products()
```

## Development Workflow

All developer commands are exposed via the Makefile and ultimately run through
`tox`:

- Run unit tests: `make test`
- Lint with flake8: `make flake8`
- Build distributions: `make build`
- Install wheel into user site-packages: `make install`
- Produce a source archive: `make archive`

The primary test suite uses `pytest` to execute `unittest`-based test cases so
it can take advantage of pytest fixtures and reporting while keeping tests in
the standard library style.

## Documentation

- CLI quickstart scenarios: `docs/cli_quickstart.rst`
- Configuration reference: `docs/configuration_reference.rst`
- Auto-generated API reference (Swagger): `reference/swagger.yaml`

Sphinx documentation will be added under `docs/` in a future milestone.

## License

This project is licensed under the GNU General Public License v3.0. See
`LICENSE` for the full text.
