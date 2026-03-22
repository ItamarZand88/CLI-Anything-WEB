from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-stitch",
    version="0.1.0",
    description="CLI for Google Stitch AI design tool",
    packages=find_namespace_packages(include=["cli_web.*"]),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "httpx>=0.24",
        "rich>=13.0",
    ],
    extras_require={
        "auth": ["playwright>=1.40"],
    },
    entry_points={
        "console_scripts": [
            "cli-web-stitch=cli_web.stitch.stitch_cli:cli",
        ],
    },
)
