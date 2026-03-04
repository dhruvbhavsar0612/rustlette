"""Tests for rustlette.applications — Starlette app class."""

import contextlib

import pytest

from rustlette.applications import Starlette
from rustlette.exceptions import HTTPException
from rustlette.middleware import Middleware
from rustlette.middleware.cors import CORSMiddleware
from rustlette.requests import Request
from rustlette.responses import JSONResponse, PlainTextResponse
from rustlette.routing import Mount, Route, Router
from rustlette.testclient import TestClient


class TestStarletteApp:
    def test_basic_app(self):
        async def homepage(request):
            return PlainTextResponse("Hello, World!")

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "Hello, World!"

    def test_debug_mode(self):
        app = Starlette(debug=True)
        assert app.debug is True

    def test_default_not_debug(self):
        app = Starlette()
        assert app.debug is False

    def test_app_state(self):
        app = Starlette()
        app.state.counter = 0
        assert app.state.counter == 0
        app.state.counter = 1
        assert app.state.counter == 1

    def test_multiple_routes(self):
        async def homepage(request):
            return PlainTextResponse("Home")

        async def about(request):
            return PlainTextResponse("About")

        app = Starlette(
            routes=[
                Route("/", homepage),
                Route("/about", about),
            ]
        )
        client = TestClient(app)
        assert client.get("/").text == "Home"
        assert client.get("/about").text == "About"

    def test_add_route(self):
        app = Starlette()

        async def endpoint(request):
            return PlainTextResponse("added")

        app.add_route("/test", endpoint)
        client = TestClient(app)
        assert client.get("/test").text == "added"

    def test_add_route_with_methods(self):
        app = Starlette()

        async def endpoint(request):
            return PlainTextResponse(request.method)

        app.add_route("/test", endpoint, methods=["POST"])
        client = TestClient(app)
        assert client.post("/test").text == "POST"
        assert client.get("/test").status_code == 405


class TestExceptionHandlers:
    def test_http_exception_handler(self):
        async def homepage(request):
            raise HTTPException(status_code=400, detail="Bad request")

        async def bad_request_handler(request, exc):
            return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

        app = Starlette(
            routes=[Route("/", homepage)],
            exception_handlers={400: bad_request_handler},
        )
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 400
        assert response.json() == {"error": "Bad request"}

    def test_404_handler(self):
        async def not_found(request, exc):
            return JSONResponse({"error": "Custom 404"}, status_code=404)

        app = Starlette(exception_handlers={404: not_found})
        client = TestClient(app)
        response = client.get("/nonexistent")
        assert response.status_code == 404
        assert response.json() == {"error": "Custom 404"}

    def test_generic_exception_handler(self):
        async def homepage(request):
            raise HTTPException(status_code=500, detail="Server error")

        async def error_handler(request, exc):
            return JSONResponse({"error": "handled"}, status_code=500)

        app = Starlette(
            routes=[Route("/", homepage)],
            exception_handlers={500: error_handler},
        )
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert response.status_code == 500


class TestLifespan:
    def test_lifespan_context(self):
        startup_done = []
        shutdown_done = []

        @contextlib.asynccontextmanager
        async def lifespan(app):
            startup_done.append(True)
            yield
            shutdown_done.append(True)

        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)], lifespan=lifespan)

        with TestClient(app) as client:
            assert startup_done == [True]
            response = client.get("/")
            assert response.status_code == 200

        assert shutdown_done == [True]

    def test_on_startup_on_shutdown(self):
        events = []

        async def on_startup():
            events.append("startup")

        async def on_shutdown():
            events.append("shutdown")

        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            on_startup=[on_startup],
            on_shutdown=[on_shutdown],
        )

        with TestClient(app) as client:
            assert events == ["startup"]
            response = client.get("/")
            assert response.status_code == 200

        assert events == ["startup", "shutdown"]


class TestMiddlewareIntegration:
    def test_middleware_in_constructor(self):
        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[Middleware(CORSMiddleware, allow_origins=["*"])],
        )
        client = TestClient(app)
        response = client.get("/", headers={"Origin": "http://example.com"})
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_add_middleware(self):
        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(CORSMiddleware, allow_origins=["*"])
        client = TestClient(app)
        response = client.get("/", headers={"Origin": "http://example.com"})
        assert response.status_code == 200


class TestURLPathFor:
    def test_url_path_for(self):
        async def user(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[
                Route("/users/{user_id:int}", user, name="user-detail"),
            ]
        )
        url = app.url_path_for("user-detail", user_id=42)
        assert "/users/42" in str(url)

    def test_url_path_for_no_match(self):
        app = Starlette()
        with pytest.raises(Exception):
            app.url_path_for("nonexistent")
