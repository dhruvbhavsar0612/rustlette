# Contributing to Rustlette

Thank you for your interest in contributing to Rustlette! This document provides guidelines and instructions for contributing.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Project Structure](#project-structure)

## Code of Conduct

Be respectful, inclusive, and considerate of others. We're all here to build something great together.

## Getting Started

### Prerequisites

- **Python 3.8+**
- **Rust 1.75+** (install from https://rustup.rs/)
- **Git**

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/rustlette.git
cd rustlette

# Run quick start script
./quickstart.sh

# Or manual setup:
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install maturin pytest pytest-asyncio httpx
maturin develop
```

### Verify Setup

```bash
# Run setup validation
python check_setup.py

# Test import
python -c "import rustlette; print(rustlette.hello_rustlette())"
```

## Development Setup

### Installing Development Dependencies

```bash
pip install -e ".[dev]"
# Or:
pip install pytest pytest-asyncio httpx black isort mypy ruff
```

### Building from Source

```bash
# Debug build (faster, for development)
maturin develop

# Release build (optimized, for testing)
maturin develop --release

# Build wheel
maturin build --release
```

### Running the Project

```bash
# After building, you can import and use rustlette
python
>>> import rustlette
>>> rustlette.hello_rustlette()
```

## Making Changes

### Workflow

1. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes** following our code style guidelines

3. **Test your changes** thoroughly

4. **Commit your changes** with clear messages:
   ```bash
   git add .
   git commit -m "feat: add WebSocket support"
   # or
   git commit -m "fix: handle empty request body correctly"
   ```

5. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(routing): add support for path parameters
fix(request): handle empty body correctly
docs(readme): update installation instructions
test(middleware): add tests for CORS middleware
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_routing.py -v

# Run with coverage
pytest --cov=rustlette tests/

# Run Rust tests
cargo test
```

### Writing Tests

#### Python Tests

Create test files in `tests/` directory:

```python
# tests/test_feature.py
import pytest
from rustlette import MyFeature

def test_my_feature():
    """Test description."""
    feature = MyFeature()
    result = feature.do_something()
    assert result == expected_value

@pytest.mark.asyncio
async def test_async_feature():
    """Test async functionality."""
    result = await async_function()
    assert result is not None
```

#### Rust Tests

Add tests in Rust source files:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_feature() {
        let result = my_function();
        assert_eq!(result, expected_value);
    }
}
```

## Submitting Changes

### Pull Request Process

1. **Ensure CI passes**: All tests and linting must pass
2. **Update documentation**: If adding features, update README and docs
3. **Add tests**: New features should have tests
4. **Update CHANGELOG**: Add entry in `CHANGELOG.md`
5. **Fill PR template**: Describe your changes clearly

### Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] Rust code formatted (`cargo fmt`)
- [ ] Rust code linted (`cargo clippy -- -D warnings`)
- [ ] Documentation updated (if applicable)
- [ ] CHANGELOG.md updated
- [ ] Commit messages follow conventional commits
- [ ] PR description explains the changes

## Code Style

### Rust Code Style

Follow standard Rust conventions:

```bash
# Format code
cargo fmt

# Check for issues
cargo clippy

# Run both
cargo fmt && cargo clippy -- -D warnings
```

**Guidelines:**
- Use descriptive variable names
- Add documentation comments (`///`) for public items
- Handle errors explicitly, don't unwrap in production code
- Use `RustletteResult<T>` for functions that can fail
- Keep functions focused and small
- Prefer owned types when crossing Python/Rust boundary

**Example:**
```rust
/// Parse HTTP request headers.
///
/// # Arguments
/// * `raw_headers` - Raw header bytes from HTTP request
///
/// # Returns
/// Parsed headers or error if malformed
///
/// # Examples
/// ```
/// let headers = parse_headers(raw_bytes)?;
/// ```
pub fn parse_headers(raw_headers: &[u8]) -> RustletteResult<Headers> {
    // Implementation
}
```

### Python Code Style

Follow PEP 8 with these tools:

```bash
# Format with Black
black rustlette/

# Sort imports
isort rustlette/

# Lint with Ruff
ruff check rustlette/

# Type check with mypy
mypy rustlette/
```

**Guidelines:**
- Use type hints for function signatures
- Add docstrings to public functions/classes
- Maximum line length: 88 characters (Black default)
- Use meaningful variable names

**Example:**
```python
def parse_query_string(query: str) -> dict[str, str]:
    """
    Parse URL query string into dictionary.
    
    Args:
        query: Raw query string (e.g., "foo=bar&baz=qux")
    
    Returns:
        Dictionary of query parameters
    
    Examples:
        >>> parse_query_string("foo=bar")
        {'foo': 'bar'}
    """
    # Implementation
```

### PyO3 Bindings

When writing PyO3 code:

```rust
// ✅ Good: Proper error handling
#[pyfunction]
pub fn my_function(data: &str) -> PyResult<String> {
    let result = process_data(data)
        .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))?;
    Ok(result)
}

