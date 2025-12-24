# 🦀 Rustlette

**High-performance Python web framework with Rust internals**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Rust](https://img.shields.io/badge/rust-1.70+-orange.svg)](https://www.rust-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Rustlette provides the **Starlette developer experience** with **Rust performance**. It's a drop-in replacement for Starlette that delivers measurable performance improvements through its Rust core.

## 🏆 Performance Benchmarks

Rustlette **outperforms** all major Python web frameworks:

| Framework | RPS | Avg Latency | P95 Latency | vs Rustlette |
|-----------|-----|-------------|-------------|--------------|
| **🥇 Rustlette** | **182** | **54.9ms** | **91.6ms** | **Baseline** |
| 🥈 Starlette | 178 | 56.1ms | 91.9ms | -2.1% slower |
| 🥉 FastAPI | 177 | 57.1ms | 95.0ms | -3.0% slower |
| Flask | 173 | 79.0ms | 102.9ms | -5.2% slower |

*Benchmarks run with 20 concurrent clients, 15 seconds per endpoint*

## ✨ Features

- 🚀 **High Performance**: Rust-powered internals for maximum speed
- 🔌 **Starlette Compatible**: Drop-in replacement with identical API
- 🛡️ **Type Safe**: Full type hints and validation
- ⚡ **Async/Await**: First-class async support throughout
- 🔧 **ASGI Compatible**: Works with Uvicorn, Gunicorn, etc.
- 🔄 **Background Tasks**: Built-in task execution
- 📡 **Path Parameters**: Type-safe parameter conversion (`{user_id:int}`)
- 🐛 **Error Handling**: Comprehensive exception system

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/dhruvbhavsar0612/rustlette.git
cd rustlette

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with development dependencies
pip install maturin
maturin develop

# Or build a release wheel
maturin build --release
```

### Requirements

- Python 3.8+
- Rust 1.70+ (install from https://rustup.rs/)
- maturin (`pip install maturin`)

## 🚀 Quick Start

```python
from rustlette import Rustlette, Request, JSONResponse

app = Rustlette(debug=True)

@app.route("/")
async def homepage(request: Request):
    return {"message": "Hello, Rustlette!"}

@app.get("/users/{user_id:int}")
async def get_user(request: Request):
    user_id = request.path_params["user_id"]
    return {"user_id": user_id, "name": f"User {user_id}"}

@app.post("/users")
async def create_user(request: Request):
    data = await request.json()
    return JSONResponse({"created": data}, status_code=201)

@app.route("/search")
async def search(request: Request):
    query = request.query_params.get("q", "")
    return {"query": query, "results": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

## 📖 API Reference

### Application

```python
from rustlette import Rustlette

app = Rustlette(debug=False)
```

### Route Decorators

```python
@app.route("/path", methods=["GET", "POST"])
@app.get("/path")
@app.post("/path")
@app.put("/path")
@app.delete("/path")
@app.patch("/path")
@app.options("/path")
@app.head("/path")
```

### Path Parameters

```python
# String (default)
@app.route("/users/{username}")

# Integer
@app.route("/users/{user_id:int}")

# Float
@app.route("/items/{price:float}")

# Path (matches multiple segments)
@app.route("/files/{file_path:path}")
```

### Request Object

```python
@app.route("/example")
async def example(request: Request):
    # Method and path
    method = request.method  # "GET", "POST", etc.
    path = request.path      # "/example"
    
    # Path parameters
    user_id = request.path_params.get("user_id")
    
    # Query parameters
    query = request.query_params.get("q", "default")
    
    # Headers
    content_type = request.headers.get("content-type")
    
    # Body
    body_bytes = await request.body()
    json_data = await request.json()
    
    return {"status": "ok"}
```

### Response Types

```python
from rustlette import Response, JSONResponse

# JSON Response (default for dicts)
return {"message": "Hello"}
return JSONResponse({"message": "Hello"}, status_code=200)

# Plain text
return Response("Hello", headers={"content-type": "text/plain"})

# Custom status code
return JSONResponse({"error": "Not found"}, status_code=404)
```

### Event Handlers

```python
@app.on_event("startup")
async def startup():
    print("Application starting...")

@app.on_event("shutdown")
async def shutdown():
    print("Application shutting down...")
```

### Exception Handlers

```python
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        {"error": str(exc)},
        status_code=400
    )
```

## 🏗️ Project Structure

```
rustlette/
├── src/                    # Rust source code
│   ├── lib.rs             # Main module exports
│   ├── app.rs             # Application logic
│   ├── server.rs          # HTTP server
│   ├── routing.rs         # Route matching
│   ├── middleware.rs      # Middleware system
│   ├── request.rs         # Request handling
│   ├── response.rs        # Response types
│   ├── background.rs      # Background tasks
│   ├── asgi.rs            # ASGI compatibility
│   ├── error.rs           # Error handling
│   └── types.rs           # Core types
├── rustlette/             # Python package
│   ├── __init__.py        # Public API & ASGI app
│   ├── applications.py    # Main app class
│   ├── requests.py        # Request wrapper
│   ├── responses.py       # Response wrappers
│   ├── routing.py         # Routing utilities
│   ├── middleware.py      # Middleware classes
│   ├── background.py      # Background tasks
│   ├── exceptions.py      # Exception handling
│   ├── convertors.py      # Path convertors
│   ├── types.py           # Type definitions
│   └── status.py          # HTTP status codes
├── benchmarks/            # Performance benchmarks
├── examples/              # Example applications
├── tests/                 # Test suite
├── Cargo.toml             # Rust dependencies
├── pyproject.toml         # Python packaging
└── README.md              # This file
```

## 🧪 Running Tests

```bash
# Run Python tests
pytest tests/

# Run endpoint tests
python test_endpoints.py

# Run server integration test
python test_server.py

# Run benchmarks
cd benchmarks
python benchmark.py --quick
python simple_benchmark.py
```

## 🔧 Development

### Building from Source

```bash
# Debug build (faster compilation)
maturin develop

# Release build (optimized)
maturin develop --release

# Build wheel
maturin build --release
```

### Running Benchmarks

```bash
cd benchmarks

# Quick benchmark (all frameworks)
python simple_benchmark.py

# Specific frameworks
python simple_benchmark.py --frameworks rustlette starlette

# Full benchmark suite
python benchmark.py --quick
```

## 🎯 Architecture

Rustlette uses a **bipartite design**:

- **Python Layer**: Provides the developer-facing API (Starlette-compatible)
- **Rust Core**: Handles performance-critical operations (routing, parsing, etc.)

### Key Design Principles

1. **Zero-Copy Operations**: Minimal data copying between Python and Rust
2. **Lazy Evaluation**: Request parsing only when needed
3. **Memory Efficient**: Rust data structures with Python views
4. **Concurrent Safe**: Thread-safe Rust core with async Python API

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Starlette](https://www.starlette.io/) - For the amazing API design
- [PyO3](https://pyo3.rs/) - For Python/Rust bindings
- [Tokio](https://tokio.rs/) - For async Rust runtime

## 📊 Roadmap

- [ ] WebSocket support
- [ ] More middleware (CORS, Rate Limiting, etc.)
- [ ] Database integration helpers
- [ ] OpenAPI/Swagger documentation
- [ ] More Rust optimizations
- [ ] HTTP/2 support

---

**Made with ❤️ and 🦀**