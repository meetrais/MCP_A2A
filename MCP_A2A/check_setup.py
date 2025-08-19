#!/usr/bin/env python3
"""
Setup checker for MCP A2A Trading System.
Verifies that all dependencies are installed and the system is ready to run.
"""

import sys
import subprocess
import importlib
import os

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} is not compatible")
        print("  Required: Python 3.8 or higher")
        return False

def check_required_packages():
    """Check if required packages are installed."""
    print("\n📦 Checking required packages...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "httpx",
        "pydantic",
        "numpy",
        "asyncio"  # Built-in, but let's check
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == "asyncio":
                import asyncio
            else:
                importlib.import_module(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    else:
        print("✓ All required packages are installed")
        return True

def check_ports():
    """Check if required ports are available."""
    print("\n🔌 Checking port availability...")
    
    import socket
    
    required_ports = [8000, 8001, 8002, 8003, 8004, 9000, 9001, 9002]
    busy_ports = []
    
    for port in required_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('localhost', port))
            if result == 0:
                busy_ports.append(port)
                print(f"✗ Port {port} is in use")
            else:
                print(f"✓ Port {port} is available")
        except Exception as e:
            print(f"? Port {port} - Could not check: {e}")
        finally:
            sock.close()
    
    if busy_ports:
        print(f"\n⚠️  Ports in use: {busy_ports}")
        print("You may need to stop other services or change port configuration")
        return False
    else:
        print("✓ All required ports are available")
        return True

def check_file_structure():
    """Check if all required files exist."""
    print("\n📁 Checking file structure...")
    
    required_files = [
        "config.py",
        "models/trading_models.py",
        "models/market_data.py",
        "utils/a2a_client.py",
        "utils/a2a_server.py",
        "utils/http_client.py",
        "mcp_servers/market_data_server.py",
        "mcp_servers/technical_analysis_server.py",
        "mcp_servers/trading_execution_server.py",
        "agents/portfolio_manager_agent.py",
        "agents/fundamental_analyst_agent.py",
        "agents/technical_analyst_agent.py",
        "agents/risk_manager_agent.py",
        "agents/trade_executor_agent.py"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Missing files: {len(missing_files)}")
        return False
    else:
        print("✓ All required files are present")
        return True

def install_missing_packages():
    """Attempt to install missing packages."""
    print("\n🔧 Attempting to install missing packages...")
    
    try:
        # Install basic requirements
        packages = ["fastapi", "uvicorn[standard]", "httpx", "pydantic", "numpy", "python-dotenv"]
        
        for package in packages:
            print(f"Installing {package}...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", package], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ {package} installed successfully")
            else:
                print(f"✗ Failed to install {package}: {result.stderr}")
                
    except Exception as e:
        print(f"✗ Error installing packages: {e}")

def main():
    """Main setup checker."""
    print("🔍 MCP A2A Trading System - Setup Checker")
    print("=" * 50)
    
    checks = [
        check_python_version(),
        check_required_packages(),
        check_file_structure(),
        check_ports()
    ]
    
    passed_checks = sum(checks)
    total_checks = len(checks)
    
    print("\n" + "=" * 50)
    print(f"📊 Setup Check Results: {passed_checks}/{total_checks} passed")
    
    if passed_checks == total_checks:
        print("🎉 System is ready to run!")
        print("\nTo start the system, run:")
        print("  python start_system.py")
        print("\nOr try the main script:")
        print("  python main.py")
        return True
    else:
        print("❌ System is not ready. Please fix the issues above.")
        
        if not check_required_packages():
            response = input("\n🤔 Would you like to try installing missing packages? (y/n): ")
            if response.lower() in ['y', 'yes']:
                install_missing_packages()
                print("\n🔄 Please run the setup checker again after installation.")
        
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Setup check cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Error during setup check: {e}")
        sys.exit(1)