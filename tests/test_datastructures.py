"""Tests for rustlette.datastructures — URL, Headers, QueryParams, State, etc."""

import io

import pytest

from rustlette.datastructures import (
    URL,
    Address,
    CommaSeparatedStrings,
    FormData,
    Headers,
    ImmutableMultiDict,
    MultiDict,
    MutableHeaders,
    QueryParams,
    Secret,
    State,
    UploadFile,
    URLPath,
)


class TestURL:
    def test_basic_url(self):
        url = URL("https://example.com/path?q=1#frag")
        assert url.scheme == "https"
        assert url.hostname == "example.com"
        assert url.path == "/path"
        assert url.query == "q=1"
        assert url.fragment == "frag"

    def test_url_str(self):
        url = URL("https://example.com/path")
        assert str(url) == "https://example.com/path"

    def test_url_repr(self):
        url = URL("https://example.com")
        assert "example.com" in repr(url)

    def test_url_eq(self):
        assert URL("http://example.com") == URL("http://example.com")

    def test_url_components(self):
        url = URL("http://user:pass@host:8080/path?q=1")
        assert url.port == 8080
        assert url.netloc == "user:pass@host:8080"

    def test_url_replace(self):
        url = URL("http://example.com/path")
        new = url.replace(scheme="https")
        assert str(new).startswith("https://")

    def test_url_from_scope(self):
        scope = {
            "type": "http",
            "scheme": "https",
            "server": ("example.com", 443),
            "path": "/test",
            "query_string": b"a=1",
            "headers": [],
        }
        url = URL(scope=scope)
        assert url.path == "/test"
        assert url.scheme == "https"


class TestURLPath:
    def test_basic(self):
        path = URLPath("/users/42")
        assert str(path) == "/users/42"
        # URLPath is a str subclass — no .path attribute in Starlette

    def test_with_protocol_and_host(self):
        path = URLPath("/users/42", protocol="http", host="example.com")
        url = path.make_absolute_url("http://example.com")
        assert "example.com" in str(url)


class TestSecret:
    def test_repr_hides_value(self):
        s = Secret("my-secret-key")
        assert "my-secret-key" not in repr(s)
        assert "Secret" in repr(s)
        assert "**********" in repr(s)

    def test_str_reveals_value(self):
        s = Secret("my-secret-key")
        assert str(s) == "my-secret-key"

    def test_bool(self):
        assert bool(Secret("value"))
        assert not bool(Secret(""))


class TestCommaSeparatedStrings:
    def test_basic(self):
        css = CommaSeparatedStrings("a, b, c")
        assert list(css) == ["a", "b", "c"]

    def test_from_list(self):
        css = CommaSeparatedStrings(["x", "y", "z"])
        assert list(css) == ["x", "y", "z"]

    def test_repr(self):
        css = CommaSeparatedStrings("a, b")
        r = repr(css)
        assert "a" in r and "b" in r

    def test_str(self):
        css = CommaSeparatedStrings("a, b, c")
        # Starlette's __str__ returns repr-like format with quoted items
        assert str(css) == "'a', 'b', 'c'"


class TestAddress:
    def test_named_tuple(self):
        addr = Address(host="127.0.0.1", port=8000)
        assert addr.host == "127.0.0.1"
        assert addr.port == 8000
        assert addr[0] == "127.0.0.1"
        assert addr[1] == 8000


