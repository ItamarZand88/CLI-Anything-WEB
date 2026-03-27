"""Setup for cli-web-hackernews — Hacker News CLI."""

from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-hackernews",
    version="0.2.0",
    description="CLI for Hacker News — browse, search, upvote, submit, comment, and more",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    install_requires=[
        "click>=8.0",
        "httpx>=0.24",
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-hackernews=cli_web.hackernews.hackernews_cli:main",
        ],
    },
    python_requires=">=3.10",
)
