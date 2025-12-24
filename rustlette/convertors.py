"""
Path parameter convertors for route parsing
"""

import re
import typing
import uuid
from typing import Any, Dict, Type


class Convertor:
    """Base class for path parameter convertors."""

    regex = ""

    def convert(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        raise NotImplementedError  # pragma: no cover

    def to_string(self, value: Any) -> str:
        """Convert value back to string for URL generation."""
        return str(value)


class StringConvertor(Convertor):
    """String convertor (default)."""

    regex = "[^/]+"

    def convert(self, value: str) -> str:
        return value

    def to_string(self, value: Any) -> str:
        value = str(value)
        assert "/" not in value, "May not contain path separators"
        assert value, "Must not be empty"
        return value


class PathConvertor(Convertor):
    """Path convertor (allows forward slashes)."""

    regex = ".*"

    def convert(self, value: str) -> str:
        return value

    def to_string(self, value: Any) -> str:
        return str(value)


class IntegerConvertor(Convertor):
    """Integer convertor."""

    regex = r"-?\d+"

    def convert(self, value: str) -> int:
        return int(value)

    def to_string(self, value: Any) -> str:
        value = int(value)
        return str(value)


class FloatConvertor(Convertor):
    """Float convertor."""

    regex = r"-?\d+(\.\d+)?"

    def convert(self, value: str) -> float:
        return float(value)

    def to_string(self, value: Any) -> str:
        value = float(value)
        return str(value)


class UUIDConvertor(Convertor):
    """UUID convertor."""

    regex = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def convert(self, value: str) -> uuid.UUID:
        return uuid.UUID(value)

    def to_string(self, value: Any) -> str:
        return str(value)


class SlugConvertor(Convertor):
    """Slug convertor (alphanumeric + hyphens/underscores)."""

    regex = r"[-a-zA-Z0-9_]+"

    def convert(self, value: str) -> str:
        return value

    def to_string(self, value: Any) -> str:
        value = str(value)
        assert re.match(r"^[-a-zA-Z0-9_]+$", value), (
            "Must be alphanumeric with hyphens/underscores"
        )
        return value


# Registry of available convertors
CONVERTORS: Dict[str, Type[Convertor]] = {
    "str": StringConvertor,
    "string": StringConvertor,
    "path": PathConvertor,
    "int": IntegerConvertor,
    "integer": IntegerConvertor,
    "float": FloatConvertor,
    "uuid": UUIDConvertor,
    "slug": SlugConvertor,
}


def get_convertor(convertor_type: str) -> Convertor:
    """Get a convertor instance by type name."""
    if convertor_type not in CONVERTORS:
        raise ValueError(f"Unknown convertor type: {convertor_type}")

    convertor_class = CONVERTORS[convertor_type]
    return convertor_class()


def register_convertor(name: str, convertor_class: Type[Convertor]) -> None:
    """Register a custom convertor."""
    CONVERTORS[name] = convertor_class
