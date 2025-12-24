# GitHub & PyPI Setup Guide for Rustlette

Complete guide to set up GitHub repository and PyPI publishing for Rustlette.

## Table of Contents
- [Initial GitHub Setup](#initial-github-setup)
- [PyPI Setup](#pypi-setup)
- [GitHub Secrets Configuration](#github-secrets-configuration)
- [First Release](#first-release)
- [Maintenance](#maintenance)

---

## Initial GitHub Setup

### 1. Create GitHub Repository

```bash
# Initialize git if not already done
cd /mnt/c/Projects/rastapi
git init

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: Rustlette web framework with Rust core"

# Create repository on GitHub (via web or CLI)
gh repo create rustlette --public --source=. --remote=origin --description="High-performance Python web framework with Rust internals"

# Or manually:
# 1. Go to https://github.com/new
# 2. Name: rustlette
# 3. Description: High-performance Python web framework with Rust internals
# 4. Public repository
# 5. Don't initialize with README (we have one)
# 6. Create repository

# Add remote and push
git remote add origin https://github.com/YOURUSERNAME/rustlette.git
git branch -M main
git push -u origin main
```

### 2. Configure Repository Settings

Go to your repository settings on GitHub:

**General Settings:**
- ✅ Allow squash merging
- ✅ Automatically delete head branches
- ✅ Enable issues
- ✅ Enable discussions (optional)

**Branch Protection (recommended):**
1. Go to Settings → Branches → Add rule
2. Branch name pattern: `main`
3. Check:
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
4. Save changes

**Topics:**
Add these topics to help discovery:
- `python`
- `rust`
- `web-framework`
- `asgi`
- `fastapi`
- `starlette`
- `performance`
- `async`

### 3. Set Up GitHub Actions

The workflows are already created in `.github/workflows/`:
- `ci.yml` - Continuous Integration (runs on every push/PR)
- `release.yml` - Build and publish wheels (runs on release)

These will run automatically once you push to GitHub.

---

## PyPI Setup

### 1. Create PyPI Accounts

#### Production PyPI
1. Go to https://pypi.org/account/register/
2. Create account with email verification
3. Enable 2FA (required for publishing)

#### Test PyPI (for testing)
1. Go to https://test.pypi.org/account/register/
2. Create account (separate from production)
3. Enable 2FA

### 2. Generate API Tokens

#### For Production PyPI:
1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Token name: `rustlette-github-actions`
4. Scope: "Entire account" (or specific to `rustlette` project once created)
5. Copy the token (starts with `pypi-`)
6. **Save it securely** - you can't view it again!

#### For Test PyPI:
1. Go to https://test.pypi.org/manage/account/token/
2. Click "Add API token"
3. Token name: `rustlette-github-actions-test`
4. Scope: "Entire account"
5. Copy the token
6. Save it securely

### 3. Test Local Publishing (Optional)

Create `~/.pypirc` for manual testing:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

**⚠️ Never commit this file to git!**

---

## GitHub Secrets Configuration

### 1. Add Secrets to GitHub Repository

Go to: **Settings → Secrets and variables → Actions**

Click **"New repository secret"** and add:

#### Required Secrets:

1. **PYPI_API_TOKEN**
   - Name: `PYPI_API_TOKEN`
   - Value: Your production PyPI token (`pypi-...`)
   - Used by: `release.yml` workflow

2. **TEST_PYPI_API_TOKEN** 
   - Name: `TEST_PYPI_API_TOKEN`
   - Value: Your Test PyPI token (`pypi-...`)
   - Used by: `release.yml` workflow for testing

### 2. Configure Environments (Optional but Recommended)

Go to: **Settings → Environments**

#### Create "pypi" Environment:
1. Click "New environment"
2. Name: `pypi`
3. Add protection rules:
   - ✅ Required reviewers: (add yourself)
   - ✅ Wait timer: 5 minutes
4. Add environment secret:
   - Name: `PYPI_API_TOKEN`
   - Value: Your production token

#### Create "testpypi" Environment:
1. Click "New environment"
2. Name: `testpypi`
3. Add environment secret:
   - Name: `TEST_PYPI_API_TOKEN`
   - Value: Your test token

---

## First Release

### 1. Verify Everything is Ready

```bash
# Run setup check
python check_setup.py

# Try building locally
maturin build --release

# Check generated wheel
ls target/wheels/
```

### 2. Test on Test PyPI (Recommended First Step)

#### Option A: Manual Test
```bash
# Build and publish to Test PyPI
maturin publish --repository testpypi

# Test installation
pip install --index-url https://test.pypi.org/simple/ rustlette

# Verify it works
python -c "import rustlette; print(rustlette.hello_rustlette())"
```

#### Option B: GitHub Actions Test
```bash
# Trigger test release via GitHub Actions
gh workflow run release.yml -f test_pypi=true

# Or go to Actions tab and manually trigger "Build and Release"
# with test_pypi=true
```

### 3. Create First Production Release

Once testing is successful:

```bash
# Update version if needed
# Edit: Cargo.toml and pyproject.toml

# Commit changes
git add .
git commit -m "Release v0.1.0"

# Create and push tag
git tag v0.1.0
git push origin v0.1.0

# Create GitHub Release
gh release create v0.1.0 \
  --title "Rustlette v0.1.0 - Initial Alpha Release" \
  --notes "First alpha release of Rustlette web framework.

Features:
- Rust-powered HTTP handling
- Starlette-compatible API
- Request/Response handling
- Route matching with parameters
- Middleware support
- Background tasks
- ASGI compatibility

Known Limitations:
- WebSocket support not yet implemented
- File upload not yet implemented

See CHANGELOG.md for details."
```

This will automatically:
1. Trigger the `release.yml` workflow
2. Build wheels for Linux, macOS, Windows
3. Build source distribution
4. Publish to PyPI
5. Package is available via `pip install rustlette`

### 4. Verify Release

```bash
# Wait for GitHub Actions to complete (5-10 minutes)
# Check: https://github.com/YOURUSERNAME/rustlette/actions

# Once complete, test installation
pip install rustlette

# Verify
python -c "import rustlette; print(rustlette.hello_rustlette())"

# Check PyPI page
# https://pypi.org/project/rustlette/
```

---

## Maintenance

### Updating Package

For subsequent releases:

```bash
# 1. Update version numbers
# Edit Cargo.toml: version = "0.1.1"
# Edit pyproject.toml: version = "0.1.1"

# 2. Update CHANGELOG.md
# Add new section for v0.1.1

# 3. Commit and tag
git add .
git commit -m "Release v0.1.1: Bug fixes and improvements"
git tag v0.1.1
git push origin v0.1.1

# 4. Create GitHub Release
gh release create v0.1.1 --title "v0.1.1" --notes "See CHANGELOG.md"
```

### Yanking a Release

If you need to remove a broken release:

```bash
# On PyPI web interface:
# 1. Go to https://pypi.org/project/rustlette/
# 2. Click on the version
# 3. Click "Options" → "Yank release"

# Or via CLI:
pip install twine
twine upload --repository pypi target/wheels/* --skip-existing
```

### Monitoring

- **PyPI Stats**: https://pypistats.org/packages/rustlette
- **GitHub Insights**: https://github.com/YOURUSERNAME/rustlette/pulse
- **Actions**: https://github.com/YOURUSERNAME/rustlette/actions

---

## Troubleshooting

### Build Fails in CI

```bash
# Check GitHub Actions logs
gh run list
gh run view <run-id>

# Common fixes:
# - Update Rust version in workflow
# - Fix Cargo.lock conflicts
# - Check for platform-specific issues
```

### PyPI Upload Fails

```bash
# Common issues:
# 1. Token expired - regenerate on PyPI
# 2. Version already exists - increment version
# 3. Package name taken - choose different name
# 4. File too large - check wheel size

# Verify credentials
maturin publish --repository testpypi --dry-run
```

### Installation Fails

```bash
# Check if wheels are available for platform
pip install rustlette --verbose

# Try forcing from source
pip install rustlette --no-binary :all:

# Check platform compatibility
python -c "import platform; print(platform.platform())"
```

---

## Quick Reference

### Key Commands

```bash
# Build locally
maturin build --release

# Build and install
maturin develop

# Publish to Test PyPI
maturin publish --repository testpypi

# Publish to PyPI
maturin publish

# Create release
git tag v0.1.0 && git push origin v0.1.0
gh release create v0.1.0

# Check setup
python check_setup.py

# Run tests
pytest tests/

# Format Rust code
cargo fmt

# Lint Rust code
cargo clippy
```

### Important URLs

- **PyPI**: https://pypi.org/project/rustlette/
- **Test PyPI**: https://test.pypi.org/project/rustlette/
- **GitHub**: https://github.com/YOURUSERNAME/rustlette
- **Actions**: https://github.com/YOURUSERNAME/rustlette/actions
- **PyPI Stats**: https://pypistats.org/packages/rustlette

---

## Next Steps

After successful setup:

1. ✅ Verify CI passes on GitHub Actions
2. ✅ Test installation from PyPI
3. ✅ Update documentation with correct URLs
4. ✅ Write announcement blog post
5. ✅ Share on social media
6. ✅ Submit to awesome lists
7. ✅ Create project website (optional)
8. ✅ Set up documentation hosting (Read the Docs)

---

**Questions?** Open an issue on GitHub!
