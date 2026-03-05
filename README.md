# Rustlette

**Drop-in Starlette replacement with Rust acceleration.**

[![PyPI version](https://img.shields.io/pypi/v/rustlette.svg)](https://pypi.org/project/rustlette/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/dhruvbhavsar0612/rustlette/actions/workflows/ci.yml/badge.svg)](https://github.com/dhruvbhavsar0612/rustlette/actions/workflows/ci.yml)

Rustlette is an API-compatible replacement for [Starlette](https://www.starlette.io/) 0.50.0.
Swap one import and your existing FastAPI or Starlette application runs unchanged.

**Phase 1 (current):** Full Starlette API surface in pure Python — 30 modules, 333 tests passing.
**Phase 2 (planned):** Rust-accelerated routing, header parsing, and body accumulation via PyO3.

## Installation

```bash
pip install rustlette
```

With optional dependencies (sessions, multipart, test client):

```bash
pip install rustlette[full]
```

### Building from source

Rustlette uses [maturin](https://www.maturin.rs/) as its build backend. To build from source you need Rust 1.75+ installed.

```bash
git clone https://github.com/dhruvbhavsar0612/rustlette.git
cd rustlette
python -m venv venv && source venv/bin/activate
pip install maturin
maturin develop          # debug build
maturin develop --release  # optimized build
```

## Quick start

Rustlette mirrors the Starlette API exactly:

```python
from rustlette.applications import Starlette
from rustlette.requests import Request
from rustlette.responses import JSONResponse
from rustlette.routing import Route

async def homepage(request: Request) -> JSONResponse:
    return JSONResponse({"hello": "world"})

app = Starlette(routes=[
    Route("/", homepage),
])
```

Run with any ASGI server:

```bash
uvicorn app:app
```

### Using with FastAPI

Rustlette works as a transparent backend for FastAPI. Point your imports at `rustlette` instead of `starlette`:

```python
# Before
from starlette.requests import Request
from starlette.responses import JSONResponse

# After
from rustlette.requests import Request
from rustlette.responses import JSONResponse
```

FastAPI subclasses `starlette.applications.Starlette` and `starlette.routing.Router` internally — Rustlette provides identical classes so FastAPI works without modification.

## What's included

Rustlette implements every public module from Starlette 0.50.0:

| Module | Description |
|---|---|
| `applications` | `Starlette` application class |
| `authentication` | `AuthCredentials`, `AuthenticationBackend`, `@requires` |
| `background` | `BackgroundTask`, `BackgroundTasks` |
| `concurrency` | `run_in_threadpool`, `iterate_in_threadpool` |
| `convertors` | Path parameter convertors (`int`, `float`, `path`, `uuid`) |
| `datastructures` | `URL`, `Headers`, `QueryParams`, `State`, `UploadFile` |
| `endpoints` | `HTTPEndpoint`, `WebSocketEndpoint` |
| `exceptions` | `HTTPException`, `WebSocketException` |
| `formparsers` | `FormParser`, `MultiPartParser`, `MultiPartException` |
| `middleware` | `Middleware` class + all built-in middleware |
| `requests` | `Request`, `HTTPConnection` |
| `responses` | `Response`, `JSONResponse`, `HTMLResponse`, `RedirectResponse`, `StreamingResponse`, `FileResponse` |
| `routing` | `Route`, `WebSocketRoute`, `Mount`, `Host`, `Router` |
| `status` | All HTTP and WebSocket status codes |
| `testclient` | `TestClient` (wraps `httpx`) |
| `types` | `ASGIApp`, `Scope`, `Receive`, `Send`, `Lifespan` |
| `websockets` | `WebSocket`, `WebSocketClose` |

Plus private modules required by FastAPI: `_exception_handler`, `_utils`.

## Middleware

All Starlette built-in middleware is included:

```python
from rustlette.applications import Starlette
from rustlette.middleware import Middleware
from rustlette.middleware.cors import CORSMiddleware
from rustlette.middleware.gzip import GZipMiddleware
from rustlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from rustlette.middleware.trustedhost import TrustedHostMiddleware
from rustlette.middleware.sessions import SessionMiddleware
from rustlette.middleware.authentication import AuthenticationMiddleware

app = Starlette(
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"]),
        Middleware(GZipMiddleware, minimum_size=1000),
    ],
)
```

## Testing

```bash
# Run the test suite
pip install rustlette[test]
pytest

# With coverage
pytest --cov=rustlette --cov-report=term-missing
```

## Current status

- **API compatibility:** Starlette 0.50.0 (all 30 modules)
- **Test suite:** 333 tests, all passing
- **Coverage:** 72%
- **Python:** 3.10, 3.11, 3.12, 3.13
- **Rust extension:** Compiled but not yet wired into hot paths (Phase 2)

The Rust extension (`_rustlette_core.abi3.so`) is built and included in the wheel but is not used by the Python code in Phase 1. All functionality is pure Python matching Starlette's own implementation.

## Roadmap

- **Phase 2:** Rust-accelerated routing engine, header parsing, URL parsing, body accumulation
- Benchmark suite comparing Rustlette vs Starlette on identical workloads
- Full Starlette test suite port (beyond current 333 tests)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and how to submit changes.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

- [Starlette](https://www.starlette.io/) for the API design this project is built to match
- [PyO3](https://pyo3.rs/) for Python/Rust bindings
- [maturin](https://www.maturin.rs/) for the build system
