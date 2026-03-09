"""
In-memory per-sender rate limiter.

Prevents bulk-scanning individuals by limiting how many verify requests
a single sender_hash can make in a sliding window.
"""

import os
import time
from collections import defaultdict
from threading import Lock

_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX", "30"))
_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

_buckets: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def is_rate_limited(sender_hash: str) -> bool:
    """Return True if *sender_hash* has exceeded the rate limit."""
    now = time.time()
    cutoff = now - _WINDOW_SECONDS
    with _lock:
        timestamps = _buckets[sender_hash]
        _buckets[sender_hash] = [t for t in timestamps if t > cutoff]
        if len(_buckets[sender_hash]) >= _MAX_REQUESTS:
            return True
        _buckets[sender_hash].append(now)
        return False
