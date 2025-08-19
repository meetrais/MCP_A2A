#!/usr/bin/env python3
"""
Simple run script for MCP A2A Trading System.
Handles common startup issues and provides clear error messages.
"""

import sys
import os
import subprocess
import time

def print_banner():
    """Print startup banner."""
    print("🚀 MCP A2A Trading System")
    print("=" * 40)

def check_python():
    """Check Python version."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True

def install_requirements():
    """Install basic requirements."""
    print("📦 Installing requirements...")
    
    basic_packages = [
        "fastapi",
        "uvicorn[standard]", 
        "httpx",
        "pydantic",
        "numpy"
    ]
    
    for package in basic_packages:
        try:
            print(f"Installing {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                print(f"⚠️  Warning: Could not install {package}")
        except Exception as e:
            print(f"⚠️  Warning: Error installing {package}: {e}")

def run_setup_check():
    """Run the setup checker."""
    print("🔍 Running setup check...")
    try:
        result = subprocess.run([sys.executable, "check_setup.py"], 
                              capture_output=True, text=True, timeout=30)
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"⚠️  Could not run setup check: {e}")
        return True  # Continue anyway

def start_system():
    """Start the trading system."""
    print("🎯 Starting trading system...")
    
    scripts_to_try = [
        "start_system.py",
        "main.py"
    ]
    
    for script in scripts_to_try:
        if os.path.exists(script):
            print(f"Running {script}...")
            try:
                # Run the script and let it handle its own output
                subprocess.run([sys.executable, script])
                return True
            except KeyboardInterrupt:
                print("\n👋 Shutdown requested")
                return True
            except Exception as e:
                print(f"❌ Error running {script}: {e}")
                continue
    
    print("❌ Could not find a working startup script")
    return False

def main():
    """Main function."""
    print_banner()
    
    # Check Python version
    if not check_python():
        return 1
    
    # Try to install requirements
    try:
        install_requirements()
    except Exception as e:
        print(f"⚠️  Warning: Could not install requirements: {e}")
    
    # Run setup check
    run_setup_check()
    
    # Start the system
    if start_system():
        return 0
    else:
        print("\n❌ Failed to start the system")
        print("\nTroubleshooting tips:")
        print("1. Make sure you're in the MCP_A2A directory")
        print("2. Try: pip install fastapi uvicorn httpx pydantic numpy")
        print("3. Check if ports 8000-8004 and 9000-9002 are available")
        print("4. Run: python check_setup.py")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n👋 Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)