"""Tests for rustlette.endpoints — HTTPEndpoint, WebSocketEndpoint."""

import pytest

from rustlette.applications import Starlette
from rustlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from rustlette.responses import JSONResponse, PlainTextResponse
from rustlette.routing import Route, WebSocketRoute
from rustlette.testclient import TestClient
from rustlette.websockets import WebSocket


class TestHTTPEndpoint:
    def test_get(self):
        class Homepage(HTTPEndpoint):
            async def get(self, request):
                return PlainTextResponse("GET response")

        app = Starlette(routes=[Route("/", Homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "GET response"

    def test_post(self):
        class ItemEndpoint(HTTPEndpoint):
            async def post(self, request):
                return JSONResponse({"created": True})

        app = Starlette(routes=[Route("/items", ItemEndpoint)])
        client = TestClient(app)
        response = client.post("/items")
        assert response.status_code == 200
        assert response.json() == {"created": True}

    def test_multiple_methods(self):
        class UserEndpoint(HTTPEndpoint):
            async def get(self, request):
                return PlainTextResponse("GET user")

            async def put(self, request):
                return PlainTextResponse("PUT user")

            async def delete(self, request):
                return PlainTextResponse("DELETE user")

        app = Starlette(routes=[Route("/user", UserEndpoint)])
        client = TestClient(app)
        assert client.get("/user").text == "GET user"
        assert client.put("/user").text == "PUT user"
        assert client.delete("/user").text == "DELETE user"

    def test_method_not_allowed(self):
        class GetOnly(HTTPEndpoint):
            async def get(self, request):
                return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", GetOnly)])
        client = TestClient(app)
        response = client.post("/")
        assert response.status_code == 405


class TestWebSocketEndpoint:
    def test_basic_websocket_endpoint(self):
        class WSEndpoint(WebSocketEndpoint):
            encoding = "text"

            async def on_connect(self, websocket):
                await websocket.accept()

            async def on_receive(self, websocket, data):
                await websocket.send_text(f"echo: {data}")

            async def on_disconnect(self, websocket, close_code):
                pass

        app = Starlette(routes=[WebSocketRoute("/ws", WSEndpoint)])
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            ws.send_text("hello")
            data = ws.receive_text()
            assert data == "echo: hello"

    def test_json_websocket_endpoint(self):
        class WSEndpoint(WebSocketEndpoint):
            encoding = "json"

            async def on_connect(self, websocket):
                await websocket.accept()

            async def on_receive(self, websocket, data):
                await websocket.send_json({"received": data})

            async def on_disconnect(self, websocket, close_code):
                pass

        app = Starlette(routes=[WebSocketRoute("/ws", WSEndpoint)])
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"key": "value"})
            data = ws.receive_json()
            assert data == {"received": {"key": "value"}}
