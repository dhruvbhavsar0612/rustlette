# Contributing to Rustlette

Thank you for considering contributing to Rustlette. This document explains how to set up your development environment and submit changes.

## Development setup

### Prerequisites

- Python 3.10+
- Rust 1.75+ (install from https://rustup.rs/)
- maturin (`pip install maturin`)
- git

### Getting started

```bash
git clone https://github.com/dhruvbhavsar0612/rustlette.git
cd rustlette
python -m venv venv
source venv/bin/activate
pip install maturin
maturin develop
pip install -e ".[dev]"
```

### Running tests

```bash
# Full test suite
pytest

# With coverage
pytest --cov=rustlette --cov-report=term-missing

# Single test file
pytest tests/test_routing.py -v
```

### Linting

```bash
ruff check rustlette/ tests/
ruff format --check rustlette/ tests/
```

## Project structure

- `rustlette/` -- Python package (Phase 1: pure Python, API-compatible with Starlette 0.50.0)
- `src/` -- Rust source (Phase 2: performance-critical hot paths)
- `tests/` -- pytest test suite
- `pyproject.toml` -- Python packaging (maturin backend)
- `Cargo.toml` -- Rust dependencies

## How to contribute

### Reporting bugs

Open an issue using the bug report template. Include:

1. Python and Rust versions
2. Minimal reproduction script
3. Expected vs actual behavior
4. Full traceback if applicable

### Submitting changes

1. Fork the repository and create a branch from `main`
2. Make your changes
3. Add or update tests for the change
4. Run `pytest` and `ruff check` -- all must pass
5. Open a pull request using the PR template

### Commit messages

Use clear, concise commit messages. Prefix with the area of change:

```
routing: fix 405 response when partial match exists
middleware: add timeout parameter to GZipMiddleware
tests: add coverage for WebSocket close codes
docs: update installation instructions
```

### What we accept

- Bug fixes with a reproducing test
- Missing Starlette API surface (if we diverge from 0.50.0)
- Test coverage improvements
- Documentation improvements
- Phase 2 Rust acceleration work (coordinate via an issue first)

### What we do not accept

- API changes that break Starlette compatibility
- New features not present in Starlette (this is a drop-in replacement)
- Dependencies beyond what Starlette itself requires

## Code style

- Follow existing patterns in the codebase
- Match Starlette's API surface exactly (parameter names, defaults, behavior)
- Use type hints consistent with Starlette 0.50.0
- Line length limit: 120 characters (enforced by ruff)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
