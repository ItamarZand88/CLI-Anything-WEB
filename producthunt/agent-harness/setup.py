from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-producthunt",
    version="0.1.1",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    description="CLI for Product Hunt — browse launches, leaderboards, and product details",
    install_requires=["click>=8.0", "curl_cffi", "beautifulsoup4", "prompt_toolkit>=3.0"],
    entry_points={
        "console_scripts": ["cli-web-producthunt=cli_web.producthunt.producthunt_cli:main"]
    },
    python_requires=">=3.10",
)
