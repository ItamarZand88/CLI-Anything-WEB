"""Setup for cli-web-unsplash."""

from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-unsplash",
    version="0.1.0",
    description="CLI for Unsplash photo search and discovery",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "curl_cffi",
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-unsplash=cli_web.unsplash.unsplash_cli:main",
        ],
    },
)
