#!/usr/bin/env python3
"""
Setup script for Seegene Bid MCP Server
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="seegene-bid-mcp",
    version="2.0.0",
    author="Seegene",
    author_email="info@seegene.com",
    description="Global procurement bidding information collection and analysis system for Seegene",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/seegene/seegene-bid-mcp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Framework :: FastAPI",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "black>=23.11.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "seegene-bid-mcp=src.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.txt"],
    },
    keywords=[
        "mcp",
        "model-context-protocol",
        "procurement",
        "bidding",
        "government",
        "e-procurement",
        "seegene",
        "healthcare",
        "medical",
        "api",
        "crawler",
        "fastapi",
    ],
    project_urls={
        "Bug Reports": "https://github.com/seegene/seegene-bid-mcp/issues",
        "Source": "https://github.com/seegene/seegene-bid-mcp",
        "Documentation": "https://github.com/seegene/seegene-bid-mcp/blob/main/README.md",
    },
)