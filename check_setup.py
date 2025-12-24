#!/usr/bin/env python3
"""
Quick setup validation script for Rustlette.
Run this to ensure your development environment is correctly configured.
"""

import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version >= (3, 8):
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor} (need 3.8+)")
        return False


def check_rust():
    """Check Rust installation."""
    print("\n🦀 Checking Rust installation...")
    try:
        result = subprocess.run(
            ["rustc", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        print(f"   ✅ {version}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("   ❌ Rust not found")
        print("      Install from: https://rustup.rs/")
        return False


def check_cargo():
    """Check Cargo installation."""
    print("\n📦 Checking Cargo...")
    try:
        result = subprocess.run(
            ["cargo", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        print(f"   ✅ {version}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("   ❌ Cargo not found")
        return False


def check_maturin():
    """Check Maturin installation."""
    print("\n🔨 Checking Maturin...")
    try:
        result = subprocess.run(
            ["maturin", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        print(f"   ✅ {version}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("   ❌ Maturin not found")
        print("      Install with: pip install maturin")
        return False


def check_project_structure():
    """Check project structure."""
    print("\n📁 Checking project structure...")
    required_files = [
        "Cargo.toml",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "src/lib.rs",
        "rustlette/__init__.py",
    ]
    
    all_exist = True
    for file in required_files:
        path = Path(file)
        if path.exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (missing)")
            all_exist = False
    
    return all_exist


def check_cargo_lock():
    """Check if Cargo.lock is valid."""
    print("\n🔒 Checking Cargo.lock...")
    if Path("Cargo.lock").exists():
        try:
            result = subprocess.run(
                ["cargo", "check"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print("   ✅ Cargo.lock is valid")
                return True
            else:
                print("   ⚠️  Cargo check failed")
                print("      Run: cargo clean && cargo check")
                return False
        except subprocess.TimeoutExpired:
            print("   ⚠️  Cargo check timed out")
            return False
    else:
        print("   ℹ️  Cargo.lock not found (will be generated on first build)")
        return True


def try_build():
    """Try a quick build."""
    print("\n🔨 Trying quick build...")
    try:
        result = subprocess.run(
            ["cargo", "check"],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print("   ✅ Build check passed")
            return True
        else:
            print("   ❌ Build check failed")
            print("\n   Error output:")
            for line in result.stderr.split('\n')[:10]:
                if line.strip():
                    print(f"      {line}")
            return False
    except subprocess.TimeoutExpired:
        print("   ⚠️  Build timed out")
        return False
    except Exception as e:
        print(f"   ❌ Build error: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("🦀 Rustlette Development Environment Check")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Rust Installation", check_rust),
        ("Cargo Installation", check_cargo),
        ("Maturin Installation", check_maturin),
        ("Project Structure", check_project_structure),
        ("Cargo Lock", check_cargo_lock),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[name] = False
    
    # Optional build check
    if all(results.values()):
        results["Build Check"] = try_build()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, passed_check in results.items():
        status = "✅" if passed_check else "❌"
        print(f"{status} {name}")
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ All checks passed! You're ready to develop Rustlette.")
        print("\nNext steps:")
        print("  1. Run: maturin develop")
        print("  2. Test: python -c 'import rustlette'")
        print("  3. Read: CONTRIBUTING.md")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
