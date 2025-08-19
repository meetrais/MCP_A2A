# MCP A2A Trading System - Deployment Guide

This guide provides comprehensive instructions for deploying the MCP A2A Trading System in various environments.

## 📋 Table of Contents

- [Development Environment](#development-environment)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Monitoring and Observability](#monitoring-and-observability)
- [Security Configuration](#security-configuration)
- [Troubleshooting](#troubleshooting)

## 🛠️ Development Environment

### Prerequisites

- **Python 3.8+** with pip
- **Git** for version control
- **Available Ports**: 8000-8004, 9000-9002
- **Memory**: Minimum 2GB RAM
- **Disk Space**: 1GB free space

### Quick Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd MCP_A2A

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python -c "import fastapi, httpx; print('✓ Dependencies installed')"

# 5. Run system
python main.py
```

### Environment Configuration

Create `.env` file in project root:

```env
# Development Configuration
LOG_LEVEL=INFO
LOG_FORMAT=structured

# Service Ports
PORTFOLIO_MANAGER_PORT=8000
FUNDAMENTAL_ANALYST_PORT=8001
TECHNICAL_ANALYST_PORT=8002
RISK_MANAGER_PORT=8003
TRADE_EXECUTOR_PORT=8004
MARKET_DATA_MCP_PORT=9000
TECHNICAL_ANALYSIS_MCP_PORT=9001
TRADING_EXECUTION_MCP_PORT=9002

# Trading Parameters
INITIAL_PORTFOLIO_VALUE=100000.0
MAX_POSITION_SIZE=0.10
MIN_CASH_RESERVE=0.20
MAX_TRADE_VALUE=10000.0

# Performance Settings
REQUEST_TIMEOUT=30
WORKFLOW_TIMEOUT=120
MAX_RETRIES=3
```

## 🐳 Docker Deployment

### Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Expose ports
EXPOSE 8000 8001 8002 8003 8004 9000 9001 9002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health')"

# Start command
CMD ["python", "main.py"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # MCP Servers
  market-data-mcp:
    build: .
    command: python -m MCP_A2A.mcp_servers.market_data_server
    ports:
      - "9000:9000"
    environment:
      - LOG_LEVEL=INFO
      - PORT=9000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  technical-analysis-mcp:
    build: .
    command: python -m MCP_A2A.mcp_servers.technical_analysis_server
    ports:
      - "9001:9001"
    environment:
      - LOG_LEVEL=INFO
      - PORT=9001
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  trading-execution-mcp:
    build: .
    command: python -m MCP_A2A.mcp_servers.trading_execution_server
    ports:
      - "9002:9002"
    environment:
      - LOG_LEVEL=INFO
      - PORT=9002
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Agent Services
  fundamental-analyst:
    build: .
    command: python -m MCP_A2A.agents.fundamental_analyst_agent
    ports:
      - "8001:8001"
    environment:
      - LOG_LEVEL=INFO
      - PORT=8001
    depends_on:
      - market-data-mcp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  technical-analyst:
    build: .
    command: python -m MCP_A2A.agents.technical_analyst_agent
    ports:
      - "8002:8002"
    environment:
      - LOG_LEVEL=INFO
      - PORT=8002
    depends_on:
      - market-data-mcp
      - technical-analysis-mcp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  risk-manager:
    build: .
    command: python -m MCP_A2A.agents.risk_manager_agent
    ports:
      - "8003:8003"
    environment:
      - LOG_LEVEL=INFO
      - PORT=8003
    depends_on:
      - trading-execution-mcp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  trade-executor:
    build: .
    command: python -m MCP_A2A.agents.trade_executor_agent
    ports:
      - "8004:8004"
    environment:
      - LOG_LEVEL=INFO
      - PORT=8004
    depends_on:
      - trading-execution-mcp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  portfolio-manager:
    build: .
    command: python -m MCP_A2A.agents.portfolio_manager_agent
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
      - PORT=8000
    depends_on:
      - fundamental-analyst
      - technical-analyst
      - risk-manager
      - trade-executor
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Monitoring (Optional)
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
    restart: unless-stopped

volumes:
  grafana-storage:

networks:
  default:
    name: mcp-a2a-network
```

### Docker Commands

```bash
# Build and start all services
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild specific service
docker-compose build portfolio-manager
docker-compose up -d portfolio-manager

# Scale services (if needed)
docker-compose up --scale technical-analyst=2
```

## 🏭 Production Deployment

### System Requirements

**Minimum Requirements**:
- **CPU**: 4 cores
- **Memory**: 8GB RAM
- **Storage**: 20GB SSD
- **Network**: 100 Mbps

**Recommended Requirements**:
- **CPU**: 8 cores
- **Memory**: 16GB RAM
- **Storage**: 50GB SSD
- **Network**: 1 Gbps

### Production Configuration

Create `production.env`:

```env
# Production Configuration
ENVIRONMENT=production
LOG_LEVEL=WARNING
LOG_FORMAT=json

# Security
ENABLE_HTTPS=true
SSL_CERT_PATH=/etc/ssl/certs/trading-system.crt
SSL_KEY_PATH=/etc/ssl/private/trading-system.key
API_KEY_REQUIRED=true
RATE_LIMIT_ENABLED=true

# Database (if using persistent storage)
DATABASE_URL=postgresql://user:password@localhost:5432/trading_system

# Redis (for caching and session management)
REDIS_URL=redis://localhost:6379/0

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30

# Performance
MAX_WORKERS=4
WORKER_TIMEOUT=300
MAX_CONCURRENT_REQUESTS=100
```

### Systemd Service Files

Create `/etc/systemd/system/mcp-a2a-trading.service`:

```ini
[Unit]
Description=MCP A2A Trading System
After=network.target
Requires=network.target

[Service]
Type=simple
User=trading
Group=trading
WorkingDirectory=/opt/mcp-a2a-trading
Environment=PATH=/opt/mcp-a2a-trading/venv/bin
EnvironmentFile=/opt/mcp-a2a-trading/production.env
ExecStart=/opt/mcp-a2a-trading/venv/bin/python main.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mcp-a2a-trading

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration

Create `/etc/nginx/sites-available/mcp-a2a-trading`:

```nginx
upstream portfolio_manager {
    server 127.0.0.1:8000;
}

upstream mcp_servers {
    server 127.0.0.1:9000;
    server 127.0.0.1:9001;
    server 127.0.0.1:9002;
}

server {
    listen 80;
    server_name trading-system.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name trading-system.example.com;

    ssl_certificate /etc/ssl/certs/trading-system.crt;
    ssl_certificate_key /etc/ssl/private/trading-system.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Main API
    location /api/ {
        proxy_pass http://portfolio_manager/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_timeout 300s;
    }

    # Health checks
    location /health {
        proxy_pass http://portfolio_manager/health;
        access_log off;
    }

    # Static files (if any)
    location /static/ {
        alias /opt/mcp-a2a-trading/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Production Deployment Steps

```bash
# 1. Create deployment user
sudo useradd -m -s /bin/bash trading
sudo usermod -aG sudo trading

# 2. Create application directory
sudo mkdir -p /opt/mcp-a2a-trading
sudo chown trading:trading /opt/mcp-a2a-trading

# 3. Deploy application
sudo -u trading git clone <repository-url> /opt/mcp-a2a-trading
cd /opt/mcp-a2a-trading

# 4. Create virtual environment
sudo -u trading python3 -m venv venv
sudo -u trading venv/bin/pip install -r requirements.txt

# 5. Configure environment
sudo -u trading cp production.env.example production.env
sudo -u trading nano production.env

# 6. Install systemd service
sudo cp deployment/mcp-a2a-trading.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mcp-a2a-trading

# 7. Configure nginx
sudo cp deployment/nginx.conf /etc/nginx/sites-available/mcp-a2a-trading
sudo ln -s /etc/nginx/sites-available/mcp-a2a-trading /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 8. Start services
sudo systemctl start mcp-a2a-trading
sudo systemctl status mcp-a2a-trading
```

## ☁️ Cloud Deployment

### AWS Deployment

#### ECS with Fargate

Create `ecs-task-definition.json`:

```json
{
  "family": "mcp-a2a-trading",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "portfolio-manager",
      "image": "your-account.dkr.ecr.region.amazonaws.com/mcp-a2a-trading:latest",
      "command": ["python", "-m", "MCP_A2A.agents.portfolio_manager_agent"],
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        },
        {
          "name": "PORT",
          "value": "8000"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mcp-a2a-trading",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

#### Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: portfolio-manager
  labels:
    app: mcp-a2a-trading
    component: portfolio-manager
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mcp-a2a-trading
      component: portfolio-manager
  template:
    metadata:
      labels:
        app: mcp-a2a-trading
        component: portfolio-manager
    spec:
      containers:
      - name: portfolio-manager
        image: mcp-a2a-trading:latest
        command: ["python", "-m", "MCP_A2A.agents.portfolio_manager_agent"]
        ports:
        - containerPort: 8000
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: PORT
          value: "8000"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: portfolio-manager-service
spec:
  selector:
    app: mcp-a2a-trading
    component: portfolio-manager
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Google Cloud Platform

#### Cloud Run Deployment

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/mcp-a2a-trading

# Deploy to Cloud Run
gcloud run deploy mcp-a2a-trading \
  --image gcr.io/PROJECT_ID/mcp-a2a-trading \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 100 \
  --timeout 300 \
  --set-env-vars LOG_LEVEL=INFO,ENVIRONMENT=production
```

### Azure Container Instances

```bash
# Create resource group
az group create --name mcp-a2a-trading --location eastus

# Deploy container
az container create \
  --resource-group mcp-a2a-trading \
  --name mcp-a2a-trading \
  --image your-registry.azurecr.io/mcp-a2a-trading:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables LOG_LEVEL=INFO ENVIRONMENT=production \
  --restart-policy Always
```

## 📊 Monitoring and Observability

### Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "trading_system_rules.yml"

scrape_configs:
  - job_name: 'mcp-a2a-trading'
    static_configs:
      - targets: ['localhost:8000', 'localhost:8001', 'localhost:8002', 'localhost:8003', 'localhost:8004']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'mcp-servers'
    static_configs:
      - targets: ['localhost:9000', 'localhost:9001', 'localhost:9002']
    metrics_path: '/metrics'
    scrape_interval: 10s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboard

Create `monitoring/grafana-dashboard.json`:

```json
{
  "dashboard": {
    "title": "MCP A2A Trading System",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{service}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      }
    ]
  }
}
```

### Logging Configuration

Create `logging.yaml`:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /var/log/mcp-a2a-trading/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

  syslog:
    class: logging.handlers.SysLogHandler
    level: WARNING
    formatter: json
    address: ['localhost', 514]

loggers:
  MCP_A2A:
    level: INFO
    handlers: [console, file]
    propagate: false

  uvicorn:
    level: INFO
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console, file, syslog]
```

## 🔒 Security Configuration

### SSL/TLS Configuration

```bash
# Generate self-signed certificate (development)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Or use Let's Encrypt (production)
certbot certonly --nginx -d trading-system.example.com
```

### API Key Authentication

Add to `config.py`:

```python
import secrets
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# Generate API keys
API_KEYS = {
    "client1": secrets.token_urlsafe(32),
    "client2": secrets.token_urlsafe(32)
}

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials not in API_KEYS.values():
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials
```

### Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/start_strategy")
@limiter.limit("10/minute")
async def start_strategy(request: Request, strategy: InvestmentStrategy):
    # Implementation
    pass
```

## 🔧 Troubleshooting

### Common Deployment Issues

#### Port Conflicts

```bash
# Check port usage
netstat -tulpn | grep :8000
lsof -i :8000

# Kill process using port
sudo kill -9 $(lsof -t -i:8000)
```

#### Memory Issues

```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Adjust container memory limits
docker run --memory=2g mcp-a2a-trading
```

#### Service Dependencies

```bash
# Check service status
systemctl status mcp-a2a-trading
journalctl -u mcp-a2a-trading -f

# Restart services in order
systemctl restart mcp-a2a-trading
```

### Performance Tuning

#### Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_portfolio_ticker ON portfolio(ticker);
```

#### Caching Configuration

```python
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, expiration, json.dumps(result))
            return result
        return wrapper
    return decorator
```

### Health Check Scripts

Create `scripts/health_check.sh`:

```bash
#!/bin/bash

# Health check script for MCP A2A Trading System

SERVICES=(
    "http://localhost:8000/health"
    "http://localhost:8001/health"
    "http://localhost:8002/health"
    "http://localhost:8003/health"
    "http://localhost:8004/health"
    "http://localhost:9000/health"
    "http://localhost:9001/health"
    "http://localhost:9002/health"
)

echo "Checking service health..."

for service in "${SERVICES[@]}"; do
    if curl -f -s "$service" > /dev/null; then
        echo "✓ $service is healthy"
    else
        echo "✗ $service is unhealthy"
        exit 1
    fi
done

echo "All services are healthy!"
```

### Backup and Recovery

```bash
#!/bin/bash

# Backup script
BACKUP_DIR="/backup/mcp-a2a-trading/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup configuration
cp -r /opt/mcp-a2a-trading/config "$BACKUP_DIR/"

# Backup logs
cp -r /var/log/mcp-a2a-trading "$BACKUP_DIR/"

# Backup database (if using persistent storage)
pg_dump trading_system > "$BACKUP_DIR/database.sql"

echo "Backup completed: $BACKUP_DIR"
```

---

This deployment guide provides comprehensive instructions for deploying the MCP A2A Trading System in various environments, from development to production cloud deployments. Choose the deployment method that best fits your requirements and infrastructure.