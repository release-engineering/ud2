

import sys
from dataclasses import dataclass
from functools import wraps
from itertools import zip_longest
from operator import itemgetter
from typing import (Any, Callable, List, Optional, Sequence, TextIO, Tuple,
                    Union)

from pathlib import Path
from click import ClickException, Context, echo, pass_context
from pydantic import ValidationError
from requests import HTTPError
from yaml import YAMLError

from ..client import UDClient
from ..config import UDConfig, ConfigurationError


@dataclass
class CLIState:
    """
    Container for shared CLI state.

    :param client: Configured UDClient instance.
    :param yaml_output: When True, render results as YAML.
    :param debug: Indicates whether debug mode is enabled.
    """

    config: UDConfig
    client: UDClient
    yaml_output: bool
    debug: bool


def build_cli_state(
        config_path: str,
        environment: Optional[str] = None,
        yaml_output: bool = False,
        debug: bool = False) -> CLIState:
    """
    Build the CLI state object.
    """

    # This is mostly a separate function so that we can mock its imported
    # version in testing. Otherwise it could just bein main() directly.

    path = Path(config_path).expanduser().resolve()

    config = UDConfig.from_file(path, environment)

    client = UDClient(config=config)

    return CLIState(
        config=config,
        client=client,
        yaml_output=yaml_output,
        debug=debug,
    )


def pass_state(function: Callable[..., Any]) -> Callable[..., Any]:

    @wraps(function)
    @pass_context
    def wrapper(ctx: Context, *args: Any, **kwargs: Any) -> Any:
        return function(ctx.obj, *args, **kwargs)
    return wrapper


def catchall(function: Callable[..., Any]) -> Callable[..., Any]:

    @wraps(function)
    def wrapper(state: CLIState, *args: Any, **kwargs: Any) -> Any:

        if state.debug:
            # when debug mode is set, we let all exceptions propagate
            return function(state, *args, **kwargs)

        try:
            return function(state, *args, **kwargs)

        except ClickException:
            raise

        except KeyboardInterrupt:
            echo("\n[Interrupted]", err=True)
            return 130

        except ConfigurationError as e:
            echo(f"Configuration Error: {e}", err=True)
            return 1

        except YAMLError as e:
            # YAML parsing errors - show formatted error with file context
            echo(f"YAML Error:\n{e}", err=True)
            return 1

        except ValidationError as e:
            # Validation errors - show formatted error with object and file context
            echo(f"Validation Error:\n{e}", err=True)
            return 1

        except HTTPError as exc:
            response = getattr(exc, "response", None)
            if response is None:
                raise ClickException(f"HTTP error: {exc}") from exc

            body = getattr(response, "text", "")
            snippet = body.strip().splitlines()
            preview = snippet[0] if snippet else ""
            if len(preview) > 200:
                preview = preview[:197] + "..."
            message = f"HTTP {response.status_code}: {preview}" if preview else f"HTTP {response.status_code}"
            echo(f"HTTP Error: {message}", err=True)
            return 1

        except OSError as e:
            echo(f"OS Error: {e}", err=True)
            return 1

        except Exception as exc:
            echo(f"Unexpected Error: {exc}", err=True)
            # print the traceback
            import traceback
            traceback.print_exc()
            raise

    return wrapper


def tabulate(
        headings: Sequence[str],
        data: Any,
        key: Union[Callable[[Any], Tuple], List, Tuple] = None,
        sorting: int = 0,
        quiet: Optional[bool] = None,
        out: TextIO = None):
    """
    Prints tabulated data, with the given headings.

    This function is not resilient -- the headings and data must have
    the same count of rows, nothing will inject empty values.

    Output will be configured to set the columns to their maximum
    width necessary for the longest value from all the rows or the
    heading.

    :param headings: The column titles

    :param data: Rows of data

    :param key: Transformation to apply to each row of data to get the
      actual individual columns. Should be a unary function. Default,
      data is iterated as-is.

    :param sorting: Whether data rows should be sorted and in what
      direction. 0 for no sorting, 1 for ascending, -1 for
      descending. If key is specified, then sorting will be based on
      those transformations. Default, no sorting.

    :param quiet: Whether to print headings or not. Default, only print
      headings if out is a TTY device.

    :param out: Stream to write output to. Default, `sys.stdout`
    """
    # Adapted from koji-smoky-dingo, which is written by the same author and
    # licensed under the GPLv3
    # https://github.com/obriencj/koji-smoky-dingo

    if out is None:
        out = sys.stdout

    # The quiet setting has three values. True meaning no header,
    # False meaning header, and None meaning no header if out is not a
    # TTY.
    if quiet is None:
        quiet = not out.isatty()

    if key is not None:
        if isinstance(key, (tuple, list)):
            key = itemgetter(*key)
        elif not callable(key):
            key = itemgetter(key)

        # convert data to a list, and apply the key if necessary to find
        # the real columns
        data = map(key, data)

    if sorting:
        data = sorted(data, reverse=(sorting < 0))
    else:
        data = list(data)

    # now we need to compute the maximum width of each columns
    if data:
        widths = [max(len(str(v)) for v in col)
                  for col in zip_longest(*data, fillvalue="")]
    else:
        widths = []

    if headings and not quiet:
        widths = [max(w or 0, len(h or "")) for w, h in
                  zip_longest(widths, headings)]

    # now we create the format string based on the max width of each
    # column plus some spacing.
    fmt = "  ".join(f"{{{c}!s:<{w}}}" for (c, w) in enumerate(widths))

    if headings and not quiet:
        echo(fmt.format(*headings), file=out)
        echo("  ".join(("-" * h) for h in widths), file=out)

    for row in data:
        echo(fmt.format(*row), file=out)


# def _format_validation_error(exc: ValidationError) -> str:
#     """
#     Format a Pydantic validation error for presentation to end users.
#     """

#     entries: List[str] = []

#     for location_parts, message in _iter_validation_entries(exc.errors()):
#         location = ".".join(str(item) for item in location_parts if item != '')
#         if not location:
#             location = "<root>"
#         entries.append(f"{location}: {message}")

#     header = "Validation failed:"
#     bullet_list = "\n".join(f"- {entry}" for entry in entries)
#     return f"{header}\n{bullet_list}"


# def _iter_validation_entries(
#         errors: Sequence[Dict[str, Any]],
#         prefix: Tuple[Any, ...] = ()) -> Iterable[Tuple[Tuple[Any, ...], str]]:
#     """
#     Flatten validation errors, yielding (location, message) tuples.
#     """

#     for error in errors:
#         loc = prefix + tuple(error.get("loc", ()))
#         ctx = error.get("ctx")

#         nested_errors = None
#         if isinstance(ctx, dict):
#             nested_errors = ctx.get("errors")
#             if nested_errors is None:
#                 nested_error = ctx.get("error")
#                 if isinstance(nested_error, ValidationError):
#                     nested_errors = nested_error.errors()
#                 elif isinstance(nested_error, list):
#                     nested_errors = nested_error

#         message = error.get("msg", "")

#         if error.get("type") == "model_type":
#             fragments = [message]
#             if isinstance(ctx, dict):
#                 class_name = ctx.get("class_name")
#             else:
#                 class_name = None
#             if class_name:
#                 fragments.append(f"(expected {class_name})")
#             if "input" in error:
#                 input_value = error["input"]
#                 fragments.append(f"(received {type(input_value).__name__})")
#             message = " ".join(fragments)

#         if nested_errors is not None:
#             yield loc, message
#             yield from _iter_validation_entries(nested_errors, loc)
#             continue

#         yield loc, message


# The end.
