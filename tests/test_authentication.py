"""Tests for rustlette.authentication — AuthCredentials, requires decorator, etc."""

import pytest

from rustlette.applications import Starlette
from rustlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
    SimpleUser,
    UnauthenticatedUser,
    has_required_scope,
    requires,
)
from rustlette.middleware import Middleware
from rustlette.middleware.authentication import AuthenticationMiddleware
from rustlette.requests import Request
from rustlette.responses import JSONResponse, PlainTextResponse
from rustlette.routing import Route
from rustlette.testclient import TestClient


class TestAuthCredentials:
    def test_basic(self):
        creds = AuthCredentials(["read", "write"])
        assert "read" in creds.scopes
        assert "write" in creds.scopes

    def test_empty(self):
        creds = AuthCredentials()
        assert len(creds.scopes) == 0


class TestBaseUser:
    def test_simple_user(self):
        user = SimpleUser("alice")
        assert user.is_authenticated is True
        assert user.display_name == "alice"
        # Starlette's SimpleUser does NOT override identity — it raises NotImplementedError
        with pytest.raises(NotImplementedError):
            _ = user.identity

    def test_unauthenticated_user(self):
        user = UnauthenticatedUser()
        assert user.is_authenticated is False
        assert user.display_name == ""


class TestAuthenticationError:
    def test_is_exception(self):
        exc = AuthenticationError("Invalid credentials")
        assert isinstance(exc, Exception)


class TestHasRequiredScope:
    def test_has_scope(self):
        conn_scope = {
            "type": "http",
            "auth": AuthCredentials(["read", "write"]),
        }
        # has_required_scope checks conn.auth.scopes
        # We need to simulate an HTTPConnection
        from rustlette.requests import HTTPConnection

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 80),
            "scheme": "http",
            "root_path": "",
            "auth": AuthCredentials(["read", "write"]),
        }
        conn = HTTPConnection(scope)
        assert has_required_scope(conn, ["read"])
        assert has_required_scope(conn, ["read", "write"])
        assert not has_required_scope(conn, ["admin"])


class TestAuthenticationMiddleware:
    def test_authenticated_request(self):
        class TestBackend(AuthenticationBackend):
            async def authenticate(self, conn):
                return AuthCredentials(["authenticated"]), SimpleUser("testuser")

        async def homepage(request):
            return JSONResponse(
                {
                    "user": request.user.display_name,
                    "authenticated": request.user.is_authenticated,
                }
            )

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[Middleware(AuthenticationMiddleware, backend=TestBackend())],
        )
        client = TestClient(app)
        response = client.get("/")
        assert response.json() == {
            "user": "testuser",
            "authenticated": True,
        }

    def test_unauthenticated_request(self):
        class TestBackend(AuthenticationBackend):
            async def authenticate(self, conn):
                return None  # No authentication

        async def homepage(request):
            return JSONResponse(
                {
                    "authenticated": request.user.is_authenticated,
                }
            )

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[Middleware(AuthenticationMiddleware, backend=TestBackend())],
        )
        client = TestClient(app)
        response = client.get("/")
        assert response.json() == {"authenticated": False}


class TestRequiresDecorator:
    def test_requires_with_scope(self):
        class TestBackend(AuthenticationBackend):
            async def authenticate(self, conn):
                auth_header = conn.headers.get("authorization", "")
                if auth_header == "Bearer valid":
                    return AuthCredentials(["authenticated"]), SimpleUser("testuser")
                return None

        @requires("authenticated")
        async def protected(request):
            return PlainTextResponse("protected content")

        async def public(request):
            return PlainTextResponse("public")

        app = Starlette(
            routes=[
                Route("/protected", protected),
                Route("/public", public),
            ],
            middleware=[Middleware(AuthenticationMiddleware, backend=TestBackend())],
        )
        client = TestClient(app)

        # Without auth
        response = client.get("/protected")
        assert response.status_code == 403

        # With auth
        response = client.get("/protected", headers={"Authorization": "Bearer valid"})
        assert response.status_code == 200
        assert response.text == "protected content"

        # Public endpoint always works
        assert client.get("/public").status_code == 200
