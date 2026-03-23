"""Market data API endpoints."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from services.market_data_service import (
    MarketDataService,
    DataProvider,
    get_market_data_service,
)
from services.price_cache_service import get_price_cache_service

router = APIRouter(prefix="/market", tags=["market"])


class QuoteResponse(BaseModel):
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
    timestamp: datetime


class IndexResponse(BaseModel):
    symbol: str
    last_price: float
    open: float
    high: float
    low: float
    previous_close: float
    change: float
    pct_change: float
    timestamp: datetime


class OHLCVResponse(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class SearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(
    symbol: str,
    exchange: str = Query("NSE", description="Exchange (NSE/BSE)"),
    use_cache: bool = Query(True, description="Use cached price if available"),
    market_service: MarketDataService = Depends(get_market_data_service),
):
    """Get current quote for a symbol."""
    if use_cache:
        cache_service = get_price_cache_service()
        cached = await cache_service.get_price(symbol, exchange)
        if cached:
            return QuoteResponse(**cached)
    
    quote = await market_service.get_quote(symbol, exchange)
    
    if not quote or not quote.get("last_price"):
        raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")
    
    # Update cache
    if use_cache:
        cache_service = get_price_cache_service()
        await cache_service.update_price(symbol, exchange, quote)
    
    return QuoteResponse(**quote, timestamp=datetime.now())


@router.get("/quotes", response_model=list[QuoteResponse])
async def get_quotes(
    symbols: str = Query(..., description="Comma-separated symbols"),
    exchange: str = Query("NSE", description="Exchange (NSE/BSE)"),
    market_service: MarketDataService = Depends(get_market_data_service),
):
    """Get quotes for multiple symbols."""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    # Try cache first
    cache_service = get_price_cache_service()
    cached = await cache_service.get_prices(symbol_list, exchange)
    
    results = []
    symbols_to_fetch = []
    
    for symbol in symbol_list:
        if symbol in cached:
            results.append(QuoteResponse(**cached[symbol]))
        else:
            symbols_to_fetch.append(symbol)
    
    # Fetch missing from provider
    if symbols_to_fetch:
        for symbol in symbols_to_fetch:
            quote = await market_service.get_quote(symbol, exchange)
            if quote and quote.get("last_price"):
                results.append(QuoteResponse(**quote, timestamp=datetime.now()))
                await cache_service.update_price(symbol, exchange, quote)
    
    return results


@router.get("/index/{index}", response_model=IndexResponse)
async def get_index(
    index: str,
    market_service: MarketDataService = Depends(get_market_data_service),
):
    """Get index quote."""
    index = index.upper()
    quote = await market_service.get_index_quote(index)
    
    if not quote or not quote.get("last_price"):
        raise HTTPException(status_code=404, detail=f"Index {index} not found")
    
    return IndexResponse(**quote, timestamp=datetime.now())


@router.get("/historical/{symbol}", response_model=list[OHLCVResponse])
async def get_historical(
    symbol: str,
    exchange: str = Query("NSE", description="Exchange"),
    interval: str = Query("1d", description="Interval (1m/5m/15m/60m/1d)"),
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="To date (YYYY-MM-DD)"),
    market_service: MarketDataService = Depends(get_market_data_service),
):
    """Get historical OHLCV data."""
    # Parse dates
    from_dt = None
    to_dt = None
    
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format")
    
    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format")
    
    if not from_dt:
        from_dt = datetime.now() - timedelta(days=30)
    if not to_dt:
        to_dt = datetime.now()
    
    ohlcv_data = await market_service.get_ohlcv(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        from_date=from_dt,
        to_date=to_dt,
    )
    
    if not ohlcv_data:
        raise HTTPException(status_code=404, detail=f"No historical data for {symbol}")
    
    return [
        OHLCVResponse(
            timestamp=bar.timestamp,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
        for bar in ohlcv_data
    ]


@router.get("/search", response_model=list[SearchResult])
async def search_symbols(
    q: str = Query(..., min_length=1, description="Search query"),
    market_service: MarketDataService = Depends(get_market_data_service),
):
    """Search for symbols."""
    results = await market_service.search_symbol(q)
    return [SearchResult(**r) for r in results]


@router.get("/cache/stats")
async def get_cache_stats():
    """Get price cache statistics."""
    cache_service = get_price_cache_service()
    return cache_service.get_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear price cache."""
    cache_service = get_price_cache_service()
    return {"status": "cleared"}


# ==================== Options Trading Endpoints ====================

class OptionsLotSizeResponse(BaseModel):
    symbol: str
    lot_size: int


@router.get("/options/lot-sizes", response_model=dict)
async def get_options_lot_sizes():
    """Get lot sizes for all supported options symbols."""
    from services.options_service import get_all_lot_sizes
    return get_all_lot_sizes()


@router.get("/options/{symbol}/lot-size")
async def get_lot_size(symbol: str):
    """Get lot size for a specific symbol."""
    from services.options_service import get_lot_size
    lot_size = get_lot_size(symbol)
    return OptionsLotSizeResponse(symbol=symbol.upper(), lot_size=lot_size)


class StrikeSelectionRequest(BaseModel):
    current_price: float
    selection_type: str  # ATM, ITM, OTM
    option_type: str  # CE, PE
    distance: int = 0  # Points for ITM/OTM


class StrikeSelectionResponse(BaseModel):
    strike: int
    strike_type: str
    symbol: str
    lot_size: int
    quantity: int


@router.post("/options/select-strike", response_model=StrikeSelectionResponse)
async def select_strike(request: StrikeSelectionRequest):
    """Select appropriate strike based on current price and criteria."""
    from services.options_service import OptionsStrikeSelector
    
    selector = OptionsStrikeSelector()
    result = selector.select_strike(
        current_price=request.current_price,
        selection_type=request.selection_type,
        distance=request.distance,
        option_type=request.option_type,
    )
    
    return StrikeSelectionResponse(**result)
