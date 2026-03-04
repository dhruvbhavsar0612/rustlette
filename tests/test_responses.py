"""Tests for rustlette.responses — all response types."""

import os
import tempfile

import pytest

from rustlette.applications import Starlette
from rustlette.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from rustlette.routing import Route
from rustlette.testclient import TestClient


class TestResponse:
    def test_basic_response(self):
        async def homepage(request):
            return Response("hello", media_type="text/plain")

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "hello"

    def test_response_bytes(self):
        async def homepage(request):
            return Response(b"binary data", media_type="application/octet-stream")

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.content == b"binary data"

    def test_response_status_code(self):
        async def homepage(request):
            return Response("created", status_code=201)

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 201

    def test_response_headers(self):
        async def homepage(request):
            return Response("ok", headers={"X-Custom": "value"})

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.headers["x-custom"] == "value"

    def test_set_cookie(self):
        async def homepage(request):
            resp = Response("ok")
            resp.set_cookie("session", "abc123", httponly=True)
            return resp

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert "session=abc123" in response.headers.get("set-cookie", "")

    def test_delete_cookie(self):
        async def homepage(request):
            resp = Response("ok")
            resp.delete_cookie("session")
            return resp

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        cookie_header = response.headers.get("set-cookie", "")
        assert "session=" in cookie_header
        assert (
            "max-age=0" in cookie_header.lower() or "expires=" in cookie_header.lower()
        )


class TestJSONResponse:
    def test_json_dict(self):
        async def homepage(request):
            return JSONResponse({"key": "value"})

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.json() == {"key": "value"}
        assert "application/json" in response.headers["content-type"]

    def test_json_list(self):
        async def homepage(request):
            return JSONResponse([1, 2, 3])

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.json() == [1, 2, 3]

    def test_json_status_code(self):
        async def homepage(request):
            return JSONResponse({"error": "not found"}, status_code=404)

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 404


class TestHTMLResponse:
    def test_html(self):
        async def homepage(request):
            return HTMLResponse("<h1>Hello</h1>")

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.text == "<h1>Hello</h1>"
        assert "text/html" in response.headers["content-type"]


class TestPlainTextResponse:
    def test_plain_text(self):
        async def homepage(request):
            return PlainTextResponse("Hello, World!")

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.text == "Hello, World!"
        assert "text/plain" in response.headers["content-type"]


class TestRedirectResponse:
    def test_redirect_default_307(self):
        """RedirectResponse must default to 307 (not 302)."""

        async def homepage(request):
            return RedirectResponse("/destination")

        app = Starlette(
            routes=[
                Route("/", homepage),
                Route("/destination", lambda r: PlainTextResponse("dest")),
            ]
        )
        client = TestClient(app, follow_redirects=False)
        response = client.get("/")
        assert response.status_code == 307
        assert response.headers["location"] == "/destination"

    def test_redirect_301(self):
        async def homepage(request):
            return RedirectResponse("/destination", status_code=301)

        app = Starlette(
            routes=[
                Route("/", homepage),
                Route("/destination", lambda r: PlainTextResponse("dest")),
            ]
        )
        client = TestClient(app, follow_redirects=False)
        response = client.get("/")
        assert response.status_code == 301

    def test_redirect_follow(self):
        async def homepage(request):
            return RedirectResponse("/destination")

        async def destination(request):
            return PlainTextResponse("arrived")

        app = Starlette(
            routes=[
                Route("/", homepage),
                Route("/destination", destination),
            ]
        )
        client = TestClient(app)
        response = client.get("/")
        assert response.text == "arrived"


class TestStreamingResponse:
    def test_sync_generator(self):
        async def homepage(request):
            def gen():
                yield b"hello "
                yield b"world"

            return StreamingResponse(gen(), media_type="text/plain")

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.text == "hello world"

    def test_async_generator(self):
        async def homepage(request):
            async def gen():
                yield b"async "
                yield b"stream"

            return StreamingResponse(gen(), media_type="text/plain")

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.text == "async stream"

    def test_streaming_status_code(self):
        async def homepage(request):
            async def gen():
                yield b"data"

            return StreamingResponse(gen(), status_code=201)

        app = Starlette(routes=[Route("/", homepage)])
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 201


class TestFileResponse:
    def test_basic_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("file content")
            filepath = f.name
        try:

            async def homepage(request):
                return FileResponse(filepath)

            app = Starlette(routes=[Route("/", homepage)])
            client = TestClient(app)
            response = client.get("/")
            assert response.status_code == 200
            assert response.text == "file content"
            assert "text/plain" in response.headers.get("content-type", "")
        finally:
            os.unlink(filepath)

    def test_file_with_filename(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("download content")
            filepath = f.name
        try:

            async def homepage(request):
                return FileResponse(filepath, filename="download.txt")

            app = Starlette(routes=[Route("/", homepage)])
            client = TestClient(app)
            response = client.get("/")
            assert "attachment" in response.headers.get("content-disposition", "")
            assert "download.txt" in response.headers.get("content-disposition", "")
        finally:
            os.unlink(filepath)

    def test_file_content_length(self):
        content = "x" * 100
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write(content)
            filepath = f.name
        try:

            async def homepage(request):
                return FileResponse(filepath)

            app = Starlette(routes=[Route("/", homepage)])
            client = TestClient(app)
            response = client.get("/")
            assert response.headers.get("content-length") == "100"
        finally:
            os.unlink(filepath)
