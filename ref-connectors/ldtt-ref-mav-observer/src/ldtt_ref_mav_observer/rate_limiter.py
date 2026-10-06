"""C6 rate limiter — token bucket for Observe reads_per_s (Phase 2 draft).

Creator lock #2 (Phase 2): GCS HEARTBEAT TX is a keepalive, not a read, and is
EXEMPT from the reads_per_s bucket. It still must pass the TX allowlist.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


# TX message names that never consume reads_per_s tokens (creator lock #2).
EXEMPT_TX: frozenset[str] = frozenset({"HEARTBEAT"})


def is_exempt(msg_name: str) -> bool:
    """True if msg_name is a keepalive exempt from reads_per_s (HEARTBEAT only)."""
    return msg_name in EXEMPT_TX


class RateLimitExceeded(RuntimeError):
    """Raised when a request would exceed reads_per_s."""


@dataclass
class RateLimiter:
    """Token bucket. capacity and refill_rate both equal reads_per_s."""

    reads_per_s: float
    _tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        if self.reads_per_s < 0:
            raise ValueError("reads_per_s must be >= 0")
        self._tokens = float(self.reads_per_s)
        self._last = time.monotonic()

    def _refill(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        elapsed = max(0.0, now - self._last)
        self._last = now
        if self.reads_per_s == 0:
            self._tokens = 0.0
            return
        self._tokens = min(self.reads_per_s, self._tokens + elapsed * self.reads_per_s)

    def allow(self, cost: float = 1.0, now: float | None = None) -> bool:
        self._refill(now)
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def check(self, cost: float = 1.0, now: float | None = None, msg_name: str | None = None) -> None:
        if msg_name is not None and is_exempt(msg_name):
            return  # keepalive: no token consumed (creator lock #2)
        if not self.allow(cost, now=now):
            raise RateLimitExceeded(
                f"rate limit exceeded: reads_per_s={self.reads_per_s}"
            )
