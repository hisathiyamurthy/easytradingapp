"""Simulated Trading Engine - Paper Trading with Virtual Balance."""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
import random

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class VirtualPosition:
    """Virtual position in paper trading."""
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    strategy_id: Optional[str] = None
    symbol: str = ""
    exchange: str = "NSE"
    side: PositionSide = PositionSide.LONG
    quantity: int = 0
    entry_price: float = 0
    current_price: float = 0
    realized_pnl: float = 0
    unrealized_pnl: float = 0
    opened_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.entry_price


@dataclass
class VirtualBalance:
    """Virtual trading account balance."""
    cash: float = 100000.0  # Default virtual balance
    initial_balance: float = 100000.0
    realized_pnl: float = 0
    unrealized_pnl: float = 0
    total_commission: float = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    @property
    def equity(self) -> float:
        return self.cash + self.realized_pnl + self.unrealized_pnl

    @property
    def available_balance(self) -> float:
        # Reserve for unrealized losses
        reserved = max(0, -self.unrealized_pnl)
        return self.cash - reserved

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0
        return (self.winning_trades / self.total_trades) * 100


@dataclass
class SimulatedOrder:
    """Simulated order for paper trading."""
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    strategy_id: Optional[str] = None
    symbol: str = ""
    exchange: str = "NSE"
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    fill_price: Optional[float] = None
    commission: float = 0
    slippage: float = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TradeSimulation:
    """Trade simulation result."""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    fill_price: float
    commission: float
    slippage: float
    total_value: float
    net_value: float
    new_balance: float
    position_id: Optional[str]
    executed_at: datetime


