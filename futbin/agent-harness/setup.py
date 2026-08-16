from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-futbin",
    version="0.1.2",
    description="Agent-native CLI for FUTBIN — EA FC Ultimate Team database",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    install_requires=[
        "click>=8.0",
        "httpx>=0.24",
        # FUTBIN's Cloudflare edge requires a real browser when it challenges
        # the plain HTTP transport. Keep this aligned with the canary cache.
        "camoufox==0.5.4",
        "beautifulsoup4>=4.12",
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-futbin=cli_web.futbin.futbin_cli:cli",
        ],
    },
    python_requires=">=3.10",
)
