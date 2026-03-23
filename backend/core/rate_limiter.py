"""Rate limiting middleware and dependencies."""
import hashlib
import time
from typing import Optional

from fastapi import HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse

from core.config import get_settings
from database.session import get_redis_client

settings = get_settings()


class RateLimitConfig:
    """Rate limit configuration for different endpoint types."""
    
    DEFAULT = {"limit": 60, "window": 60}  # 60 requests per minute
    AUTH = {"limit": 10, "window": 60}     # 10 requests per minute for auth endpoints
    STRATEGY = {"limit": 30, "window": 60} # 30 requests per minute for strategy endpoints
    TRADING = {"limit": 100, "window": 60} # 100 requests per minute for trading
    ANALYTICS = {"limit": 20, "window": 60} # 20 requests per minute for analytics


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_rate_limit_key(prefix: str, identifier: str) -> str:
    """Generate rate limit key."""
    return f"rate_limit:{prefix}:{identifier}"


async def check_rate_limit(
    prefix: str,
    identifier: str,
    limit: int,
    window: int,
) -> tuple[bool, int]:
    """
    Check rate limit for given prefix and identifier.
    Returns (is_allowed, remaining_requests)
    """
    redis_client = get_redis_client()
    if not redis_client:
        return True, limit
    
    key = get_rate_limit_key(prefix, identifier)
    
    try:
        current = redis_client.get(key)
        if current is None:
            redis_client.setex(key, window, 1)
            return True, limit - 1
        
        current = int(current)
        if current >= limit:
            ttl = redis_client.ttl(key)
            return False, 0
        
        redis_client.incr(key)
        return True, limit - current - 1
    except Exception:
        return True, limit


async def verify_rate_limit(
    request: Request,
    prefix: str,
    limit: int = 60,
    window: int = 60,
) -> None:
    """Verify rate limit and raise exception if exceeded."""
    ip = get_client_ip(request)
    user_id = getattr(request.state, "user_id", None)
    
    identifier = user_id if user_id else ip
    is_allowed, remaining = await check_rate_limit(prefix, identifier, limit, window)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again later.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + window),
            },
        )


def rate_limit_dependency(prefix: str, limit: int = 60, window: int = 60):
    """Dependency for rate limiting specific endpoints."""
    async def _rate_limit(request: Request = None):
        if request:
            await verify_rate_limit(request, prefix, limit, window)
    return _rate_limit


def get_endpoint_category(path: str) -> tuple[str, dict]:
    """Determine rate limit config based on endpoint path."""
    if "/auth/" in path or "/oauth/" in path or "/mfa/" in path:
        return "auth", RateLimitConfig.AUTH
    if "/strategies" in path:
        return "strategy", RateLimitConfig.STRATEGY
    if "/orders" in path or "/positions" in path or "/trades" in path:
        return "trading", RateLimitConfig.TRADING
    if "/analytics" in path or "/backtest" in path:
        return "analytics", RateLimitConfig.ANALYTICS
    return "default", RateLimitConfig.DEFAULT


class RateLimitMiddleware:
    """Middleware for automatic rate limiting based on endpoint."""
    
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        path = scope.get("path", "")
        
        if path.startswith("/api/") and path not in ["/api/v1/oauth/google/status"]:
            prefix, config = get_endpoint_category(path)
            
            client_ip = "unknown"
            for header in scope.get("headers", []):
                if header[0].decode() == "x-forwarded-for":
                    client_ip = header[1].decode().split(",")[0]
                    break
                elif header[0].decode() == "host":
                    client_ip = header[1].decode()
            
            redis_client = get_redis_client()
            if redis_client:
                key = f"rate_limit:{prefix}:{client_ip}"
                try:
                    current = redis_client.get(key)
                    limit = config["limit"]
                    window = config["window"]
                    
                    if current is None:
                        redis_client.setex(key, window, 1)
                    else:
                        current = int(current)
                        if current >= limit:
                            response = JSONResponse(
                                status_code=429,
                                content={"detail": "Rate limit exceeded"},
                                headers={
                                    "X-RateLimit-Limit": str(limit),
                                    "X-RateLimit-Remaining": "0",
                                },
                            )
                            await response(scope, receive, send)
                            return
                        redis_client.incr(key)
                except Exception:
                    pass
        
        await self.app(scope, receive, send)