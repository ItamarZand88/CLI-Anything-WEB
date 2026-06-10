"""Exponential-backoff polling (HARNESS.md: never fixed ``time.sleep`` loops)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from .exceptions import AppError

T = TypeVar("T")


def poll_until_complete(
    check_fn: Callable[[], T | None],
    *,
    timeout: float = 300.0,
    initial_delay: float = 2.0,
    max_delay: float = 10.0,
    backoff_factor: float = 1.5,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Poll ``check_fn`` with exponential backoff until it returns non-None.

    Args:
        check_fn: Returns the result when done (any value, including falsy
            ones like 0 or []) or None to keep waiting.
        timeout: Maximum total wait in seconds.
        initial_delay: First sleep interval.
        max_delay: Cap on the sleep interval.
        backoff_factor: Interval multiplier per iteration.
        sleep: Injectable sleep function (for tests).

    Raises:
        AppError: if the timeout is exceeded.
    """
    elapsed = 0.0
    delay = initial_delay
    while elapsed < timeout:
        result = check_fn()
        if result is not None:
            return result
        sleep(delay)
        elapsed += delay
        delay = min(delay * backoff_factor, max_delay)
    raise AppError(f"Operation timed out after {timeout}s")
