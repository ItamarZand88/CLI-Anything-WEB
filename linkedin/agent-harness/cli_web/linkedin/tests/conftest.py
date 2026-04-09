"""Pytest configuration — register custom markers."""


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Fast unit tests (mocked HTTP, no network)")
    config.addinivalue_line("markers", "live: Live API tests that hit the real API")
    config.addinivalue_line("markers", "subprocess: Subprocess tests that invoke the installed CLI binary")
    config.addinivalue_line("markers", "e2e: End-to-end tests that hit the live LinkedIn API")
