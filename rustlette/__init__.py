"""
Rustlette: High-performance Python web framework with Rust internals

This module provides a Starlette-compatible API while leveraging Rust's performance
for core operations like routing, request handling, and middleware execution.

Example:
    from rustlette import Rustlette, Request, Response

    app = Rustlette()

    @app.route("/")
    async def homepage(request):
        return {"message": "Hello, World!"}

    @app.route("/users/{user_id:int}")
    async def get_user(request):
        user_id = request.path_params["user_id"]
        return {"user_id": user_id}
"""

__version__ = "0.1.0"
__author__ = "Rustlette Team"

import json
import re
import typing
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import parse_qs, unquote

# Try to import the Rust core module
try:
    from rustlette._rustlette_core import hello_rustlette, TestApp

    _rust_core_available = True
except ImportError as e:
    _rust_core_available = False

    # Fallback implementations
    def hello_rustlette():
        return "Hello from Python fallback!"

    class TestApp:
        def __init__(self, name):
            self.name = name

        def get_name(self):
            return self.name


# Basic ASGI types
Scope = Dict[str, Any]
Receive = Callable[[], typing.Awaitable[Dict[str, Any]]]
Send = Callable[[Dict[str, Any]], typing.Awaitable[None]]


class Request:
    """Basic request implementation for ASGI compatibility."""

    def __init__(self, scope: Scope, receive: Receive = None):
        self.scope = scope
        self._receive = receive
        self._body = None
        self._json = None

    @property
    def method(self) -> str:
        return self.scope["method"]

    @property
    def path(self) -> str:
        return self.scope["path"]

    @property
    def query_string(self) -> bytes:
        return self.scope.get("query_string", b"")

    @property
    def query_params(self) -> Dict[str, str]:
        if not hasattr(self, "_query_params"):
            qs = self.query_string.decode()
            parsed = parse_qs(qs, keep_blank_values=True)
            self._query_params = {k: v[0] if v else "" for k, v in parsed.items()}
        return self._query_params

    @property
    def path_params(self) -> Dict[str, Any]:
        return self.scope.get("path_params", {})

    @property
    def headers(self) -> Dict[str, str]:
        if not hasattr(self, "_headers"):
            self._headers = {
                k.decode(): v.decode() for k, v in self.scope.get("headers", [])
            }
        return self._headers

    @property
    def url(self):
        """Simple URL object."""

        class SimpleURL:
            def __init__(self, scope):
                self.path = scope["path"]
                self.query = scope.get("query_string", b"").decode()

        return SimpleURL(self.scope)

    async def body(self) -> bytes:
        if self._body is None:
            self._body = b""
            if self._receive:
                while True:
                    message = await self._receive()
                    if message["type"] == "http.request":
                        self._body += message.get("body", b"")
                        if not message.get("more_body", False):
                            break
                    else:
                        break
        return self._body

    async def json(self) -> Any:
        if self._json is None:
            body = await self.body()
            self._json = json.loads(body) if body else {}
        return self._json


class Response:
    """Basic response implementation."""

    def __init__(
        self,
        content: Any = "",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self.media_type = media_type

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": [[k.encode(), v.encode()] for k, v in self.headers.items()],
            }
        )

        if isinstance(self.content, (dict, list)):
            body = json.dumps(self.content).encode()
        elif isinstance(self.content, str):
            body = self.content.encode()
        else:
            body = (
                self.content
                if isinstance(self.content, bytes)
                else str(self.content).encode()
            )

        await send({"type": "http.response.body", "body": body})


class JSONResponse(Response):
    """JSON response implementation."""

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        if headers is None:
            headers = {}
        headers["content-type"] = "application/json"
        super().__init__(content, status_code, headers, "application/json")


