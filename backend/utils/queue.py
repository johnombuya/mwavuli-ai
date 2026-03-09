"""
Optional queue-based processing for surge capacity.

When Redis is available and ``QUEUE_ENABLED=true``, incoming verify
requests are enqueued and processed asynchronously.  When Redis is
unavailable, processing falls back to synchronous (current behaviour).
"""

import os
import json
from typing import Optional

_QUEUE_ENABLED = os.getenv("QUEUE_ENABLED", "false").lower() == "true"
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis = None


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    if not _QUEUE_ENABLED:
        return None
    try:
        import redis
        _redis = redis.from_url(_REDIS_URL, decode_responses=True)
        _redis.ping()
        return _redis
    except Exception as e:
        print(f"[queue] Redis unavailable — sync fallback: {e}")
        return None


def enqueue_verify(payload: dict) -> Optional[str]:
    """Push a verify task onto the Redis queue. Returns a task-id or None."""
    r = _get_redis()
    if r is None:
        return None
    import uuid
    task_id = str(uuid.uuid4())
    r.lpush("mwavuli:verify", json.dumps({"id": task_id, **payload}))
    return task_id


def dequeue_verify() -> Optional[dict]:
    """Pop a verify task from the Redis queue (blocking, 5 s timeout)."""
    r = _get_redis()
    if r is None:
        return None
    result = r.brpop("mwavuli:verify", timeout=5)
    if result is None:
        return None
    return json.loads(result[1])


def store_result(task_id: str, result: dict, ttl: int = 300):
    """Store a processing result, keyed by task_id, with TTL."""
    r = _get_redis()
    if r is None:
        return
    r.setex(f"mwavuli:result:{task_id}", ttl, json.dumps(result))


def get_result(task_id: str) -> Optional[dict]:
    """Retrieve a stored result by task_id."""
    r = _get_redis()
    if r is None:
        return None
    raw = r.get(f"mwavuli:result:{task_id}")
    return json.loads(raw) if raw else None
