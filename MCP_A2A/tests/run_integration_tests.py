"""
Integration test runner for MCP A2A Trading System.

This script starts all required services and runs comprehensive integration tests.
"""

import asyncio
import subprocess
import sys
import time
import signal
import os
from typing import List, Optional
import httpx
import pytest

from MCP_A2A.config import SERVICE_URLS


class ServiceManager:
    """Manages starting and stopping all system services for testing."""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.services_config = [
            # MCP Servers
            {
                "name": "MarketDataMCP",
                "module": "MCP_A2A.mcp_servers.market_data_server",
                "port": 9000
            },
            {
                "name": "TechnicalAnalysisMCP", 
                "module": "MCP_A2A.mcp_servers.technical_analysis_server",
                "port": 9001
            },
            {
                "name": "TradingExecutionMCP",
                "module": "MCP_A2A.mcp_servers.trading_execution_server", 
                "port": 9002
            },
            # Agent Services
            {
                "name": "FundamentalAnalyst",
                "module": "MCP_A2A.agents.fundamental_analyst_agent",
                "port": 8001
            },
            {
                "name": "TechnicalAnalyst",
                "module": "MCP_A2A.agents.technical_analyst_agent",
                "port": 8002
            },
            {
                "name": "RiskManager", 
                "module": "MCP_A2A.agents.risk_manager_agent",
                "port": 8003
            },
            {
                "name": "TradeExecutor",
                "module": "MCP_A2A.agents.trade_executor_agent",
                "port": 8004
            },
            {
                "name": "PortfolioManager",
                "module": "MCP_A2A.agents.portfolio_manager_agent",
                "port": 8000
            }
        ]
    
    async def start_service(self, service_config: dict) -> Optional[subprocess.Popen]:
        """Start a single service."""
        try:
            print(f"Starting {service_config['name']} on port {service_config['port']}...")
            
            # Start the service process
            process = subprocess.Popen([
                sys.executable, "-m", service_config["module"]
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a moment for the service to start
            await asyncio.sleep(2)
            
            # Check if service is responding
            service_url = f"http://localhost:{service_config['port']}"
            if await self.wait_for_service(service_url):
                print(f"✓ {service_config['name']} started successfully")
                return process
            else:
                print(f"✗ {service_config['name']} failed to start")
                process.terminate()
                return None
                
        except Exception as e:
            print(f"✗ Error starting {service_config['name']}: {e}")
            return None
    
    async def wait_for_service(self, url: str, max_retries: int = 15) -> bool:
        """Wait for a service to become available."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            for _ in range(max_retries):
                try:
                    response = await client.get(f"{url}/health")
                    if response.status_code == 200:
                        return True
                except:
                    pass
                await asyncio.sleep(1)
        return False
    
    async def start_all_services(self) -> bool:
        """Start all services required for integration testing."""
        print("Starting all services for integration testing...")
        
        for service_config in self.services_config:
            process = await self.start_service(service_config)
            if process:
                self.processes.append(process)
            else:
                print(f"Failed to start {service_config['name']}")
                await self.stop_all_services()
                return False
        
        print(f"✓ All {len(self.processes)} services started successfully")
        return True
    
    async def stop_all_services(self):
        """Stop all running services."""
        print("Stopping all services...")
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                print(f"Error stopping process: {e}")
        
        self.processes.clear()
        print("✓ All services stopped")
    
    async def health_check_all_services(self) -> bool:
        """Perform health check on all services."""
        print("Performing health check on all services...")
        
        services_to_check = [
            ("PortfolioManager", SERVICE_URLS["portfolio_manager"]),
            ("FundamentalAnalyst", SERVICE_URLS["fundamental_analyst"]),
            ("TechnicalAnalyst", SERVICE_URLS["technical_analyst"]),
            ("RiskManager", SERVICE_URLS["risk_manager"]),
            ("TradeExecutor", SERVICE_URLS["trade_executor"]),
            ("MarketDataMCP", SERVICE_URLS["market_data_mcp"]),
            ("TechnicalAnalysisMCP", SERVICE_URLS["technical_analysis_mcp"]),
            ("TradingExecutionMCP", SERVICE_URLS["trading_execution_mcp"])
        ]
        
        all_healthy = True
        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, url in services_to_check:
                try:
                    response = await client.get(f"{url}/health")
                    if response.status_code == 200:
                        print(f"✓ {name} is healthy")
                    else:
                        print(f"✗ {name} health check failed (status: {response.status_code})")
                        all_healthy = False
                except Exception as e:
                    print(f"✗ {name} health check failed: {e}")
                    all_healthy = False
        
        return all_healthy


class IntegrationTestRunner:
    """Runs integration tests with proper service management."""
    
    def __init__(self):
        self.service_manager = ServiceManager()
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print("\nReceived interrupt signal, shutting down...")
            asyncio.create_task(self.cleanup())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.service_manager.stop_all_services()
    
    async def run_tests(self, test_args: List[str] = None) -> int:
        """Run integration tests with service management."""
        try:
            # Start all services
            print("=" * 60)
            print("MCP A2A Trading System - Integration Test Runner")
            print("=" * 60)
            
            if not await self.service_manager.start_all_services():
                print("✗ Failed to start all services")
                return 1
            
            # Wait a bit more for services to fully initialize
            print("Waiting for services to fully initialize...")
            await asyncio.sleep(5)
            
            # Perform health check
            if not await self.service_manager.health_check_all_services():
                print("✗ Health check failed")
                return 1
            
            print("\n" + "=" * 60)
            print("Running Integration Tests")
            print("=" * 60)
            
            # Prepare test arguments
            if test_args is None:
                test_args = [
                    "MCP_A2A/tests/test_integration_workflows.py",
                    "-v",
                    "--tb=short",
                    "--maxfail=5",
                    "-x"  # Stop on first failure for faster feedback
                ]
            
            # Run pytest
            exit_code = pytest.main(test_args)
            
            print("\n" + "=" * 60)
            print("Integration Tests Completed")
            print("=" * 60)
            
            if exit_code == 0:
                print("✓ All integration tests passed!")
            else:
                print(f"✗ Integration tests failed (exit code: {exit_code})")
            
            return exit_code
            
        except Exception as e:
            print(f"✗ Error running integration tests: {e}")
            return 1
        
        finally:
            await self.cleanup()


async def main():
    """Main entry point for integration test runner."""
    runner = IntegrationTestRunner()
    
    # Parse command line arguments
    test_args = sys.argv[1:] if len(sys.argv) > 1 else None
    
    try:
        exit_code = await runner.run_tests(test_args)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        await runner.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    # Run the integration test runner
    asyncio.run(main())