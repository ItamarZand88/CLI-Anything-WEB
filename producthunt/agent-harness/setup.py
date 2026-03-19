from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-producthunt",
    version="2.0.0",
    packages=find_namespace_packages(include=["cli_web.*"]),
    install_requires=["click>=8.0", "curl_cffi", "beautifulsoup4"],
    entry_points={"console_scripts": ["cli-web-producthunt=cli_web.producthunt.producthunt_cli:main"]},
    python_requires=">=3.10",
)