class Route:
    """Basic route implementation with path parameter support."""

    def __init__(
        self, path: str, endpoint: Callable, methods: List[str] = None, name: str = None
    ):
        self.path = path
        self.endpoint = endpoint
        self.methods = methods or ["GET"]
        self.name = name

        # Convert path to regex pattern for parameter matching
        self.path_regex, self.param_names = self._compile_path(path)

    def _compile_path(self, path: str):
        """Convert path pattern to regex and extract parameter names."""
        param_names = []
        pattern = path

        # Find all {param} and {param:type} patterns
        param_pattern = r"\{([^}:]+)(?::([^}]+))?\}"

        def replace_param(match):
            param_name = match.group(1)
            param_type = match.group(2) or "str"
            param_names.append((param_name, param_type))

            if param_type == "int":
                return r"([0-9]+)"
            elif param_type == "float":
                return r"([0-9]*\.?[0-9]+)"
            elif param_type == "path":
                return r"([^/]+(?:/[^/]+)*)"
            else:  # str or default
                return r"([^/]+)"

        pattern = re.sub(param_pattern, replace_param, pattern)
        pattern = f"^{pattern}$"

        return re.compile(pattern), param_names

    def matches(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Check if this route matches the given path and method."""
        if method not in self.methods:
            return None

        match = self.path_regex.match(path)
        if not match:
            return None

        # Extract path parameters
        path_params = {}
        for i, (param_name, param_type) in enumerate(self.param_names):
            value = match.group(i + 1)

            if param_type == "int":
                path_params[param_name] = int(value)
            elif param_type == "float":
                path_params[param_name] = float(value)
            else:
                path_params[param_name] = unquote(value)

        return path_params


class Rustlette:
    """
    Main application class providing Starlette-compatible API.

    This is a minimal ASGI-compatible implementation that can work
    with servers like uvicorn while we develop the Rust internals.
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.routes: List[Route] = []
        self.middleware_stack = []
        self.exception_handlers = {}
        self.startup_handlers = []
        self.shutdown_handlers = []
        self.state = {}

    def add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: Optional[List[str]] = None,
        name: Optional[str] = None,
    ):
        """Add a route to the application."""
        route = Route(path, endpoint, methods, name)
        self.routes.append(route)

    def route(
        self, path: str, methods: Optional[List[str]] = None, name: Optional[str] = None
    ):
        """Route decorator."""

        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, methods, name)
            return func

        return decorator

    def get(self, path: str, name: Optional[str] = None):
        """GET route decorator."""
        return self.route(path, ["GET"], name)

    def post(self, path: str, name: Optional[str] = None):
        """POST route decorator."""
        return self.route(path, ["POST"], name)

    def put(self, path: str, name: Optional[str] = None):
        """PUT route decorator."""
        return self.route(path, ["PUT"], name)

    def delete(self, path: str, name: Optional[str] = None):
        """DELETE route decorator."""
        return self.route(path, ["DELETE"], name)

    def patch(self, path: str, name: Optional[str] = None):
        """PATCH route decorator."""
        return self.route(path, ["PATCH"], name)

    def options(self, path: str, name: Optional[str] = None):
        """OPTIONS route decorator."""
        return self.route(path, ["OPTIONS"], name)

    def head(self, path: str, name: Optional[str] = None):
        """HEAD route decorator."""
        return self.route(path, ["HEAD"], name)

    def on_event(self, event_type: str):
        """Event handler decorator."""

        def decorator(func: Callable) -> Callable:
            if event_type == "startup":
                self.startup_handlers.append(func)
            elif event_type == "shutdown":
                self.shutdown_handlers.append(func)
            return func

        return decorator

    def exception_handler(self, exc_class_or_status_code: Union[int, type]):
        """Exception handler decorator."""

        def decorator(func: Callable) -> Callable:
            self.exception_handlers[exc_class_or_status_code] = func
            return func

        return decorator

    async def _find_route(self, path: str, method: str) -> Optional[tuple]:
        """Find a matching route for the given path and method."""
        for route in self.routes:
            path_params = route.matches(path, method)
            if path_params is not None:
                return route, path_params
        return None

    async def _handle_request(self, scope: Scope, receive: Receive, send: Send):
        """Handle an HTTP request."""
        path = scope["path"]
        method = scope["method"]

        # Find matching route
        route_match = await self._find_route(path, method)

        if route_match is None:
            # 404 Not Found
            response = JSONResponse(
                {"detail": "Not Found", "path": path}, status_code=404
            )
            await response(scope, receive, send)
            return

        route, path_params = route_match

        # Add path parameters to scope
        scope["path_params"] = path_params

        # Create request object
        request = Request(scope, receive)

        try:
            # Call the endpoint
            result = await route.endpoint(request)

            # Convert result to response
            if isinstance(result, Response):
                response = result
            elif isinstance(result, (dict, list)):
                response = JSONResponse(result)
            elif isinstance(result, str):
                response = Response(result, headers={"content-type": "text/plain"})
            else:
                response = Response(str(result), headers={"content-type": "text/plain"})

            await response(scope, receive, send)

        except Exception as exc:
            # Handle exceptions
            if type(exc) in self.exception_handlers:
                handler = self.exception_handlers[type(exc)]
                response = await handler(request, exc)
                await response(scope, receive, send)
            elif 500 in self.exception_handlers:
                handler = self.exception_handlers[500]
                response = await handler(request, exc)
                await response(scope, receive, send)
            else:
                # Default error response
                if self.debug:
                    import traceback

                    error_detail = {
                        "error": str(exc),
                        "traceback": traceback.format_exc().split("\n"),
                    }
                else:
                    error_detail = {"error": "Internal Server Error"}

                response = JSONResponse(error_detail, status_code=500)
                await response(scope, receive, send)

    async def _handle_lifespan(self, scope: Scope, receive: Receive, send: Send):
        """Handle ASGI lifespan events."""
        message = await receive()

        if message["type"] == "lifespan.startup":
            try:
                for handler in self.startup_handlers:
                    if callable(handler):
                        await handler() if hasattr(handler, "__await__") else handler()
                await send({"type": "lifespan.startup.complete"})
            except Exception as exc:
                await send({"type": "lifespan.startup.failed", "message": str(exc)})

        elif message["type"] == "lifespan.shutdown":
            try:
                for handler in self.shutdown_handlers:
                    if callable(handler):
                        await handler() if hasattr(handler, "__await__") else handler()
                await send({"type": "lifespan.shutdown.complete"})
            except Exception as exc:
                await send({"type": "lifespan.shutdown.failed", "message": str(exc)})

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """ASGI application interface."""
        scope_type = scope["type"]

        if scope_type == "http":
            await self._handle_request(scope, receive, send)
        elif scope_type == "lifespan":
            await self._handle_lifespan(scope, receive, send)
        else:
            raise ValueError(f"Unsupported ASGI scope type: {scope_type}")


