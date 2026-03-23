"""Broker WebSocket streaming for real-time market data.

Supports live price streaming from Indian brokers via WebSocket connections.
"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


@dataclass
class StreamingQuote:
    """Real-time streaming quote."""
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


class BrokerWebSocketStreamer(ABC):
    """Abstract base class for broker WebSocket streaming."""
    
    def __init__(self, api_key: str, access_token: str, feed_token: Optional[str] = None):
        self.api_key = api_key
        self.access_token = access_token
        self.feed_token = feed_token
        self._ws = None
        self._running = False
        self._subscribed_symbols: set[str] = set()
        self._callbacks: list[Callable[[StreamingQuote], None]] = []
        self._reconnect_delay = 5
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close WebSocket connection."""
        pass
    
    @abstractmethod
    async def subscribe(self, symbols: list[str]):
        """Subscribe to symbols for live quotes."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, symbols: list[str]):
        """Unsubscribe from symbols."""
        pass
    
    @abstractmethod
    def _parse_message(self, message: dict) -> Optional[StreamingQuote]:
        """Parse WebSocket message to StreamingQuote."""
        pass
    
    def add_callback(self, callback: Callable[[StreamingQuote], None]):
        """Add callback for quote updates."""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[StreamingQuote], None]):
        """Remove callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def _notify_callbacks(self, quote: StreamingQuote):
        """Notify all callbacks of new quote."""
        for callback in self._callbacks:
            try:
                callback(quote)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    async def _handle_message(self, message: dict):
        """Handle incoming WebSocket message."""
        quote = self._parse_message(message)
        if quote:
            await self._notify_callbacks(quote)
    
    async def _reconnect(self):
        """Reconnect on failure."""
        if self._running:
            logger.info(f"Reconnecting in {self._reconnect_delay} seconds...")
            await asyncio.sleep(self._reconnect_delay)
            try:
                await self.connect()
                if self._subscribed_symbols:
                    await self.subscribe(list(self._subscribed_symbols))
            except Exception as e:
                logger.error(f"Reconnect failed: {e}")


