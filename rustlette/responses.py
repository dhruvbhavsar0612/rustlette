"""
Response wrappers providing Starlette-compatible interface
"""

import json
import os
import typing
from typing import Any, Dict, Iterable, List, Optional, Union

from ._rustlette_core import (
    RustletteResponse as _RustletteResponse,
    JSONResponse as _JSONResponse,
    HTMLResponse as _HTMLResponse,
    PlainTextResponse as _PlainTextResponse,
)
from .background import BackgroundTasks
from .types import Scope, Receive, Send


class Response:
    """
    Base response class providing Starlette-compatible interface.
    """

    media_type = None
    charset = "utf-8"

    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[BackgroundTasks] = None,
    ) -> None:
        """
        Initialize response.

        Args:
            content: Response content
            status_code: HTTP status code
            headers: Response headers
            media_type: Content-Type header value
            background: Background tasks to execute after response
        """
        self.status_code = status_code
        self.media_type = media_type or self.media_type
        self.background = background
        self._headers = headers or {}

        # Create underlying Rust response
        self._rust_response = _RustletteResponse(
            content=content,
            status_code=status_code,
            headers=self._headers,
            media_type=self.media_type,
            background=background.func if background else None,
        )

    @property
    def headers(self) -> Dict[str, str]:
        """Response headers."""
        return self._rust_response.headers

    @headers.setter
    def headers(self, value: Dict[str, str]) -> None:
        """Set response headers."""
        self._headers = value
        # Update Rust response headers
        for key, val in value.items():
            self._rust_response.headers.set(key, val)

    @property
    def body(self) -> bytes:
        """Response body as bytes."""
        return self._rust_response.body()

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: Optional[int] = None,
        expires: Optional[str] = None,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Optional[str] = "lax",
    ) -> None:
        """Set a cookie."""
        self._rust_response.set_cookie(
            name=key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    def delete_cookie(
        self,
        key: str,
        path: str = "/",
        domain: Optional[str] = None,
    ) -> None:
        """Delete a cookie."""
        self._rust_response.delete_cookie(name=key, path=path, domain=domain)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface."""
        # Send response start
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": [
                    (name.encode(), value.encode())
                    for name, value in self.headers.items()
                ],
            }
        )

        # Send response body
        body = self.body
        await send(
            {
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            }
        )

        # Execute background tasks
        if self.background:
            await self.background()

    def __repr__(self) -> str:
        return f"<Response {self.status_code}>"


class PlainTextResponse(Response):
    """Plain text response."""

    media_type = "text/plain"

    def __init__(
        self,
        content: Any = "",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[BackgroundTasks] = None,
    ) -> None:
        if media_type is None:
            media_type = f"{self.media_type}; charset={self.charset}"

        super().__init__(
            content=str(content),
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )


class HTMLResponse(Response):
    """HTML response."""

    media_type = "text/html"

    def __init__(
        self,
        content: Any = "",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[BackgroundTasks] = None,
    ) -> None:
        if media_type is None:
            media_type = f"{self.media_type}; charset={self.charset}"

        super().__init__(
            content=str(content),
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )


class JSONResponse(Response):
    """JSON response."""

    media_type = "application/json"

    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[BackgroundTasks] = None,
        **kwargs: Any,
    ) -> None:
        # Serialize content to JSON
        if content is not None:
            json_content = json.dumps(content, **kwargs)
        else:
            json_content = "null"

        super().__init__(
            content=json_content,
            status_code=status_code,
            headers=headers,
            media_type=media_type or self.media_type,
            background=background,
        )


class RedirectResponse(Response):
    """Redirect response."""

    def __init__(
        self,
        url: str,
        status_code: int = 302,
        headers: Optional[Dict[str, str]] = None,
        background: Optional[BackgroundTasks] = None,
    ) -> None:
        if status_code not in (301, 302, 303, 307, 308):
            raise ValueError(f"Invalid redirect status code: {status_code}")

        headers = headers or {}
        headers["location"] = url

        super().__init__(
            content="",
            status_code=status_code,
            headers=headers,
            background=background,
        )


class StreamingResponse(Response):
    """Streaming response for large content."""

    def __init__(
        self,
        content: typing.Union[typing.Iterable[bytes], typing.AsyncIterable[bytes]],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[BackgroundTasks] = None,
    ) -> None:
        if isinstance(content, (str, bytes)):
            raise TypeError("StreamingResponse content must be iterable")

        self.content = content
        super().__init__(
            content=None,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface for streaming."""
        # Send response start
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": [
                    (name.encode(), value.encode())
                    for name, value in self.headers.items()
                ],
            }
        )

        # Stream content
        if hasattr(self.content, "__aiter__"):
            # Async iterable
            async for chunk in self.content:
                if isinstance(chunk, str):
                    chunk = chunk.encode(self.charset)
                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    }
                )
        else:
            # Sync iterable
            for chunk in self.content:
                if isinstance(chunk, str):
                    chunk = chunk.encode(self.charset)
                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    }
                )

        # Send final empty chunk
        await send(
            {
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            }
        )

        # Execute background tasks
        if self.background:
            await self.background()


class FileResponse(Response):
    """File response for serving static files."""

    def __init__(
        self,
        path: typing.Union[str, os.PathLike],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[BackgroundTasks] = None,
        filename: Optional[str] = None,
        stat_result: Optional[os.stat_result] = None,
        method: Optional[str] = None,
    ) -> None:
        self.path = path
        self.status_code = status_code
        self.filename = filename
        self.background = background

        if stat_result is None:
            try:
                stat_result = os.stat(path)
            except FileNotFoundError:
                raise FileNotFoundError(f"File not found: {path}")

        self.stat_result = stat_result

        # Determine media type
        if media_type is None:
            media_type = self._guess_media_type(str(path))
        self.media_type = media_type

        # Set headers
        self._headers = headers or {}
        self._headers["content-length"] = str(stat_result.st_size)

        if filename:
            content_disposition = f'attachment; filename="{filename}"'
            self._headers["content-disposition"] = content_disposition

        if self.media_type:
            self._headers["content-type"] = self.media_type

    def _guess_media_type(self, path: str) -> str:
        """Guess media type from file extension."""
        import mimetypes

        media_type, _ = mimetypes.guess_type(path)
        return media_type or "application/octet-stream"

    @property
    def headers(self) -> Dict[str, str]:
        """Response headers."""
        return self._headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface for file serving."""
        method = scope.get("method", "GET")

        # Send response start
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": [
                    (name.encode(), value.encode())
                    for name, value in self.headers.items()
                ],
            }
        )

        # For HEAD requests, don't send body
        if method == "HEAD":
            await send(
                {
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False,
                }
            )
        else:
            # Stream file content
            chunk_size = 64 * 1024  # 64KB chunks

            with open(self.path, "rb") as file:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break

                    await send(
                        {
                            "type": "http.response.body",
                            "body": chunk,
                            "more_body": True,
                        }
                    )

            # Send final empty chunk
            await send(
                {
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False,
                }
            )

        # Execute background tasks
        if self.background:
            await self.background()

    def __repr__(self) -> str:
        return f"<FileResponse {self.path}>"
