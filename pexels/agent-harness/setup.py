"""Setup for cli-web-pexels."""

from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-pexels",
    version="0.1.0",
    description="CLI for Pexels free stock photos and videos",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "curl_cffi>=0.5",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-pexels=cli_web.pexels.pexels_cli:main",
        ],
    },
)
