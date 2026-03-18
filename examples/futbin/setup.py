"""Setup for cli-web-futbin."""

from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-futbin",
    version="1.0.0",
    description="CLI interface for FUTBIN — EA FC 26 Ultimate Team database",
    author="CLI-Anything-Web",
    packages=find_namespace_packages(include=["cli_web.*"]),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "httpx>=0.24.0",
        "beautifulsoup4>=4.12.0",
    ],
    extras_require={
        "browser": ["playwright>=1.40.0"],
        "repl": ["prompt_toolkit>=3.0.0"],
    },
    entry_points={
        "console_scripts": [
            "cli-web-futbin=cli_web.futbin.futbin_cli:main",
        ],
    },
)
