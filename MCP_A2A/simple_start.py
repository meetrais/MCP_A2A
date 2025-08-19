#!/usr/bin/env python3
"""
Simple startup script for MCP A2A Trading System.
Avoids complex imports and focuses on getting the system running.
"""

import asyncio
import subprocess
import sys
import time
import os
import json
import signal
from typing import List
import httpx

# Simple configuration
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
    print(f"\nReceived signal {signum}, shutting down...")
    shutdown_requested = True

def start_service(module_path: str, port: int, service_name: str) -> bool:
    """Start a service and return success status."""
    try:
        print(f"Starting {service_name} on port {port}...")
        
        # Try different startup methods
        startup_commands = [
            # Method 1: Direct uvicorn
            [sys.executable, "-m", "uvicorn", f"{module_path}:app", 
             "--host", "0.0.0.0", "--port", str(port), "--log-level", "error"],
            
            # Method 2: Direct Python execution
            [sys.executable, "-m", module_path],
            
            # Method 3: File execution
            [sys.executable, f"{module_path.replace('.', '/')}.py"]
        ]
        
        for cmd in startup_commands:
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                
                # Wait a moment to see if it starts
                time.sleep(2)
                if process.poll() is None:  # Still running
                    running_processes.append(process)
                    print(f"✓ {service_name} started (PID: {process.pid})")
                    return True
                else:
                    # Process died, try next method
                    stdout, stderr = process.communicate()
                    continue
                    
            except Exception:
                continue
        
        print(f"✗ Failed to start {service_name}")
        return False
        
    except Exception as e:
        print(f"✗ Error starting {service_name}: {e}")
        return False

async def wait_for_service(url: str, service_name: str, timeout: int = 20) -> bool:
    """Wait for service to become available."""
    print(f"Waiting for {service_name}...")
    
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(f"{url}/health", timeout=3.0)
                if response.status_code == 200:
                    print(f"✓ {service_name} is ready!")
                    return True
            except:
                pass
            await asyncio.sleep(1)
    
    print(f"⚠ {service_name} not responding (continuing anyway)")
    return False

async def test_trading_workflow():
    """Test the trading system with a simple request."""
    try:
        print("\n" + "="*50)
        print("🎯 Testing Trading Workflow")
        print("="*50)
        
        strategy = {
            "goal": "Find a good tech stock to invest in",
            "sector_preference": "technology",
            "risk_tolerance": "medium",
            "max_investment": 10000.0,
            "time_horizon": "short"
        }
        
        print("Sending trading strategy request...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
                json=strategy
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Trading workflow completed successfully!")
                print(f"Result: {json.dumps(result, indent=2)}")
                return True
            else:
                print(f"❌ Trading workflow failed: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error in trading workflow: {e}")
        return False

def shutdown_all_services():
    """Shutdown all services."""
    print("\nShutting down services...")
    
    for process in running_processes:
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        except Exception:
            pass
    
    running_processes.clear()
    print("✓ All services stopped")

async def main():
    """Main function."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("🚀 MCP A2A Trading System - Simple Startup")
        print("="*50)
        
        # Services to start (order matters)
        services = [
            ("mcp_servers.market_data_server", PORTS["market_data_mcp"], "MarketData MCP"),
            ("mcp_servers.technical_analysis_server", PORTS["technical_analysis_mcp"], "TechnicalAnalysis MCP"),
            ("mcp_servers.trading_execution_server", PORTS["trading_execution_mcp"], "TradingExecution MCP"),
            ("agents.fundamental_analyst_agent", PORTS["fundamental_analyst"], "FundamentalAnalyst"),
            ("agents.technical_analyst_agent", PORTS["technical_analyst"], "TechnicalAnalyst"),
            ("agents.risk_manager_agent", PORTS["risk_manager"], "RiskManager"),
            ("agents.trade_executor_agent", PORTS["trade_executor"], "TradeExecutor"),
            ("agents.portfolio_manager_agent", PORTS["portfolio_manager"], "PortfolioManager"),
        ]
        
        # Start all services
        started_services = 0
        for module, port, name in services:
            if start_service(module, port, name):
                started_services += 1
            await asyncio.sleep(1)  # Small delay between starts
        
        print(f"\n📊 Started {started_services}/{len(services)} services")
        
        if started_services == 0:
            print("❌ No services started successfully")
            return 1
        
        # Wait for key services
        print("\n🔍 Checking service health...")
        key_services = [
            (SERVICE_URLS["market_data_mcp"], "MarketData MCP"),
            (SERVICE_URLS["portfolio_manager"], "PortfolioManager")
        ]
        
        for url, name in key_services:
            await wait_for_service(url, name)
        
        # Test the system
        await test_trading_workflow()
        
        print("\n" + "="*50)
        print("🎮 System is running!")
        print("Available endpoints:")
        for service, url in SERVICE_URLS.items():
            print(f"  • {service}: {url}")
        print("\n💡 Press Ctrl+C to shutdown")
        print("💡 Visit http://localhost:8000/docs for API documentation")
        
        # Keep running
        while not shutdown_requested:
            await asyncio.sleep(1)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠ Shutdown requested")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        shutdown_all_services()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)