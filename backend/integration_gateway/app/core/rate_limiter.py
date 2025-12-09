"""Simple in-memory rate limiter for gateway."""

import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimiter:
    """Token-bucket like limiter per key (IP)."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        bucket = self._buckets[key]

        # Drop old requests
        while bucket and bucket[0] < now - self.window:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            return False

        bucket.append(now)
        return True

