from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-futbin",
    version="0.1.0",
    description="Agent-native CLI for FUTBIN — EA FC Ultimate Team database",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    install_requires=[
        "click>=8.0",
        "httpx>=0.24",
        "beautifulsoup4>=4.12",
        "rich>=13.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-futbin=cli_web.futbin.futbin_cli:cli",
        ],
    },
    python_requires=">=3.10",
)