// ✅ Good: Extract with py parameter (PyO3 0.20)
Python::with_gil(|py| {
    let value = py_object.extract::<String>(py)?;
    Ok(value)
})

// ❌ Bad: Unwrap (will panic)
pub fn bad_function(data: &str) -> String {
    process_data(data).unwrap()  // Don't do this!
}
```

## Project Structure

```
rustlette/
├── src/                    # Rust source code
│   ├── lib.rs             # Main module and Python exports
│   ├── error.rs           # Error types
│   ├── types.rs           # Core HTTP types
│   ├── request.rs         # Request handling
│   ├── response.rs        # Response types
│   ├── routing.rs         # Route matching
│   ├── middleware.rs      # Middleware system
│   ├── background.rs      # Background tasks
│   ├── asgi.rs            # ASGI compatibility
│   ├── app.rs             # Application class
│   └── server.rs          # HTTP server
├── rustlette/             # Python package
│   ├── __init__.py        # Public API
│   ├── applications.py    # App wrapper
│   ├── requests.py        # Request wrapper
│   ├── responses.py       # Response wrappers
│   └── ...                # Other Python modules
├── tests/                 # Test suite
├── benchmarks/            # Performance benchmarks
├── examples/              # Example applications
├── docs/                  # Documentation
├── .github/               # GitHub configuration
│   ├── workflows/         # CI/CD workflows
│   └── copilot-instructions.md  # AI assistant context
├── Cargo.toml            # Rust dependencies
├── pyproject.toml        # Python package config
├── README.md             # Main documentation
├── CONTRIBUTING.md       # This file
└── CHANGELOG.md          # Version history
```

## Areas to Contribute

### High Priority
- [ ] Fix remaining compilation errors (see `.github/copilot-instructions.md`)
- [ ] WebSocket support
- [ ] File upload / multipart parsing
- [ ] More middleware (rate limiting, compression, etc.)
- [ ] Better error messages
- [ ] Performance optimizations

### Medium Priority
- [ ] Route mounting / sub-applications
- [ ] TestClient implementation
- [ ] More comprehensive tests
- [ ] Better documentation
- [ ] Example applications

### Nice to Have
- [ ] HTTP/2 support
- [ ] Database integration helpers
- [ ] OpenAPI/Swagger generation
- [ ] Admin interface
- [ ] CLI tools

## Getting Help

- **Questions?** Open a [GitHub Discussion](https://github.com/yourusername/rustlette/discussions)
- **Bug?** Open an [Issue](https://github.com/yourusername/rustlette/issues)
- **Chat?** Join our [Discord](https://discord.gg/rustlette) (if available)

## Recognition

Contributors will be:
- Listed in README.md
- Credited in release notes
- Given contributor badge on GitHub

Thank you for contributing to Rustlette! 🦀🐍
