"""
Middleware components providing Starlette-compatible interface
"""

import typing
from typing import Any, Callable, Dict, List, Optional, Union

from ._rustlette_core import Middleware as _Middleware, MiddlewareStack
from .requests import Request
from .responses import PlainTextResponse, Response
from .types import ASGIApp, Scope, Receive, Send


class Middleware:
    """
    Middleware wrapper for Python middleware functions.
    """

    def __init__(
        self,
        middleware: Union[Callable, type],
        name: Optional[str] = None,
        **options: Any,
    ) -> None:
        """
        Initialize middleware.

        Args:
            middleware: Middleware function or class
            name: Optional middleware name
            **options: Middleware options
        """
        if isinstance(middleware, type):
            # Class-based middleware
            self.middleware = middleware(**options)
        else:
            # Function-based middleware
            self.middleware = middleware

        self.name = name or getattr(middleware, "__name__", "Middleware")
        self.options = options

        # Create Rust middleware wrapper
        self._rust_middleware = _Middleware(self.middleware, self.name)

    @property
    def func(self) -> Callable:
        """Get the underlying middleware function."""
        return self.middleware

    def __repr__(self) -> str:
        return f"Middleware({self.name})"


class BaseHTTPMiddleware:
    """
    Base class for HTTP middleware.
    """

    def __init__(self, app: ASGIApp, dispatch: Optional[Callable] = None) -> None:
        """
        Initialize middleware.

        Args:
            app: ASGI application
            dispatch: Optional dispatch function
        """
        self.app = app
        self.dispatch_func = dispatch

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        response = await self.dispatch(request, self.call_next)
        await response(scope, receive, send)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], typing.Awaitable[Response]],
    ) -> Response:
        """
        Override this method to implement middleware logic.

        Args:
            request: The request object
            call_next: Function to call the next middleware/handler

        Returns:
            Response object
        """
        if self.dispatch_func:
            return await self.dispatch_func(request, call_next)
        return await call_next(request)

    async def call_next(self, request: Request) -> Response:
        """Call the next middleware or endpoint."""
        # This would need integration with the Rust middleware stack
        # For now, return a placeholder
        return PlainTextResponse("Middleware call_next not implemented")


