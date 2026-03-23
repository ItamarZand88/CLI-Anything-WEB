from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-booking",
    version="0.1.0",
    description="Agent-native CLI for Booking.com — hotel search, property details, destination resolution",
    packages=find_namespace_packages(include=["cli_web.*"]),
    package_data={
        "": ["skills/*.md", "*.md"],
    },
    install_requires=[
        "click>=8.0",
        "curl_cffi>=0.5",
        "beautifulsoup4>=4.12",
        "rich>=13.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-booking=cli_web.booking.booking_cli:cli",
        ],
    },
    python_requires=">=3.10",
)