class SimulatedTradeEngine:
    """Paper trading engine with virtual balance."""

    def __init__(
        self,
        user_id: str,
        initial_balance: float = 100000.0,
        commission_rate: float = 0.001,  # 0.1% commission
        slippage_bps: float = 1.0,  # 1 basis point slippage
    ):
        self.user_id = user_id
        self.commission_rate = commission_rate
        self.slippage_bps = slippage_bps

        # Initialize balance
        self.balance = VirtualBalance(
            cash=initial_balance,
            initial_balance=initial_balance,
        )

        # Position tracking
        self.positions: dict[str, VirtualPosition] = {}  # key: symbol

        # Order tracking
        self.orders: dict[str, SimulatedOrder] = {}

        # Trade history
        self.trades: list[TradeSimulation] = []

        logger.info(
            f"Simulated trading engine initialized for user {user_id} "
            f"with balance {initial_balance}"
        )

    def reset(self, initial_balance: Optional[float] = None):
        """Reset the simulation to initial state."""
        if initial_balance:
            self.balance = VirtualBalance(
                cash=initial_balance,
                initial_balance=initial_balance,
            )
        else:
            self.balance = VirtualBalance(
                cash=self.balance.initial_balance,
                initial_balance=self.balance.initial_balance,
            )

        self.positions.clear()
        self.orders.clear()
        self.trades.clear()

        logger.info(f"Simulation reset for user {self.user_id}")

    def get_balance(self) -> VirtualBalance:
        """Get current virtual balance."""
        self._update_unrealized_pnl()
        return self.balance

    def get_position(self, symbol: str) -> Optional[VirtualPosition]:
        """Get position for a symbol."""
        return self.positions.get(symbol)

    def get_all_positions(self) -> list[VirtualPosition]:
        """Get all open positions."""
        return list(self.positions.values())

    def get_pending_orders(self) -> list[SimulatedOrder]:
        """Get all pending orders."""
        return [
            order for order in self.orders.values()
            if order.status == OrderStatus.PENDING
        ]

    def _update_unrealized_pnl(self):
        """Update unrealized P&L for all positions."""
        total_unrealized = 0
        
        for position in self.positions.values():
            if position.current_price > 0:
                position.unrealized_pnl = (
                    (position.current_price - position.entry_price) 
                    * position.quantity
                )
                total_unrealized += position.unrealized_pnl

        self.balance.unrealized_pnl = total_unrealized

    def _apply_slippage(self, price: float, side: OrderSide) -> float:
        """Apply simulated slippage to price."""
        slippage = price * (self.slippage_bps / 10000)
        
        if side == OrderSide.BUY:
            # Buy at higher price
            return price + slippage
        else:
            # Sell at lower price
            return price - slippage

    def _calculate_commission(self, value: float) -> float:
        """Calculate commission for trade."""
        return value * self.commission_rate

    def can_place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: Optional[float] = None,
    ) -> tuple[bool, str]:
        """Check if order can be placed."""
        # Check balance
        if side == OrderSide.BUY:
            required = (price or 0) * quantity
            commission = self._calculate_commission(required)
            total_required = required + commission

            if total_required > self.balance.available_balance:
                return False, f"Insufficient balance. Required: {total_required:.2f}, Available: {self.balance.available_balance:.2f}"

        # Check position for sell
        if side == OrderSide.SELL:
            position = self.positions.get(symbol)
            if not position or position.quantity < quantity:
                return False, f"Insufficient position. Have: {position.quantity if position else 0}, Required: {quantity}"

        return True, "OK"

    async def place_market_order(
        self,
        symbol: str,
        exchange: str,
        side: OrderSide,
        quantity: int,
        current_price: float,
        strategy_id: Optional[str] = None,
    ) -> TradeSimulation:
        """Place a market order at current price."""
        # Apply slippage
        fill_price = self._apply_slippage(current_price, side)

        return await self._execute_order(
            symbol=symbol,
            exchange=exchange,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            limit_price=fill_price,
            strategy_id=strategy_id,
        )

    async def place_limit_order(
        self,
        symbol: str,
        exchange: str,
        side: OrderSide,
        quantity: int,
        limit_price: float,
        strategy_id: Optional[str] = None,
    ) -> SimulatedOrder:
        """Place a limit order."""
        order = SimulatedOrder(
            user_id=self.user_id,
            strategy_id=strategy_id,
            symbol=symbol,
            exchange=exchange,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=limit_price,
            status=OrderStatus.PENDING,
        )

        self.orders[order.id] = order
        return order

    async def _execute_order(
        self,
        symbol: str,
        exchange: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: int,
        limit_price: float,
        strategy_id: Optional[str] = None,
    ) -> TradeSimulation:
        """Execute an order (internal method)."""
        # Calculate values
        gross_value = limit_price * quantity
        commission = self._calculate_commission(gross_value)
        total_value = gross_value + commission

        # Update balance
        if side == OrderSide.BUY:
            self.balance.cash -= total_value
        else:
            self.balance.cash += gross_value - commission

        self.balance.total_commission += commission
        self.balance.total_trades += 1

        # Update position
        position_id = await self._update_position(
            symbol=symbol,
            exchange=exchange,
            side=side,
            quantity=quantity,
            price=limit_price,
        )

        # Create trade
        trade = TradeSimulation(
            order_id=str(uuid4()),
            symbol=symbol,
            side=side,
            quantity=quantity,
            fill_price=limit_price,
            commission=commission,
            slippage=abs(limit_price - (limit_price * (self.slippage_bps / 10000))),
            total_value=total_value,
            net_value=gross_value - commission if side == OrderSide.SELL else -total_value,
            new_balance=self.balance.cash,
            position_id=position_id,
            executed_at=datetime.utcnow(),
        )

        self.trades.append(trade)

        logger.info(
            f"Simulated trade executed: {side.value} {quantity} {symbol} "
            f"@ {limit_price:.2f}, Commission: {commission:.2f}"
        )

        return trade

    async def _update_position(
        self,
        symbol: str,
        exchange: str,
        side: OrderSide,
        quantity: int,
        price: float,
    ) -> str:
        """Update position after trade."""
        position = self.positions.get(symbol)

        if side == OrderSide.BUY:
            if position is None:
                # Open new long position
                position = VirtualPosition(
                    user_id=self.user_id,
                    symbol=symbol,
                    exchange=exchange,
                    side=PositionSide.LONG,
                    quantity=quantity,
                    entry_price=price,
                    current_price=price,
                )
            else:
                # Add to existing position (average down/up)
                total_cost = (position.quantity * position.entry_price) + (quantity * price)
                position.quantity += quantity
                position.entry_price = total_cost / position.quantity
                position.current_price = price

        else:  # SELL
            if position and position.quantity >= quantity:
                # Calculate realized P&L
                pnl = (price - position.entry_price) * quantity
                position.realized_pnl += pnl
                position.quantity -= quantity

                # Track win/loss
                if pnl > 0:
                    self.balance.winning_trades += 1
                else:
                    self.balance.losing_trades += 1

                # Close position if fully sold
                if position.quantity == 0:
                    self.balance.realized_pnl += position.realized_pnl
                    del self.positions[symbol]
                    return position.id

        if position:
            self.positions[symbol] = position
            position.updated_at = datetime.utcnow()

        return position.id if position else None

    async def process_pending_orders(
        self,
        symbol: str,
        current_price: float,
    ) -> list[TradeSimulation]:
        """Process pending limit orders that can be filled."""
        executed_trades = []

        for order in self.get_pending_orders():
            if order.symbol != symbol:
                continue

            can_fill = False

            if order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and current_price <= order.price:
                    can_fill = True
                elif order.side == OrderSide.SELL and current_price >= order.price:
                    can_fill = True

            if can_fill:
                trade = await self._execute_order(
                    symbol=order.symbol,
                    exchange=order.exchange,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    limit_price=order.price,
                    strategy_id=order.strategy_id,
                )
                executed_trades.append(trade)

                order.status = OrderStatus.FILLED
                order.filled_quantity = order.quantity
                order.fill_price = order.price
                order.filled_at = datetime.utcnow()

        return executed_trades

    def update_market_prices(self, prices: dict[str, float]):
        """Update current prices for all positions and calculate P&L."""
        for symbol, price in prices.items():
            position = self.positions.get(symbol)
            if position:
                position.current_price = price

        self._update_unrealized_pnl()

    def get_performance_summary(self) -> dict:
        """Get trading performance summary."""
        self._update_unrealized_pnl()

        return {
            "initial_balance": self.balance.initial_balance,
            "current_balance": self.balance.cash,
            "equity": self.balance.equity,
            "realized_pnl": self.balance.realized_pnl,
            "unrealized_pnl": self.balance.unrealized_pnl,
            "total_pnl": self.balance.realized_pnl + self.balance.unrealized_pnl,
            "total_return_pct": (
                ((self.balance.equity - self.balance.initial_balance) 
                 / self.balance.initial_balance) * 100
            ),
            "total_trades": self.balance.total_trades,
            "winning_trades": self.balance.winning_trades,
            "losing_trades": self.balance.losing_trades,
            "win_rate": self.balance.win_rate,
            "total_commission": self.balance.total_commission,
            "open_positions": len(self.positions),
        }

    def get_trade_history(
        self,
        limit: int = 50,
        symbol: Optional[str] = None,
    ) -> list[dict]:
        """Get trade history."""
        trades = self.trades

        if symbol:
            trades = [t for t in trades if t.symbol == symbol]

        trades = trades[-limit:]

        return [
            {
                "order_id": t.order_id,
                "symbol": t.symbol,
                "side": t.side.value,
                "quantity": t.quantity,
                "fill_price": t.fill_price,
                "commission": t.commission,
                "total_value": t.total_value,
                "net_value": t.net_value,
                "executed_at": t.executed_at.isoformat(),
            }
            for t in trades
        ]