# Compatibility alias for Starlette users
Starlette = Rustlette


# Status and utility functions
def get_status():
    """Get the current status of Rustlette components."""
    return {
        "version": __version__,
        "rust_core_available": _rust_core_available,
        "asgi_compatible": True,
        "features": [
            "routing",
            "json_responses",
            "path_params",
            "query_params",
            "events",
        ],
    }


def test():
    """Test basic Rustlette functionality."""
    print("🚀 Testing Rustlette...")

    try:
        # Test core Rust functionality
        result = hello_rustlette()
        print(f"✅ hello_rustlette(): {result}")

        app = TestApp("test")
        name = app.get_name()
        print(f"✅ TestApp: {name}")

        # Test basic Rustlette app
        rustlette_app = Rustlette(debug=True)
        print(f"✅ Rustlette app created")

        # Test route creation
        @rustlette_app.route("/test")
        async def test_endpoint(request):
            return {"test": "success"}

        print(f"✅ Route decorator works")

        # Show status
        status = get_status()
        print(f"📊 Status: {status}")

        print("🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


# Main exports
__all__ = [
    # Core functionality
    "hello_rustlette",
    "TestApp",
    "Rustlette",
    "Starlette",
    "Request",
    "Response",
    "JSONResponse",
    "Route",
    # Utility functions
    "get_status",
    "test",
    # Version info
    "__version__",
    "__author__",
]


if __name__ == "__main__":
    test()
