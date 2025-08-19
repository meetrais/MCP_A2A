# MCP A2A Trading System - Docker Configuration
# Multi-stage build for optimized production image

# =============================================================================
# BUILD STAGE
# =============================================================================
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION=1.0.0
ARG VCS_REF

# Set labels
LABEL maintainer="MCP A2A Trading Team <team@mcp-a2a-trading.com>"
LABEL org.label-schema.build-date=$BUILD_DATE
LABEL org.label-schema.name="MCP A2A Trading System"
LABEL org.label-schema.description="Multi-agent financial trading system using MCP servers and A2A protocol"
LABEL org.label-schema.version=$VERSION
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.schema-version="1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
COPY setup.py .
COPY README.md .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

# Copy application code
COPY MCP_A2A/ ./MCP_A2A/

# Install the application
RUN pip install -e .

# =============================================================================
# PRODUCTION STAGE
# =============================================================================
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ENVIRONMENT=production
ENV LOG_LEVEL=INFO

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r trading && useradd -r -g trading trading

# Create application directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app/MCP_A2A ./MCP_A2A
COPY --from=builder /app/setup.py .
COPY --from=builder /app/README.md .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/config
RUN chown -R trading:trading /app

# Switch to non-root user
USER trading

# Expose ports
EXPOSE 8000 8001 8002 8003 8004 9000 9001 9002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "MCP_A2A.main"]

# =============================================================================
# DEVELOPMENT STAGE
# =============================================================================
FROM builder as development

# Install development dependencies
RUN pip install -e ".[dev,test,docs]"

# Install additional development tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Set development environment
ENV ENVIRONMENT=development
ENV DEBUG=true
ENV LOG_LEVEL=DEBUG

# Expose additional ports for development
EXPOSE 8000 8001 8002 8003 8004 9000 9001 9002 9090

# Development command with auto-reload
CMD ["uvicorn", "MCP_A2A.agents.portfolio_manager_agent:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]