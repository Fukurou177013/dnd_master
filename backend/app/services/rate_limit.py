from __future__ import annotations

import time
import uuid
from collections import deque
from threading import Lock

_lock = Lock()
_requests: dict[uuid.UUID, deque[float]] = {}
_last_sweep = 0.0


def _sweep_expired(now: float, window_seconds: float) -> None:
    global _last_sweep
    if now - _last_sweep < window_seconds:
        return
    _last_sweep = now
    expired = [
        user_id
        for user_id, timestamps in _requests.items()
        if not timestamps or now - timestamps[-1] >= window_seconds
    ]
    for user_id in expired:
        del _requests[user_id]


def allow_request(
    user_id: uuid.UUID,
    limit: int,
    window_seconds: float = 60.0,
) -> bool:
    if limit <= 0:
        return True
    now = time.monotonic()
    with _lock:
        _sweep_expired(now, window_seconds)
        timestamps = _requests.setdefault(user_id, deque())
        while timestamps and now - timestamps[0] >= window_seconds:
            timestamps.popleft()
        if len(timestamps) >= limit:
            return False
        timestamps.append(now)
        return True


def reset_rate_limits() -> None:
    global _last_sweep
    with _lock:
        _requests.clear()
        _last_sweep = 0.0
