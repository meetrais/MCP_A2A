"""
Setup configuration for MCP A2A Trading System.
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements from requirements.txt
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mcp-a2a-trading-system",
    version="1.0.0",
    author="MCP A2A Trading System Team",
    author_email="team@mcp-a2a-trading.com",
    description="A sophisticated multi-agent financial trading system using MCP servers and A2A protocol",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/mcp-a2a-trading-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.7.0",
            "pre-commit>=3.6.0",
        ],
        "test": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "httpx-mock>=0.7.0",
        ],
        "docs": [
            "sphinx>=7.2.0",
            "sphinx-rtd-theme>=1.3.0",
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.4.0",
        ],
        "monitoring": [
            "prometheus-client>=0.19.0",
            "opentelemetry-api>=1.21.0",
            "opentelemetry-sdk>=1.21.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "mcp-a2a-trading=MCP_A2A.main:main",
            "mcp-a2a-test=MCP_A2A.tests.run_integration_tests:main",
            "mcp-a2a-health=MCP_A2A.utils.health_check:main",
        ],
    },
    include_package_data=True,
    package_data={
        "MCP_A2A": [
            "config/*.yaml",
            "config/*.json",
            "tests/data/*.json",
            "docs/*.md",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/your-org/mcp-a2a-trading-system/issues",
        "Source": "https://github.com/your-org/mcp-a2a-trading-system",
        "Documentation": "https://mcp-a2a-trading-system.readthedocs.io/",
    },
    keywords="trading, finance, mcp, a2a, multi-agent, microservices, fastapi",
)