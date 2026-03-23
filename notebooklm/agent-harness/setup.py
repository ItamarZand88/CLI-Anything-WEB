"""Setup configuration for cli-web-notebooklm."""
from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-notebooklm",
    version="0.1.0",
    description="Agent-native CLI for NotebookLM — built with CLI-Anything-Web",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "httpx>=0.24.0",
        "rich>=13.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-notebooklm=cli_web.notebooklm.notebooklm_cli:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
