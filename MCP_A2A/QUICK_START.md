# Quick Start Guide

## 🚀 Fastest Way to Run

```bash
cd MCP_A2A
python run.py
```

This will:
- Check your Python version
- Install required packages
- Run setup checks
- Start the trading system

## 📋 Manual Steps

### 1. Check Setup
```bash
python check_setup.py
```

### 2. Install Dependencies (if needed)
```bash
pip install fastapi uvicorn httpx pydantic numpy
```

### 3. Start System
```bash
python start_system.py
```

## 🔧 If You Get Errors

### Import Errors
```bash
# Make sure you're in the right directory
cd MCP_A2A

# Install missing packages
pip install fastapi uvicorn httpx pydantic numpy python-dotenv

# Try the simple startup
python start_system.py
```

### Port Conflicts
```bash
# Check what's using the ports
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Mac/Linux

# Kill the process or use different ports
```

### Module Not Found
```bash
# Make sure you're in the MCP_A2A directory
pwd  # Should show .../MCP_A2A

# Try absolute path
python /full/path/to/MCP_A2A/start_system.py
```

## 🎯 What Should Happen

When working correctly, you'll see:
```
🚀 Starting MCP A2A Trading System
✓ Started MarketData MCP (PID: 1234)
✓ Started TechnicalAnalysis MCP (PID: 1235)
...
✓ Trading strategy executed successfully!
🎮 System is running! Available endpoints:
   • portfolio_manager: http://localhost:8000
   • market_data_mcp: http://localhost:9000
   ...
```

## 🌐 Test the System

Visit: http://localhost:8000/docs

Or test with curl:
```bash
curl -X POST http://localhost:8000/start_strategy \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Find a good tech stock",
    "sector_preference": "technology",
    "risk_tolerance": "medium",
    "max_investment": 10000
  }'
```

## 🆘 Still Having Issues?

1. **Check Python version**: `python --version` (need 3.8+)
2. **Check directory**: Make sure you're in the MCP_A2A folder
3. **Check ports**: Make sure ports 8000-8004 and 9000-9002 are free
4. **Try Docker**: `docker-compose up` (if you have Docker)
5. **Manual install**: `pip install -r requirements.txt`

## 📞 Common Error Solutions

**"No module named 'config'"**
- Make sure you're in the MCP_A2A directory
- Try: `python start_system.py` instead of `python main.py`

**"Port already in use"**
- Kill the process using the port
- Or wait a few minutes and try again

**"Permission denied"**
- Try: `python3` instead of `python`
- Or run as administrator/sudo

**"Package not found"**
- Run: `pip install fastapi uvicorn httpx pydantic numpy`
- Or: `pip install -r requirements.txt`