class CORSMiddleware:
    """
    CORS (Cross-Origin Resource Sharing) middleware.
    """

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        allow_origin_regex: Optional[str] = None,
        expose_headers: List[str] = None,
        max_age: int = 600,
    ) -> None:
        """
        Initialize CORS middleware.

        Args:
            app: ASGI application
            allow_origins: List of allowed origins
            allow_methods: List of allowed HTTP methods
            allow_headers: List of allowed headers
            allow_credentials: Whether to allow credentials
            allow_origin_regex: Regex pattern for allowed origins
            expose_headers: List of headers to expose
            max_age: Max age for preflight cache
        """
        self.app = app
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
        ]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.allow_origin_regex = allow_origin_regex
        self.expose_headers = expose_headers or []
        self.max_age = max_age

        if allow_origin_regex:
            import re

            self.origin_regex = re.compile(allow_origin_regex)
        else:
            self.origin_regex = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        origin = request.headers.get("origin")

        if request.method == "OPTIONS" and origin:
            # Preflight request
            response = self.preflight_response(request)
            await response(scope, receive, send)
        else:
            # Regular request
            response = await self.app(scope, receive, send)

            # Add CORS headers to response
            if origin and self.is_allowed_origin(origin):
                # This would need proper response modification
                pass

    def is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed."""
        if "*" in self.allow_origins:
            return True

        if origin in self.allow_origins:
            return True

        if self.origin_regex and self.origin_regex.match(origin):
            return True

        return False

    def preflight_response(self, request: Request) -> Response:
        """Create preflight response."""
        headers = {}
        origin = request.headers.get("origin")

        if origin and self.is_allowed_origin(origin):
            headers["access-control-allow-origin"] = origin

        if self.allow_credentials:
            headers["access-control-allow-credentials"] = "true"

        headers["access-control-allow-methods"] = ", ".join(self.allow_methods)
        headers["access-control-allow-headers"] = ", ".join(self.allow_headers)
        headers["access-control-max-age"] = str(self.max_age)

        if self.expose_headers:
            headers["access-control-expose-headers"] = ", ".join(self.expose_headers)

        return PlainTextResponse("", status_code=200, headers=headers)


class TrustedHostMiddleware:
    """
    Middleware to enforce trusted hosts.
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: List[str] = None,
        www_redirect: bool = True,
    ) -> None:
        """
        Initialize trusted host middleware.

        Args:
            app: ASGI application
            allowed_hosts: List of allowed hostnames
            www_redirect: Whether to redirect www to non-www
        """
        self.app = app
        self.allowed_hosts = allowed_hosts or ["*"]
        self.www_redirect = www_redirect

        # Compile host patterns
        import re

        self.host_patterns = []
        for host in self.allowed_hosts:
            if host == "*":
                self.host_patterns.append(re.compile(".*"))
            else:
                # Escape dots and allow wildcards
                pattern = host.replace(".", r"\.").replace("*", ".*")
                self.host_patterns.append(re.compile(f"^{pattern}$"))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface."""
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        host = headers.get(b"host", b"").decode("latin1")

        if not self.is_allowed_host(host):
            # Invalid host
            if scope["type"] == "http":
                response = PlainTextResponse("Invalid host header", status_code=400)
                await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def is_allowed_host(self, host: str) -> bool:
        """Check if host is allowed."""
        if not host:
            return False

        for pattern in self.host_patterns:
            if pattern.match(host):
                return True

        return False


class GZipMiddleware:
    """
    GZip compression middleware.
    """

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compresslevel: int = 9,
    ) -> None:
        """
        Initialize GZip middleware.

        Args:
            app: ASGI application
            minimum_size: Minimum response size to compress
            compresslevel: Compression level (1-9)
        """
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        accept_encoding = request.headers.get("accept-encoding", "")

        if "gzip" not in accept_encoding:
            await self.app(scope, receive, send)
            return

        # This would need proper implementation with response interception
        await self.app(scope, receive, send)


class SessionMiddleware:
    """
    Session middleware using secure cookies.
    """

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        session_cookie: str = "session",
        max_age: Optional[int] = 14 * 24 * 60 * 60,  # 14 days
        path: str = "/",
        same_site: str = "lax",
        https_only: bool = False,
    ) -> None:
        """
        Initialize session middleware.

        Args:
            app: ASGI application
            secret_key: Secret key for signing cookies
            session_cookie: Cookie name for session
            max_age: Maximum age of session in seconds
            path: Cookie path
            same_site: SameSite cookie attribute
            https_only: Whether to set Secure flag
        """
        self.app = app
        self.secret_key = secret_key
        self.session_cookie = session_cookie
        self.max_age = max_age
        self.path = path
        self.same_site = same_site
        self.https_only = https_only

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # This would need proper session implementation
        # For now, just pass through
        await self.app(scope, receive, send)


# Common middleware factory functions
def cors(
    allow_origins: List[str] = None,
    allow_methods: List[str] = None,
    allow_headers: List[str] = None,
    allow_credentials: bool = False,
    allow_origin_regex: Optional[str] = None,
    expose_headers: List[str] = None,
    max_age: int = 600,
) -> Callable[[ASGIApp], CORSMiddleware]:
    """
    Factory function for CORS middleware.
    """

    def create_middleware(app: ASGIApp) -> CORSMiddleware:
        return CORSMiddleware(
            app=app,
            allow_origins=allow_origins,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            allow_credentials=allow_credentials,
            allow_origin_regex=allow_origin_regex,
            expose_headers=expose_headers,
            max_age=max_age,
        )

    return create_middleware


def trusted_host(
    allowed_hosts: List[str],
    www_redirect: bool = True,
) -> Callable[[ASGIApp], TrustedHostMiddleware]:
    """
    Factory function for trusted host middleware.
    """

    def create_middleware(app: ASGIApp) -> TrustedHostMiddleware:
        return TrustedHostMiddleware(
            app=app,
            allowed_hosts=allowed_hosts,
            www_redirect=www_redirect,
        )

    return create_middleware


def gzip(
    minimum_size: int = 500,
    compresslevel: int = 9,
) -> Callable[[ASGIApp], GZipMiddleware]:
    """
    Factory function for GZip middleware.
    """

    def create_middleware(app: ASGIApp) -> GZipMiddleware:
        return GZipMiddleware(
            app=app,
            minimum_size=minimum_size,
            compresslevel=compresslevel,
        )

    return create_middleware


def session(
    secret_key: str,
    session_cookie: str = "session",
    max_age: Optional[int] = 14 * 24 * 60 * 60,
    path: str = "/",
    same_site: str = "lax",
    https_only: bool = False,
) -> Callable[[ASGIApp], SessionMiddleware]:
    """
    Factory function for session middleware.
    """

    def create_middleware(app: ASGIApp) -> SessionMiddleware:
        return SessionMiddleware(
            app=app,
            secret_key=secret_key,
            session_cookie=session_cookie,
            max_age=max_age,
            path=path,
            same_site=same_site,
            https_only=https_only,
        )

    return create_middleware
