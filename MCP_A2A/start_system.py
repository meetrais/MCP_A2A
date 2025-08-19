#!/usr/bin/env python3
"""
Simple startup script for the MCP A2A Trading System.
This script starts all services without complex imports.
"""

import asyncio
import subprocess
import sys
import time
import signal
import json
import os
from typing import List, Dict, Optional
import httpx

# Configuration
PORTS = {
    "market_data_mcp": 9000,
    "technical_analysis_mcp": 9001,
    "trading_execution_mcp": 9002,
    "fundamental_analyst": 8001,
    "technical_analyst": 8002,
    "risk_manager": 8003,
    "trade_executor": 8004,
    "portfolio_manager": 8000
}

SERVICE_URLS = {
    "market_data_mcp": "http://localhost:9000",
    "technical_analysis_mcp": "http://localhost:9001",
    "trading_execution_mcp": "http://localhost:9002",
    "fundamental_analyst": "http://localhost:8001",
    "technical_analyst": "http://localhost:8002",
    "risk_manager": "http://localhost:8003",
    "trade_executor": "http://localhost:8004",
    "portfolio_manager": "http://localhost:8000"
}

# Global process tracking
running_processes: List[subprocess.Popen] = []
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    print(f"\nReceived signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True

def start_service(module_path: str, port: int, service_name: str) -> subprocess.Popen:
    """Start a service as a subprocess."""
    try:
        print(f"Starting {service_name} on port {port}...")
        
        # Try different ways to start the service
        commands_to_try = [
            # Method 1: Direct Python module execution
            [sys.executable, "-m", module_path],
            # Method 2: Using uvicorn
            [sys.executable, "-m", "uvicorn", f"{module_path}:app", "--host", "0.0.0.0", "--port", str(port), "--log-level", "info"],
            # Method 3: Direct file execution
            [sys.executable, f"{module_path.replace('.', '/')}.py"]
        ]
        
        for cmd in commands_to_try:
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                
                # Wait a moment to see if it starts successfully
                time.sleep(1)
                if process.poll() is None:  # Still running
                    running_processes.append(process)
                    print(f"✓ Started {service_name} (PID: {process.pid})")
                    return process
                else:
                    # Process died, try next command
                    stdout, stderr = process.communicate()
                    print(f"Command failed: {' '.join(cmd)}")
                    if stderr:
                        print(f"Error: {stderr[:200]}...")
                    continue
                    
            except Exception as e:
                print(f"Failed to run command {' '.join(cmd)}: {e}")
                continue
        
        raise Exception(f"All startup methods failed for {service_name}")
        
    except Exception as e:
        print(f"Failed to start {service_name}: {e}")
        raise

async def wait_for_service(url: str, service_name: str, timeout: int = 30) -> bool:
    """Wait for a service to become available."""
    print(f"Waiting for {service_name} to become available...")
    
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(f"{url}/health", timeout=5.0)
                if response.status_code == 200:
                    print(f"✓ {service_name} is ready!")
                    return True
            except:
                pass
            
            await asyncio.sleep(1)
    
    print(f"✗ {service_name} failed to start within {timeout} seconds")
    return False

async def test_simple_request():
    """Test a simple request to the portfolio manager."""
    try:
        print("\n" + "="*60)
        print("Testing simple trading strategy...")
        
        strategy = {
            "goal": "Find a good tech stock to buy",
            "sector_preference": "technology",
            "risk_tolerance": "medium",
            "max_investment": 10000.0,
            "time_horizon": "short"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
                json=strategy
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✓ Trading strategy executed successfully!")
                print(f"Result: {json.dumps(result, indent=2)}")
                return True
            else:
                print(f"✗ Trading strategy failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"✗ Error testing trading strategy: {e}")
        return False

def shutdown_all_services():
    """Shutdown all running services gracefully."""
    print("\nShutting down all services...")
    
    for process in running_processes:
        try:
            if process.poll() is None:  # Process is still running
                print(f"Terminating process {process.pid}...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                    print(f"✓ Process {process.pid} terminated gracefully")
                except subprocess.TimeoutExpired:
                    print(f"⚠ Process {process.pid} did not terminate gracefully, killing...")
                    process.kill()
                    process.wait()
                    print(f"✓ Process {process.pid} killed")
        except Exception as e:
            print(f"✗ Error shutting down process {process.pid}: {e}")
    
    running_processes.clear()
    print("✓ All services shut down")

async def main():
    """Main function."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("🚀 Starting MCP A2A Trading System")
        print("="*60)
        
        # Define services in startup order
        services = [
            # MCP Servers first
            ("mcp_servers.market_data_server", PORTS["market_data_mcp"], "MarketData MCP"),
            ("mcp_servers.technical_analysis_server", PORTS["technical_analysis_mcp"], "TechnicalAnalysis MCP"),
            ("mcp_servers.trading_execution_server", PORTS["trading_execution_mcp"], "TradingExecution MCP"),
            
            # Then agents
            ("agents.fundamental_analyst_agent", PORTS["fundamental_analyst"], "FundamentalAnalyst"),
            ("agents.technical_analyst_agent", PORTS["technical_analyst"], "TechnicalAnalyst"),
            ("agents.risk_manager_agent", PORTS["risk_manager"], "RiskManager"),
            ("agents.trade_executor_agent", PORTS["trade_executor"], "TradeExecutor"),
            ("agents.portfolio_manager_agent", PORTS["portfolio_manager"], "PortfolioManager"),
        ]
        
        # Start all services
        for module, port, name in services:
            try:
                start_service(module, port, name)
                await asyncio.sleep(2)  # Small delay between starts
            except Exception as e:
                print(f"✗ Failed to start {name}: {e}")
                print("Continuing with other services...")
        
        print(f"\n📡 Started {len(running_processes)} services")
        
        # Wait for key services to be ready
        key_services = [
            (SERVICE_URLS["market_data_mcp"], "MarketData MCP"),
            (SERVICE_URLS["portfolio_manager"], "PortfolioManager"),
        ]
        
        print("\n🔍 Checking service health...")
        for url, name in key_services:
            await wait_for_service(url, name, timeout=20)
        
        # Test the system
        await test_simple_request()
        
        print("\n" + "="*60)
        print("🎮 System is running! Available endpoints:")
        for service, url in SERVICE_URLS.items():
            print(f"   • {service}: {url}")
        print("\n💡 Press Ctrl+C to shutdown all services")
        print("💡 Visit http://localhost:8000/docs for API documentation")
        
        # Keep running until shutdown
        while not shutdown_requested:
            await asyncio.sleep(1)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠ Received keyboard interrupt")
        return 0
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1
    finally:
        shutdown_all_services()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)