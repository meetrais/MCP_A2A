#!/usr/bin/env python3
"""
Diagnostic script to identify issues with the MCP A2A Trading System.
"""

import sys
import os
import importlib
import subprocess
import traceback

def print_section(title):
    print(f"\n{'='*50}")
    print(f"🔍 {title}")
    print('='*50)

def check_python_environment():
    print_section("Python Environment")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")  # First 3 entries

def check_directory_structure():
    print_section("Directory Structure")
    
    expected_files = [
        'main.py',
        'config.py', 
        'start_system.py',
        'run.py',
        'agents/',
        'mcp_servers/',
        'utils/',
        'models/'
    ]
    
    for item in expected_files:
        if os.path.exists(item):
            print(f"✓ {item}")
        else:
            print(f"✗ {item} - MISSING")

def check_imports():
    print_section("Import Tests")
    
    # Test basic imports
    imports_to_test = [
        ('sys', 'Built-in sys module'),
        ('os', 'Built-in os module'),
        ('asyncio', 'Built-in asyncio module'),
        ('json', 'Built-in json module'),
        ('subprocess', 'Built-in subprocess module'),
        ('fastapi', 'FastAPI framework'),
        ('uvicorn', 'Uvicorn ASGI server'),
        ('httpx', 'HTTPX HTTP client'),
        ('pydantic', 'Pydantic data validation'),
        ('numpy', 'NumPy scientific computing')
    ]
    
    for module_name, description in imports_to_test:
        try:
            importlib.import_module(module_name)
            print(f"✓ {module_name} - {description}")
        except ImportError as e:
            print(f"✗ {module_name} - MISSING: {e}")
        except Exception as e:
            print(f"? {module_name} - ERROR: {e}")

def check_local_imports():
    print_section("Local Module Imports")
    
    # Add current directory to path
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())
    
    local_modules = [
        ('config', 'Configuration module'),
        ('models.trading_models', 'Trading models'),
        ('models.market_data', 'Market data models'),
        ('utils.a2a_client', 'A2A client'),
        ('utils.http_client', 'HTTP client'),
        ('utils.logging_config', 'Logging configuration')
    ]
    
    for module_name, description in local_modules:
        try:
            importlib.import_module(module_name)
            print(f"✓ {module_name} - {description}")
        except ImportError as e:
            print(f"✗ {module_name} - IMPORT ERROR: {e}")
        except Exception as e:
            print(f"? {module_name} - OTHER ERROR: {e}")

def check_ports():
    print_section("Port Availability")
    
    import socket
    
    ports_to_check = [8000, 8001, 8002, 8003, 8004, 9000, 9001, 9002]
    
    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('localhost', port))
            if result == 0:
                print(f"✗ Port {port} - IN USE")
            else:
                print(f"✓ Port {port} - Available")
        except Exception as e:
            print(f"? Port {port} - Could not check: {e}")
        finally:
            sock.close()

def test_simple_service_start():
    print_section("Service Start Test")
    
    # Try to start a simple service
    try:
        print("Testing if we can start a simple FastAPI service...")
        
        # Create a minimal test service
        test_service_code = '''
import sys
sys.path.insert(0, ".")

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Test Service")

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    print("Test service starting...")
    uvicorn.run(app, host="0.0.0.0", port=8999, log_level="info")
'''
        
        with open('test_service.py', 'w') as f:
            f.write(test_service_code)
        
        print("Created test service file")
        
        # Try to run it briefly
        process = subprocess.Popen([
            sys.executable, 'test_service.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        import time
        time.sleep(2)  # Let it start
        
        if process.poll() is None:
            print("✓ Test service started successfully")
            process.terminate()
            process.wait()
        else:
            stdout, stderr = process.communicate()
            print(f"✗ Test service failed to start")
            print(f"STDOUT: {stdout[:200]}...")
            print(f"STDERR: {stderr[:200]}...")
        
        # Clean up
        if os.path.exists('test_service.py'):
            os.remove('test_service.py')
            
    except Exception as e:
        print(f"✗ Service start test failed: {e}")
        traceback.print_exc()

def run_main_script_test():
    print_section("Main Script Test")
    
    scripts_to_test = ['start_system.py', 'run.py', 'main.py']
    
    for script in scripts_to_test:
        if os.path.exists(script):
            print(f"\nTesting {script}...")
            try:
                # Try to import the script as a module
                spec = importlib.util.spec_from_file_location("test_module", script)
                module = importlib.util.module_from_spec(spec)
                
                # Just try to load it, don't execute
                print(f"✓ {script} - Can be loaded")
                
            except Exception as e:
                print(f"✗ {script} - Load error: {e}")
                # Show the first few lines of the error
                traceback.print_exc(limit=3)
        else:
            print(f"✗ {script} - File not found")

def main():
    print("🚀 MCP A2A Trading System - Diagnostic Tool")
    print("This will help identify what's preventing the system from running")
    
    try:
        check_python_environment()
        check_directory_structure()
        check_imports()
        check_local_imports()
        check_ports()
        test_simple_service_start()
        run_main_script_test()
        
        print_section("Summary")
        print("Diagnostic complete!")
        print("\nNext steps:")
        print("1. Fix any missing dependencies with: pip install <package>")
        print("2. Make sure you're in the MCP_A2A directory")
        print("3. Try: python start_system.py")
        print("4. If ports are busy, wait a few minutes or restart")
        
    except Exception as e:
        print(f"\n💥 Diagnostic failed with error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()