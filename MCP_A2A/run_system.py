"""
Simple runner script for the MCP A2A Trading System.
This script can be executed directly to start the entire system.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import and run the main orchestrator
from MCP_A2A.main import main
import asyncio

if __name__ == "__main__":
    print("🚀 MCP A2A Trading System")
    print("=" * 50)
    print("Starting sophisticated multi-agent trading system...")
    print("This will start all MCP servers and agents, then demonstrate")
    print("a complete trading workflow from strategy to execution.")
    print("=" * 50)
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)