class ZerodhaWebSocketStreamer(BrokerWebSocketStreamer):
    """Zerodha Kite WebSocket streaming implementation."""
    
    WS_URL = "wss://ws.kite.trade"
    
    async def connect(self) -> bool:
        """Connect to Zerodha WebSocket."""
        try:
            import websockets
            from websockets.exceptions import ConnectionClosed
            
            # Get session token (enctype for WebSocket)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.kite.trade/session/token",
                    data={
                        "api_key": self.api_key,
                        "access_token": self.access_token,
                        "request_id": "",
                        "skip_session": "true",
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    self.enctoken = data.get("data", {}).get("enctoken")
                    if not self.enctoken:
                        logger.error("No enctoken received")
                        return False
            
            # Connect with enctoken
            ws_url = f"{self.WS_URL}?api_key={self.api_key}&enctoken={self.enctoken}"
            self._ws = await websockets.connect(ws_url, ping_interval=20)
            self._running = True
            logger.info("Zerodha WebSocket connected")
            
            # Start message handler
            asyncio.create_task(self._message_loop())
            return True
        except Exception as e:
            logger.error(f"Zerodha WebSocket connect error: {e}")
            await self._reconnect()
            return False
    
    async def disconnect(self):
        """Disconnect from Zerodha WebSocket."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("Zerodha WebSocket disconnected")
    
    async def subscribe(self, symbols: list[str]):
        """Subscribe to symbols."""
        self._subscribed_symbols.update(symbols)
        
        if self._ws and self._running:
            message = {
                "a": "subscribe",
                "v": list(self._subscribed_symbols)
            }
            await self._ws.send(json.dumps(message))
            logger.info(f"Subscribed to {symbols}")
    
    async def unsubscribe(self, symbols: list[str]):
        """Unsubscribe from symbols."""
        self._subscribed_symbols -= set(symbols)
        
        if self._ws and self._running:
            message = {
                "a": "unsubscribe",
                "v": symbols
            }
            await self._ws.send(json.dumps(message))
    
    async def _message_loop(self):
        """Main message handling loop."""
        try:
            async for message in self._ws:
                if not self._running:
                    break
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"Message loop error: {e}")
            if self._running:
                await self._reconnect()
    
    def _parse_message(self, message: dict) -> Optional[StreamingQuote]:
        """Parse Zerodha WebSocket message."""
        try:
            # Zerodha sends in different formats
            if "tk" in message:  # Trade tick
                return StreamingQuote(
                    symbol=message.get("tk", ""),
                    exchange=message.get("e", "NSE"),
                    last_price=float(message.get("lp", 0)),
                    open=float(message.get("o", 0)),
                    high=float(message.get("h", 0)),
                    low=float(message.get("l", 0)),
                    close=float(message.get("c", 0)),
                    volume=int(message.get("v", 0)),
                    bid=float(message.get("bdp", 0)),
                    ask=float(message.get("bsp", 0)),
                    bid_quantity=int(message.get("bfq", 0)),
                    ask_quantity=int(message.get("bsq", 0)),
                    timestamp=datetime.now(timezone.utc),
                )
        except Exception as e:
            logger.error(f"Parse error: {e}")
        return None


class KotakWebSocketStreamer(BrokerWebSocketStreamer):
    """Kotak Neo WebSocket streaming implementation."""
    
    WS_URL = "wss://gw-napi.kotakdemo.com/streaming/quote"
    
    async def connect(self) -> bool:
        """Connect to Kotak WebSocket."""
        try:
            import websockets
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "x-api-key": self.api_key,
            }
            
            self._ws = await websockets.connect(self.WS_URL, headers=headers)
            self._running = True
            logger.info("Kotak WebSocket connected")
            
            asyncio.create_task(self._message_loop())
            return True
        except Exception as e:
            logger.error(f"Kotak WebSocket connect error: {e}")
            await self._reconnect()
            return False
    
    async def disconnect(self):
        """Disconnect from Kotak WebSocket."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
    
    async def subscribe(self, symbols: list[str]):
        """Subscribe to symbols."""
        self._subscribed_symbols.update(symbols)
        
        if self._ws and self._running:
            message = {
                "type": "subscribe",
                "segments": ["NSE", "BSE"],
                "instruments": list(self._subscribed_symbols),
            }
            await self._ws.send(json.dumps(message))
    
    async def unsubscribe(self, symbols: list[str]):
        """Unsubscribe from symbols."""
        self._subscribed_symbols -= set(symbols)
        
        if self._ws and self._running:
            message = {
                "type": "unsubscribe",
                "instruments": symbols,
            }
            await self._ws.send(json.dumps(message))
    
    async def _message_loop(self):
        """Main message handling loop."""
        try:
            async for message in self._ws:
                if not self._running:
                    break
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Message loop error: {e}")
            if self._running:
                await self._reconnect()
    
    def _parse_message(self, message: dict) -> Optional[StreamingQuote]:
        """Parse Kotak WebSocket message."""
        try:
            if message.get("type") == "quote":
                data = message.get("data", {})
                return StreamingQuote(
                    symbol=data.get("instrument_token", ""),
                    exchange=data.get("exchange", "NSE"),
                    last_price=float(data.get("last_price", 0)),
                    open=float(data.get("ohlc", {}).get("open", 0)),
                    high=float(data.get("ohlc", {}).get("high", 0)),
                    low=float(data.get("ohlc", {}).get("low", 0)),
                    close=float(data.get("ohlc", {}).get("close", 0)),
                    volume=int(data.get("volume", 0)),
                    bid=float(data.get("depth", {}).get("buy", [{}])[0].get("price", 0)),
                    ask=float(data.get("depth", {}).get("sell", [{}])[0].get("price", 0)),
                    bid_quantity=int(data.get("depth", {}).get("buy", [{}])[0].get("quantity", 0)),
                    ask_quantity=int(data.get("depth", {}).get("sell", [{}])[0].get("quantity", 0)),
                    timestamp=datetime.now(timezone.utc),
                )
        except Exception as e:
            logger.error(f"Parse error: {e}")
        return None


class UpstoxWebSocketStreamer(BrokerWebSocketStreamer):
    """Upstox WebSocket streaming implementation."""
    
    WS_URL = "wss://ws.upstox.com/v2/quote"
    
    async def connect(self) -> bool:
        """Connect to Upstox WebSocket."""
        try:
            import websockets
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "x-api-key": self.api_key,
            }
            
            self._ws = await websockets.connect(self.WS_URL, headers=headers)
            self._running = True
            logger.info("Upstox WebSocket connected")
            
            asyncio.create_task(self._message_loop())
            return True
        except Exception as e:
            logger.error(f"Upstox WebSocket connect error: {e}")
            await self._reconnect()
            return False
    
    async def disconnect(self):
        """Disconnect from Upstox WebSocket."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
    
    async def subscribe(self, symbols: list[str]):
        """Subscribe to symbols."""
        self._subscribed_symbols.update(symbols)
        
        if self._ws and self._running:
            message = {
                "type": "subscribe",
                "instrumentKeys": list(self._subscribed_symbols),
            }
            await self._ws.send(json.dumps(message))
    
    async def unsubscribe(self, symbols: list[str]):
        """Unsubscribe from symbols."""
        self._subscribed_symbols -= set(symbols)
        
        if self._ws and self._running:
            message = {
                "type": "unsubscribe",
                "instrumentKeys": symbols,
            }
            await self._ws.send(json.dumps(message))
    
    async def _message_loop(self):
        """Main message handling loop."""
        try:
            async for message in self._ws:
                if not self._running:
                    break
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Message loop error: {e}")
            if self._running:
                await self._reconnect()
    
    def _parse_message(self, message: dict) -> Optional[StreamingQuote]:
        """Parse Upstox WebSocket message."""
        try:
            data = message.get("data", {})
            for key, value in data.items():
                if isinstance(value, dict) and "last_price" in value:
                    return StreamingQuote(
                        symbol=key,
                        exchange="NSE",
                        last_price=float(value.get("last_price", 0)),
                        open=float(value.get("ohlc", {}).get("open", 0)),
                        high=float(value.get("ohlc", {}).get("high", 0)),
                        low=float(value.get("ohlc", {}).get("low", 0)),
                        close=float(value.get("ohlc", {}).get("close", 0)),
                        volume=int(value.get("volume", 0)),
                        bid=float(value.get("depth", {}).get("buy", [{}])[0].get("price", 0)),
                        ask=float(value.get("depth", {}).get("sell", [{}])[0].get("price", 0)),
                        bid_quantity=int(value.get("depth", {}).get("buy", [{}])[0].get("quantity", 0)),
                        ask_quantity=int(value.get("depth", {}).get("sell", [{}])[0].get("quantity", 0)),
                        timestamp=datetime.now(timezone.utc),
                    )
        except Exception as e:
            logger.error(f"Parse error: {e}")
        return None


class MarketDataStreamManager:
    """Manager for market data streaming across multiple sources."""
    
    def __init__(self):
        self._streamers: dict[str, BrokerWebSocketStreamer] = {}
        self._price_cache: dict[str, StreamingQuote] = {}
        self._callbacks: list[Callable[[StreamingQuote], None]] = []
    
    def add_streamer(self, user_id: str, streamer: BrokerWebSocketStreamer):
        """Add a broker streamer."""
        self._streamers[user_id] = streamer
        streamer.add_callback(self._on_quote_update)
    
    def remove_streamer(self, user_id: str):
        """Remove a broker streamer."""
        if user_id in self._streamers:
            self._streamers[user_id]._running = False
            del self._streamers[user_id]
    
    async def subscribe_symbols(self, user_id: str, symbols: list[str]):
        """Subscribe to symbols for a user."""
        if user_id in self._streamers:
            await self._streamers[user_id].subscribe(symbols)
    
    async def unsubscribe_symbols(self, user_id: str, symbols: list[str]):
        """Unsubscribe from symbols."""
        if user_id in self._streamers:
            await self._streamers[user_id].unsubscribe(symbols)
    
    async def subscribe_global(self, symbols: list[str]):
        """Subscribe to symbols across all streamers."""
        for streamer in self._streamers.values():
            await streamer.subscribe(symbols)
    
    async def disconnect_all(self):
        """Disconnect all streamers."""
        for streamer in self._streamers.values():
            await streamer.disconnect()
        self._streamers.clear()
    
    def add_callback(self, callback: Callable[[StreamingQuote], None]):
        """Add global callback."""
        self._callbacks.append(callback)
    
    def get_cached_quote(self, symbol: str) -> Optional[StreamingQuote]:
        """Get cached quote for symbol."""
        return self._price_cache.get(symbol)
    
    def get_all_cached_quotes(self) -> dict[str, StreamingQuote]:
        """Get all cached quotes."""
        return self._price_cache.copy()
    
    async def _on_quote_update(self, quote: StreamingQuote):
        """Handle quote update."""
        self._price_cache[quote.symbol] = quote
        
        for callback in self._callbacks:
            try:
                callback(quote)
            except Exception as e:
                logger.error(f"Callback error: {e}")


# Singleton instance
_stream_manager: Optional[MarketDataStreamManager] = None


def get_stream_manager() -> MarketDataStreamManager:
    """Get market data stream manager singleton."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = MarketDataStreamManager()
    return _stream_manager


if __name__ == "__main__":
    # Example usage
    async def main():
        manager = MarketDataStreamManager()
        
        # Example with mock callback
        def on_quote(quote: StreamingQuote):
            print(f"Quote: {quote.symbol} = ₹{quote.last_price}")
        
        manager.add_callback(on_quote)
        
        # Note: Need actual API credentials for real streaming
        # streamer = ZerodhaWebSocketStreamer(api_key="...", access_token="...")
        # manager.add_streamer("user123", streamer)
        # await streamer.connect()
        # await streamer.subscribe(["RELIANCE", "TCS"])
        
        print("Stream manager initialized")
    
    asyncio.run(main())
