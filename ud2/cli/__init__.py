"""
UDv2 Command Line Interface package.

::author: Christopher O'Brien <cobrien@redhat.com>
::license: GPLv3
"""


import functools
import logging
import pathlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Type, Union

import click
import requests
import yaml
from pydantic import BaseModel, ValidationError

from .. import __version__
from ..config import ConfigurationError, load_config
from ..client import UDClient


DEFAULT_CONFIG_PATH = pathlib.Path("~/.config/ud2/config.ini")
@dataclass
class CLIState:
    """
    Container for shared CLI state.

    :param client: Configured UDClient instance.
    :param yaml_output: When True, render results as YAML.
    :param debug: Indicates whether debug mode is enabled.
    """

    client: UDClient
    yaml_output: bool
    debug: bool


pass_state = click.make_pass_decorator(CLIState)


def _debug_enabled() -> bool:
    """
    Determine whether the current Click context has debug enabled.
    """

    context = click.get_current_context(silent=True)

    if context is None:
        return False

    state = context.obj

    if isinstance(state, CLIState):
        return state.debug

    return getattr(state, "debug", False)


def with_error_handling(function: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorate a command handler to translate common exceptions into Click failures.
    """

    @functools.wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except click.ClickException:
            raise
        except Exception as exc:
            if _debug_enabled():
                raise
            raise _as_click_exception(exc)

    return wrapper


def invoke_with_handling(operation: Callable[[], Any]) -> Any:
    """
    Execute an operation while converting known exceptions into Click failures.
    """

    try:
        return operation()
    except click.ClickException:
        raise
    except Exception as exc:
        if _debug_enabled():
            raise
        raise _as_click_exception(exc)


def resolve_config_path(path_value: str) -> pathlib.Path:
    """
    Resolve a configuration path to an absolute Path instance.

    :param path_value: Path supplied by the user.
    :returns: Resolved absolute path.
    """

    path = pathlib.Path(path_value).expanduser()
    return path.resolve()


def load_yaml_payload(path_value: str) -> Dict[str, Any]:
    """
    Load a YAML payload from disk.

    :param path_value: Path to the YAML file.
    :returns: Parsed dictionary representing the payload.
    """

    path = pathlib.Path(path_value).expanduser().resolve()

    if not path.is_file():
        raise click.ClickException(f"Payload file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise click.ClickException(f"Unable to parse YAML payload: {exc}") from exc

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise click.ClickException("Payload file must describe a YAML mapping.")

    return data


def load_model(path_value: str, model_type: Type[BaseModel]) -> BaseModel:
    """
    Load and validate a payload file into the requested Pydantic model.

    :param path_value: Path pointing to the YAML payload.
    :param model_type: Model type used for validation.
    :returns: Instantiated model.
    """

    payload = load_yaml_payload(path_value)

    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        if _debug_enabled():
            raise
        message = _format_validation_error(exc)
        raise click.ClickException(message)


def emit(data: Any, state: CLIState) -> None:
    """
    Render data using the configured output mode.
    """

    normalized = _to_primitive(data)

    if state.yaml_output:
        rendered = yaml.safe_dump(normalized, sort_keys=False)
        click.echo(rendered)
        return

    click.echo(_render_friendly(normalized))


def _to_primitive(value: Any) -> Any:
    """
    Convert models and other custom objects into basic Python types.
    """

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, BaseModel):
        return _to_primitive(value.model_dump())

    if isinstance(value, dict):
        return {key: _to_primitive(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_to_primitive(item) for item in value]

    return value


def _render_friendly(data: Any) -> str:
    """
    Render friendly output for the CLI.
    """

    if data is None:
        return "Success."

    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        table = _render_table(data["data"])
        meta_lines = [
            f"{key.title()}: {value}"
            for key, value in data.items()
            if key != "data"
        ]
        if not meta_lines:
            return table

        return "\n".join([table, "", *meta_lines])

    if isinstance(data, list):
        return _render_table(data)

    if isinstance(data, dict):
        return "\n".join(
            f"{key.title()}: {value}"
            for key, value in data.items()
        )

    return str(data)


def _render_table(rows: Sequence[Any]) -> str:
    """
    Render a list of dictionaries into a simple table.
    """

    if not rows:
        return "No items found."

    prepared: List[Dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            prepared.append(row)
        elif isinstance(row, BaseModel):
            prepared.append(row.model_dump())
        else:
            prepared.append({"value": row})

    headers = sorted({key for row in prepared for key in row.keys()})
    column_widths = {
        header: max(len(header), *(len(str(row.get(header, ""))) for row in prepared))
        for header in headers
    }

    def render_row(values: Iterable[str]) -> str:
        parts: List[str] = []
        for header, value in zip(headers, values):
            width = column_widths[header]
            parts.append(f"{value:<{width}}")
        return "  ".join(parts)

    header_line = render_row(headers)
    rule_line = render_row("-" * column_widths[header] for header in headers)

    data_lines = [
        render_row(str(row.get(header, "")) for header in headers)
        for row in prepared
    ]

    return "\n".join([header_line, rule_line, *data_lines])


def _as_click_exception(exc: Exception) -> click.ClickException:
    """
    Convert known exception types into ClickException instances.
    """

    if isinstance(exc, click.ClickException):
        return exc

    if isinstance(exc, ConfigurationError):
        return click.ClickException(str(exc))

    if isinstance(exc, ValidationError):
        message = _format_validation_error(exc)
        return click.ClickException(message)

    if isinstance(exc, requests.HTTPError):
        response = getattr(exc, "response", None)
        if response is None:
            return click.ClickException(f"HTTP error: {exc}")

        body = getattr(response, "text", "")
        snippet = body.strip().splitlines()
        preview = snippet[0] if snippet else ""
        if len(preview) > 200:
            preview = preview[:197] + "..."
        message = f"HTTP {response.status_code}: {preview}" if preview else f"HTTP {response.status_code}"
        return click.ClickException(message)

    if isinstance(exc, OSError):
        return click.ClickException(str(exc))

    return click.ClickException(str(exc))


def _format_validation_error(exc: ValidationError) -> str:
    """
    Format a Pydantic validation error for presentation to end users.
    """

    entries: List[str] = []

    for location_parts, message in _iter_validation_entries(exc.errors()):
        location = ".".join(str(item) for item in location_parts if item != '')
        if not location:
            location = "<root>"
        entries.append(f"{location}: {message}")

    header = "Validation failed:"
    bullet_list = "\n".join(f"- {entry}" for entry in entries)
    return f"{header}\n{bullet_list}"


def _iter_validation_entries(
        errors: Sequence[Dict[str, Any]],
        prefix: Tuple[Any, ...] = ()) -> Iterable[Tuple[Tuple[Any, ...], str]]:
    """
    Flatten validation errors, yielding (location, message) tuples.
    """

    for error in errors:
        loc = prefix + tuple(error.get("loc", ()))
        ctx = error.get("ctx")

        nested_errors = None
        if isinstance(ctx, dict):
            nested_errors = ctx.get("errors")
            if nested_errors is None:
                nested_error = ctx.get("error")
                if isinstance(nested_error, ValidationError):
                    nested_errors = nested_error.errors()
                elif isinstance(nested_error, list):
                    nested_errors = nested_error

        message = error.get("msg", "")

        if error.get("type") == "model_type":
            fragments = [message]
            if isinstance(ctx, dict):
                class_name = ctx.get("class_name")
            else:
                class_name = None
            if class_name:
                fragments.append(f"(expected {class_name})")
            if "input" in error:
                input_value = error["input"]
                fragments.append(f"(received {type(input_value).__name__})")
            message = " ".join(fragments)

        if nested_errors is not None:
            yield loc, message
            yield from _iter_validation_entries(nested_errors, loc)
            continue

        yield loc, message


def _configure_logging(debug: bool) -> None:
    """
    Configure logging based on the debug flag.
    """

    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--config",
    "config_path",
    type=str,
    default=str(DEFAULT_CONFIG_PATH),
    help="Path to the ud2 configuration file.",
)
@click.option(
    "--env",
    "environment",
    type=str,
    default="default",
    help="Environment profile to load from the configuration file.",
)
@click.option(
    "--yaml/--no-yaml",
    "yaml_output",
    default=False,
    help="Render results as YAML instead of friendly text.",
)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Enable verbose logging.",
)
@click.pass_context
def cli(
        ctx: click.Context,
        config_path: str,
        environment: str,
        yaml_output: bool,
        debug: bool) -> None:
    """
    ud2 command line interface entry point.
    """

    _configure_logging(debug)

    state = _build_state(config_path, environment, yaml_output, debug)

    ctx.obj = state


def _build_state(
        config_path: str,
        environment: str,
        yaml_output: bool,
        debug: bool) -> CLIState:
    """
    Build the CLI state object used by command handlers.
    """

    path = resolve_config_path(config_path)

    try:
        config = load_config(path, environment)
    except ConfigurationError as exc:
        raise click.ClickException(str(exc))

    client = UDClient(config=config)

    return CLIState(
        client=client,
        yaml_output=yaml_output,
        debug=debug,
    )


def _register_resource_commands() -> None:
    """
    Attach resource command groups to the CLI.
    """

    from .product import register as register_product
    from .repository import register as register_repository
    from .version import register as register_version

    for register in (register_product, register_repository, register_version):
        register(cli)


_register_resource_commands()


def main() -> None:
    """
    Entrypoint for console_scripts.
    """

    cli(obj=None)


# The end.
