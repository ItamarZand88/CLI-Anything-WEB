from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-worldcup",
    version="0.1.0",
    description="CLI for Worldcup",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={"": ["skills/*.md", "*.md"]},
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "httpx",
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-worldcup=cli_web.worldcup.worldcup_cli:main",
        ],
    },
)
