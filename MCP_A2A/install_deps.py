#!/usr/bin/env python3
"""
Install required dependencies for MCP A2A Trading System.
"""

import subprocess
import sys

def install_package(package):
    """Install a package using pip."""
    try:
        print(f"Installing {package}...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", package
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print(f"✓ {package} installed successfully")
            return True
        else:
            print(f"✗ Failed to install {package}")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error installing {package}: {e}")
        return False

def main():
    print("📦 Installing MCP A2A Trading System Dependencies")
    print("=" * 50)
    
    # Required packages
    packages = [
        "fastapi",
        "uvicorn[standard]",
        "httpx",
        "pydantic",
        "numpy",
        "python-dotenv"
    ]
    
    print("Installing required packages...")
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 Installation Results: {success_count}/{len(packages)} packages installed")
    
    if success_count == len(packages):
        print("✅ All dependencies installed successfully!")
        print("\nNext steps:")
        print("1. Run: python test_basic.py")
        print("2. Run: python simple_start.py")
    else:
        print("❌ Some packages failed to install")
        print("\nTry manual installation:")
        for package in packages:
            print(f"  pip install {package}")

if __name__ == "__main__":
    main()