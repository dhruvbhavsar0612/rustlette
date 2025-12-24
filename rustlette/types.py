"""
Type definitions for Rustlette ASGI compatibility
"""

import typing
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

# ASGI type definitions
Scope = Dict[str, Any]
Message = Dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

# Lifespan types
Lifespan = Callable[["Rustlette"], typing.AsyncContextManager[None]]

# HTTP types
HTTPScope = typing.TypedDict(
    "HTTPScope",
    {
        "type": typing.Literal["http"],
        "asgi": Dict[str, str],
        "http_version": str,
        "method": str,
        "scheme": str,
        "path": str,
        "raw_path": bytes,
        "query_string": bytes,
        "root_path": str,
        "headers": List[Tuple[bytes, bytes]],
        "server": Optional[Tuple[str, Optional[int]]],
        "client": Optional[Tuple[str, int]],
        "state": Dict[str, Any],
        "extensions": Dict[str, Dict[object, object]],
    },
    total=False,
)

# WebSocket types
WebSocketScope = typing.TypedDict(
    "WebSocketScope",
    {
        "type": typing.Literal["websocket"],
        "asgi": Dict[str, str],
        "http_version": str,
        "scheme": str,
        "path": str,
        "raw_path": bytes,
        "query_string": bytes,
        "root_path": str,
        "headers": List[Tuple[bytes, bytes]],
        "server": Optional[Tuple[str, Optional[int]]],
        "client": Optional[Tuple[str, int]],
        "subprotocols": List[str],
        "state": Dict[str, Any],
        "extensions": Dict[str, Dict[object, object]],
    },
    total=False,
)

# Lifespan types
LifespanScope = typing.TypedDict(
    "LifespanScope",
    {
        "type": typing.Literal["lifespan"],
        "asgi": Dict[str, str],
        "state": Dict[str, Any],
    },
    total=False,
)

# HTTP Messages
HTTPRequestMessage = typing.TypedDict(
    "HTTPRequestMessage",
    {
        "type": typing.Literal["http.request"],
        "body": bytes,
        "more_body": bool,
    },
    total=False,
)

HTTPResponseStartMessage = typing.TypedDict(
    "HTTPResponseStartMessage",
    {
        "type": typing.Literal["http.response.start"],
        "status": int,
        "headers": List[Tuple[bytes, bytes]],
    },
    total=False,
)

HTTPResponseBodyMessage = typing.TypedDict(
    "HTTPResponseBodyMessage",
    {
        "type": typing.Literal["http.response.body"],
        "body": bytes,
        "more_body": bool,
    },
    total=False,
)

HTTPDisconnectMessage = typing.TypedDict(
    "HTTPDisconnectMessage",
    {
        "type": typing.Literal["http.disconnect"],
    },
)

# WebSocket Messages
WebSocketConnectMessage = typing.TypedDict(
    "WebSocketConnectMessage",
    {
        "type": typing.Literal["websocket.connect"],
    },
)

WebSocketAcceptMessage = typing.TypedDict(
    "WebSocketAcceptMessage",
    {
        "type": typing.Literal["websocket.accept"],
        "subprotocol": Optional[str],
        "headers": List[Tuple[bytes, bytes]],
    },
    total=False,
)

WebSocketReceiveMessage = typing.TypedDict(
    "WebSocketReceiveMessage",
    {
        "type": typing.Literal["websocket.receive"],
        "bytes": Optional[bytes],
        "text": Optional[str],
    },
    total=False,
)

WebSocketSendMessage = typing.TypedDict(
    "WebSocketSendMessage",
    {
        "type": typing.Literal["websocket.send"],
        "bytes": Optional[bytes],
        "text": Optional[str],
    },
    total=False,
)

WebSocketCloseMessage = typing.TypedDict(
    "WebSocketCloseMessage",
    {
        "type": typing.Literal["websocket.close"],
        "code": int,
        "reason": Optional[str],
    },
    total=False,
)

WebSocketDisconnectMessage = typing.TypedDict(
    "WebSocketDisconnectMessage",
    {
        "type": typing.Literal["websocket.disconnect"],
        "code": int,
    },
)

# Lifespan Messages
LifespanStartupMessage = typing.TypedDict(
    "LifespanStartupMessage",
    {
        "type": typing.Literal["lifespan.startup"],
    },
)

LifespanShutdownMessage = typing.TypedDict(
    "LifespanShutdownMessage",
    {
        "type": typing.Literal["lifespan.shutdown"],
    },
)

LifespanStartupCompleteMessage = typing.TypedDict(
    "LifespanStartupCompleteMessage",
    {
        "type": typing.Literal["lifespan.startup.complete"],
    },
)

LifespanStartupFailedMessage = typing.TypedDict(
    "LifespanStartupFailedMessage",
    {
        "type": typing.Literal["lifespan.startup.failed"],
        "message": str,
    },
)

LifespanShutdownCompleteMessage = typing.TypedDict(
    "LifespanShutdownCompleteMessage",
    {
        "type": typing.Literal["lifespan.shutdown.complete"],
    },
)

LifespanShutdownFailedMessage = typing.TypedDict(
    "LifespanShutdownFailedMessage",
    {
        "type": typing.Literal["lifespan.shutdown.failed"],
        "message": str,
    },
)

# Union types for all messages
HTTPMessage = Union[
    HTTPRequestMessage,
    HTTPDisconnectMessage,
]

WebSocketMessage = Union[
    WebSocketConnectMessage,
    WebSocketReceiveMessage,
    WebSocketDisconnectMessage,
]

LifespanMessage = Union[
    LifespanStartupMessage,
    LifespanShutdownMessage,
]

# All possible messages
ReceiveMessage = Union[HTTPMessage, WebSocketMessage, LifespanMessage]

SendMessage = Union[
    HTTPResponseStartMessage,
    HTTPResponseBodyMessage,
    WebSocketAcceptMessage,
    WebSocketSendMessage,
    WebSocketCloseMessage,
    LifespanStartupCompleteMessage,
    LifespanStartupFailedMessage,
    LifespanShutdownCompleteMessage,
    LifespanShutdownFailedMessage,
]

# Common type aliases
Headers = List[Tuple[str, str]]
QueryParams = Dict[str, Union[str, List[str]]]
PathParams = Dict[str, Any]
