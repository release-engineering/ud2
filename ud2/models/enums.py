"""
Enumerations representing canonical UD model values.
"""

from enum import Enum
from typing import Any, Optional, Type, TypeVar, Union


__all__ = (
    'Architecture',
    'ContentType',
    'Visibility',
    'EnumValue',
    'coerce_enum',
)


class ContentType(str, Enum):
    """
    Content type classification for repository files.
    """

    DISTRIBUTION = 'DISTRIBUTION'
    BUGFIX = 'BUGFIX'
    SECURITY = 'SECURITY'


class Visibility(str, Enum):
    """
    Visibility markers describing product version exposure.
    """

    VISIBLE = 'visible'
    HIDDEN = 'hidden'
    INTERNAL = 'internal'
    DEPRECATED = 'deprecated'


class Architecture(str, Enum):
    """
    Known architecture identifiers supported by UD resources.
    """

    X86_64 = 'x86_64'
    AARCH64 = 'aarch64'
    PPC64LE = 'ppc64le'
    S390X = 's390x'


EnumValue = TypeVar('EnumValue', bound=Enum)


def coerce_enum(
        enum_cls: Type[EnumValue],
        value: Optional[Any]) -> Optional[Union[EnumValue, str]]:
    """
    Attempt to coerce a value into the requested enum class.

    The function preserves unknown strings so newer backend values continue to
    round-trip even if this client has not been updated yet.
    """

    if value is None or isinstance(value, enum_cls):
        return value

    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return value

    if isinstance(value, enum_cls):
        return value

    return str(value)


# The end.
