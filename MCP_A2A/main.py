"""
Main orchestration script for the MCP A2A Trading System.
Starts all services and demonstrates the complete trading workflow.
"""

import asyncio
import subprocess
import sys
import time
import signal
import json
import os
from typing import List, Dict, Optional
from pathlib import Path
import httpx

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import PORTS, SERVICE_URLS
    from utils.logging_config import setup_logging, get_logger
except ImportError:
    # Fallback configuration if imports fail
    PORTS = {
        "portfolio_manager": 8000,
        "fundamental_analyst": 8001,
        "technical_analyst": 8002,
        "risk_manager": 8003,
        "trade_executor": 8004,
        "market_data_mcp": 9000,
        "technical_analysis_mcp": 9001,
        "trading_execution_mcp": 9002
    }
    
    SERVICE_URLS = {
        "portfolio_manager": "http://localhost:8000",
        "fundamental_analyst": "http://localhost:8001",
        "technical_analyst": "http://localhost:8002",
        "risk_manager": "http://localhost:8003",
        "trade_executor": "http://localhost:8004",
        "market_data_mcp": "http://localhost:9000",
        "technical_analysis_mcp": "http://localhost:9001",
        "trading_execution_mcp": "http://localhost:9002"
    }
    
    # Simple logging setup
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def setup_logging(name):
        pass
    
    def get_logger(name):
        return logging.getLogger(name)

# Initialize logging
setup_logging("main_orchestrator")
logger = get_logger(__name__)

