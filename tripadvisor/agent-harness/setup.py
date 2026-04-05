"""Setup for cli-web-tripadvisor."""
from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-tripadvisor",
    version="0.1.0",
    description="CLI for TripAdvisor — search hotels, restaurants, and attractions",
    packages=find_namespace_packages(include=["cli_web.*"]),
    install_requires=[
        "click>=8.0",
        "curl_cffi>=0.5.10",
        "beautifulsoup4>=4.12.0",
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-tripadvisor=cli_web.tripadvisor.tripadvisor_cli:main",
        ],
    },
    package_data={"": ["*.md"]},
    python_requires=">=3.10",
)
