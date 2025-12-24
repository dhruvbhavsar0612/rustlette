# Publishing Rustlette to PyPI

This guide explains how to publish Rustlette to PyPI.

## Prerequisites

1. **PyPI Account**
   - Create an account at https://pypi.org/account/register/
   - Create an account at https://test.pypi.org/account/register/ (for testing)

2. **API Tokens**
   - Generate API token at https://pypi.org/manage/account/token/
   - Generate test API token at https://test.pypi.org/manage/account/token/
   - Store tokens in `~/.pypirc`:
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-AgEIcHlwaS5vcmc...

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-AgENdGVzdC5weXBpLm9yZw...
   ```

3. **Tools**
   ```bash
   pip install maturin twine
   ```

## Manual Publishing

### 1. Test Build Locally

```bash
# Build wheels for current platform
maturin build --release

# Or build source distribution
maturin sdist

# Check built packages
ls target/wheels/
```

### 2. Test Installation

```bash
# Install from local wheel
pip install target/wheels/rustlette-*.whl

# Test import
python -c "import rustlette; print(rustlette.hello_rustlette())"
```

### 3. Publish to Test PyPI

```bash
# Upload to test PyPI
maturin publish --repository testpypi

# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ rustlette

# Test that it works
python -c "import rustlette; print(rustlette.hello_rustlette())"
```

### 4. Publish to PyPI

```bash
# Once everything is tested, publish to real PyPI
maturin publish

# Install and verify
pip install rustlette
python -c "import rustlette; print(rustlette.hello_rustlette())"
```

## Automated Publishing via GitHub Actions

The repository includes automated workflows for building and publishing.

### Setup GitHub Secrets

1. Go to repository Settings → Secrets and variables → Actions
2. Add repository secrets:
   - `PYPI_API_TOKEN`: Your PyPI API token
   - `TEST_PYPI_API_TOKEN`: Your Test PyPI API token

### Publishing Workflow

#### Test PyPI (Manual Trigger)

```bash
# Trigger workflow manually from GitHub Actions tab
# Or via gh CLI:
gh workflow run release.yml -f test_pypi=true
```

#### Production PyPI (On Release)

1. Create a new release on GitHub:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. Go to GitHub → Releases → Draft a new release
3. Choose the tag `v0.1.0`
4. Write release notes
5. Publish release

6. GitHub Actions will automatically:
   - Build wheels for Linux, macOS, Windows
   - Build source distribution
   - Publish to PyPI

## Version Management

Update version in three places:

1. **Cargo.toml**
   ```toml
   [package]
   version = "0.1.0"
   ```

2. **pyproject.toml**
   ```toml
   [project]
   version = "0.1.0"
   ```

3. **Create git tag**
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

## Multi-Platform Builds

### Using GitHub Actions (Recommended)

The `.github/workflows/release.yml` workflow builds for:
- Linux (x86_64, manylinux)
- macOS (x86_64, arm64)
- Windows (x86_64)

### Manual Cross-Compilation

```bash
# Install cross-compilation targets
rustup target add x86_64-unknown-linux-gnu
rustup target add x86_64-apple-darwin
rustup target add aarch64-apple-darwin
rustup target add x86_64-pc-windows-msvc

# Build for specific target
maturin build --release --target x86_64-unknown-linux-gnu
```

## Troubleshooting

### Build Fails

```bash
# Clean build
cargo clean
rm -rf target/
maturin build --release
```

### Import Fails After Installation

```bash
# Check if module is importable
python -c "import rustlette"

# Check module location
python -c "import rustlette; print(rustlette.__file__)"

# Reinstall
pip uninstall rustlette
pip install rustlette --no-cache-dir
```

### Wrong Platform Wheel

```bash
# Check platform tags
ls target/wheels/*.whl

# Should see platform-specific tags like:
# rustlette-0.1.0-cp38-cp38-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

## PyPI Package Page

After publishing, your package will be available at:
- **PyPI**: https://pypi.org/project/rustlette/
- **Test PyPI**: https://test.pypi.org/project/rustlette/

Users can install with:
```bash
pip install rustlette
```

## Best Practices

1. **Always test on Test PyPI first**
2. **Build for multiple platforms** (use GitHub Actions)
3. **Keep versions synchronized** (Cargo.toml, pyproject.toml, git tags)
4. **Update CHANGELOG.md** before releasing
5. **Write clear release notes** on GitHub
6. **Test installation** on clean environments before announcing

## Resources

- [Maturin Documentation](https://www.maturin.rs/)
- [PyPI Publishing Guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [Python Packaging User Guide](https://packaging.python.org/)
