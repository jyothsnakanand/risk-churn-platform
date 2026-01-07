"""Rate limiting middleware for API requests."""

import time
from collections import defaultdict
from typing import Callable, Tuple

import structlog
from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: int = 1000, per: int = 3600) -> None:
        """Initialize rate limiter.

        Args:
            rate: Number of requests allowed
            per: Time period in seconds (default: 3600 = 1 hour)
        """
        self.rate = rate
        self.per = per
        self.allowance_per_second = rate / per

        # Store: {client_id: (tokens, last_check_time)}
        self.clients: dict[str, Tuple[float, float]] = defaultdict(
            lambda: (float(rate), time.time())
        )

    def is_allowed(self, client_id: str) -> Tuple[bool, dict[str, int]]:
        """Check if request is allowed for client.

        Args:
            client_id: Unique client identifier (API key hash or IP)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        tokens, last_check = self.clients[client_id]

        # Add tokens based on time passed
        time_passed = current_time - last_check
        tokens = min(self.rate, tokens + time_passed * self.allowance_per_second)

        # Check if we have tokens available
        allowed = tokens >= 1.0

        if allowed:
            tokens -= 1.0

        # Update state
        self.clients[client_id] = (tokens, current_time)

        # Calculate rate limit headers
        rate_limit_info = {
            "limit": self.rate,
            "remaining": int(tokens),
            "reset": int(last_check + self.per),
        }

        return allowed, rate_limit_info

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a client.

        Args:
            client_id: Client identifier to reset
        """
        if client_id in self.clients:
            del self.clients[client_id]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, rate: int = 1000, per: int = 3600) -> None:
        """Initialize rate limit middleware.

        Args:
            app: FastAPI application
            rate: Requests allowed per period
            per: Time period in seconds
        """
        super().__init__(app)
        self.limiter = RateLimiter(rate=rate, per=per)

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint

        Returns:
            Response with rate limit headers

        Raises:
            HTTPException: If rate limit exceeded
        """
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        # Get client identifier (API key hash or IP address)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            import hashlib
            client_id = hashlib.sha256(api_key.encode()).hexdigest()
        else:
            # Fall back to IP address
            client_id = request.client.host if request.client else "unknown"

        # Check rate limit
        allowed, rate_limit_info = self.limiter.is_allowed(client_id)

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                client_id=client_id[:8],  # Log only first 8 chars for privacy
                path=request.url.path,
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": rate_limit_info["limit"],
                    "reset_at": rate_limit_info["reset"],
                    "message": f"Too many requests. Limit: {rate_limit_info['limit']} requests per hour.",
                },
                headers={
                    "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_limit_info["reset"]),
                    "Retry-After": str(rate_limit_info["reset"] - int(time.time())),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset"])

        return response


class AdaptiveRateLimiter:
    """Rate limiter that adapts based on API key tier."""

    def __init__(self) -> None:
        """Initialize adaptive rate limiter."""
        # Different rate limiters for different tiers
        self.limiters: dict[str, RateLimiter] = {
            "free": RateLimiter(rate=100, per=3600),      # 100/hour
            "basic": RateLimiter(rate=1000, per=3600),    # 1000/hour
            "premium": RateLimiter(rate=10000, per=3600), # 10000/hour
            "enterprise": RateLimiter(rate=100000, per=3600),  # 100k/hour
        }

    def is_allowed(
        self, client_id: str, tier: str = "basic"
    ) -> Tuple[bool, dict[str, int]]:
        """Check if request is allowed for client based on tier.

        Args:
            client_id: Client identifier
            tier: Rate limit tier (free, basic, premium, enterprise)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        limiter = self.limiters.get(tier, self.limiters["basic"])
        return limiter.is_allowed(client_id)


# Global rate limiter instance
_global_limiter: RateLimiter = RateLimiter(rate=1000, per=3600)


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance.

    Returns:
        Global rate limiter
    """
    return _global_limiter
