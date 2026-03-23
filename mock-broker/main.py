from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pydantic import BaseModel

app = FastAPI(title="Mock Broker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OrderRequest(BaseModel):
    symbol: str
    quantity: int
    transaction_type: str
    order_type: str
    price: Optional[float] = None
    product: str = "CNC"


class OrderResponse(BaseModel):
    order_id: str
    status: str
    message: str
    symbol: str
    quantity: int
    transaction_type: str
    order_type: str
    price: Optional[float]
    average_price: float
    filled_quantity: int
    pending_quantity: int
    order_timestamp: str


class Position(BaseModel):
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float


class Portfolio(BaseModel):
    total_value: float
    cash_balance: float
    positions: List[Position]
    total_pnl: float


class Quote(BaseModel):
    symbol: str
    last_price: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: str


MOCK_STOCKS = {
    "RELIANCE": {"base": 2500, "volatility": 0.02},
    "TCS": {"base": 3200, "volatility": 0.015},
    "INFY": {"base": 1400, "volatility": 0.025},
    "HDFCBANK": {"base": 1600, "volatility": 0.018},
    "ICICIBANK": {"base": 900, "volatility": 0.02},
    "SBIN": {"base": 550, "volatility": 0.022},
    "WIPRO": {"base": 450, "volatility": 0.019},
    "MARUTI": {"base": 2800, "volatility": 0.016},
    "BHARTIARTL": {"base": 750, "volatility": 0.024},
    "TITAN": {"base": 3100, "volatility": 0.021},
}

orders_db: Dict[str, dict] = {}
positions_db: Dict[str, dict] = {}
portfolio_cash = 1000000.0


def get_mock_price(symbol: str) -> float:
    if symbol not in MOCK_STOCKS:
        return 100.0
    
    stock = MOCK_STOCKS[symbol]
    change = random.gauss(0, stock["volatility"])
    price = stock["base"] * (1 + change)
    return round(price, 2)


def get_ohlc(symbol: str) -> dict:
    price = get_mock_price(symbol)
    stock = MOCK_STOCKS.get(symbol, {"base": 100})
    return {
        "open": round(price * random.uniform(0.98, 1.02), 2),
        "high": round(price * random.uniform(1.0, 1.05), 2),
        "low": round(price * random.uniform(0.95, 1.0), 2),
        "close": price,
        "volume": random.randint(100000, 10000000),
    }


@app.get("/")
async def root():
    return {"message": "Mock Broker API - Paper Trading", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/orders/place", response_model=OrderResponse)
async def place_order(order: OrderRequest):
    global portfolio_cash
    
    order_id = f"MOCK{uuid.uuid4().hex[:10].upper()}"
    
    if order.price:
        execution_price = order.price
    else:
        execution_price = get_mock_price(order.symbol)
    
    order_cost = execution_price * order.quantity
    
    if order.transaction_type == "BUY":
        if order_cost > portfolio_cash:
            return OrderResponse(
                order_id=order_id,
                status="REJECTED",
                message="Insufficient funds",
                symbol=order.symbol,
                quantity=order.quantity,
                transaction_type=order.transaction_type,
                order_type=order.order_type,
                price=order.price,
                average_price=0,
                filled_quantity=0,
                pending_quantity=order.quantity,
                order_timestamp=datetime.utcnow().isoformat(),
            )
        portfolio_cash -= order_cost
    
    symbol = order.symbol.upper()
    if symbol not in positions_db:
        positions_db[symbol] = {
            "symbol": symbol,
            "quantity": 0,
            "average_price": 0,
            "realized_pnl": 0,
        }
    
    position = positions_db[symbol]
    
    if order.transaction_type == "BUY":
        new_qty = position["quantity"] + order.quantity
        new_avg = (
            (position["quantity"] * position["average_price"] + order.quantity * execution_price)
            / new_qty
        )
        position["quantity"] = new_qty
        position["average_price"] = new_avg
    else:
        position["quantity"] -= order.quantity
        pnl = (execution_price - position["average_price"]) * order.quantity
        position["realized_pnl"] += pnl
        portfolio_cash += execution_price * order.quantity
    
    orders_db[order_id] = {
        "order_id": order_id,
        "status": "COMPLETE",
        "message": "Order filled",
        "symbol": symbol,
        "quantity": order.quantity,
        "transaction_type": order.transaction_type,
        "order_type": order.order_type,
        "price": order.price,
        "average_price": execution_price,
        "filled_quantity": order.quantity,
        "pending_quantity": 0,
        "order_timestamp": datetime.utcnow().isoformat(),
    }
    
    return OrderResponse(
        order_id=order_id,
        status="COMPLETE",
        message="Order filled at market price",
        symbol=symbol,
        quantity=order.quantity,
        transaction_type=order.transaction_type,
        order_type=order.order_type,
        price=order.price,
        average_price=execution_price,
        filled_quantity=order.quantity,
        pending_quantity=0,
        order_timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    if order_id not in orders_db:
        return {"error": "Order not found"}, 404
    return orders_db[order_id]


@app.get("/orders")
async def get_orders():
    return list(orders_db.values())


@app.get("/portfolio", response_model=Portfolio)
async def get_portfolio():
    positions = []
    total_pnl = 0
    
    for symbol, pos in positions_db.items():
        if pos["quantity"] > 0:
            current_price = get_mock_price(symbol)
            unrealized = (current_price - pos["average_price"]) * pos["quantity"]
            total_pnl += unrealized + pos["realized_pnl"]
            positions.append(
                Position(
                    symbol=symbol,
                    quantity=pos["quantity"],
                    average_price=pos["average_price"],
                    current_price=current_price,
                    unrealized_pnl=unrealized,
                    realized_pnl=pos["realized_pnl"],
                )
            )
    
    position_value = sum(
        p.current_price * p.quantity for p in positions
    )
    
    return Portfolio(
        total_value=portfolio_cash + position_value,
        cash_balance=portfolio_cash,
        positions=positions,
        total_pnl=total_pnl,
    )


@app.get("/quote/{symbol}", response_model=Quote)
async def get_quote(symbol: str):
    symbol = symbol.upper()
    ohlc = get_ohlc(symbol)
    last_price = ohlc["close"]
    
    return Quote(
        symbol=symbol,
        last_price=last_price,
        open=ohlc["open"],
        high=ohlc["high"],
        low=ohlc["low"],
        close=ohlc["close"],
        volume=ohlc["volume"],
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/quotes")
async def get_quotes():
    quotes = []
    for symbol in MOCK_STOCKS.keys():
        ohlc = get_ohlc(symbol)
        quotes.append(
            {
                "symbol": symbol,
                "last_price": ohlc["close"],
                "open": ohlc["open"],
                "high": ohlc["high"],
                "low": ohlc["low"],
                "close": ohlc["close"],
                "volume": ohlc["volume"],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    return quotes


@app.get("/holdings")
async def get_holdings():
    holdings = []
    for symbol, pos in positions_db.items():
        if pos["quantity"] > 0:
            current_price = get_mock_price(symbol)
            holdings.append(
                {
                    "symbol": symbol,
                    "quantity": pos["quantity"],
                    "average_price": pos["average_price"],
                    "current_price": current_price,
                    "pnl": (current_price - pos["average_price"]) * pos["quantity"],
                }
            )
    return holdings


@app.post("/portfolio/reset")
async def reset_portfolio():
    global portfolio_cash
    portfolio_cash = 1000000.0
    positions_db.clear()
    orders_db.clear()
    return {"message": "Portfolio reset successful", "cash_balance": portfolio_cash}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
