"""Tests for rustlette.testclient — TestClient basics."""

import pytest

from rustlette.applications import Starlette
from rustlette.responses import JSONResponse, PlainTextResponse
from rustlette.routing import Route, WebSocketRoute
from rustlette.testclient import TestClient
from rustlette.websockets import WebSocket


class TestTestClientBasics:
    def test_get(self):
        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "ok"

    def test_post(self):
        async def endpoint(request):
            body = await request.json()
            return JSONResponse(body)

        app = Starlette(routes=[Route("/", endpoint, methods=["POST"])])
        client = TestClient(app)
        response = client.post("/", json={"key": "value"})
        assert response.json() == {"key": "value"}

    def test_put(self):
        async def endpoint(request):
            return PlainTextResponse("put ok")

        app = Starlette(routes=[Route("/", endpoint, methods=["PUT"])])
        client = TestClient(app)
        response = client.put("/")
        assert response.text == "put ok"

    def test_delete(self):
        async def endpoint(request):
            return PlainTextResponse("deleted")

        app = Starlette(routes=[Route("/", endpoint, methods=["DELETE"])])
        client = TestClient(app)
        response = client.delete("/")
        assert response.text == "deleted"

    def test_patch(self):
        async def endpoint(request):
            return PlainTextResponse("patched")

        app = Starlette(routes=[Route("/", endpoint, methods=["PATCH"])])
        client = TestClient(app)
        response = client.patch("/")
        assert response.text == "patched"

    def test_head(self):
        async def endpoint(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", endpoint)])
        client = TestClient(app)
        response = client.head("/")
        assert response.status_code == 200

    def test_options(self):
        async def endpoint(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", endpoint, methods=["OPTIONS"])])
        client = TestClient(app)
        response = client.options("/")
        assert response.status_code == 200


class TestTestClientHeaders:
    def test_default_user_agent(self):
        async def endpoint(request):
            return JSONResponse({"ua": request.headers.get("user-agent", "")})

        app = Starlette(routes=[Route("/", endpoint)])
        client = TestClient(app)
        response = client.get("/")
        assert response.json()["ua"] == "testclient"

    def test_custom_headers(self):
        async def endpoint(request):
            return JSONResponse({"auth": request.headers.get("authorization", "")})

        app = Starlette(routes=[Route("/", endpoint)])
        client = TestClient(app, headers={"Authorization": "Bearer token"})
        response = client.get("/")
        assert response.json()["auth"] == "Bearer token"


class TestTestClientCookies:
    def test_cookies_persist(self):
        async def set_cookie(request):
            from rustlette.responses import Response

            resp = Response("ok")
            resp.set_cookie("session", "xyz")
            return resp

        async def get_cookie(request):
            return PlainTextResponse(request.cookies.get("session", "none"))

        app = Starlette(
            routes=[
                Route("/set", set_cookie),
                Route("/get", get_cookie),
            ]
        )
        client = TestClient(app)
        client.get("/set")
        response = client.get("/get")
        assert response.text == "xyz"


class TestTestClientLifespan:
    def test_context_manager(self):
        import contextlib

        events = []

        @contextlib.asynccontextmanager
        async def lifespan(app):
            events.append("startup")
            yield
            events.append("shutdown")

        async def endpoint(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", endpoint)], lifespan=lifespan)

        with TestClient(app) as client:
            assert events == ["startup"]
            response = client.get("/")
            assert response.status_code == 200

        assert events == ["startup", "shutdown"]


class TestTestClientWebSocket:
    def test_websocket_connect(self):
        async def ws_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("connected")
            await websocket.close()

        app = Starlette(routes=[WebSocketRoute("/ws", ws_endpoint)])
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            data = ws.receive_text()
            assert data == "connected"

    def test_websocket_subprotocol(self):
        async def ws_endpoint(websocket: WebSocket):
            await websocket.accept(subprotocol="graphql")
            await websocket.send_text("ok")
            await websocket.close()

        app = Starlette(routes=[WebSocketRoute("/ws", ws_endpoint)])
        client = TestClient(app)

        with client.websocket_connect("/ws", subprotocols=["graphql"]) as ws:
            assert ws.accepted_subprotocol == "graphql"
            data = ws.receive_text()
            assert data == "ok"


class TestTestClientRaiseExceptions:
    def test_raise_server_exceptions_true(self):
        async def endpoint(request):
            raise RuntimeError("Server error")

        app = Starlette(routes=[Route("/", endpoint)])
        client = TestClient(app, raise_server_exceptions=True)
        with pytest.raises(RuntimeError, match="Server error"):
            client.get("/")

    def test_raise_server_exceptions_false(self):
        async def endpoint(request):
            raise RuntimeError("Server error")

        app = Starlette(routes=[Route("/", endpoint)])
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert response.status_code == 500
