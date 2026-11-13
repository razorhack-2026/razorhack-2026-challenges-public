"""Token-bucket rate limiting keyed by session or client IP."""
import time


class RateLimiter:
    def __init__(self, per_minute: int, burst: int | None = None):
        self.rate = per_minute / 60.0
        self.burst = float(burst or per_minute)
        self._b: dict[str, tuple[float, float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        tokens, last = self._b.get(key, (self.burst, now))
        tokens = min(self.burst, tokens + (now - last) * self.rate)
        if len(self._b) > 50000:  # crude bound on memory
            self._b.clear()
        if tokens < 1:
            self._b[key] = (tokens, now)
            return False
        self._b[key] = (tokens - 1, now)
        return True
