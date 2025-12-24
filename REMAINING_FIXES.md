# Remaining Compilation Fixes Needed

## Current Status
- **Errors**: 31
- **Progress**: 73 → 31 (57% reduction, 42 errors fixed)

## Remaining Error Categories

### 1. Return Type Mismatches (11 errors)
**Problem**: Methods using `pyo3_asyncio::tokio::future_into_py` return `&PyAny` but functions declare `PyResult<()>` or `PyResult<PyObject>`

**Files affected**: `src/app.rs`, `src/asgi.rs`

**Fix pattern**:
```rust
// BEFORE:
pub fn method_name(&self) -> PyResult<()> {
    Python::with_gil(|py| {
        pyo3_asyncio::tokio::future_into_py(py, async move {
            // ...
        })
    })
}

// AFTER:
pub fn method_name<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
    pyo3_asyncio::tokio::future_into_py(py, async move {
        // ...
    })
}
```

**Specific locations**:
- `src/app.rs:145` - add_route
- `src/app.rs:284` - add_middleware  
- `src/app.rs:297` - add_event_handler
- `src/app.rs:325` - add_exception_handler
- `src/app.rs:355` - route_info
- `src/app.rs:368` - call
- `src/app.rs:378` - get_state
- `src/app.rs:387` - set_state
- `src/asgi.rs:435` - call_http
- `src/asgi.rs:482` - call_websocket
- `src/asgi.rs:497` - call_lifespan

### 2. Route AsRef<PyAny> Issues (2 errors)
**Problem**: Route doesn't implement AsRef<PyAny> for Python calls

**Location**: `src/routing.rs:377`

**Fix**: Either:
- Make Route methods not need AsRef (change implementation)
- Or wrap Route in Py<> when needed

### 3. Type Annotations Needed (2 errors)
**Problem**: Compiler can't infer types in certain contexts

**Fix**: Add explicit type annotations where needed

### 4. QueryParams IntoPy Issue (1 error)
**Problem**: QueryParams doesn't implement IntoPy<Py<PyAny>>

**Location**: Variable usage in routing

**Fix**: Either implement IntoPy for QueryParams or change how it's used

### 5. Vec<&Route> IntoPyCallbackOutput (1 error)
**Problem**: Can't return Vec<&Route> to Python

**Fix**: Convert to Vec of Python objects or change return type

### 6. Option/Result operator mismatches (4 errors)
**Problem**: Using `?` in wrong context (Option vs Result)

**Fix**: Use proper error handling pattern for each context

### 7. MiddlewareStack Debug (1 error)
**Problem**: MiddlewareStack has Vec<Arc<dyn MiddlewareHandler>> which doesn't implement Debug

**Fix**: Manually implement Debug or don't derive it

### 8. Miscellaneous (9 errors)
- iter not found on Py<PyAny>
- if/else incompatible types
- RustletteRequest AsRef<PyAny>
- Result<Option<RouteMatch>> OkWrap
- &str IntoPy issues

## Quick Win Fixes (Start Here)

1. **MiddlewareStack Debug** - Easy, just implement it manually
2. **Partial moves** - Already fixed
3. **Return type signatures** - Pattern is clear, just apply it

## Estimated Time
- ~30-45 minutes to fix all remaining issues
- Most are repetitive pattern application

## Next Steps
1. Fix all return type mismatches in app.rs and asgi.rs (bulk of remaining errors)
2. Fix MiddlewareStack Debug implementation
3. Handle Route/QueryParams trait issues
4. Clean up remaining type annotations

