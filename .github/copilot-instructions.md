# Rustlette - Copilot Instructions

## Project Overview

**Rustlette** is a high-performance Python web framework with Rust internals, designed to be API-compatible with Starlette and eventually serve as a drop-in replacement for it in FastAPI applications.

## Tech Stack

- **Core Language:** Rust 1.75+ (targeting 1.83+ eventually)
- **Python Binding:** PyO3 0.20 with abi3-py38
- **Async Runtime:** Tokio 1.0 with full features
- **HTTP Server:** Hyper 0.14
- **WebSocket:** hyper-tungstenite 0.10
- **Serialization:** serde 1.0, serde_json 1.0
- **Build Tool:** maturin for Python wheel generation

## Project Structure

```
rustlette/
├── src/
│   ├── lib.rs              # Python module definition & exports
│   ├── types.rs            # Core HTTP types (Method, Status, Headers, QueryParams)
│   ├── error.rs            # Error handling & Python exception conversion
│   ├── request.rs          # Request parsing & handling
│   ├── response.rs         # Response types (JSON, HTML, File, Stream, etc.)
│   ├── routing.rs          # Trie-based route matching
│   ├── middleware.rs       # Middleware stack (CORS, Security, Timing)
│   ├── background.rs       # Background task execution
│   ├── asgi.rs             # ASGI 3.0 compatibility layer
│   ├── app.rs              # Main application class (RustletteApp)
│   └── server.rs           # HTTP server implementation
├── Cargo.toml              # Rust dependencies
├── pyproject.toml          # Python package metadata
└── README.md               # Documentation
```

## Key Dependencies

### Rust (Cargo.toml)
- `pyo3 = "0.20"` - Python bindings
- `pyo3-asyncio = "0.20"` - Async Python integration
- `tokio = "1.0"` - Async runtime
- `hyper = "0.14"` - HTTP server
- `serde/serde_json` - Serialization
- `regex = "1.10"` - Route pattern matching
- `dashmap = "5.5"` - Concurrent hash maps
- `urlencoding = "2.1"` - URL encoding/decoding
- `num_cpus = "1.16"` - CPU detection

## Current Status (as of Phase 1)

### ✅ Completed Modules
- `error.rs` - Error types with PyO3 conversion
- `types.rs` - HTTP types (HTTPMethod, StatusCode, Headers)
- Core structure established

### 🔧 In Progress
- **Phase 1: Fix Compilation Errors** (Current)
  - Fixed: PyO3 0.20 API migration issues
  - Fixed: Missing dependencies (urlencoding, num_cpus)
  - Fixed: `from_dict` visibility in Headers
  - Fixed: Module exports in lib.rs
  - **Remaining:** ~73 errors related to PyO3 API parameter passing

### ❌ Not Yet Implemented
- WebSocket support (Priority 1 for FastAPI)
- File upload / multipart parsing (Priority 2)
- Route mounting / sub-applications (Priority 3)
- TestClient (Priority 4)
- Full ASGI compatibility testing

## Coding Conventions

### Rust Code Style

1. **Use standard Rust formatting** - Run `cargo fmt` before committing
2. **Handle errors explicitly** - Use `RustletteResult<T>` for internal errors
3. **Document public APIs** - All public items need doc comments (`///`)
4. **Prefer owned types in PyO3** - Clone data when crossing Python/Rust boundary
5. **Use Arc for shared state** - Thread-safe shared references

### PyO3 0.20 Migration Patterns

**CRITICAL:** PyO3 0.20 requires explicit `Python<'py>` parameters for many operations.

#### Extract Pattern
```rust
// ❌ OLD (PyO3 0.19)
result.extract::<String>()

// ✅ NEW (PyO3 0.20)
result.extract::<String>(py)
```

#### Downcast Pattern
```rust
// ❌ OLD
content.downcast::<PyDict>()

// ✅ NEW
content.downcast::<PyDict>(py)
```

#### HasAttr Pattern
```rust
// ❌ OLD
obj.hasattr(py, "__call__")

// ✅ NEW
obj.as_ref(py).hasattr("__call__")
```

#### String Conversion Pattern
```rust
// ❌ OLD
obj.str()?.extract::<String>()

// ✅ NEW
obj.call_method0(py, "__str__")?.extract::<String>(py)
```

#### GetItem Pattern (PyDict)
```rust
// ❌ OLD
if let Some(value) = kwargs.get_item("key") {

// ✅ NEW
if let Ok(Some(value)) = kwargs.get_item("key") {
```

### PyClass Patterns

```rust
// Standard PyClass with Python GIL context
#[pyclass]
pub struct MyType {
    #[pyo3(get, set)]
    pub field: String,
}

#[pymethods]
impl MyType {
    #[new]
    fn new(field: String) -> Self {
        Self { field }
    }
    
    // Methods that need Python context
    fn method_with_py(&self, py: Python<'_>) -> PyResult<String> {
        // Has access to py
        Ok(self.field.clone())
    }
}
```

## Common Patterns

### Error Conversion
```rust
// Convert Rust errors to Python exceptions
impl From<RustletteError> for PyErr {
    fn from(err: RustletteError) -> PyErr {
        PyRuntimeError::new_err(err.message)
    }
}
```

### Async Python Functions
```rust
// Return coroutine to Python
pub fn async_method<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
    pyo3_asyncio::tokio::future_into_py(py, async move {
        // async code
        Ok(())
    })
}
```

