# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- Core HTTP types (Method, Status, Headers)
- Request and Response handling
- Route matching with trie-based router
- Middleware system (CORS, Security Headers, Timing)
- Background task execution
- ASGI 3.0 compatibility layer
- Error handling with Python exception conversion

### In Progress
- Fixing PyO3 0.20 compilation errors
- WebSocket support
- File upload / multipart parsing
- TestClient implementation

## [0.1.0] - TBD

### Added
- First alpha release
- Basic Starlette-compatible API
- Rust-powered core for performance
- HTTP request/response handling
- Path parameter extraction
- Query parameter parsing
- JSON serialization
- Multiple response types
- Event handlers (startup/shutdown)
- Exception handlers

### Known Limitations
- WebSocket not yet supported
- File upload not yet supported
- Route mounting not yet implemented
- Limited middleware selection
- No production deployment guide

[Unreleased]: https://github.com/yourusername/rustlette/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/rustlette/releases/tag/v0.1.0
