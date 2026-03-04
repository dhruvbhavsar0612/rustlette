"""Tests for rustlette.exceptions — HTTPException and WebSocketException."""

import pytest

from rustlette.exceptions import HTTPException, WebSocketException


class TestHTTPException:
    def test_basic_creation(self):
        exc = HTTPException(status_code=404)
        assert exc.status_code == 404
        # Starlette auto-fills detail from HTTP status phrase
        assert exc.detail == "Not Found"

    def test_with_detail_string(self):
        exc = HTTPException(status_code=400, detail="Bad request data")
        assert exc.status_code == 400
        assert exc.detail == "Bad request data"

    def test_with_detail_dict(self):
        detail = {"error": "validation_failed", "fields": ["name"]}
        exc = HTTPException(status_code=422, detail=detail)
        assert exc.detail == detail

    def test_with_headers(self):
        headers = {"X-Custom": "value"}
        exc = HTTPException(status_code=403, headers=headers)
        assert exc.headers == headers

    def test_default_headers_none(self):
        exc = HTTPException(status_code=500)
        assert exc.headers is None

    def test_repr(self):
        exc = HTTPException(status_code=404, detail="Not Found")
        r = repr(exc)
        assert "404" in r
        assert "Not Found" in r

    def test_is_exception(self):
        exc = HTTPException(status_code=500)
        assert isinstance(exc, Exception)

    def test_status_code_attribute(self):
        exc = HTTPException(status_code=418, detail="I'm a teapot")
        assert exc.status_code == 418

    def test_auto_detail_from_status(self):
        # detail auto-fills from HTTP status phrase per Starlette 0.50.0
        exc = HTTPException(status_code=404)
        assert exc.detail == "Not Found"


class TestWebSocketException:
    def test_basic_creation(self):
        exc = WebSocketException(code=1008)
        assert exc.code == 1008
        # Starlette default reason is "" (empty string), not None
        assert exc.reason == ""

    def test_with_reason(self):
        exc = WebSocketException(code=1008, reason="Policy violation")
        assert exc.code == 1008
        assert exc.reason == "Policy violation"

    def test_is_exception(self):
        exc = WebSocketException(code=1000)
        assert isinstance(exc, Exception)

    def test_default_reason_none(self):
        exc = WebSocketException(code=1003)
        # Starlette default reason is "" (empty string), not None
        assert exc.reason == ""
