"""Pytest configuration — register custom markers."""


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Fast unit tests (mocked Playwright, no network)")
    config.addinivalue_line("markers", "live: Live tests that launch a real browser against Google")
    config.addinivalue_line(
        "markers", "subprocess: Subprocess tests that invoke the installed CLI binary"
    )
