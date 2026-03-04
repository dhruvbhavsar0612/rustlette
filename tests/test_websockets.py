"""Tests for rustlette.websockets — WebSocket, WebSocketState, WebSocketDisconnect."""

import pytest

from rustlette.applications import Starlette
from rustlette.routing import WebSocketRoute
from rustlette.testclient import TestClient
from rustlette.websockets import (
    WebSocket,
    WebSocketClose,
    WebSocketDisconnect,
    WebSocketState,
)


class TestWebSocketState:
    def test_enum_values(self):
        assert WebSocketState.CONNECTING.value == 0
        assert WebSocketState.CONNECTED.value == 1
        assert WebSocketState.DISCONNECTED.value == 2
        assert WebSocketState.RESPONSE.value == 3

    def test_enum_members(self):
        assert len(WebSocketState) == 4


class TestWebSocketDisconnect:
    def test_default_code(self):
        exc = WebSocketDisconnect()
        assert exc.code == 1000

    def test_custom_code(self):
        exc = WebSocketDisconnect(code=1008)
        assert exc.code == 1008

    def test_with_reason(self):
        exc = WebSocketDisconnect(code=1008, reason="Policy violation")
        assert exc.reason == "Policy violation"

    def test_is_exception(self):
        assert isinstance(WebSocketDisconnect(), Exception)


class TestWebSocketClose:
    def test_default(self):
        close = WebSocketClose()
        assert close.code == 1000

    def test_custom(self):
        close = WebSocketClose(code=1001, reason="Going away")
        assert close.code == 1001
        assert close.reason == "Going away"


class TestWebSocketEchoServer:
    """Test WebSocket through actual ASGI lifecycle using TestClient."""

    def test_text_echo(self):
        async def ws_endpoint(websocket: WebSocket):
            await websocket.accept()
            data = await websocket.receive_text()
            await websocket.send_text(f"echo: {data}")
            await websocket.close()

        app = Starlette(routes=[WebSocketRoute("/ws", ws_endpoint)])
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            ws.send_text("hello")
            data = ws.receive_text()
            assert data == "echo: hello"

    def test_json_echo(self):
        async def ws_endpoint(websocket: WebSocket):
            await websocket.accept()
            data = await websocket.receive_json()
            await websocket.send_json({"received": data})
            await websocket.close()

        app = Starlette(routes=[WebSocketRoute("/ws", ws_endpoint)])
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"key": "value"})
            data = ws.receive_json()
            assert data == {"received": {"key": "value"}}

    def test_bytes_echo(self):
        async def ws_endpoint(websocket: WebSocket):
            await websocket.accept()
            data = await websocket.receive_bytes()
            await websocket.send_bytes(data)
            await websocket.close()

        app = Starlette(routes=[WebSocketRoute("/ws", ws_endpoint)])
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            ws.send_bytes(b"\x00\x01\x02")
            data = ws.receive_bytes()
            assert data == b"\x00\x01\x02"

    def test_websocket_disconnect(self):
        async def ws_endpoint(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass  # Expected

        app = Starlette(routes=[WebSocketRoute("/ws", ws_endpoint)])
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            ws.send_text("hello")
            # Close is handled automatically by context manager

    def test_websocket_url_and_headers(self):
        async def ws_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_json(
                {
                    "path": str(websocket.url.path),
                    "headers_present": "sec-websocket-version" in websocket.headers,
                }
            )
            await websocket.close()

        app = Starlette(routes=[WebSocketRoute("/ws", ws_endpoint)])
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            data = ws.receive_json()
            assert data["path"] == "/ws"
            assert data["headers_present"] is True
