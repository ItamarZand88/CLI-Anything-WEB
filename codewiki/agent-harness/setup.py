"""Setup for cli-web-codewiki."""

from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-codewiki",
    version="0.1.1",
    description="CLI for Google Code Wiki — AI-generated documentation for open source repos",
    packages=find_namespace_packages(include=["cli_web.*"]),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "httpx>=0.24",
        "rich>=13.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0"],
    },
    entry_points={
        "console_scripts": [
            "cli-web-codewiki=cli_web.codewiki.codewiki_cli:main",
        ],
    },
)
