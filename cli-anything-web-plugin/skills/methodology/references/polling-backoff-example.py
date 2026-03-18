"""
Reference: Exponential Backoff Polling & Rate-Limit Retry
==========================================================
Two patterns every content-generation CLI needs:

1. poll_until_complete() — for async operations (audio gen, file processing)
2. retry_on_rate_limit() — for 429 responses with backoff

Never use fixed time.sleep(). Always use exponential backoff with configurable
timeouts and intervals.
"""
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def poll_until_complete(
    check_fn: Callable[[], dict | None],
    initial_interval: float = 2.0,
    max_interval: float = 10.0,
    timeout: float = 300.0,
    backoff_factor: float = 1.5,
) -> dict:
    """Poll an operation until it completes or times out.

    Args:
        check_fn: Returns status dict when done, None when still in progress.
                  Should return dict with 'status' field ('completed'/'failed').
        initial_interval: First sleep duration in seconds.
        max_interval: Maximum sleep between polls.
        timeout: Total time before giving up.
        backoff_factor: Multiply interval by this each iteration.

    Returns:
        The completed status dict.

    Raises:
        TimeoutError: If operation doesn't complete within timeout.

    Example:
        def check():
            artifacts = client.artifacts.list(nb_id)
            match = [a for a in artifacts if a['task_id'] == task_id]
            if match and match[0]['status'] in ('completed', 'failed'):
                return match[0]
            return None

        result = poll_until_complete(check, timeout=600)
    """
    start = time.perf_counter()
    interval = initial_interval

    while True:
        result = check_fn()
        if result is not None:
            return result

        elapsed = time.perf_counter() - start
        if elapsed + interval > timeout:
            raise TimeoutError(
                f"Operation timed out after {elapsed:.0f}s "
                f"(limit: {timeout:.0f}s)"
            )

        time.sleep(min(interval, max_interval))
        interval *= backoff_factor


def retry_on_rate_limit(
    fn: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 60.0,
    max_delay: float = 300.0,
    backoff_factor: float = 2.0,
) -> T:
    """Retry a function on RateLimitError with exponential backoff.

    Args:
        fn: The function to call. Should raise RateLimitError on 429.
        max_retries: Maximum number of retry attempts.
        initial_delay: Base delay in seconds (first retry).
        max_delay: Maximum delay cap.
        backoff_factor: Multiply delay by this each retry.

    Returns:
        The function's return value on success.

    Raises:
        RateLimitError: If all retries are exhausted.

    Example:
        result = retry_on_rate_limit(
            lambda: client.artifacts.generate(nb_id, "audio"),
            max_retries=3,
        )
    """
    # Import from the generated exceptions module
    # from .exceptions import RateLimitError

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            # Check if it's a RateLimitError (duck-type for portability)
            if not hasattr(e, 'retry_after') and 'rate limit' not in str(e).lower():
                raise  # Not a rate limit error — don't retry

            last_error = e
            if attempt == max_retries:
                raise

            # Use server's retry_after if available, otherwise backoff
            delay = getattr(e, 'retry_after', None)
            if delay is None:
                delay = min(initial_delay * (backoff_factor ** attempt), max_delay)

            time.sleep(delay)

    raise last_error  # Should never reach here


def calculate_backoff_delay(
    attempt: int,
    initial_delay: float = 60.0,
    max_delay: float = 300.0,
    multiplier: float = 2.0,
) -> float:
    """Calculate exponential backoff delay.

    delay = min(initial * (multiplier ^ attempt), max_delay)
    """
    return min(initial_delay * (multiplier ** attempt), max_delay)
