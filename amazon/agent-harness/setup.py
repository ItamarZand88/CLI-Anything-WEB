"""Setup for cli-web-amazon."""
from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-amazon",
    version="1.0.0",
    description="Amazon CLI — Search, browse, and shop Amazon from your terminal",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={"": ["skills/*.md", "*.md"]},
    install_requires=[
        "click>=8.0",
        "httpx>=0.25",
        "beautifulsoup4>=4.12",
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-amazon=cli_web.amazon.amazon_cli:main",
        ],
    },
    python_requires=">=3.10",
)