class PaperTradingService:
    """Service for managing multiple paper trading accounts."""

    def __init__(self):
        self._accounts: dict[str, SimulatedTradeEngine] = {}

    def get_or_create_account(
        self,
        user_id: str,
        initial_balance: float = 100000.0,
    ) -> SimulatedTradeEngine:
        """Get existing or create new paper trading account."""
        if user_id not in self._accounts:
            self._accounts[user_id] = SimulatedTradeEngine(
                user_id=user_id,
                initial_balance=initial_balance,
            )
        return self._accounts[user_id]

    def get_account(self, user_id: str) -> Optional[SimulatedTradeEngine]:
        """Get paper trading account."""
        return self._accounts.get(user_id)

    def delete_account(self, user_id: str) -> bool:
        """Delete paper trading account."""
        if user_id in self._accounts:
            del self._accounts[user_id]
            return True
        return False


# Singleton instance
_paper_trading_service: Optional[PaperTradingService] = None


def get_paper_trading_service() -> PaperTradingService:
    """Get paper trading service singleton."""
    global _paper_trading_service
    if _paper_trading_service is None:
        _paper_trading_service = PaperTradingService()
    return _paper_trading_service


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Create paper trading engine
        engine = SimulatedTradeEngine(
            user_id="user123",
            initial_balance=100000.0,
            commission_rate=0.001,
            slippage_bps=1.0,
        )

        print("=== Paper Trading Simulation ===\n")

        # Check initial balance
        balance = engine.get_balance()
        print(f"Initial Balance: ₹{balance.cash:,.2f}")
        print(f"Equity: ₹{balance.equity:,.2f}\n")

        # Simulate buying NIFTY at 18000
        print("Placing BUY order: 100 shares @ ₹18,000")
        trade1 = await engine.place_market_order(
            symbol="NIFTY",
            exchange="NSE",
            side=OrderSide.BUY,
            quantity=100,
            current_price=18000.0,
        )
        print(f"Executed: Bought 100 @ ₹{trade1.fill_price:.2f}")
        print(f"Commission: ₹{trade1.commission:.2f}")
        print(f"Balance: ₹{engine.balance.cash:,.2f}\n")

        # Simulate price movement - NIFTY goes up
        engine.update_market_prices({"NIFTY": 18100.0})
        balance = engine.get_balance()
        print(f"NIFTY now trading @ ₹18,100")
        print(f"Unrealized P&L: ₹{balance.unrealized_pnl:,.2f}")
        print(f"Equity: ₹{balance.equity:,.2f}\n")

        # Sell half position
        print("Placing SELL order: 50 shares @ ₹18,100")
        trade2 = await engine.place_market_order(
            symbol="NIFTY",
            exchange="NSE",
            side=OrderSide.SELL,
            quantity=50,
            current_price=18100.0,
        )
        print(f"Executed: Sold 50 @ ₹{trade2.fill_price:.2f}")
        print(f"Commission: ₹{trade2.commission:.2f}")
        print(f"Balance: ₹{engine.balance.cash:,.2f}\n")

        # Performance summary
        summary = engine.get_performance_summary()
        print("=== Performance Summary ===")
        for key, value in summary.items():
            if isinstance(value, float):
                print(f"{key}: {value:,.2f}")
            else:
                print(f"{key}: {value}")

    asyncio.run(main())
