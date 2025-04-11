#!/usr/bin/env python3
"""
Setup script for the Wikipedia MCP server.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="wikipedia-mcp",
    version="0.1.0",
    author="Ravikumar E",
    author_email="your.email@example.com",
    description="A Model Context Protocol server for Wikipedia integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rudra-ravi/wikipedia-mcp.git",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "wikipedia-mcp=wikipedia_mcp.__main__:main",
        ],
    },
)
