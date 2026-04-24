

def poll_until_complete(
    check_fn,
    *,
    timeout: float = 300.0,
    initial_delay: float = 2.0,
    max_delay: float = 10.0,
    backoff_factor: float = 1.5,
):
    """Poll check_fn with exponential backoff until it returns a truthy value.

    Args:
        check_fn: Callable that returns a result (truthy = done) or None/falsy.
        timeout: Maximum total wait time in seconds.
        initial_delay: First sleep interval.
        max_delay: Cap on sleep interval.
        backoff_factor: Multiplier per iteration.

    Returns:
        The truthy result from check_fn.

    Raises:
        ${AppName}Error if timeout is exceeded.
    """
    import time

    from ..core.exceptions import ${AppName}Error

    elapsed = 0.0
    delay = initial_delay
    while elapsed < timeout:
        result = check_fn()
        if result:
            return result
        time.sleep(delay)
        elapsed += delay
        delay = min(delay * backoff_factor, max_delay)
    raise ${AppName}Error(f"Operation timed out after {timeout}s")
