#!/usr/bin/env python3
"""
Test basic functionality and dependencies.
"""

import sys
import os

def test_imports():
    """Test if we can import required packages."""
    print("Testing basic imports...")
    
    try:
        import fastapi
        print("✓ FastAPI available")
    except ImportError as e:
        print(f"✗ FastAPI missing: {e}")
        return False
    
    try:
        import uvicorn
        print("✓ Uvicorn available")
    except ImportError as e:
        print(f"✗ Uvicorn missing: {e}")
        return False
    
    try:
        import httpx
        print("✓ HTTPX available")
    except ImportError as e:
        print(f"✗ HTTPX missing: {e}")
        return False
    
    try:
        import pydantic
        print("✓ Pydantic available")
    except ImportError as e:
        print(f"✗ Pydantic missing: {e}")
        return False
    
    return True

def test_simple_fastapi():
    """Test if we can create a simple FastAPI app."""
    print("\nTesting FastAPI app creation...")
    
    try:
        from fastapi import FastAPI
        
        app = FastAPI(title="Test App")
        
        @app.get("/health")
        def health():
            return {"status": "healthy"}
        
        print("✓ FastAPI app created successfully")
        return True
        
    except Exception as e:
        print(f"✗ FastAPI app creation failed: {e}")
        return False

def test_service_file():
    """Test if we can load one of the service files."""
    print("\nTesting service file loading...")
    
    # Try to read the market data server file
    try:
        with open("mcp_servers/market_data_server.py", "r") as f:
            content = f.read()
        
        print("✓ Service file readable")
        
        # Check for basic FastAPI structure
        if "FastAPI" in content and "app = " in content:
            print("✓ Service file has FastAPI structure")
            return True
        else:
            print("✗ Service file missing FastAPI structure")
            return False
            
    except Exception as e:
        print(f"✗ Cannot read service file: {e}")
        return False

def main():
    print("🔍 Basic System Test")
    print("=" * 30)
    
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    
    tests = [
        test_imports(),
        test_simple_fastapi(),
        test_service_file()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ Basic system looks good!")
        print("\nNext steps:")
        print("1. Try starting a single service manually")
        print("2. Check for import errors in service files")
    else:
        print("❌ Basic system has issues")
        print("\nTo fix:")
        print("1. Install missing packages: pip install fastapi uvicorn httpx pydantic")
        print("2. Make sure you're in the MCP_A2A directory")

if __name__ == "__main__":
    main()