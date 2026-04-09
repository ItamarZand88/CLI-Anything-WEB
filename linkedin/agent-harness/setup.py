from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-linkedin",
    version="0.1.0",
    description="CLI for Linkedin",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={"": ["skills/*.md", "*.md"]},
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "curl_cffi",
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    extras_require={
        "browser": ["playwright>=1.40.0"],
    },
    entry_points={
        "console_scripts": [
            "cli-web-linkedin=cli_web.linkedin.linkedin_cli:main",
        ],
    },
)
