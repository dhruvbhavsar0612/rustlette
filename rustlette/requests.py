"""
Request wrapper providing Starlette-compatible interface
"""

import json
import typing
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qs, unquote_plus

from ._rustlette_core import RustletteRequest as _RustletteRequest
from .types import Scope, Receive, Message


class Request:
    """
    Request wrapper that provides Starlette-compatible interface
    while delegating to the Rust implementation for performance.
    """

    def __init__(
        self,
        scope: Scope,
        receive: Optional[Receive] = None,
        send: Optional[typing.Callable] = None,
    ) -> None:
        """
        Initialize request from ASGI scope.

        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable (optional)
            send: ASGI send callable (optional)
        """
        self.scope = scope
        self._receive = receive
        self._send = send

        # Extract basic info from scope
        self._method = scope["method"]
        self._url = self._build_url_from_scope(scope)
        self._headers = dict(scope.get("headers", []))

        # Create internal Rust request
        self._rust_request = None
        self._body = None
        self._json = None
        self._form = None
        self._query_params = None
        self._path_params = scope.get("path_params", {})

        # State for storing arbitrary data
        self.state = {}

    def _build_url_from_scope(self, scope: Scope) -> str:
        """Build full URL from ASGI scope."""
        scheme = scope.get("scheme", "http")
        server = scope.get("server")
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"")

        if server:
            host, port = server
            if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
                url = f"{scheme}://{host}{path}"
            else:
                url = f"{scheme}://{host}:{port}{path}"
        else:
            url = f"{scheme}://localhost{path}"

        if query_string:
            url += f"?{query_string.decode('latin1')}"

        return url

    @property
    def method(self) -> str:
        """HTTP method."""
        return self._method

    @property
    def url(self) -> str:
        """Full URL."""
        return self._url

    @property
    def base_url(self) -> str:
        """Base URL without path and query string."""
        scope = self.scope
        scheme = scope.get("scheme", "http")
        server = scope.get("server")

        if server:
            host, port = server
            if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
                return f"{scheme}://{host}"
            else:
                return f"{scheme}://{host}:{port}"
        else:
            return f"{scheme}://localhost"

    @property
    def headers(self) -> Dict[str, str]:
        """Request headers."""
        if not hasattr(self, "_parsed_headers"):
            self._parsed_headers = {
                name.decode("latin1").lower(): value.decode("latin1")
                for name, value in self.scope.get("headers", [])
            }
        return self._parsed_headers

    @property
    def query_params(self) -> Dict[str, Union[str, List[str]]]:
        """Query parameters."""
        if self._query_params is None:
            query_string = self.scope.get("query_string", b"").decode("latin1")
            parsed = parse_qs(query_string, keep_blank_values=True)

            # Convert single-item lists to strings
            self._query_params = {}
            for key, values in parsed.items():
                if len(values) == 1:
                    self._query_params[key] = values[0]
                else:
                    self._query_params[key] = values

        return self._query_params

    @property
    def path_params(self) -> Dict[str, Any]:
        """Path parameters extracted from route."""
        return self._path_params

    @path_params.setter
    def path_params(self, value: Dict[str, Any]) -> None:
        """Set path parameters."""
        self._path_params = value

    @property
    def cookies(self) -> Dict[str, str]:
        """Request cookies."""
        if not hasattr(self, "_cookies"):
            self._cookies = {}
            cookie_header = self.headers.get("cookie", "")

            for chunk in cookie_header.split(";"):
                if "=" in chunk:
                    key, value = chunk.strip().split("=", 1)
                    self._cookies[key] = unquote_plus(value)

        return self._cookies

    @property
    def client(self) -> Optional[typing.Tuple[str, int]]:
        """Client connection info (host, port)."""
        return self.scope.get("client")

    @property
    def auth(self) -> Any:
        """Authentication info (if middleware sets it)."""
        return getattr(self, "_auth", None)

    @auth.setter
    def auth(self, value: Any) -> None:
        """Set authentication info."""
        self._auth = value

    @property
    def user(self) -> Any:
        """User object (if authentication middleware sets it)."""
        return getattr(self, "_user", None)

    @user.setter
    def user(self, value: Any) -> None:
        """Set user object."""
        self._user = value

    @property
    def session(self) -> Dict[str, Any]:
        """Session data (if session middleware is used)."""
        if not hasattr(self, "_session"):
            self._session = {}
        return self._session

    @session.setter
    def session(self, value: Dict[str, Any]) -> None:
        """Set session data."""
        self._session = value

    # URL components
    @property
    def scheme(self) -> str:
        """URL scheme (http/https)."""
        return self.scope.get("scheme", "http")

    @property
    def path(self) -> str:
        """URL path."""
        return self.scope.get("path", "/")

    @property
    def query_string(self) -> bytes:
        """Raw query string as bytes."""
        return self.scope.get("query_string", b"")

    # Content properties
    @property
    def content_type(self) -> Optional[str]:
        """Content-Type header value."""
        return self.headers.get("content-type")

    @property
    def charset(self) -> str:
        """Character encoding from Content-Type header."""
        content_type = self.content_type
        if content_type:
            parts = content_type.split(";")
            for part in parts[1:]:
                if "charset=" in part:
                    return part.split("=", 1)[1].strip()
        return "utf-8"

    # Body access methods
    async def body(self) -> bytes:
        """Get raw request body as bytes."""
        if self._body is None:
            if not self._receive:
                raise RuntimeError("Request receive callable not available")

            body_parts = []

            while True:
                message = await self._receive()

                if message["type"] == "http.request":
                    body_parts.append(message.get("body", b""))
                    if not message.get("more_body", False):
                        break
                elif message["type"] == "http.disconnect":
                    break

            self._body = b"".join(body_parts)

        return self._body

    async def json(self) -> Any:
        """Parse request body as JSON."""
        if self._json is None:
            body = await self.body()
            if not body:
                raise ValueError("Request body is empty")

            try:
                text = body.decode(self.charset)
                self._json = json.loads(text)
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                raise ValueError(f"Invalid JSON in request body: {e}")

        return self._json

    async def form(self) -> Dict[str, Union[str, List[str]]]:
        """Parse request body as form data."""
        if self._form is None:
            body = await self.body()
            text = body.decode(self.charset)

            parsed = parse_qs(text, keep_blank_values=True)

            # Convert single-item lists to strings
            self._form = {}
            for key, values in parsed.items():
                if len(values) == 1:
                    self._form[key] = values[0]
                else:
                    self._form[key] = values

        return self._form

    async def stream(self) -> typing.AsyncIterator[bytes]:
        """Stream request body in chunks."""
        if not self._receive:
            raise RuntimeError("Request receive callable not available")

        while True:
            message = await self._receive()

            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                if chunk:
                    yield chunk
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

    async def is_disconnected(self) -> bool:
        """Check if client has disconnected."""
        if not self._receive:
            return False

        try:
            message = await self._receive()
            return message.get("type") == "http.disconnect"
        except:
            return True

    # Convenience methods
    def accepts(self, media_type: str) -> bool:
        """Check if client accepts given media type."""
        accept = self.headers.get("accept", "")
        return media_type in accept or "*/*" in accept

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get header value with optional default."""
        return self.headers.get(name.lower(), default)

    def get_query_param(
        self, name: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Get query parameter value."""
        value = self.query_params.get(name, default)
        if isinstance(value, list):
            return value[0] if value else default
        return value

    def get_path_param(self, name: str, default: Any = None) -> Any:
        """Get path parameter value."""
        return self.path_params.get(name, default)

    # State management
    def __setitem__(self, key: str, value: Any) -> None:
        """Set state value."""
        self.state[key] = value

    def __getitem__(self, key: str) -> Any:
        """Get state value."""
        return self.state[key]

    def __contains__(self, key: str) -> bool:
        """Check if state contains key."""
        return key in self.state

    def get(self, key: str, default: Any = None) -> Any:
        """Get state value with default."""
        return self.state.get(key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        """Get state value or set and return default."""
        return self.state.setdefault(key, default)

    def __repr__(self) -> str:
        return f"<Request {self.method} {self.path}>"
