#!/usr/bin/env python3
"""
Setup script for Sticky Note Printer
Allows standalone installation via pip
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read version from package
version = "1.0.0"

setup(
    name="stickyprint",
    version=version,
    description="Print notifications, QR codes, calendar events, and todo lists to IPP-compatible sticky note printers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sticky Print Development Team",
    author_email="dev@stickyprint.local",
    url="https://github.com/your-username/stickyprint",
    license="MIT",
    
    packages=find_packages(),
    include_package_data=True,
    
    python_requires=">=3.8",
    
    install_requires=[
        "aiohttp>=3.9.1",
        "Pillow>=10.1.0",
        "qrcode[pil]>=7.4.2",
        "requests>=2.31.0",
        "aiofiles>=23.2.1",
        "python-dateutil>=2.8.2",
        "pydantic>=2.5.2",
        "pyyaml>=6.0.0",
    ],
    
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "ha": [
            "asyncio-mqtt>=0.16.2",
        ]
    },
    
    entry_points={
        "console_scripts": [
            "stickyprint=src.main:main",
            "stickyprint-cli=src.cli:main",
            "stickyprint-config=src.config:create_example_config_cli",
        ],
    },
    
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Home Automation",
        "Topic :: Printing",
        "Topic :: System :: Networking",
    ],
    
    keywords="home-assistant printer ipp sticky-note automation notifications qr-code calendar todo",
    
    project_urls={
        "Bug Reports": "https://github.com/your-username/stickyprint/issues",
        "Source": "https://github.com/your-username/stickyprint",
        "Documentation": "https://github.com/your-username/stickyprint/blob/main/README.md",
    },
)
