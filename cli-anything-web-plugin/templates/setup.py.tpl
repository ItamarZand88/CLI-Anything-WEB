from setuptools import find_namespace_packages, setup

setup(
    name="cli-web-${app_name}",
    version="0.1.0",
    description="CLI for ${AppName}",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={"": ["skills/*.md", "*.md"]},
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        ${install_requires}
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
    ${extras_require_block}
    entry_points={
        "console_scripts": [
            "cli-web-${app_name}=cli_web.${app_name_underscore}.${app_name_underscore}_cli:main",
        ],
    },
)
