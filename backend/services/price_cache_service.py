"""Price caching service for real-time market data.

Provides in-memory caching with optional Redis support for distributed caching.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
import json

logger = logging.getLogger(__name__)


@dataclass
class CachedQuote:
    """Cached market quote."""
    symbol: str
    exchange: str
    last_price: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    bid: float
    ask: float
    bid_quantity: int
    ask_quantity: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl: int = 5  # seconds
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age > self.ttl
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "last_price": self.last_price,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "bid": self.bid,
            "ask": self.ask,
            "bid_quantity": self.bid_quantity,
            "ask_quantity": self.ask_quantity,
            "timestamp": self.timestamp.isoformat(),
            "age_seconds": (datetime.now(timezone.utc) - self.timestamp).total_seconds(),
        }


class PriceCache:
    """In-memory price cache with optional Redis backend."""
    
    def __init__(self, use_redis: bool = False, redis_url: Optional[str] = None):
        self._cache: dict[str, CachedQuote] = {}
        self._lock = asyncio.Lock()
        self._use_redis = use_redis
        self._redis_url = redis_url
        self._redis = None
        
        if use_redis:
            self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(
                self._redis_url or "redis://localhost:6379/0",
                decode_responses=True
            )
            logger.info("Redis price cache initialized")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self._use_redis = False
    
    async def set(self, symbol: str, exchange: str, quote_data: dict, ttl: int = 5):
        """Cache a quote."""
        quote = CachedQuote(
            symbol=symbol,
            exchange=exchange,
            last_price=quote_data.get("last_price", 0),
            open=quote_data.get("open", 0),
            high=quote_data.get("high", 0),
            low=quote_data.get("low", 0),
            close=quote_data.get("close", 0),
            volume=quote_data.get("volume", 0),
            bid=quote_data.get("bid", 0),
            ask=quote_data.get("ask", 0),
            bid_quantity=quote_data.get("bid_quantity", 0),
            ask_quantity=quote_data.get("ask_quantity", 0),
            timestamp=datetime.now(timezone.utc),
            ttl=ttl,
        )
        
        cache_key = f"{exchange}:{symbol}"
        
        if self._use_redis and self._redis:
            try:
                await self._redis.setex(
                    f"price:{cache_key}",
                    ttl,
                    json.dumps(quote.to_dict())
                )
                return
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        
        async with self._lock:
            self._cache[cache_key] = quote
    
    async def get(self, symbol: str, exchange: str = "NSE") -> Optional[CachedQuote]:
        """Get cached quote."""
        cache_key = f"{exchange}:{symbol}"
        
        if self._use_redis and self._redis:
            try:
                data = await self._redis.get(f"price:{cache_key}")
                if data:
                    quote_dict = json.loads(data)
                    return CachedQuote(
                        symbol=quote_dict["symbol"],
                        exchange=quote_dict["exchange"],
                        last_price=quote_dict["last_price"],
                        open=quote_dict["open"],
                        high=quote_dict["high"],
                        low=quote_dict["low"],
                        close=quote_dict["close"],
                        volume=quote_dict["volume"],
                        bid=quote_dict["bid"],
                        ask=quote_dict["ask"],
                        bid_quantity=quote_dict["bid_quantity"],
                        ask_quantity=quote_dict["ask_quantity"],
                        timestamp=datetime.fromisoformat(quote_dict["timestamp"]),
                        ttl=quote_dict.get("ttl", 5),
                    )
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        async with self._lock:
            quote = self._cache.get(cache_key)
            if quote and not quote.is_expired():
                return quote
            return None
    
    async def get_bulk(self, symbols: list[str], exchange: str = "NSE") -> dict[str, CachedQuote]:
        """Get multiple cached quotes."""
        result = {}
        for symbol in symbols:
            quote = await self.get(symbol, exchange)
            if quote:
                result[symbol] = quote
        return result
    
    async def invalidate(self, symbol: str, exchange: str = "NSE"):
        """Invalidate cached quote."""
        cache_key = f"{exchange}:{symbol}"
        
        if self._use_redis and self._redis:
            try:
                await self._redis.delete(f"price:{cache_key}")
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
        
        async with self._lock:
            self._cache.pop(cache_key, None)
    
    async def clear_all(self):
        """Clear all cached quotes."""
        if self._use_redis and self._redis:
            try:
                await self._redis.delete(*[
                    f"price:{k}" for k in self._cache.keys()
                ])
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")
        
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self):
        """Remove expired entries."""
        if self._use_redis:
            return  # Redis handles TTL
        
        async with self._lock:
            expired = [
                k for k, v in self._cache.items()
                if v.is_expired()
            ]
            for k in expired:
                del self._cache[k]
            
            return len(expired)
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = len(self._cache)
        expired = sum(1 for q in self._cache.values() if q.is_expired())
        
        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired,
            "redis_enabled": self._use_redis,
        }


class PriceCacheService:
    """Service for managing price caching."""
    
    def __init__(self):
        self._cache = PriceCache()
        self._subscribers: dict[str, list[callable]] = {}
    
    async def update_price(self, symbol: str, exchange: str, quote_data: dict):
        """Update price in cache."""
        await self._cache.set(symbol, exchange, quote_data)
        
        # Notify subscribers
        cache_key = f"{exchange}:{symbol}"
        if cache_key in self._subscribers:
            for callback in self._subscribers[cache_key]:
                try:
                    callback(quote_data)
                except Exception as e:
                    logger.error(f"Subscriber error: {e}")
    
    async def get_price(self, symbol: str, exchange: str = "NSE") -> Optional[dict]:
        """Get cached price."""
        quote = await self._cache.get(symbol, exchange)
        return quote.to_dict() if quote else None
    
    async def get_prices(self, symbols: list[str], exchange: str = "NSE") -> dict:
        """Get multiple prices."""
        quotes = await self._cache.get_bulk(symbols, exchange)
        return {s: q.to_dict() for s, q in quotes.items()}
    
    def subscribe(self, symbol: str, exchange: str, callback: callable):
        """Subscribe to price updates."""
        cache_key = f"{exchange}:{symbol}"
        if cache_key not in self._subscribers:
            self._subscribers[cache_key] = []
        self._subscribers[cache_key].append(callback)
    
    def unsubscribe(self, symbol: str, exchange: str, callback: callable):
        """Unsubscribe from price updates."""
        cache_key = f"{exchange}:{symbol}"
        if cache_key in self._subscribers:
            self._subscribers[cache_key].remove(callback)
    
    async def start_cleanup_task(self, interval: int = 60):
        """Start periodic cleanup task."""
        while True:
            await asyncio.sleep(interval)
            await self._cache.cleanup_expired()
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return self._cache.get_stats()


# Singleton instance
_price_cache_service: Optional[PriceCacheService] = None


def get_price_cache_service() -> PriceCacheService:
    """Get price cache service singleton."""
    global _price_cache_service
    if _price_cache_service is None:
        _price_cache_service = PriceCacheService()
    return _price_cache_service


if __name__ == "__main__":
    import asyncio
    
    async def main():
        service = PriceCacheService()
        
        # Update price
        await service.update_price("RELIANCE", "NSE", {
            "last_price": 2500.50,
            "open": 2480,
            "high": 2510,
            "low": 2475,
            "close": 2490,
            "volume": 5000000,
            "bid": 2500.00,
            "ask": 2501.00,
            "bid_quantity": 100,
            "ask_quantity": 150,
        })
        
        # Get price
        price = await service.get_price("RELIANCE", "NSE")
        print("Price:", price)
        
        # Stats
        print("Stats:", service.get_stats())
    
    asyncio.run(main())
