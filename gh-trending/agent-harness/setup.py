"""Setup for cli-web-gh-trending — GitHub Trending CLI."""

from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-gh-trending",
    version="1.0.0",
    description="CLI for GitHub Trending repositories and developers",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    install_requires=[
        "click>=8.0",
        "httpx>=0.24",
        "beautifulsoup4>=4.12",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-gh-trending=cli_web.gh_trending.gh_trending_cli:main",
        ],
    },
    python_requires=">=3.10",
)
