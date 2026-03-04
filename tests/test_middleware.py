"""Tests for rustlette.middleware — CORS, GZip, Sessions, TrustedHost, etc."""

import pytest

from rustlette.applications import Starlette
from rustlette.middleware import Middleware
from rustlette.middleware.cors import CORSMiddleware
from rustlette.middleware.gzip import GZipMiddleware
from rustlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from rustlette.middleware.trustedhost import TrustedHostMiddleware
from rustlette.middleware.sessions import SessionMiddleware
from rustlette.middleware.base import BaseHTTPMiddleware
from rustlette.requests import Request
from rustlette.responses import JSONResponse, PlainTextResponse
from rustlette.routing import Route
from rustlette.testclient import TestClient


class TestMiddlewareClass:
    def test_middleware_iter(self):
        """Middleware.__iter__ must yield (cls, args, kwargs) — load-bearing for build_middleware_stack."""
        m = Middleware(CORSMiddleware, allow_origins=["*"])
        cls, args, kwargs = m  # type: ignore
        assert cls == CORSMiddleware
        assert args == ()
        assert kwargs == {"allow_origins": ["*"]}

    def test_middleware_repr(self):
        m = Middleware(CORSMiddleware, allow_origins=["*"])
        r = repr(m)
        assert "CORSMiddleware" in r


class TestCORSMiddleware:
    def test_cors_allow_all_origins(self):
        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[
                Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])
            ],
        )
        client = TestClient(app)
        response = client.get("/", headers={"Origin": "http://example.com"})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "*"

    def test_cors_preflight(self):
        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[
                Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])
            ],
        )
        client = TestClient(app)
        response = client.options(
            "/",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_specific_origin(self):
        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[
                Middleware(CORSMiddleware, allow_origins=["http://allowed.com"])
            ],
        )
        client = TestClient(app)

        # Allowed origin
        response = client.get("/", headers={"Origin": "http://allowed.com"})
        assert (
            response.headers.get("access-control-allow-origin") == "http://allowed.com"
        )

        # Disallowed origin
        response = client.get("/", headers={"Origin": "http://evil.com"})
        assert response.headers.get("access-control-allow-origin") is None


class TestGZipMiddleware:
    def test_gzip_response(self):
        async def homepage(request):
            # Return enough data to trigger compression
            return PlainTextResponse("x" * 500)

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[Middleware(GZipMiddleware, minimum_size=100)],
        )
        client = TestClient(app)
        response = client.get("/", headers={"Accept-Encoding": "gzip"})
        assert response.status_code == 200
        # Content should be compressed
        assert response.headers.get("content-encoding") == "gzip"

    def test_gzip_below_minimum_size(self):
        async def homepage(request):
            return PlainTextResponse("small")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[Middleware(GZipMiddleware, minimum_size=500)],
        )
        client = TestClient(app)
        response = client.get("/", headers={"Accept-Encoding": "gzip"})
        assert response.headers.get("content-encoding") is None


class TestSessionMiddleware:
    def test_session_set_get(self):
        async def set_session(request):
            request.session["user"] = "alice"
            return PlainTextResponse("set")

        async def get_session(request):
            user = request.session.get("user", "none")
            return PlainTextResponse(user)

        app = Starlette(
            routes=[
                Route("/set", set_session),
                Route("/get", get_session),
            ],
            middleware=[Middleware(SessionMiddleware, secret_key="secret")],
        )
        client = TestClient(app)
        # Set session
        response = client.get("/set")
        assert response.status_code == 200
        # Get session (cookies are persisted across requests in TestClient)
        response = client.get("/get")
        assert response.text == "alice"


class TestTrustedHostMiddleware:
    def test_allowed_host(self):
        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[
                Middleware(TrustedHostMiddleware, allowed_hosts=["testserver"])
            ],
        )
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

    def test_disallowed_host(self):
        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[
                Middleware(TrustedHostMiddleware, allowed_hosts=["trusted.com"])
            ],
        )
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 400


class TestHTTPSRedirectMiddleware:
    def test_redirect_to_https(self):
        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[Middleware(HTTPSRedirectMiddleware)],
        )
        client = TestClient(app, base_url="http://testserver", follow_redirects=False)
        response = client.get("/")
        assert response.status_code in (301, 307)
        location = response.headers.get("location", "")
        assert location.startswith("https://")


class TestBaseHTTPMiddleware:
    def test_custom_middleware(self):
        class CustomMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                response = await call_next(request)
                response.headers["X-Custom"] = "middleware-value"
                return response

        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[Middleware(CustomMiddleware)],
        )
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["x-custom"] == "middleware-value"

    def test_middleware_modifies_request(self):
        class AddHeaderMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                # We can inspect the request
                response = await call_next(request)
                response.headers["X-Method"] = request.method
                return response

        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[Middleware(AddHeaderMiddleware)],
        )
        client = TestClient(app)
        response = client.get("/")
        assert response.headers["x-method"] == "GET"


class TestMiddlewareStack:
    """Test that middleware stack wrapping order is correct:
    ServerErrorMiddleware -> [user middlewares] -> ExceptionMiddleware -> Router
    """

    def test_middleware_order(self):
        order = []

        class FirstMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                order.append("first_before")
                response = await call_next(request)
                order.append("first_after")
                return response

        class SecondMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                order.append("second_before")
                response = await call_next(request)
                order.append("second_after")
                return response

        async def homepage(request):
            order.append("endpoint")
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[
                Middleware(FirstMiddleware),
                Middleware(SecondMiddleware),
            ],
        )
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert order == [
            "first_before",
            "second_before",
            "endpoint",
            "second_after",
            "first_after",
        ]
