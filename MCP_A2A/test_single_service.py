#!/usr/bin/env python3
"""
Test starting a single service to identify issues.
"""

import sys
import os
import subprocess
import time

def test_service_directly():
    """Try to import and run a service directly."""
    print("Testing direct service import...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.getcwd())
        
        # Try to import the market data server
        print("Importing market_data_server...")
        from mcp_servers.market_data_server import app
        
        print("✓ Successfully imported market_data_server")
        print("✓ FastAPI app object created")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_uvicorn_command():
    """Test running uvicorn command."""
    print("\nTesting uvicorn command...")
    
    try:
        # Try to run uvicorn with our service
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "mcp_servers.market_data_server:app",
            "--host", "0.0.0.0", 
            "--port", "9000",
            "--log-level", "debug"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        # Wait a few seconds
        time.sleep(3)
        
        if process.poll() is None:
            print("✓ Service started successfully!")
            process.terminate()
            process.wait()
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"✗ Service failed to start")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Command failed: {e}")
        return False

def test_python_module():
    """Test running as Python module."""
    print("\nTesting Python module execution...")
    
    try:
        cmd = [sys.executable, "-m", "mcp_servers.market_data_server"]
        
        print(f"Running: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        time.sleep(3)
        
        if process.poll() is None:
            print("✓ Module execution successful!")
            process.terminate()
            process.wait()
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"✗ Module execution failed")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Module execution error: {e}")
        return False

def main():
    print("🔍 Single Service Test")
    print("=" * 30)
    
    # Check if we're in the right directory
    if not os.path.exists("mcp_servers"):
        print("❌ mcp_servers directory not found!")
        print("Make sure you're in the MCP_A2A directory")
        return
    
    if not os.path.exists("mcp_servers/market_data_server.py"):
        print("❌ market_data_server.py not found!")
        return
    
    print("✓ Service files found")
    
    tests = [
        test_service_directly(),
        test_uvicorn_command(),
        test_python_module()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed > 0:
        print("✅ At least one method works!")
    else:
        print("❌ All methods failed - there's a fundamental issue")
        print("\nCommon fixes:")
        print("1. pip install fastapi uvicorn httpx pydantic")
        print("2. Check Python version (need 3.8+)")
        print("3. Make sure you're in the MCP_A2A directory")

if __name__ == "__main__":
    main()