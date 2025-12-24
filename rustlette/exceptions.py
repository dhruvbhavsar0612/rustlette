"""
Exception handling for Rustlette
"""

import typing
from typing import Any, Dict, Optional, Union

from .responses import JSONResponse, PlainTextResponse, Response


class HTTPException(Exception):
    """
    Base HTTP exception that can be raised to return an HTTP error response.
    """

    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize HTTP exception.

        Args:
            status_code: HTTP status code
            detail: Error detail message
            headers: Optional response headers
        """
        if detail is not None:
            self.detail = detail
        else:
            self.detail = http_status_message(status_code)

        self.status_code = status_code
        self.headers = headers

    def __str__(self) -> str:
        return f"{self.status_code}: {self.detail}"

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code!r}, detail={self.detail!r})"


class WebSocketException(Exception):
    """
    Exception for WebSocket connections.
    """

    def __init__(self, code: int = 1000, reason: Optional[str] = None) -> None:
        self.code = code
        self.reason = reason or ""

    def __str__(self) -> str:
        return f"WebSocket exception: {self.code} - {self.reason}"

    def __repr__(self) -> str:
        return f"WebSocketException(code={self.code!r}, reason={self.reason!r})"


# Specific HTTP exceptions for common status codes
class BadRequestException(HTTPException):
    """400 Bad Request"""

    def __init__(
        self,
        detail: Any = "Bad Request",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=400, detail=detail, headers=headers)


class UnauthorizedException(HTTPException):
    """401 Unauthorized"""

    def __init__(
        self,
        detail: Any = "Unauthorized",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=401, detail=detail, headers=headers)


class ForbiddenException(HTTPException):
    """403 Forbidden"""

    def __init__(
        self,
        detail: Any = "Forbidden",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=403, detail=detail, headers=headers)


class NotFoundException(HTTPException):
    """404 Not Found"""

    def __init__(
        self,
        detail: Any = "Not Found",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=404, detail=detail, headers=headers)


class MethodNotAllowedException(HTTPException):
    """405 Method Not Allowed"""

    def __init__(
        self,
        detail: Any = "Method Not Allowed",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=405, detail=detail, headers=headers)


class NotAcceptableException(HTTPException):
    """406 Not Acceptable"""

    def __init__(
        self,
        detail: Any = "Not Acceptable",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=406, detail=detail, headers=headers)


class ConflictException(HTTPException):
    """409 Conflict"""

    def __init__(
        self,
        detail: Any = "Conflict",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=409, detail=detail, headers=headers)


class GoneException(HTTPException):
    """410 Gone"""

    def __init__(
        self,
        detail: Any = "Gone",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=410, detail=detail, headers=headers)


class UnprocessableEntityException(HTTPException):
    """422 Unprocessable Entity"""

    def __init__(
        self,
        detail: Any = "Unprocessable Entity",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=422, detail=detail, headers=headers)


class TooManyRequestsException(HTTPException):
    """429 Too Many Requests"""

    def __init__(
        self,
        detail: Any = "Too Many Requests",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=429, detail=detail, headers=headers)


class InternalServerErrorException(HTTPException):
    """500 Internal Server Error"""

    def __init__(
        self,
        detail: Any = "Internal Server Error",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=500, detail=detail, headers=headers)


class NotImplementedException(HTTPException):
    """501 Not Implemented"""

    def __init__(
        self,
        detail: Any = "Not Implemented",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=501, detail=detail, headers=headers)


class BadGatewayException(HTTPException):
    """502 Bad Gateway"""

    def __init__(
        self,
        detail: Any = "Bad Gateway",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=502, detail=detail, headers=headers)


class ServiceUnavailableException(HTTPException):
    """503 Service Unavailable"""

    def __init__(
        self,
        detail: Any = "Service Unavailable",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=503, detail=detail, headers=headers)


class GatewayTimeoutException(HTTPException):
    """504 Gateway Timeout"""

    def __init__(
        self,
        detail: Any = "Gateway Timeout",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=504, detail=detail, headers=headers)


# Validation exceptions
class ValidationError(Exception):
    """
    Exception for validation errors.
    """

    def __init__(self, errors: Union[str, Dict[str, Any], list]) -> None:
        self.errors = errors

    def __str__(self) -> str:
        return f"Validation error: {self.errors}"

    def __repr__(self) -> str:
        return f"ValidationError(errors={self.errors!r})"


class RequestValidationError(ValidationError):
    """
    Exception for request validation errors.
    """

    def __init__(self, errors: Union[str, Dict[str, Any], list]) -> None:
        super().__init__(errors)


# Helper functions
def http_status_message(status_code: int) -> str:
    """
    Get the standard HTTP status message for a status code.
    """
    messages = {
        100: "Continue",
        101: "Switching Protocols",
        102: "Processing",
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        207: "Multi-Status",
        208: "Already Reported",
        226: "IM Used",
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        307: "Temporary Redirect",
        308: "Permanent Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Timeout",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Payload Too Large",
        414: "URI Too Long",
        415: "Unsupported Media Type",
        416: "Range Not Satisfiable",
        417: "Expectation Failed",
        418: "I'm a teapot",
        421: "Misdirected Request",
        422: "Unprocessable Entity",
        423: "Locked",
        424: "Failed Dependency",
        425: "Too Early",
        426: "Upgrade Required",
        428: "Precondition Required",
        429: "Too Many Requests",
        431: "Request Header Fields Too Large",
        451: "Unavailable For Legal Reasons",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported",
        506: "Variant Also Negotiates",
        507: "Insufficient Storage",
        508: "Loop Detected",
        510: "Not Extended",
        511: "Network Authentication Required",
    }
    return messages.get(status_code, "Unknown")


def create_error_response(
    status_code: int,
    detail: Any = None,
    headers: Optional[Dict[str, str]] = None,
) -> Response:
    """
    Create an error response from status code and detail.
    """
    if detail is None:
        detail = http_status_message(status_code)

    if isinstance(detail, dict):
        return JSONResponse(
            content={"detail": detail},
            status_code=status_code,
            headers=headers,
        )
    else:
        return PlainTextResponse(
            content=str(detail),
            status_code=status_code,
            headers=headers,
        )


def install_error_handlers(app) -> None:
    """
    Install default error handlers for common exceptions.
    """
    from .requests import Request

    async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
        """Handle HTTPException instances."""
        return create_error_response(
            status_code=exc.status_code,
            detail=exc.detail,
            headers=exc.headers,
        )

    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> Response:
        """Handle ValidationError instances."""
        return create_error_response(
            status_code=422,
            detail={"errors": exc.errors},
        )

    async def generic_exception_handler(request: Request, exc: Exception) -> Response:
        """Handle generic exceptions."""
        if app.debug:
            # In debug mode, show the full exception
            import traceback

            detail = {
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        else:
            detail = "Internal Server Error"

        return create_error_response(status_code=500, detail=detail)

    # Register the handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


# Convenience aliases for backward compatibility
# These match Starlette's naming conventions
HTTP_400_BAD_REQUEST = BadRequestException
HTTP_401_UNAUTHORIZED = UnauthorizedException
HTTP_403_FORBIDDEN = ForbiddenException
HTTP_404_NOT_FOUND = NotFoundException
HTTP_405_METHOD_NOT_ALLOWED = MethodNotAllowedException
HTTP_406_NOT_ACCEPTABLE = NotAcceptableException
HTTP_409_CONFLICT = ConflictException
HTTP_410_GONE = GoneException
HTTP_422_UNPROCESSABLE_ENTITY = UnprocessableEntityException
HTTP_429_TOO_MANY_REQUESTS = TooManyRequestsException
HTTP_500_INTERNAL_SERVER_ERROR = InternalServerErrorException
HTTP_501_NOT_IMPLEMENTED = NotImplementedException
HTTP_502_BAD_GATEWAY = BadGatewayException
HTTP_503_SERVICE_UNAVAILABLE = ServiceUnavailableException
HTTP_504_GATEWAY_TIMEOUT = GatewayTimeoutException
