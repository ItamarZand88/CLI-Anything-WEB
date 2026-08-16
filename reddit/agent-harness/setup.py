"""Setup for cli-web-reddit."""

from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-reddit",
    version="0.1.2",
    description="CLI for Reddit browsing, search, and interaction",
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
        # Required: auth login (and silent token refresh) drive a real browser
        # via playwright, and Reddit now 403s anonymous reads, so a logged-in
        # session is needed for every command.
        "playwright>=1.40.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-reddit=cli_web.reddit.reddit_cli:main",
        ],
    },
)
