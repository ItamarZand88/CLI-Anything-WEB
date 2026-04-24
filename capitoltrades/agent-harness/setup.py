from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-capitoltrades",
    version="0.1.0",
    description="CLI for Capitoltrades",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={"": ["skills/*.md", "*.md"]},
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "curl_cffi",
        "beautifulsoup4>=4.12",
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    extras_require={
        
    },
    entry_points={
        "console_scripts": [
            "cli-web-capitoltrades=cli_web.capitoltrades.capitoltrades_cli:main",
        ],
    },
)
