"""Tests for rustlette.requests — HTTPConnection, Request."""

import pytest

from rustlette.requests import HTTPConnection, Request, cookie_parser
from rustlette.testclient import TestClient
from rustlette.applications import Starlette
from rustlette.responses import JSONResponse, PlainTextResponse
from rustlette.routing import Route


class TestCookieParser:
    def test_basic(self):
        cookies = cookie_parser("session=abc; theme=dark")
        assert cookies["session"] == "abc"
        assert cookies["theme"] == "dark"

    def test_empty(self):
        cookies = cookie_parser("")
        assert cookies == {}

    def test_single(self):
        cookies = cookie_parser("key=value")
        assert cookies == {"key": "value"}


class TestHTTPConnection:
    def test_scope_interface(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"a=1&b=2",
            "headers": [
                (b"host", b"example.com"),
                (b"content-type", b"text/plain"),
            ],
            "server": ("example.com", 443),
            "scheme": "https",
            "root_path": "",
        }
        conn = HTTPConnection(scope)
        assert conn.url.path == "/test"
        assert conn.headers["host"] == "example.com"
        assert conn.query_params["a"] == "1"

    def test_path_params(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/users/42",
            "query_string": b"",
            "headers": [],
            "path_params": {"user_id": 42},
            "server": ("localhost", 80),
            "scheme": "http",
            "root_path": "",
        }
        conn = HTTPConnection(scope)
        assert conn.path_params == {"user_id": 42}


class TestRequestWithTestClient:
    """Test Request through actual ASGI request/response cycle."""

    def test_request_method(self):
        async def homepage(request):
            return JSONResponse({"method": request.method})

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.json() == {"method": "GET"}

    def test_request_url(self):
        async def homepage(request):
            return JSONResponse({"path": request.url.path})

        app = Starlette(routes=[Route("/test", homepage)])
        client = TestClient(app)
        response = client.get("/test")
        assert response.json() == {"path": "/test"}

    def test_request_headers(self):
        async def homepage(request):
            custom = request.headers.get("x-custom", "missing")
            return JSONResponse({"x-custom": custom})

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/", headers={"X-Custom": "test-value"})
        assert response.json() == {"x-custom": "test-value"}

    def test_request_query_params(self):
        async def homepage(request):
            return JSONResponse({"q": request.query_params.get("q", "none")})

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/?q=search")
        assert response.json() == {"q": "search"}

    def test_request_path_params(self):
        async def user(request):
            uid = request.path_params["user_id"]
            return JSONResponse({"user_id": uid})

        app = Starlette(routes=[Route("/users/{user_id:int}", user)])
        client = TestClient(app)
        response = client.get("/users/42")
        assert response.json() == {"user_id": 42}

    def test_request_body(self):
        async def endpoint(request):
            body = await request.body()
            return PlainTextResponse(body.decode())

        app = Starlette(routes=[Route("/", endpoint, methods=["POST"])])
        client = TestClient(app)
        response = client.post("/", content=b"hello body")
        assert response.text == "hello body"

    def test_request_json(self):
        async def endpoint(request):
            data = await request.json()
            return JSONResponse(data)

        app = Starlette(routes=[Route("/", endpoint, methods=["POST"])])
        client = TestClient(app)
        response = client.post("/", json={"key": "value"})
        assert response.json() == {"key": "value"}

    def test_request_cookies(self):
        async def endpoint(request):
            return JSONResponse({"session": request.cookies.get("session", "none")})

        app = Starlette(routes=[Route("/", endpoint)])
        client = TestClient(app, cookies={"session": "abc123"})
        response = client.get("/")
        assert response.json() == {"session": "abc123"}

    def test_request_client(self):
        async def endpoint(request):
            return JSONResponse(
                {
                    "host": request.client.host if request.client else None,
                }
            )

        app = Starlette(routes=[Route("/", endpoint)])
        client = TestClient(app)
        response = client.get("/")
        data = response.json()
        assert data["host"] == "testclient"

    def test_request_mapping_protocol(self):
        """Request must implement Mapping protocol (via HTTPConnection)."""

        async def endpoint(request):
            # HTTPConnection inherits from Mapping — check key access
            return JSONResponse({"type": request["type"], "method": request["method"]})

        app = Starlette(routes=[Route("/", endpoint)])
        client = TestClient(app)
        response = client.get("/")
        assert response.json() == {"type": "http", "method": "GET"}
