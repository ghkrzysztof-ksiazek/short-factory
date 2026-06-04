import time
from collections import defaultdict
from functools import wraps

from short_factory.config.logging import get_logger

logger = get_logger(__name__)

_call_counts: dict[str, list[float]] = defaultdict(list)


def rate_limit(calls: int, period_sec: float):
    """Simple in-process rate limiter per function name."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = func.__name__
            now = time.time()
            _call_counts[key] = [t for t in _call_counts[key] if now - t < period_sec]
            if len(_call_counts[key]) >= calls:
                sleep_for = period_sec - (now - _call_counts[key][0])
                if sleep_for > 0:
                    logger.warning("rate_limit_hit", function=key, sleep_sec=sleep_for)
                    time.sleep(sleep_for)
            _call_counts[key].append(time.time())
            return func(*args, **kwargs)

        return wrapper

    return decorator
