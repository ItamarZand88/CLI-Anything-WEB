"""Setup for cli-web-notebooklm — CLI harness for Google NotebookLM."""

from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-notebooklm",
    version="0.1.0",
    description="CLI harness for Google NotebookLM via cli-anything-web",
    author="Itamar Zand",
    python_requires=">=3.10",
    packages=find_namespace_packages(include=["cli_web.*"]),
    install_requires=[
        "click>=8.0",
        "requests>=2.28",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "pytest-mock>=3.10", "responses>=0.23"],
    },
    entry_points={
        "console_scripts": [
            "cli-web-notebooklm=cli_web.notebooklm.notebooklm_cli:cli",
        ],
    },
)
