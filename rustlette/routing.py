"""
Routing components providing Starlette-compatible interface
"""

import inspect
import typing
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from ._rustlette_core import Route as _Route, Router as _Router
from .convertors import Convertor, get_convertor
from .requests import Request
from .responses import PlainTextResponse, Response
from .types import ASGIApp, Scope, Receive, Send


class Match:
    """Route match result."""

    def __init__(self, match_type: str, path_params: Dict[str, Any] = None) -> None:
        self.match_type = match_type
        self.path_params = path_params or {}


class BaseRoute:
    """Base class for all route types."""

    def matches(self, scope: Scope) -> typing.Tuple[Match, Scope]:
        """Check if this route matches the given scope."""
        raise NotImplementedError  # pragma: no cover

    def url_path_for(self, name: str, **path_params: Any) -> str:
        """Generate URL path for named route."""
        raise NotImplementedError  # pragma: no cover

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle the request."""
        raise NotImplementedError  # pragma: no cover

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface."""
        await self.handle(scope, receive, send)


class Route(BaseRoute):
    """HTTP route."""

    def __init__(
        self,
        path: str,
        endpoint: Callable,
        methods: Optional[List[str]] = None,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> None:
        """
        Initialize route.

        Args:
            path: URL path pattern with optional parameters
            endpoint: Callable endpoint (function or class)
            methods: Allowed HTTP methods
            name: Route name for URL generation
            include_in_schema: Whether to include in OpenAPI schema
        """
        assert path.startswith("/"), "Routed paths must start with '/'"

        self.path = path
        self.endpoint = endpoint
        self.methods = methods or ["GET"]
        self.name = name
        self.include_in_schema = include_in_schema

        # Normalize methods
        self.methods = [method.upper() for method in self.methods]
        if "GET" in self.methods and "HEAD" not in self.methods:
            self.methods.append("HEAD")

        # Compile path pattern
        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

        # Inspect endpoint
        if inspect.isfunction(endpoint) or inspect.ismethod(endpoint):
            # Function endpoint
            self.is_coroutine = inspect.iscoroutinefunction(endpoint)
        elif inspect.isclass(endpoint):
            # Class-based endpoint
            self.is_coroutine = inspect.iscoroutinefunction(endpoint.__call__)
        else:
            # Callable object
            self.is_coroutine = inspect.iscoroutinefunction(endpoint.__call__)

    def matches(self, scope: Scope) -> typing.Tuple[Match, Scope]:
        """Check if route matches the scope."""
        if scope["type"] not in ("http", "websocket"):
            return Match("none"), scope

        method = scope.get("method", "GET")
        if method not in self.methods:
            return Match("none"), scope

        path = scope["path"]
        match = self.path_regex.match(path)
        if match:
            matched_params = match.groupdict()
            for key, value in matched_params.items():
                matched_params[key] = self.param_convertors[key].convert(value)

            path_params = dict(scope.get("path_params", {}))
            path_params.update(matched_params)
            child_scope = {**scope, "path_params": path_params}
            return Match("full", matched_params), child_scope

        return Match("none"), scope

    def url_path_for(self, name: str, **path_params: Any) -> str:
        """Generate URL path for this route."""
        if name != self.name:
            raise ValueError(f"Route name '{self.name}' does not match '{name}'")

        path = self.path_format
        for key, value in path_params.items():
            convertor = self.param_convertors.get(key)
            if convertor:
                value = convertor.to_string(value)
            path = path.replace(f"{{{key}}}", str(value))

        return path

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle the request."""
        if scope["method"] == "HEAD":
            # For HEAD requests, we'll call the endpoint but not send the body
            request = Request(scope, receive, send)

            if self.is_coroutine:
                response = await self.endpoint(request)
            else:
                response = self.endpoint(request)

            if not isinstance(response, Response):
                response = PlainTextResponse(str(response))

            # For HEAD, we need to send headers but no body
            await send(
                {
                    "type": "http.response.start",
                    "status": response.status_code,
                    "headers": [
                        (name.encode(), value.encode())
                        for name, value in response.headers.items()
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False,
                }
            )
        else:
            # Regular request handling
            request = Request(scope, receive, send)

            if self.is_coroutine:
                response = await self.endpoint(request)
            else:
                response = self.endpoint(request)

            if not isinstance(response, Response):
                # Convert return value to response
                if isinstance(response, str):
                    response = PlainTextResponse(response)
                elif isinstance(response, dict):
                    from .responses import JSONResponse

                    response = JSONResponse(response)
                else:
                    response = PlainTextResponse(str(response))

            await response(scope, receive, send)

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, Route)
            and self.path == other.path
            and self.methods == other.methods
        )

    def __repr__(self) -> str:
        methods_str = ",".join(self.methods)
        return f"Route(path='{self.path}', methods=[{methods_str}])"


class WebSocketRoute(BaseRoute):
    """WebSocket route."""

    def __init__(
        self,
        path: str,
        endpoint: Callable,
        name: Optional[str] = None,
    ) -> None:
        """
        Initialize WebSocket route.

        Args:
            path: URL path pattern
            endpoint: WebSocket endpoint
            name: Route name
        """
        assert path.startswith("/"), "Routed paths must start with '/'"

        self.path = path
        self.endpoint = endpoint
        self.name = name

        # Compile path pattern
        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

    def matches(self, scope: Scope) -> typing.Tuple[Match, Scope]:
        """Check if route matches the scope."""
        if scope["type"] != "websocket":
            return Match("none"), scope

        path = scope["path"]
        match = self.path_regex.match(path)
        if match:
            matched_params = match.groupdict()
            for key, value in matched_params.items():
                matched_params[key] = self.param_convertors[key].convert(value)

            path_params = dict(scope.get("path_params", {}))
            path_params.update(matched_params)
            child_scope = {**scope, "path_params": path_params}
            return Match("full", matched_params), child_scope

        return Match("none"), scope

    def url_path_for(self, name: str, **path_params: Any) -> str:
        """Generate URL path for this route."""
        if name != self.name:
            raise ValueError(f"Route name '{self.name}' does not match '{name}'")

        path = self.path_format
        for key, value in path_params.items():
            convertor = self.param_convertors.get(key)
            if convertor:
                value = convertor.to_string(value)
            path = path.replace(f"{{{key}}}", str(value))

        return path

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle WebSocket connection."""
        # WebSocket handling would be implemented here
        # For now, just call the endpoint
        websocket = WebSocket(scope, receive, send)
        await self.endpoint(websocket)


class Mount(BaseRoute):
    """Mount a sub-application at a path."""

    def __init__(
        self,
        path: str,
        app: ASGIApp,
        name: Optional[str] = None,
    ) -> None:
        """
        Initialize mount.

        Args:
            path: Mount path (should not end with '/')
            app: ASGI application to mount
            name: Mount name
        """
        assert path == "" or path.startswith("/"), "Mount path must start with '/'"
        assert not path.endswith("/"), "Mount path must not end with '/'"

        self.path = path.rstrip("/")
        self.app = app
        self.name = name

    def matches(self, scope: Scope) -> typing.Tuple[Match, Scope]:
        """Check if mount matches the scope."""
        if scope["type"] not in ("http", "websocket"):
            return Match("none"), scope

        path = scope["path"]

        if self.path == "":
            # Root mount matches everything
            return Match("full"), scope

        if path.startswith(self.path):
            # Check for exact match or path separator
            if len(path) == len(self.path) or path[len(self.path)] == "/":
                # Create child scope with adjusted path
                child_scope = dict(scope)
                child_scope["path"] = path[len(self.path) :]
                if not child_scope["path"].startswith("/"):
                    child_scope["path"] = "/" + child_scope["path"]

                # Adjust raw_path if present
                if "raw_path" in scope:
                    raw_path = scope["raw_path"]
                    if isinstance(raw_path, bytes):
                        mount_path_bytes = self.path.encode("utf-8")
                        if raw_path.startswith(mount_path_bytes):
                            child_scope["raw_path"] = raw_path[len(mount_path_bytes) :]
                            if not child_scope["raw_path"].startswith(b"/"):
                                child_scope["raw_path"] = b"/" + child_scope["raw_path"]

                return Match("full"), child_scope

        return Match("none"), scope

    def url_path_for(self, name: str, **path_params: Any) -> str:
        """Generate URL path for mounted route."""
        if name != self.name and hasattr(self.app, "url_path_for"):
            return self.path + self.app.url_path_for(name, **path_params)
        raise ValueError(f"No route named '{name}' found")

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle request by delegating to mounted app."""
        await self.app(scope, receive, send)


class Host(BaseRoute):
    """Route based on hostname."""

    def __init__(
        self,
        host: str,
        app: ASGIApp,
        name: Optional[str] = None,
    ) -> None:
        """
        Initialize host route.

        Args:
            host: Hostname pattern
            app: ASGI application
            name: Route name
        """
        self.host = host
        self.app = app
        self.name = name

        # Compile host pattern
        self.host_regex = self._compile_host_pattern(host)

    def _compile_host_pattern(self, host: str) -> typing.Pattern:
        """Compile host pattern to regex."""
        import re

        # Simple host pattern matching
        # Convert wildcards to regex
        pattern = host.replace("*", ".*")
        return re.compile(f"^{pattern}$")

    def matches(self, scope: Scope) -> typing.Tuple[Match, Scope]:
        """Check if host matches the scope."""
        headers = dict(scope.get("headers", []))
        host_header = headers.get(b"host", b"").decode("latin1")

        if host_header and self.host_regex.match(host_header):
            return Match("full"), scope

        return Match("none"), scope

    def url_path_for(self, name: str, **path_params: Any) -> str:
        """Generate URL path for hosted route."""
        if hasattr(self.app, "url_path_for"):
            return self.app.url_path_for(name, **path_params)
        raise ValueError(f"No route named '{name}' found")

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle request by delegating to hosted app."""
        await self.app(scope, receive, send)


class Router:
    """Router for managing routes."""

    def __init__(self, routes: Optional[Sequence[BaseRoute]] = None) -> None:
        """Initialize router with optional routes."""
        self.routes = list(routes or [])

    def add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: Optional[List[str]] = None,
        name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> None:
        """Add a route."""
        route = Route(
            path=path,
            endpoint=endpoint,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
        )
        self.routes.append(route)

    def add_websocket_route(
        self,
        path: str,
        endpoint: Callable,
        name: Optional[str] = None,
    ) -> None:
        """Add a WebSocket route."""
        route = WebSocketRoute(path=path, endpoint=endpoint, name=name)
        self.routes.append(route)

    def mount(
        self,
        path: str,
        app: ASGIApp,
        name: Optional[str] = None,
    ) -> None:
        """Mount a sub-application."""
        mount = Mount(path=path, app=app, name=name)
        self.routes.append(mount)

    def host(
        self,
        host: str,
        app: ASGIApp,
        name: Optional[str] = None,
    ) -> None:
        """Add host-based routing."""
        host_route = Host(host=host, app=app, name=name)
        self.routes.append(host_route)

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

    def websocket(
        self,
        path: str,
        name: Optional[str] = None,
    ) -> Callable:
        """WebSocket route decorator."""

        def decorator(func: Callable) -> Callable:
            self.add_websocket_route(path=path, endpoint=func, name=name)
            return func

        return decorator

    def url_path_for(self, name: str, **path_params: Any) -> str:
        """Generate URL path for named route."""
        for route in self.routes:
            try:
                if hasattr(route, "name") and route.name == name:
                    return route.url_path_for(name, **path_params)
            except ValueError:
                continue
        raise ValueError(f"No route named '{name}' found")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface."""
        # Find matching route
        for route in self.routes:
            match, child_scope = route.matches(scope)
            if match.match_type == "full":
                await route.handle(child_scope, receive, send)
                return

        # No route found
        if scope["type"] == "http":
            response = PlainTextResponse("Not Found", status_code=404)
            await response(scope, receive, send)


def compile_path(path: str) -> typing.Tuple[typing.Pattern, str, Dict[str, Convertor]]:
    """
    Compile a path pattern into a regex and parameter convertors.

    Returns:
        Tuple of (regex, format_string, convertors)
    """
    import re

    convertors = {}
    regex_parts = ["^"]
    format_parts = []

    idx = 0
    while idx < len(path):
        char = path[idx]

        if char == "{":
            # Find the end of the parameter
            end_idx = path.find("}", idx)
            if end_idx == -1:
                raise ValueError(f"Unclosed parameter in path: {path}")

            param_spec = path[idx + 1 : end_idx]

            # Parse parameter name and type
            if ":" in param_spec:
                param_name, convertor_type = param_spec.split(":", 1)
            else:
                param_name = param_spec
                convertor_type = "str"

            convertor = get_convertor(convertor_type)
            convertors[param_name] = convertor

            # Add to regex
            regex_parts.append(f"(?P<{param_name}>{convertor.regex})")

            # Add to format string
            format_parts.append(f"{{{param_name}}}")

            idx = end_idx + 1
        else:
            # Regular character - escape if needed for regex
            if char in ".*+?^${}[]|()":
                regex_parts.append("\\" + char)
            else:
                regex_parts.append(char)

            format_parts.append(char)
            idx += 1

    regex_parts.append("$")
    regex = re.compile("".join(regex_parts))
    format_string = "".join(format_parts)

    return regex, format_string, convertors


# Placeholder WebSocket class
class WebSocket:
    """WebSocket connection wrapper."""

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.scope = scope
        self._receive = receive
        self._send = send

    async def accept(self, subprotocol: Optional[str] = None) -> None:
        """Accept WebSocket connection."""
        message = {"type": "websocket.accept"}
        if subprotocol:
            message["subprotocol"] = subprotocol
        await self._send(message)

    async def receive_text(self) -> str:
        """Receive text message."""
        message = await self._receive()
        return message.get("text", "")

    async def receive_bytes(self) -> bytes:
        """Receive binary message."""
        message = await self._receive()
        return message.get("bytes", b"")

    async def send_text(self, data: str) -> None:
        """Send text message."""
        await self._send({"type": "websocket.send", "text": data})

    async def send_bytes(self, data: bytes) -> None:
        """Send binary message."""
        await self._send({"type": "websocket.send", "bytes": data})

    async def close(self, code: int = 1000) -> None:
        """Close WebSocket connection."""
        await self._send({"type": "websocket.close", "code": code})
