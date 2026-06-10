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
{%- if http_client == "curl_cffi" %}
        "curl_cffi",
{%- else %}
        "httpx",
{%- endif %}
{%- if protocol == "html-scraping" %}
        "beautifulsoup4>=4.12",
{%- endif %}
        "rich>=13.0",
        "prompt_toolkit>=3.0",
    ],
{%- if auth_type in ("cookie", "google_sso") %}
    extras_require={
        "browser": ["playwright>=1.40.0"],
    },
{%- endif %}
    entry_points={
        "console_scripts": [
            "cli-web-${app_name}=cli_web.${app_name_underscore}.${app_name_underscore}_cli:main",
        ],
    },
)
