"""Setup for cli-web-notebooklm."""

from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-notebooklm",
    version="1.0.0",
    description="Agent-native CLI for Google NotebookLM",
    author="CLI-Anything-Web",
    packages=find_namespace_packages(include=["cli_web.*"]),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "httpx>=0.24",
    ],
    extras_require={
        "browser": ["playwright>=1.40.0"],
        "dev": ["pytest>=7.0", "pytest-mock"],
    },
    entry_points={
        "console_scripts": [
            "cli-web-notebooklm=cli_web.notebooklm.notebooklm_cli:cli",
        ],
    },
)
