"""Simple tests for rate limiter."""

import time

from risk_churn_platform.middleware.rate_limiter import (
    AdaptiveRateLimiter,
    RateLimiter,
)


def test_rate_limiter_allows_request() -> None:
    """Test that rate limiter allows requests."""
    limiter = RateLimiter(rate=100, per=3600)

    allowed, info = limiter.is_allowed("client-1")
    assert allowed is True
    assert info["limit"] == 100
    assert info["remaining"] <= 100


def test_rate_limiter_tracks_usage() -> None:
    """Test rate limiter tracks usage."""
    limiter = RateLimiter(rate=10, per=3600)

    # First request
    allowed1, info1 = limiter.is_allowed("client-2")
    # Second request
    allowed2, info2 = limiter.is_allowed("client-2")

    # Both should be allowed
    assert allowed1 is True
    assert allowed2 is True

    # Remaining should decrease or stay same (due to rounding)
    assert info2["remaining"] <= info1["remaining"]


def test_rate_limiter_limit_exhaustion() -> None:
    """Test rate limiter blocks when exhausted."""
    limiter = RateLimiter(rate=2, per=3600)

    # Use up the limit
    limiter.is_allowed("client-3")
    limiter.is_allowed("client-3")

    # Next should be blocked
    allowed, info = limiter.is_allowed("client-3")
    assert allowed is False
    assert info["remaining"] == 0


def test_rate_limiter_separate_clients() -> None:
    """Test clients have separate limits."""
    limiter = RateLimiter(rate=100, per=3600)

    # Different clients
    allowed1, _ = limiter.is_allowed("client-a")
    allowed2, _ = limiter.is_allowed("client-b")

    # Both allowed
    assert allowed1 is True
    assert allowed2 is True


def test_adaptive_rate_limiter_tiers() -> None:
    """Test adaptive rate limiter with different tiers."""
    limiter = AdaptiveRateLimiter()

    # Test different tiers
    _, free_info = limiter.is_allowed("user-1", tier="free")
    assert free_info["limit"] == 100

    _, basic_info = limiter.is_allowed("user-2", tier="basic")
    assert basic_info["limit"] == 1000

    _, premium_info = limiter.is_allowed("user-3", tier="premium")
    assert premium_info["limit"] == 10000

    _, enterprise_info = limiter.is_allowed("user-4", tier="enterprise")
    assert enterprise_info["limit"] == 100000


def test_adaptive_rate_limiter_default_tier() -> None:
    """Test default tier for adaptive limiter."""
    limiter = AdaptiveRateLimiter()

    # No tier specified (defaults to "basic")
    _, info = limiter.is_allowed("default-user")
    assert info["limit"] == 1000  # basic tier is default


def test_rate_limiter_reset_time() -> None:
    """Test reset time is set correctly."""
    limiter = RateLimiter(rate=100, per=3600)

    _, info = limiter.is_allowed("client-reset")

    # Reset should be in future
    current_time = int(time.time())
    assert info["reset"] > current_time
    assert info["reset"] <= current_time + 3600
