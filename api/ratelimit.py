"""Shared in-process rate limiter (PRD 5.4): a token bucket per (limiter name, client IP) and a global daily cap
per costly endpoint. One worker, so plain dicts are enough; nothing is stored on disk and no IP is logged.

    from api.ratelimit import limit
    @router.post("/api/events", dependencies=[Depends(limit("events", per_minute=60))])

Client IP is `request.client.host`. Behind Caddy that is the real client only because uvicorn runs with
`--proxy-headers --forwarded-allow-ips` (deploy/v2/Dockerfile.api). The `ratelimit` key in the features file can
switch the limiter off without a deploy (features.flag("ratelimit") = false).
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable

from fastapi import HTTPException, Request

from api import features

MAX_BUCKETS = 10_000          # prune idle buckets above this, so a spoofing script cannot grow memory without bound


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class TokenBucket:
    """`per_minute` tokens refilled continuously, burst of `burst` (default = per_minute)."""

    def __init__(self, per_minute: float, burst: float | None = None, clock: Callable[[], float] = time.monotonic):
        self.rate = per_minute / 60.0
        self.burst = float(burst if burst is not None else per_minute)
        self.clock = clock
        self._b: dict[str, tuple[float, float]] = {}       # key -> (tokens, last)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self._lock:
            tokens, last = self._b.get(key, (self.burst, now))
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            ok = tokens >= 1.0
            self._b[key] = (tokens - 1.0 if ok else tokens, now)
            if len(self._b) > MAX_BUCKETS:
                full_after = self.burst / self.rate if self.rate else 0
                self._b = {k: v for k, v in self._b.items() if now - v[1] < full_after}
            return ok

    def retry_after(self, key: str) -> int:
        with self._lock:
            tokens, _ = self._b.get(key, (self.burst, 0.0))
        return max(1, int((1.0 - tokens) / self.rate) + 1) if self.rate else 60


class DailyCap:
    """A global counter that resets at UTC midnight. `take()` is False once `cap` calls have been made today."""

    def __init__(self, cap: int, today: Callable[[], str] = lambda: time.strftime("%Y-%m-%d", time.gmtime())):
        self.cap, self.today = cap, today
        self._day, self._n = today(), 0
        self._lock = threading.Lock()

    def take(self) -> bool:
        with self._lock:
            d = self.today()
            if d != self._day:
                self._day, self._n = d, 0
            if self._n >= self.cap:
                return False
            self._n += 1
            return True

    def used(self) -> int:
        with self._lock:
            return self._n if self.today() == self._day else 0


_buckets: dict[str, TokenBucket] = {}


def bucket(name: str, per_minute: float, burst: float | None = None) -> TokenBucket:
    b = _buckets.get(name)
    if b is None:
        b = _buckets[name] = TokenBucket(per_minute, burst)
    return b


def reset() -> None:
    """Forget every named bucket (tests)."""
    _buckets.clear()


def limit(name: str, per_minute: float, burst: float | None = None):
    """FastAPI dependency: 429 {"detail": "rate_limited"} (with Retry-After) when this client IP is over its rate."""
    def dep(request: Request) -> None:
        if not features.flag("ratelimit"):
            return
        b = bucket(name, per_minute, burst)
        ip = client_ip(request)
        if not b.allow(ip):
            raise HTTPException(429, "rate_limited", headers={"Retry-After": str(b.retry_after(ip))})
    return dep
