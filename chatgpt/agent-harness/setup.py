"""Setup for cli-web-chatgpt."""

from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-chatgpt",
    version="0.1.0",
    description="CLI for ChatGPT web interface — ask questions, generate images, manage conversations",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={"": ["skills/*.md", "*.md"]},
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "curl_cffi>=0.7",
        "rich>=13.0",
        "camoufox>=0.4",
    ],
    extras_require={
        "auth": ["playwright>=1.40"],
    },
    entry_points={
        "console_scripts": [
            "cli-web-chatgpt=cli_web.chatgpt.chatgpt_cli:main",
        ],
    },
)
