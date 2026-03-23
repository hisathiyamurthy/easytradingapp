"""Market Data Provider Service.

Provides real-time and historical market data from multiple sources.
Supports Indian exchanges (NSE, BSE) with fallback providers.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class DataProvider(str, Enum):
    NSE_PYTHON = "nsepython"
    YFINANCE = "yfinance"
    ALPHA_VANTAGE = "alpha_vantage"
    MOCK = "mock"


@dataclass
class OHLCV:
    """OHLCV bar data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class TickData:
    """Real-time tick data."""
    symbol: str
    last_price: float
    bid: float
    ask: float
    bid_quantity: int
    ask_quantity: int
    volume: int
    timestamp: datetime


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""
    
    @abstractmethod
    async def get_quote(self, symbol: str, exchange: str = "NSE") -> dict:
        """Get current quote for a symbol."""
        pass
    
    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[OHLCV]:
        """Get OHLCV data."""
        pass
    
    @abstractmethod
    async def get_index_quote(self, index: str) -> dict:
        """Get index quote (NIFTY, SENSEX, etc.)."""
        pass
    
    @abstractmethod
    async def search_symbol(self, query: str) -> list[dict]:
        """Search for symbols."""
        pass


class NSEPythonDataProvider(MarketDataProvider):
    """Market data provider using nsepython library."""
    
    def __init__(self):
        self._cache: dict = {}
        self._cache_ttl = 5  # seconds
    
    async def get_quote(self, symbol: str, exchange: str = "NSE") -> dict:
        """Get current quote from NSE."""
        try:
            import nsepython
            quote = nsepython.nse_quote(symbol, quote=True)
            
            return {
                "symbol": symbol,
                "exchange": exchange,
                "last_price": float(quote.get("lastPrice", 0)),
                "open": float(quote.get("open", 0)),
                "high": float(quote.get("dayHigh", 0)),
                "low": float(quote.get("dayLow", 0)),
                "close": float(quote.get("prevClose", 0)),
                "volume": int(quote.get("totalTradedVolume", 0)),
                "bid": float(quote.get("buyPrice1", 0)),
                "ask": float(quote.get("sellPrice1", 0)),
                "bid_quantity": int(quote.get("buyQuantity1", 0)),
                "ask_quantity": int(quote.get("sellQuantity1", 0)),
                "timestamp": datetime.now(timezone.utc),
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return {}
    
    async def get_ohlcv(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[OHLCV]:
        """Get historical OHLCV data."""
        try:
            import nsepython
            from_date_str = from_date.strftime("%Y-%m-%d") if from_date else None
            to_date_str = to_date.strftime("%Y-%m-%d") if to_date else None
            
            # Map interval to nsepython format
            interval_map = {
                "1m": "1minute",
                "5m": "5minute",
                "15m": "15minute",
                "60m": "60minute",
                "1d": "1day",
            }
            nse_interval = interval_map.get(interval, "1day")
            
            data = nsepython.nse_quote_historical(
                symbol,
                from_date=from_date_str,
                to_date=to_date_str,
                series="EQ",
                consent={"oi": "yes"}
            )
            
            ohlcv_data = []
            for row in data.get("data", []):
                ohlcv_data.append(OHLCV(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row.get("volume", 0)),
                ))
            
            return ohlcv_data
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return []
    
    async def get_index_quote(self, index: str) -> dict:
        """Get index quote."""
        try:
            import nsepython
            index_map = {"NIFTY": "NIFTY 50", "SENSEX": "BSE SENSEX"}
            nse_index = index_map.get(index, index)
            
            quote = nsepython.nse_index_quote(nse_index)
            
            return {
                "symbol": index,
                "last_price": float(quote.get("lastPrice", 0)),
                "open": float(quote.get("open", 0)),
                "high": float(quote.get("dayHigh", 0)),
                "low": float(quote.get("dayLow", 0)),
                "previous_close": float(quote.get("previousClose", 0)),
                "change": float(quote.get("change", 0)),
                "pct_change": float(quote.get("pctChange", 0)),
                "timestamp": datetime.now(timezone.utc),
            }
        except Exception as e:
            logger.error(f"Error fetching index {index}: {e}")
            return {}
    
    async def search_symbol(self, query: str) -> list[dict]:
        """Search for symbols."""
        try:
            import nsepython
            results = nsepython.search_symbol(query)
            
            return [
                {"symbol": r.get("symbol"), "name": r.get("name"), "exchange": "NSE"}
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error searching for {query}: {e}")
            return []


class YFinanceDataProvider(MarketDataProvider):
    """Market data provider using yfinance library."""
    
    def __init__(self):
        self._cache: dict = {}
        self._cache_ttl = 5
    
    async def get_quote(self, symbol: str, exchange: str = "NSE") -> dict:
        """Get current quote from yfinance."""
        try:
            import yfinance as yf
            
            ticker_symbol = f"{symbol}.NS" if exchange == "NSE" else f"{symbol}.BO"
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            return {
                "symbol": symbol,
                "exchange": exchange,
                "last_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "open": info.get("open", 0),
                "high": info.get("dayHigh", 0),
                "low": info.get("dayLow", 0),
                "close": info.get("previousClose", info.get("regularMarketPreviousClose", 0)),
                "volume": info.get("volume", 0),
                "bid": info.get("bid", 0),
                "ask": info.get("ask", 0),
                "bid_quantity": info.get("bidSize", 0),
                "ask_quantity": info.get("askSize", 0),
                "timestamp": datetime.now(timezone.utc),
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return {}
    
    async def get_ohlcv(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[OHLCV]:
        """Get historical OHLCV data from yfinance."""
        try:
            import yfinance as yf
            
            ticker_symbol = f"{symbol}.NS" if exchange == "NSE" else f"{symbol}.BO"
            ticker = yf.Ticker(ticker_symbol)
            
            # Map interval
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "60m": "1h",
                "1d": "1d",
            }
            yf_interval = interval_map.get(interval, "1d")
            
            hist = ticker.history(
                period="max" if not from_date else None,
                start=from_date.strftime("%Y-%m-%d") if from_date else None,
                end=to_date.strftime("%Y-%m-%d") if to_date else None,
                interval=yf_interval,
            )
            
            ohlcv_data = []
            for idx, row in hist.iterrows():
                ohlcv_data.append(OHLCV(
                    timestamp=idx.to_pydatetime(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                ))
            
            return ohlcv_data
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return []
    
    async def get_index_quote(self, index: str) -> dict:
        """Get index quote."""
        index_map = {
            "NIFTY": "^NSEI",
            "SENSEX": "^BSESN",
            "BANK_NIFTY": "^NSEBANK",
            "FIN_NIFTY": "^NSFIN",
        }
        ticker_symbol = index_map.get(index, index)
        
        try:
            import yfinance as yf
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            return {
                "symbol": index,
                "last_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "open": info.get("open", 0),
                "high": info.get("dayHigh", 0),
                "low": info.get("dayLow", 0),
                "previous_close": info.get("previousClose", 0),
                "change": info.get("regularMarketChange", 0),
                "pct_change": info.get("regularMarketChangePercent", 0),
                "timestamp": datetime.now(timezone.utc),
            }
        except Exception as e:
            logger.error(f"Error fetching index {index}: {e}")
            return {}
    
    async def search_symbol(self, query: str) -> list[dict]:
        """Search for symbols (yfinance doesn't support search, return empty)."""
        return []


class MockDataProvider(MarketDataProvider):
    """Mock data provider for testing."""
    
    async def get_quote(self, symbol: str, exchange: str = "NSE") -> dict:
        """Return mock quote."""
        import random
        base_price = 1000 + random.random() * 1000
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "last_price": round(base_price, 2),
            "open": round(base_price * 0.98, 2),
            "high": round(base_price * 1.02, 2),
            "low": round(base_price * 0.97, 2),
            "close": round(base_price * 0.99, 2),
            "volume": random.randint(100000, 5000000),
            "bid": round(base_price - 1, 2),
            "ask": round(base_price + 1, 2),
            "bid_quantity": random.randint(100, 1000),
            "ask_quantity": random.randint(100, 1000),
            "timestamp": datetime.now(timezone.utc),
        }
    
    async def get_ohlcv(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[OHLCV]:
        """Return mock OHLCV data."""
        import random
        from datetime import timedelta
        
        from_date = from_date or datetime.now(timezone.utc) - timedelta(days=30)
        to_date = to_date or datetime.now(timezone.utc)
        
        ohlcv_data = []
        price = 1000
        current = from_date
        
        while current <= to_date:
            if current.weekday() < 5:  # Skip weekends
                change = random.uniform(-0.03, 0.03)
                open_price = price
                close_price = price * (1 + change)
                high_price = max(open_price, close_price) * random.uniform(1.0, 1.02)
                low_price = min(open_price, close_price) * random.uniform(0.98, 1.0)
                
                ohlcv_data.append(OHLCV(
                    timestamp=current,
                    open=round(open_price, 2),
                    high=round(high_price, 2),
                    low=round(low_price, 2),
                    close=round(close_price, 2),
                    volume=random.randint(100000, 5000000),
                ))
                price = close_price
            
            # Increment based on interval
            interval_map = {
                "1m": timedelta(minutes=1),
                "5m": timedelta(minutes=5),
                "15m": timedelta(minutes=15),
                "60m": timedelta(hours=1),
                "1d": timedelta(days=1),
            }
            current += interval_map.get(interval, timedelta(days=1))
        
        return ohlcv_data
    
    async def get_index_quote(self, index: str) -> dict:
        """Return mock index quote."""
        import random
        base = {"NIFTY": 22000, "SENSEX": 73000, "BANK_NIFTY": 48000}
        price = base.get(index, 10000)
        
        return {
            "symbol": index,
            "last_price": price + random.uniform(-100, 100),
            "open": price - 50,
            "high": price + 100,
            "low": price - 80,
            "previous_close": price,
            "change": random.uniform(-50, 50),
            "pct_change": random.uniform(-0.5, 0.5),
            "timestamp": datetime.now(timezone.utc),
        }
    
    async def search_symbol(self, query: str) -> list[dict]:
        """Return mock search results."""
        return [
            {"symbol": f"{query}", "name": f"{query} Ltd", "exchange": "NSE"},
            {"symbol": f"{query}1", "name": f"{query} India", "exchange": "NSE"},
        ]


class MarketDataService:
    """Service for managing market data providers."""
    
    def __init__(self, provider: DataProvider = DataProvider.YFINANCE):
        self.provider = provider
        self._provider_instance: Optional[MarketDataProvider] = None
        self._fallback_provider: Optional[MarketDataProvider] = None
    
    def _get_provider(self) -> MarketDataProvider:
        """Get current provider instance."""
        if not self._provider_instance:
            if self.provider == DataProvider.NSE_PYTHON:
                self._provider_instance = NSEPythonDataProvider()
            elif self.provider == DataProvider.YFINANCE:
                self._provider_instance = YFinanceDataProvider()
            else:
                self._provider_instance = MockDataProvider()
        
        return self._provider_instance
    
    def _get_fallback(self) -> MarketDataProvider:
        """Get fallback provider."""
        if not self._fallback_provider:
            self._fallback_provider = MockDataProvider()
        return self._fallback_provider
    
    async def get_quote(self, symbol: str, exchange: str = "NSE") -> dict:
        """Get quote with fallback support."""
        try:
            provider = self._get_provider()
            return await provider.get_quote(symbol, exchange)
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}, using fallback")
            try:
                return await self._get_fallback().get_quote(symbol, exchange)
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                return {}
    
    async def get_ohlcv(
        self,
        symbol: str,
        exchange: str = "NSE",
        interval: str = "1d",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[OHLCV]:
        """Get OHLCV with fallback."""
        try:
            provider = self._get_provider()
            return await provider.get_ohlcv(symbol, exchange, interval, from_date, to_date)
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}, using fallback")
            try:
                return await self._get_fallback().get_ohlcv(symbol, exchange, interval, from_date, to_date)
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                return []
    
    async def get_index_quote(self, index: str) -> dict:
        """Get index quote with fallback."""
        try:
            provider = self._get_provider()
            return await provider.get_index_quote(index)
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}, using fallback")
            try:
                return await self._get_fallback().get_index_quote(index)
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                return {}
    
    async def search_symbol(self, query: str) -> list[dict]:
        """Search symbols."""
        try:
            return await self._get_provider().search_symbol(query)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []


# Singleton instance
_market_data_service: Optional[MarketDataService] = None


def get_market_data_service(
    provider: DataProvider = DataProvider.YFINANCE,
) -> MarketDataService:
    """Get market data service singleton."""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService(provider)
    return _market_data_service


if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Test with mock provider
        service = MarketDataService(DataProvider.MOCK)
        
        # Get quote
        quote = await service.get_quote("RELIANCE", "NSE")
        print("Quote:", quote)
        
        # Get index
        nifty = await service.get_index_quote("NIFTY")
        print("NIFTY:", nifty)
        
        # Get historical data
        from datetime import timedelta
        ohlcv = await service.get_ohlcv(
            "RELIANCE",
            "NSE",
            "1d",
            from_date=datetime.now(timezone.utc) - timedelta(days=30),
        )
        print(f"Historical: {len(ohlcv)} bars")
        
        # Search
        results = await service.search_symbol("RELI")
        print("Search:", results)
    
    asyncio.run(main())
