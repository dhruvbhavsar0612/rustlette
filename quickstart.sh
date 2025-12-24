#!/bin/bash
# Quick start script for Rustlette development

set -e

echo "🦀 Rustlette Quick Start Script"
echo "================================"
echo ""

# Check if running in the right directory
if [ ! -f "Cargo.toml" ] || [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from rustlette project root"
    echo "   (Directory containing Cargo.toml and pyproject.toml)"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
echo "📍 Checking Python..."
if ! command_exists python3; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION"

# Check Rust
echo ""
echo "📍 Checking Rust..."
if ! command_exists rustc; then
    echo "❌ Rust not found. Install from: https://rustup.rs/"
    exit 1
fi
RUST_VERSION=$(rustc --version)
echo "✅ $RUST_VERSION"

# Check Cargo
echo ""
echo "📍 Checking Cargo..."
if ! command_exists cargo; then
    echo "❌ Cargo not found. Install Rust from: https://rustup.rs/"
    exit 1
fi
CARGO_VERSION=$(cargo --version)
echo "✅ $CARGO_VERSION"

# Create virtual environment
echo ""
echo "📍 Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "📍 Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Could not find activation script"
    exit 1
fi

# Upgrade pip
echo ""
echo "📍 Upgrading pip..."
python -m pip install --upgrade pip -q
echo "✅ pip upgraded"

# Install maturin
echo ""
echo "📍 Installing maturin..."
if ! command_exists maturin; then
    pip install maturin -q
    echo "✅ maturin installed"
else
    echo "ℹ️  maturin already installed"
fi

# Install development dependencies
echo ""
echo "📍 Installing development dependencies..."
pip install pytest pytest-asyncio httpx black isort mypy ruff -q
echo "✅ Development dependencies installed"

# Clean previous builds
echo ""
echo "📍 Cleaning previous builds..."
if [ -d "target" ]; then
    rm -rf target
    echo "✅ Cleaned target directory"
else
    echo "ℹ️  No previous builds to clean"
fi

# Build and install Rustlette
echo ""
echo "📍 Building Rustlette (this may take a few minutes)..."
if maturin develop --release; then
    echo "✅ Rustlette built and installed successfully!"
else
    echo "❌ Build failed. Check errors above."
    exit 1
fi

# Test import
echo ""
echo "📍 Testing Rustlette import..."
if python -c "import rustlette; print('✅ Import successful')" 2>/dev/null; then
    echo "✅ Rustlette is working!"
else
    echo "❌ Import failed"
    exit 1
fi

# Test hello function
echo ""
echo "📍 Testing hello_rustlette..."
python -c "import rustlette; print(f'   {rustlette.hello_rustlette()}')" || true

echo ""
echo "================================"
echo "🎉 Setup Complete!"
echo ""
echo "Next steps:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Run tests: pytest tests/ -v"
echo "  3. Start coding!"
echo ""
echo "Development commands:"
echo "  maturin develop         # Rebuild in debug mode"
echo "  maturin develop --release  # Rebuild optimized"
echo "  cargo fmt              # Format Rust code"
echo "  cargo clippy           # Lint Rust code"
echo "  cargo test             # Run Rust tests"
echo "  pytest tests/          # Run Python tests"
echo ""
echo "Build wheel:"
echo "  maturin build --release"
echo ""
echo "Happy coding! 🦀🐍"
