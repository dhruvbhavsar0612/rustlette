"""Tests for rustlette.convertors — URL path parameter convertors."""

import uuid

import pytest

from rustlette.convertors import (
    CONVERTOR_TYPES,
    Convertor,
    FloatConvertor,
    IntegerConvertor,
    PathConvertor,
    StringConvertor,
    UUIDConvertor,
    register_url_convertor,
)


class TestStringConvertor:
    def test_regex(self):
        c = StringConvertor()
        assert c.regex == "[^/]+"

    def test_convert(self):
        c = StringConvertor()
        assert c.convert("hello") == "hello"
        assert c.convert("hello%20world") == "hello%20world"

    def test_to_string(self):
        c = StringConvertor()
        assert c.to_string("hello") == "hello"


class TestPathConvertor:
    def test_regex(self):
        c = PathConvertor()
        assert c.regex == ".*"

    def test_convert(self):
        c = PathConvertor()
        assert c.convert("a/b/c") == "a/b/c"

    def test_to_string(self):
        c = PathConvertor()
        assert c.to_string("a/b/c") == "a/b/c"


class TestIntegerConvertor:
    def test_regex(self):
        c = IntegerConvertor()
        # Starlette uses [0-9]+ (no negatives)
        assert c.regex == "[0-9]+"

    def test_convert(self):
        c = IntegerConvertor()
        assert c.convert("42") == 42
        assert isinstance(c.convert("42"), int)

    def test_to_string(self):
        c = IntegerConvertor()
        assert c.to_string(42) == "42"

    def test_convert_zero(self):
        c = IntegerConvertor()
        assert c.convert("0") == 0

    def test_to_string_value_check(self):
        c = IntegerConvertor()
        # int(3.14) succeeds (becomes 3) — no AssertionError, matching Starlette
        assert c.to_string(3.14) == "3"  # type: ignore


class TestFloatConvertor:
    def test_regex(self):
        c = FloatConvertor()
        # The regex has escaped dot: \\. in the raw string
        assert c.regex == r"[0-9]+(\.[0-9]+)?"

    def test_convert(self):
        c = FloatConvertor()
        assert c.convert("3.14") == 3.14
        assert isinstance(c.convert("3.14"), float)

    def test_convert_integer_string(self):
        c = FloatConvertor()
        assert c.convert("42") == 42.0

    def test_to_string(self):
        c = FloatConvertor()
        # Starlette uses %0.20f formatting — result includes trailing precision
        assert c.to_string(3.14) == "3.14000000000000012434"

    def test_to_string_value_check(self):
        c = FloatConvertor()
        # Starlette raises ValueError (not AssertionError) for non-numeric strings
        with pytest.raises(ValueError):
            c.to_string("not_a_float")  # type: ignore


class TestUUIDConvertor:
    def test_regex(self):
        c = UUIDConvertor()
        # Starlette's regex uses [0-9a-fA-F] character class
        assert "[0-9a-fA-F]" in c.regex

    def test_convert(self):
        c = UUIDConvertor()
        uid = "12345678-1234-5678-1234-567812345678"
        result = c.convert(uid)
        assert isinstance(result, uuid.UUID)
        assert str(result) == uid

    def test_to_string(self):
        c = UUIDConvertor()
        uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        assert c.to_string(uid) == "12345678-1234-5678-1234-567812345678"


class TestConvertorTypes:
    """CONVERTOR_TYPES must be a dict of instances (not classes)."""

    def test_contains_standard_types(self):
        assert "str" in CONVERTOR_TYPES
        assert "int" in CONVERTOR_TYPES
        assert "float" in CONVERTOR_TYPES
        assert "path" in CONVERTOR_TYPES
        assert "uuid" in CONVERTOR_TYPES

    def test_values_are_instances(self):
        for name, conv in CONVERTOR_TYPES.items():
            assert isinstance(conv, Convertor), (
                f"{name} should be an instance, got {type(conv)}"
            )


class TestRegisterUrlConvertor:
    def test_register_custom_convertor(self):
        class HexConvertor(Convertor):
            regex = "[0-9a-f]+"

            def convert(self, value: str) -> int:
                return int(value, 16)

            def to_string(self, value: int) -> str:
                return hex(value)[2:]

        register_url_convertor("hex", HexConvertor())
        assert "hex" in CONVERTOR_TYPES
        assert CONVERTOR_TYPES["hex"].convert("ff") == 255
        assert CONVERTOR_TYPES["hex"].to_string(255) == "ff"

        # Cleanup
        del CONVERTOR_TYPES["hex"]
