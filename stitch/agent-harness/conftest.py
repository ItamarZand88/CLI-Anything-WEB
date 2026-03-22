"""Pytest configuration for cli-web-stitch tests."""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: E2E live tests (real API calls)")
    config.addinivalue_line("markers", "subprocess: CLI subprocess tests")
