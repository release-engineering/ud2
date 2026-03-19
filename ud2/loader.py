# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, see <http://www.gnu.org/licenses/>.

"""
Working with YAML
"""

import sys
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Type, Union

import yaml
from pydantic import BaseModel


def load_yaml(
        path: Union[str, Path],
        model: Optional[Type[BaseModel]] = None) -> Any:
    """
    Load YAML file content from the given path.
    """

    path = Path(path)
    with path.open('r', encoding='utf-8') as fd:
        data = yaml.safe_load(fd)

    if model:
        return model.model_validate(data)
    return data


class PrettyYAML(yaml.Dumper):
    """
    Custom YAML dumper for pretty-printing.

    It's not as easy as making JSON pretty, but at least it's
    possible.
    """

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

    def represent_scalar(self, tag, value, style=None):
        if isinstance(value, str) and '\n' in value:
            # For multi-line strings, use the literal block style ('|')
            return super().represent_scalar(tag, value, style='|')
        else:
            return super().represent_scalar(tag, value, style='')


def _to_primitive(value: Any) -> Any:
    """
    Convert models and other custom objects into basic Python types.
    """

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, BaseModel):
        return _to_primitive(value.model_dump(by_alias=False))

    if isinstance(value, dict):
        return {key: _to_primitive(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_to_primitive(item) for item in value]

    return value


def pretty_yaml(doc: Any, out=sys.stdout, **opts) -> None:
    """
    Pretty-print a single YAML object to the given output stream.


    :param doc: The YAML document to pretty-print
    :param out: The output stream to write to
    :param comments: Whether to include comments
    :param opts: Additional options to pass to the yaml.dump function
    """

    doc = _to_primitive(doc)

    params = {
        'default_flow_style': False,
        'sort_keys': False,
        'explicit_start': False,
    }
    params.update(opts)
    return yaml.dump(doc, Dumper=PrettyYAML, stream=out, **params)  # type: ignore


# The end.
