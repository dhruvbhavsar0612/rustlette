"""Tests for rustlette.routing — Route, Router, Mount, Match, compile_path, etc."""

import pytest

from rustlette.applications import Starlette
from rustlette.requests import Request
from rustlette.responses import JSONResponse, PlainTextResponse, Response
from rustlette.routing import (
    BaseRoute,
    Host,
    Match,
    Mount,
    NoMatchFound,
    Route,
    Router,
    WebSocketRoute,
    compile_path,
    get_name,
    replace_params,
)
from rustlette.testclient import TestClient
from rustlette.websockets import WebSocket


class TestMatchEnum:
    def test_values(self):
        assert Match.NONE.value == 0
        assert Match.PARTIAL.value == 1
        assert Match.FULL.value == 2

    def test_is_enum(self):
        import enum

        assert issubclass(Match, enum.Enum)


class TestCompilePath:
    def test_static_path(self):
        regex, path_format, convertors = compile_path("/users")
        assert path_format == "/users"
        assert convertors == {}

    def test_int_param(self):
        regex, path_format, convertors = compile_path("/users/{user_id:int}")
        assert "{user_id}" in path_format
        assert "user_id" in convertors
        # Regex should match integers
        match = regex.match("/users/42")
        assert match is not None

    def test_str_param(self):
        regex, path_format, convertors = compile_path("/items/{name}")
        match = regex.match("/items/widget")
        assert match is not None
        assert match.group("name") == "widget"

    def test_path_param(self):
        regex, path_format, convertors = compile_path("/files/{filepath:path}")
        match = regex.match("/files/a/b/c.txt")
        assert match is not None

    def test_uuid_param(self):
        regex, path_format, convertors = compile_path("/items/{item_id:uuid}")
        match = regex.match("/items/12345678-1234-5678-1234-567812345678")
        assert match is not None

    def test_no_match(self):
        regex, _, _ = compile_path("/users/{user_id:int}")
        match = regex.match("/users/abc")
        assert match is None


class TestGetName:
    def test_function_name(self):
        def my_endpoint():
            pass

        assert get_name(my_endpoint) == "my_endpoint"

    def test_class_name(self):
        class MyEndpoint:
            pass

        assert get_name(MyEndpoint) == "MyEndpoint"


class TestReplaceParams:
    def test_basic(self):
        from rustlette.convertors import StringConvertor

        path = "/users/{user_id}"
        new_path, remaining = replace_params(
            path,
            param_convertors={"user_id": StringConvertor()},
            path_params={"user_id": "42"},
        )
        assert new_path == "/users/42"
        assert remaining == {}


class TestRoute:
    def test_basic_route(self):
        async def homepage(request):
            return PlainTextResponse("Home")

        app = Router(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "Home"

    def test_route_methods(self):
        async def endpoint(request):
            return PlainTextResponse(f"Method: {request.method}")

        app = Router(routes=[Route("/", endpoint, methods=["GET", "POST"])])
        client = TestClient(app)

        assert client.get("/").text == "Method: GET"
        assert client.post("/").text == "Method: POST"

    def test_route_method_not_allowed(self):
        async def endpoint(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", endpoint, methods=["GET"])])
        client = TestClient(app)
        response = client.post("/")
        assert response.status_code == 405

    def test_route_path_params(self):
        async def endpoint(request):
            return JSONResponse(request.path_params)

        app = Router(routes=[Route("/users/{user_id:int}", endpoint)])
        client = TestClient(app)
        response = client.get("/users/42")
        assert response.json() == {"user_id": 42}

    def test_route_name(self):
        async def endpoint(request):
            return PlainTextResponse("ok")

        route = Route("/test", endpoint, name="test_route")
        assert route.name == "test_route"

    def test_route_not_found(self):
        app = Starlette(routes=[Route("/exists", lambda r: PlainTextResponse("ok"))])
        client = TestClient(app)
        response = client.get("/missing")
        assert response.status_code == 404


class TestWebSocketRoute:
    def test_websocket_route(self):
        async def ws_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("hello")
            await websocket.close()

        app = Router(routes=[WebSocketRoute("/ws", ws_endpoint)])
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            data = ws.receive_text()
            assert data == "hello"


class TestMount:
    def test_submount(self):
        async def endpoint(request):
            return PlainTextResponse("sub")

        sub_app = Router(routes=[Route("/endpoint", endpoint)])
        app = Router(routes=[Mount("/api", app=sub_app)])
        client = TestClient(app)
        response = client.get("/api/endpoint")
        assert response.status_code == 200
        assert response.text == "sub"

    def test_submount_with_routes(self):
        async def endpoint(request):
            return PlainTextResponse("mounted")

        app = Router(routes=[Mount("/api", routes=[Route("/test", endpoint)])])
        client = TestClient(app)
        response = client.get("/api/test")
        assert response.status_code == 200
        assert response.text == "mounted"


class TestRouter:
    def test_redirect_slashes(self):
        async def endpoint(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/test", endpoint)])
        client = TestClient(app, follow_redirects=False)
        response = client.get("/test/")
        assert response.status_code in (301, 307)

    def test_url_path_for(self):
        async def endpoint(request):
            url = request.url_for("user", user_id=42)
            return PlainTextResponse(str(url))

        app = Starlette(
            routes=[
                Route("/users/{user_id:int}", endpoint, name="user"),
            ]
        )
        client = TestClient(app)
        response = client.get("/users/1")
        assert "/users/42" in response.text

    def test_add_route(self):
        async def endpoint(request):
            return PlainTextResponse("added")

        app = Starlette()
        app.add_route("/test", endpoint)
        client = TestClient(app)
        response = client.get("/test")
        assert response.text == "added"

    def test_add_websocket_route(self):
        async def ws_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("ws_added")
            await websocket.close()

        app = Starlette()
        app.add_websocket_route("/ws", ws_endpoint)
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            data = ws.receive_text()
            assert data == "ws_added"


class TestNoMatchFound:
    def test_exception(self):
        with pytest.raises(NoMatchFound):
            raise NoMatchFound("test", {})