### Headers API
```rust
// Headers must use from_dict classmethod publicly
#[classmethod]
pub fn from_dict(_cls: &PyType, dict: &PyAny) -> PyResult<Self> {
    // Convert Python dict to Headers
}
```

## Implementation Plan

### Phase 1: Fix Compilation (Current)
**Goal:** Get `cargo build` to succeed with 0 errors

**Remaining Tasks:**
1. Add `py: Python<'_>` parameter to all `.extract()` calls
2. Add `py` parameter to all `.downcast()` calls  
3. Fix partial move issues (clone before moving)
4. Fix `QueryParams::IntoPy` implementation
5. Fix Option/Result mismatches in closures

**Pattern to find:** `grep -r "\.extract::<" src/` and add `py` parameter

### Phase 2: Starlette Compatibility
1. Implement WebSocket support (~500 lines)
2. Implement UploadFile & multipart parsing (~400 lines)
3. Implement Mount for sub-applications (~300 lines)
4. Implement TestClient (~500 lines)
5. Create `starlette_compat.py` wrapper

### Phase 3: PyPI Package
1. Update `pyproject.toml` with proper metadata
2. Write comprehensive README
3. Setup GitHub Actions for multi-platform wheels
4. Test on test.pypi.org
5. Publish to PyPI

### Phase 4: FastAPI Integration
1. Test with real FastAPI apps
2. Document limitations
3. Create migration guide
4. Performance benchmarks

## Rules & Best Practices

1. **Never break the build** - All commits should compile
2. **Test incrementally** - Use `cargo check` for faster feedback
3. **PyO3 API first** - When in doubt, check PyO3 0.20 docs
4. **Match Starlette API** - Keep methods and signatures compatible
5. **Performance matters** - But correctness comes first
6. **Document breaking changes** - Keep changelog updated
7. **Use `cargo clippy`** - Fix warnings before committing
8. **Async by default** - Most web operations should be async
9. **Thread-safe state** - Use Arc/RwLock for shared mutable state
10. **Graceful degradation** - Provide fallbacks for missing features

## Testing Strategy

```bash
# Check compilation
cargo check

# Build library
cargo build

# Build with optimizations
cargo build --release

# Run tests
cargo test

# Build Python wheel
maturin develop

# Test in Python
python -c "import rustlette; print(rustlette.hello_rustlette())"
```

## Common Issues & Solutions

### Issue: `extract()` missing parameter
**Solution:** Add `py` parameter: `.extract::<T>(py)`

### Issue: `downcast()` missing parameter  
**Solution:** Add `py` parameter: `.downcast::<T>(py)`

### Issue: `hasattr` not found
**Solution:** Use `obj.as_ref(py).hasattr("attr")`

### Issue: Partial move error
**Solution:** Clone before moving: `route_match.path_params.clone()`

### Issue: Type doesn't implement IntoPy
**Solution:** Implement `IntoPy` trait or wrap in `Py<PyAny>`

### Issue: Lockfile version mismatch
**Solution:** `rm Cargo.lock && cargo generate-lockfile`

### Issue: Rust version too old
**Solution:** Update rust: `rustup update` or use older dependency versions

## FastAPI Compatibility Goals

To replace Starlette in FastAPI, Rustlette MUST implement:

### Required Classes
- ✅ `Request` - HTTP request with lazy loading
- ✅ `Response` - Base response class
- ✅ `JSONResponse` - JSON serialization
- ✅ `HTMLResponse` - HTML content
- ✅ `PlainTextResponse` - Plain text
- ✅ `RedirectResponse` - HTTP redirects
- ✅ `FileResponse` - Static file serving
- ✅ `StreamingResponse` - Chunked responses
- ❌ `WebSocket` - WebSocket connections (CRITICAL)
- ❌ `UploadFile` - File upload handling (CRITICAL)
- ✅ `BackgroundTasks` - Post-response tasks
- ✅ `CORSMiddleware` - CORS headers
- ❌ `Mount` - Sub-application mounting

### Required Methods
All Starlette Request/Response methods must have matching signatures.

## Performance Targets

- Request routing: <100μs for simple routes
- JSON serialization: 2-3x faster than pure Python
- Middleware overhead: <10μs per middleware
- Memory usage: <50% of equivalent Starlette app
- Concurrent requests: Support 10k+ simultaneous connections

## Security Considerations

1. **Input validation** - Validate all data from Python
2. **Memory safety** - Rust prevents buffer overflows
3. **Thread safety** - Use proper locking for shared state
4. **DOS protection** - Limit request size, timeout long requests
5. **Secrets** - Never log sensitive data
6. **Dependencies** - Keep dependencies updated

## Contribution Guidelines

1. Fork the repository
2. Create feature branch
3. Fix compilation errors first
4. Add tests for new features
5. Update documentation
6. Submit PR with clear description

## Resources

- [PyO3 Documentation](https://pyo3.rs/)
- [Starlette Documentation](https://www.starlette.io/)
- [FastAPI Source](https://github.com/tiangolo/fastapi)
- [ASGI Specification](https://asgi.readthedocs.io/)
- [Hyper Documentation](https://hyper.rs/)

## Current Blockers

1. **73 compilation errors** - Mostly PyO3 0.20 API migrations
2. **WebSocket missing** - Blocks FastAPI WebSocket endpoints
3. **File upload missing** - Blocks FastAPI file upload endpoints
4. **No tests yet** - Need comprehensive test suite
