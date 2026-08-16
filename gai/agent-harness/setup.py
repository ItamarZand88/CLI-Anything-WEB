from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-gai",
    version="0.1.1",
    description="CLI for Google AI Mode — AI-powered search with source references",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "playwright>=1.40",
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-gai=cli_web.gai.gai_cli:main",
        ],
    },
)
