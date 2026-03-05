# Changelog

All notable changes to Rustlette are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Rustlette version numbers track the Starlette release they are API-compatible with.

## [0.50.0] - 2026-03-04

### Added

- Full Starlette 0.50.0 API compatibility (Phase 1)
- 30 Python modules matching every public and private Starlette interface
- FastAPI integration (drop-in replacement for `starlette` imports)
- All built-in middleware: CORS, GZip, HTTPS redirect, trusted host, sessions, authentication, error handling
- Complete routing system: `Route`, `WebSocketRoute`, `Mount`, `Host`, `Router`
- Request/response classes: `Request`, `Response`, `JSONResponse`, `HTMLResponse`, `RedirectResponse`, `StreamingResponse`, `FileResponse`
- WebSocket support with full state machine
- `TestClient` wrapping httpx for application testing
- Path parameter convertors: `int`, `float`, `path`, `uuid`
- Background task execution (`BackgroundTask`, `BackgroundTasks`)
- Lifespan context manager support
- HTTP status codes including WebSocket close codes and RFC 9110 names
- Form parsing (urlencoded and multipart)
- 333 tests with 72% code coverage
- PyPI packaging via maturin
- CI/CD via GitHub Actions

### Notes

- This is a Phase 1 release: all functionality is pure Python
- The Rust extension (`_rustlette_core`) is compiled and included but not yet wired into hot paths
- Phase 2 will introduce Rust-accelerated routing, header parsing, and body accumulation

[0.50.0]: https://github.com/dhruvbhavsar0612/rustlette/releases/tag/v0.50.0
