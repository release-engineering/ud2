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

Using direct from the checkout (requires uv)

```bash
uv venv --system-site-packages
uv pip install -e .  # install in editable mode
uv run ud2 --help
```

Install from source (requires Python 3.7+):

```bash
python3 -m pip install --user .
ud2 --help
```

By default the CLI reads configuration from `~/.config/ud2/config.ini`. Override
with `--config` and select profiles with `--env`.

- Create a product: `ud2 product create --yaml-file product.yaml` or `ud2 product create --name "X" --eng-id 123`
- Add a version: `ud2 version create <product-id> --yaml-file version.yaml` or `ud2 version create <product-id> --version 1.0`
- Attach release files: `ud2 repository create <version-id> --yaml-file repo.yaml` or `ud2 repository create <version-id> --file ./artifact.iso --description "Title"`
- Check or push a full release: `ud2 release check release.yaml`, `ud2 release push release.yaml`
- Build a release manifest from scratch: `ud2 release init release.yaml --product-id 1 --version 1.0`, then `ud2 release add release.yaml --file ./artifact.iso --desc "Title"` (use `edit` and `remove` to modify)

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
