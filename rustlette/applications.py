"""
Rustlette application wrapper providing Starlette-compatible API
"""

import inspect
import typing
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from ._rustlette_core import RustletteApp as _RustletteApp
from .exceptions import HTTPException
from .middleware import Middleware
from .requests import Request
from .responses import PlainTextResponse, Response
from .routing import BaseRoute, Route, Router
from .types import ASGIApp, Lifespan, Receive, Scope, Send


class Rustlette:
    """
    Main application class providing Starlette-compatible API.

    This class wraps the Rust implementation while maintaining full
    compatibility with Starlette's interface.
    """

    def __init__(
        self,
        debug: bool = False,
        routes: Optional[Sequence[BaseRoute]] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        exception_handlers: Optional[
            Dict[Union[int, type], Callable[[Request, Exception], Response]]
        ] = None,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        lifespan: Optional[Lifespan] = None,
    ) -> None:
        """
        Initialize the Rustlette application.

        Args:
            debug: Enable debug mode
            routes: Initial routes to add
            middleware: Initial middleware to add
            exception_handlers: Exception handlers mapping
            on_startup: Startup event handlers
            on_shutdown: Shutdown event handlers
            lifespan: Lifespan context manager
        """
        # Create the Rust core application
        self._app = _RustletteApp(debug=debug)

        # Store Python-level state
        self.debug = debug
        self.state = {}
        self.exception_handlers = exception_handlers or {}
        self.middleware_stack = list(middleware or [])
        self.startup_handlers = list(on_startup or [])
        self.shutdown_handlers = list(on_shutdown or [])
        self.lifespan = lifespan

        # Add initial routes
        if routes:
            for route in routes:
                self.routes.append(route)

        # Add initial middleware
        for middleware in self.middleware_stack:
            self._app.add_middleware(middleware.func, middleware.name)

        # Add event handlers
        for handler in self.startup_handlers:
            self._app.add_event_handler("startup", handler)

        for handler in self.shutdown_handlers:
            self._app.add_event_handler("shutdown", handler)

        # Add exception handlers
        for exc_class, handler in self.exception_handlers.items():
            self._app.add_exception_handler(exc_class, handler)

    @property
    def routes(self) -> List[BaseRoute]:
        """Get the list of routes."""
        # This would need to be synchronized with the Rust router
        # For now, return empty list - in full implementation would maintain sync
        return []

    def add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: Optional[List[str]] = None,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> None:
        """Add a route to the application."""
        self._app.add_route(
            path=path,
            endpoint=endpoint,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
        )

    def route(
        self,
        path: str,
        methods: Optional[List[str]] = None,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """Route decorator."""

        def decorator(func: Callable) -> Callable:
            self.add_route(
                path=path,
                endpoint=func,
                methods=methods,
                name=name,
                include_in_schema=include_in_schema,
            )
            return func

        return decorator

    def get(
        self,
        path: str,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """GET route decorator."""
        return self.route(
            path=path,
            methods=["GET"],
            name=name,
            include_in_schema=include_in_schema,
        )

    def post(
        self,
        path: str,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """POST route decorator."""
        return self.route(
            path=path,
            methods=["POST"],
            name=name,
            include_in_schema=include_in_schema,
        )

    def put(
        self,
        path: str,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """PUT route decorator."""
        return self.route(
            path=path,
            methods=["PUT"],
            name=name,
            include_in_schema=include_in_schema,
        )

    def patch(
        self,
        path: str,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """PATCH route decorator."""
        return self.route(
            path=path,
            methods=["PATCH"],
            name=name,
            include_in_schema=include_in_schema,
        )

    def delete(
        self,
        path: str,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """DELETE route decorator."""
        return self.route(
            path=path,
            methods=["DELETE"],
            name=name,
            include_in_schema=include_in_schema,
        )

    def head(
        self,
        path: str,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """HEAD route decorator."""
        return self.route(
            path=path,
            methods=["HEAD"],
            name=name,
            include_in_schema=include_in_schema,
        )

    def options(
        self,
        path: str,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """OPTIONS route decorator."""
        return self.route(
            path=path,
            methods=["OPTIONS"],
            name=name,
            include_in_schema=include_in_schema,
        )

    def trace(
        self,
        path: str,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """TRACE route decorator."""
        return self.route(
            path=path,
            methods=["TRACE"],
            name=name,
            include_in_schema=include_in_schema,
        )

    def websocket_route(
        self,
        path: str,
        name: Optional[str] = None,
    ) -> Callable:
        """WebSocket route decorator."""

        def decorator(func: Callable) -> Callable:
            # WebSocket routes would be handled differently
            # For now, just store the function
            return func

        return decorator

    def mount(
        self,
        path: str,
        app: ASGIApp,
        name: Optional[str] = None,
    ) -> None:
        """Mount a sub-application."""
        self._app.mount(path=path, app=app, name=name)

    def add_middleware(
        self,
        middleware_class: type,
        **options: Any,
    ) -> None:
        """Add middleware to the application."""
        middleware = middleware_class(**options)
        self.middleware_stack.append(Middleware(middleware))
        self._app.add_middleware(middleware)

    def middleware(self, middleware_type: str) -> Callable:
        """Middleware decorator."""

        def decorator(func: Callable) -> Callable:
            if middleware_type == "http":
                self.add_middleware(BaseHTTPMiddleware, dispatch=func)
            else:
                raise ValueError(f"Unknown middleware type: {middleware_type}")
            return func

        return decorator

    def add_exception_handler(
        self,
        exc_class_or_status_code: Union[int, type],
        handler: Callable[[Request, Exception], Response],
    ) -> None:
        """Add an exception handler."""
        self.exception_handlers[exc_class_or_status_code] = handler
        self._app.add_exception_handler(exc_class_or_status_code, handler)

    def exception_handler(
        self,
        exc_class_or_status_code: Union[int, type],
    ) -> Callable:
        """Exception handler decorator."""

        def decorator(func: Callable) -> Callable:
            self.add_exception_handler(exc_class_or_status_code, func)
            return func

        return decorator

    def add_event_handler(
        self,
        event_type: str,
        func: Callable[[], Any],
    ) -> None:
        """Add an event handler."""
        if event_type == "startup":
            self.startup_handlers.append(func)
        elif event_type == "shutdown":
            self.shutdown_handlers.append(func)
        else:
            raise ValueError(f"Unknown event type: {event_type}")

        self._app.add_event_handler(event_type, func)

    def on_event(self, event_type: str) -> Callable:
        """Event handler decorator."""

        def decorator(func: Callable) -> Callable:
            self.add_event_handler(event_type, func)
            return func

        return decorator

    def url_path_for(self, name: str, **path_params: Any) -> str:
        """Generate URL path for a named route."""
        return self._app.url_path_for(name, path_params)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI application interface."""
        # Create ASGI wrapper and delegate
        asgi_app = self._app.asgi()
        await asgi_app(scope, receive, send)

    def __repr__(self) -> str:
        return f"Rustlette(debug={self.debug})"


# Import middleware base class to avoid circular imports
class BaseHTTPMiddleware:
    """Base class for HTTP middleware."""

    def __init__(self, app: ASGIApp, dispatch: Optional[Callable] = None) -> None:
        self.app = app
        self.dispatch_func = dispatch

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if self.dispatch_func:
            request = Request(scope, receive)
            response = await self.dispatch_func(request, self.call_next)
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)

    async def call_next(self, request: Request) -> Response:
        """Call the next middleware or endpoint."""
        # This would need proper implementation
        return PlainTextResponse("Not implemented")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], typing.Awaitable[Response]],
    ) -> Response:
        """Override this method to implement middleware logic."""
        return await call_next(request)
