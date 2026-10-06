"""Unit tests: C6 rate limits (Phase 2)."""

import pytest

from ldtt_ref_mav_observer.rate_limiter import RateLimitExceeded, RateLimiter


def test_allows_within_budget():
    rl = RateLimiter(reads_per_s=5)
    t0 = 1000.0
    rl._last = t0
    rl._tokens = 5.0
    for _ in range(5):
        assert rl.allow(now=t0)
    assert not rl.allow(now=t0)


def test_refill():
    rl = RateLimiter(reads_per_s=10)
    t0 = 100.0
    rl._last = t0
    rl._tokens = 0.0
    assert not rl.allow(now=t0)
    assert rl.allow(now=t0 + 0.2)  # ~2 tokens refilled; cost 1


def test_check_raises():
    rl = RateLimiter(reads_per_s=1)
    rl._tokens = 0.0
    rl._last = 50.0
    with pytest.raises(RateLimitExceeded):
        rl.check(now=50.0)


def test_zero_rate_blocks():
    rl = RateLimiter(reads_per_s=0)
    assert not rl.allow()
