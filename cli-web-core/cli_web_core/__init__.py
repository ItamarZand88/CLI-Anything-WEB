"""Shared runtime for cli-web-* CLIs.

Canonical home of the framework code every generated CLI relies on:

- :mod:`cli_web_core.exceptions` — typed exception hierarchy + HTTP mapping
- :mod:`cli_web_core.output` — the ``--json`` success/error envelope
- :mod:`cli_web_core.polling` — exponential-backoff polling
- :mod:`cli_web_core.repl_skin` — unified REPL UI (vendored into CLIs)
- :mod:`cli_web_core.testing` — subprocess test fixtures + contract checks

Distribution model: until the fleet migrates to an import-based dependency,
``repl_skin.py`` is vendored into each CLI by ``cli-web-devkit resync`` with
provenance recorded in each CLI's ``.manifest.json``. This package is the
single source of truth either way.
"""

from .exceptions import (
    EXIT_AUTH,
    EXIT_NETWORK,
    EXIT_NOT_FOUND,
    EXIT_OK,
    EXIT_RATE_LIMIT,
    EXIT_SERVER,
    EXIT_UNKNOWN,
    EXIT_USAGE,
    AppError,
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    RPCError,
    ServerError,
    ValidationError,
    error_code_for,
    exit_code_for,
)
from .output import json_error, json_lines, json_success
from .polling import poll_until_complete

__version__ = "1.0.0"

__all__ = [
    "AppError",
    "AuthError",
    "NetworkError",
    "NotFoundError",
    "RPCError",
    "RateLimitError",
    "ServerError",
    "ValidationError",
    "EXIT_AUTH",
    "EXIT_NETWORK",
    "EXIT_NOT_FOUND",
    "EXIT_OK",
    "EXIT_RATE_LIMIT",
    "EXIT_SERVER",
    "EXIT_UNKNOWN",
    "EXIT_USAGE",
    "error_code_for",
    "exit_code_for",
    "json_error",
    "json_lines",
    "json_success",
    "poll_until_complete",
    "__version__",
]