# Global process tracking
running_processes: List[subprocess.Popen] = []
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def start_service(module_path: str, port: int, service_name: str) -> subprocess.Popen:
    """
    Start a service as a subprocess.
    
    Args:
        module_path: Python module path (e.g., 'MCP_A2A.mcp_servers.market_data_server')
        port: Port number for the service
        service_name: Human-readable service name
        
    Returns:
        Subprocess handle
    """
    try:
        logger.info(f"Starting {service_name} on port {port}...")
        
        # Use uvicorn to start the FastAPI service
        cmd = [
            sys.executable, "-m", "uvicorn",
            f"{module_path}:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--log-level", "info"
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        running_processes.append(process)
        logger.info(f"Started {service_name} (PID: {process.pid})")
        
        return process
        
    except Exception as e:
        logger.error(f"Failed to start {service_name}: {e}")
        raise


async def wait_for_service(url: str, service_name: str, timeout: int = 30) -> bool:
    """
    Wait for a service to become available.
    
    Args:
        url: Service health check URL
        service_name: Human-readable service name
        timeout: Timeout in seconds
        
    Returns:
        True if service is available, False otherwise
    """
    logger.info(f"Waiting for {service_name} to become available...")
    
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    logger.info(f"{service_name} is ready!")
                    return True
            except (httpx.RequestError, httpx.TimeoutException):
                pass
            
            await asyncio.sleep(1)
    
    logger.error(f"{service_name} failed to start within {timeout} seconds")
    return False


async def check_service_health(url: str, service_name: str) -> Dict:
    """
    Check service health status.
    
    Args:
        url: Service health check URL
        service_name: Human-readable service name
        
    Returns:
        Dictionary with health status
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return {
                    "service": service_name,
                    "status": "healthy",
                    "response": data
                }
            else:
                return {
                    "service": service_name,
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}"
                }
    except Exception as e:
        return {
            "service": service_name,
            "status": "unreachable",
            "error": str(e)
        }


async def start_all_services() -> bool:
    """
    Start all MCP servers and agents.
    
    Returns:
        True if all services started successfully, False otherwise
    """
    logger.info("Starting MCP A2A Trading System...")
    
    # Define services to start (order matters - MCP servers first, then agents)
    services = [
        # MCP Servers
        {
            "module": "MCP_A2A.mcp_servers.market_data_server",
            "port": PORTS["market_data_mcp"],
            "name": "MarketData MCP Server",
            "url": f"{SERVICE_URLS['market_data_mcp']}/"
        },
        {
            "module": "MCP_A2A.mcp_servers.technical_analysis_server",
            "port": PORTS["technical_analysis_mcp"],
            "name": "TechnicalAnalysis MCP Server",
            "url": f"{SERVICE_URLS['technical_analysis_mcp']}/"
        },
        {
            "module": "MCP_A2A.mcp_servers.trading_execution_server",
            "port": PORTS["trading_execution_mcp"],
            "name": "TradingExecution MCP Server",
            "url": f"{SERVICE_URLS['trading_execution_mcp']}/"
        },
        
        # Agents
        {
            "module": "MCP_A2A.agents.fundamental_analyst_agent",
            "port": PORTS["fundamental_analyst"],
            "name": "FundamentalAnalyst Agent",
            "url": f"{SERVICE_URLS['fundamental_analyst']}/"
        },
        {
            "module": "MCP_A2A.agents.technical_analyst_agent",
            "port": PORTS["technical_analyst"],
            "name": "TechnicalAnalyst Agent",
            "url": f"{SERVICE_URLS['technical_analyst']}/"
        },
        {
            "module": "MCP_A2A.agents.risk_manager_agent",
            "port": PORTS["risk_manager"],
            "name": "RiskManager Agent",
            "url": f"{SERVICE_URLS['risk_manager']}/"
        },
        {
            "module": "MCP_A2A.agents.trade_executor_agent",
            "port": PORTS["trade_executor"],
            "name": "TradeExecutor Agent",
            "url": f"{SERVICE_URLS['trade_executor']}/"
        },
        {
            "module": "MCP_A2A.agents.portfolio_manager_agent",
            "port": PORTS["portfolio_manager"],
            "name": "PortfolioManager Agent",
            "url": f"{SERVICE_URLS['portfolio_manager']}/"
        }
    ]
    
    # Start all services
    for service in services:
        try:
            start_service(service["module"], service["port"], service["name"])
            # Small delay between service starts
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Failed to start {service['name']}: {e}")
            return False
    
    logger.info("All services started, waiting for them to become available...")
    
    # Wait for all services to become available
    for service in services:
        if not await wait_for_service(service["url"], service["name"]):
            logger.error(f"Service {service['name']} failed to become available")
            return False
    
    logger.info("All services are ready!")
    return True


async def perform_system_health_check() -> Dict:
    """
    Perform comprehensive system health check.
    
    Returns:
        Dictionary with health check results
    """
    logger.info("Performing system health check...")
    
    services = [
        ("MarketData MCP", f"{SERVICE_URLS['market_data_mcp']}/"),
        ("TechnicalAnalysis MCP", f"{SERVICE_URLS['technical_analysis_mcp']}/"),
        ("TradingExecution MCP", f"{SERVICE_URLS['trading_execution_mcp']}/"),
        ("FundamentalAnalyst Agent", f"{SERVICE_URLS['fundamental_analyst']}/"),
        ("TechnicalAnalyst Agent", f"{SERVICE_URLS['technical_analyst']}/"),
        ("RiskManager Agent", f"{SERVICE_URLS['risk_manager']}/"),
        ("TradeExecutor Agent", f"{SERVICE_URLS['trade_executor']}/"),
        ("PortfolioManager Agent", f"{SERVICE_URLS['portfolio_manager']}/")
    ]
    
    health_results = []
    
    for service_name, url in services:
        result = await check_service_health(url, service_name)
        health_results.append(result)
    
    healthy_count = sum(1 for result in health_results if result["status"] == "healthy")
    total_count = len(health_results)
    
    overall_status = "healthy" if healthy_count == total_count else "degraded"
    
    return {
        "overall_status": overall_status,
        "healthy_services": healthy_count,
        "total_services": total_count,
        "services": health_results
    }


async def demonstrate_trading_workflow() -> Dict:
    """
    Demonstrate the complete trading workflow.
    
    Returns:
        Dictionary with workflow results
    """
    logger.info("Demonstrating trading workflow...")
    
    try:
        # Create sample trading strategy
        strategy_request = {
            "goal": "Identify and execute a simulated trade for a fundamentally strong tech stock that is currently showing bullish technical signals",
            "sector_preference": "technology",
            "risk_tolerance": "medium",
            "max_investment": 25000.0,
            "time_horizon": "short"
        }
        
        logger.info(f"Initiating trading strategy: {strategy_request['goal']}")
        
        # Call PortfolioManager to execute strategy
        async with httpx.AsyncClient(timeout=120.0) as client:  # Extended timeout for full workflow
            response = await client.post(
                f"{SERVICE_URLS['portfolio_manager']}/start_strategy",
                json=strategy_request
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Trading workflow completed: {result.get('status', 'UNKNOWN')}")
                
                # Log key results
                if result.get("success"):
                    logger.info(f"✅ Trade executed successfully!")
                    logger.info(f"   Selected ticker: {result.get('selected_ticker')}")
                    if result.get("trade_execution"):
                        exec_result = result["trade_execution"]
                        logger.info(f"   Trade ID: {exec_result.get('trade_id')}")
                        logger.info(f"   Executed price: ${exec_result.get('executed_price', 0):.2f}")
                        logger.info(f"   Quantity: {exec_result.get('executed_quantity', 0)} shares")
                        logger.info(f"   Total value: ${exec_result.get('total_value', 0):.2f}")
                else:
                    logger.warning(f"❌ Trading workflow failed")
                    if result.get("errors"):
                        for error in result["errors"]:
                            logger.warning(f"   Error: {error}")
                
                return result
            else:
                error_msg = f"Trading workflow failed with HTTP {response.status_code}: {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "status": "FAILED"
                }
                
    except Exception as e:
        error_msg = f"Error in trading workflow demonstration: {e}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "status": "ERROR"
        }


def shutdown_all_services():
    """Shutdown all running services gracefully."""
    logger.info("Shutting down all services...")
    
    for process in running_processes:
        try:
            if process.poll() is None:  # Process is still running
                logger.info(f"Terminating process {process.pid}...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                    logger.info(f"Process {process.pid} terminated gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process {process.pid} did not terminate gracefully, killing...")
                    process.kill()
                    process.wait()
                    logger.info(f"Process {process.pid} killed")
        except Exception as e:
            logger.error(f"Error shutting down process {process.pid}: {e}")
    
    running_processes.clear()
    logger.info("All services shut down")


async def main():
    """Main orchestration function."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("🚀 Starting MCP A2A Trading System Orchestrator")
        
        # Start all services
        if not await start_all_services():
            logger.error("Failed to start all services, exiting...")
            return 1
        
        # Perform health check
        health_status = await perform_system_health_check()
        logger.info(f"System health: {health_status['overall_status']} "
                   f"({health_status['healthy_services']}/{health_status['total_services']} services healthy)")
        
        if health_status["overall_status"] != "healthy":
            logger.warning("Some services are not healthy, but continuing with demonstration...")
            for service in health_status["services"]:
                if service["status"] != "healthy":
                    logger.warning(f"  {service['service']}: {service['status']} - {service.get('error', 'N/A')}")
        
        # Demonstrate trading workflow
        logger.info("🎯 Starting trading workflow demonstration...")
        workflow_result = await demonstrate_trading_workflow()
        
        # Display results
        print("\n" + "="*80)
        print("🏆 MCP A2A TRADING SYSTEM DEMONSTRATION RESULTS")
        print("="*80)
        
        if workflow_result.get("success"):
            print("✅ WORKFLOW STATUS: SUCCESS")
            print(f"📊 Selected Ticker: {workflow_result.get('selected_ticker', 'N/A')}")
            print(f"⏱️  Execution Time: {workflow_result.get('execution_time_seconds', 0):.2f} seconds")
            
            if workflow_result.get("trade_execution"):
                exec_result = workflow_result["trade_execution"]
                print(f"💰 Trade ID: {exec_result.get('trade_id', 'N/A')}")
                print(f"💵 Executed Price: ${exec_result.get('executed_price', 0):.2f}")
                print(f"📈 Quantity: {exec_result.get('executed_quantity', 0)} shares")
                print(f"💸 Total Value: ${exec_result.get('total_value', 0):.2f}")
        else:
            print("❌ WORKFLOW STATUS: FAILED")
            if workflow_result.get("errors"):
                print("🚨 Errors:")
                for error in workflow_result["errors"]:
                    print(f"   • {error}")
        
        if workflow_result.get("warnings"):
            print("⚠️  Warnings:")
            for warning in workflow_result["warnings"]:
                print(f"   • {warning}")
        
        print("="*80)
        
        # Keep services running for manual testing
        logger.info("🎮 System is ready for manual testing!")
        logger.info("📡 Available endpoints:")
        logger.info(f"   • PortfolioManager: {SERVICE_URLS['portfolio_manager']}")
        logger.info(f"   • MarketData MCP: {SERVICE_URLS['market_data_mcp']}")
        logger.info(f"   • TechnicalAnalysis MCP: {SERVICE_URLS['technical_analysis_mcp']}")
        logger.info(f"   • TradingExecution MCP: {SERVICE_URLS['trading_execution_mcp']}")
        logger.info("💡 Press Ctrl+C to shutdown all services")
        
        # Wait for shutdown signal
        while not shutdown_requested:
            await asyncio.sleep(1)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error in main orchestration: {e}")
        return 1
    finally:
        shutdown_all_services()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)