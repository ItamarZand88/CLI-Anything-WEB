"""Setup for cli-web-airbnb."""
from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-airbnb",
    version="0.1.0",
    description="CLI for Airbnb — search stays, listings, and locations",
    packages=find_namespace_packages(include=["cli_web.*"]),
    install_requires=[
        "click>=8.0",
        "curl_cffi>=0.5.10",
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-airbnb=cli_web.airbnb.airbnb_cli:main",
        ],
    },
    package_data={"": ["skills/*.md", "*.md"]},
    python_requires=">=3.10",
)
