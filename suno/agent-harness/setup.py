"""Setup for cli-web-suno: Agent-native CLI for Suno AI Music Generator."""

from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-suno",
    version="0.1.0",
    description="Agent-native CLI for Suno AI Music Generator",
    packages=find_namespace_packages(include=["cli_web.*"]),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "httpx>=0.24.0",
        "websockets>=12.0",
    ],
    extras_require={
        "browser": ["playwright>=1.40.0"],
    },
    entry_points={
        "console_scripts": [
            "cli-web-suno=cli_web.suno.suno_cli:cli",
        ],
    },
)