class TestHeaders:
    def test_from_raw(self):
        raw = [(b"content-type", b"text/html"), (b"x-custom", b"value")]
        h = Headers(raw=raw)
        assert h["content-type"] == "text/html"
        assert h["x-custom"] == "value"

    def test_case_insensitive(self):
        """Headers lookup lowercases the key, so it works when raw keys are already lowercase
        (which is the norm in ASGI / HTTP/2). Mixed-case raw keys won't match lowercase lookups."""
        raw = [(b"content-type", b"text/html")]
        h = Headers(raw=raw)
        assert h["content-type"] == "text/html"
        # Both uppercase and lowercase lookups work when raw key is lowercase
        # because Starlette lowercases the lookup key before comparing
        assert h["Content-Type"] == "text/html"

    def test_get_default(self):
        h = Headers(raw=[])
        assert h.get("missing", "default") == "default"

    def test_keys(self):
        raw = [(b"a", b"1"), (b"b", b"2")]
        h = Headers(raw=raw)
        assert list(h.keys()) == ["a", "b"]

    def test_values(self):
        raw = [(b"a", b"1"), (b"b", b"2")]
        h = Headers(raw=raw)
        assert list(h.values()) == ["1", "2"]

    def test_items(self):
        raw = [(b"a", b"1"), (b"b", b"2")]
        h = Headers(raw=raw)
        assert list(h.items()) == [("a", "1"), ("b", "2")]

    def test_len(self):
        raw = [(b"a", b"1"), (b"b", b"2")]
        h = Headers(raw=raw)
        assert len(h) == 2

    def test_contains(self):
        raw = [(b"content-type", b"text/html")]
        h = Headers(raw=raw)
        assert "content-type" in h
        assert "Content-Type" in h
        assert "missing" not in h

    def test_getlist(self):
        raw = [(b"accept", b"text/html"), (b"accept", b"application/json")]
        h = Headers(raw=raw)
        assert h.getlist("accept") == ["text/html", "application/json"]

    def test_mutableheaders(self):
        raw = [(b"a", b"1")]
        h = MutableHeaders(raw=raw)
        h["b"] = "2"
        assert h["b"] == "2"

    def test_mutableheaders_delete(self):
        raw = [(b"a", b"1"), (b"b", b"2")]
        h = MutableHeaders(raw=raw)
        del h["a"]
        assert "a" not in h

    def test_mutableheaders_append(self):
        h = MutableHeaders(raw=[])
        h.append("x-custom", "value1")
        h.append("x-custom", "value2")
        assert h.getlist("x-custom") == ["value1", "value2"]


class TestQueryParams:
    def test_from_string(self):
        q = QueryParams("a=1&b=2")
        assert q["a"] == "1"
        assert q["b"] == "2"

    def test_multi(self):
        q = QueryParams("a=1&a=2&b=3")
        assert q.multi_items() == [("a", "1"), ("a", "2"), ("b", "3")]
        assert q.getlist("a") == ["1", "2"]

    def test_empty(self):
        q = QueryParams("")
        assert len(q) == 0

    def test_str(self):
        q = QueryParams("a=1&b=2")
        assert "a=1" in str(q)
        assert "b=2" in str(q)


class TestImmutableMultiDict:
    def test_basic(self):
        d = ImmutableMultiDict([("a", "1"), ("b", "2"), ("a", "3")])
        # Starlette returns the LAST value for duplicate keys (like a dict)
        assert d["a"] == "3"
        assert d.getlist("a") == ["1", "3"]

    def test_immutable(self):
        d = ImmutableMultiDict([("a", "1")])
        with pytest.raises(TypeError):
            d["a"] = "2"  # type: ignore


class TestMultiDict:
    def test_mutable(self):
        d = MultiDict([("a", "1")])
        d["a"] = "2"
        assert d["a"] == "2"

    def test_setlist(self):
        d = MultiDict([("a", "1")])
        d.setlist("a", ["x", "y"])
        assert d.getlist("a") == ["x", "y"]


class TestState:
    def test_set_get(self):
        s = State()
        s.counter = 0
        assert s.counter == 0
        s.counter = 1
        assert s.counter == 1

    def test_delete(self):
        s = State()
        s.value = "test"
        del s.value
        with pytest.raises(AttributeError):
            _ = s.value

    def test_eq(self):
        # Starlette's State does NOT implement __eq__ — objects are identity-compared
        s1 = State()
        s1.x = 1
        s2 = State()
        s2.x = 1
        assert s1 is not s2
        assert s1 != s2  # different objects

    def test_in(self):
        # Starlette's State does NOT support `in` operator
        s = State()
        s.key = "val"
        with pytest.raises(TypeError):
            "key" in s  # type: ignore


class TestUploadFile:
    @pytest.mark.anyio
    async def test_basic(self):
        f = UploadFile(filename="test.txt", file=io.BytesIO(b"hello world"))
        content = await f.read()
        assert content == b"hello world"
        await f.close()

    @pytest.mark.anyio
    async def test_seek(self):
        f = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))
        await f.read()
        await f.seek(0)
        content = await f.read()
        assert content == b"hello"
        await f.close()

    @pytest.mark.anyio
    async def test_write(self):
        f = UploadFile(file=io.BytesIO(b""), filename="test.txt")
        await f.write(b"hello ")
        await f.write(b"world")
        await f.seek(0)
        content = await f.read()
        assert content == b"hello world"
        await f.close()

    def test_attributes(self):
        # Starlette 0.50.0 UploadFile: file (required), size, filename, headers
        # No content_type kwarg — content_type comes from headers
        f = UploadFile(file=io.BytesIO(b""), filename="test.txt")
        assert f.filename == "test.txt"
