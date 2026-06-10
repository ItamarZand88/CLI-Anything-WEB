from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-youtube",
    version="0.1.0",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    description="CLI for YouTube — search videos, get details, browse trending, explore channels",
    install_requires=[
        "click>=8.0",
        "httpx",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-youtube=cli_web.youtube.youtube_cli:main",
        ],
    },
    python_requires=">=3.10",
)
