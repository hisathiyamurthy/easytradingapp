"""
Paper Trading Service - Simulated trading engine.
Executes trades in paper mode without real broker connection.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.strategy_models import Strategy
from models.strategy_instance_models import UserStrategyInstance, InstanceTrade, InstancePosition
from strategy_engine.executor import IndicatorCalculator, OHLCV

logger = logging.getLogger(__name__)


class SimulatedMarketData:
    """Simulated market data generator for paper trading."""
    
    def __init__(self, symbol: str, base_price: float = 100.0):
        self.symbol = symbol
        self.base_price = base_price
        self.current_price = base_price
        self.volatility = 0.02
        self.trend = 0.0
    
    def get_current_ohlcv(self) -> OHLCV:
        """Get current OHLCV data with simulated price movement."""
        change = random.gauss(self.trend, self.volatility)
        open_price = self.current_price
        self.current_price *= (1 + change)
        high = max(open_price, self.current_price) * (1 + random.uniform(0, 0.01))
        low = min(open_price, self.current_price) * (1 - random.uniform(0, 0.01))
        close = self.current_price
        
        return OHLCV(
            timestamp=datetime.now(timezone.utc),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=random.randint(10000, 100000)
        )
    
    def get_historical_bars(self, periods: int = 100) -> List[OHLCV]:
        """Generate historical bars for indicator calculation."""
        bars = []
        price = self.base_price
        for i in range(periods):
            change = random.gauss(0, self.volatility)
            open_price = price
            price *= (1 + change)
            high = max(open_price, price) * (1 + random.uniform(0, 0.01))
            low = min(open_price, price) * (1 - random.uniform(0, 0.01))
            bars.append(OHLCV(
                timestamp=datetime.now(timezone.utc),
                open=open_price,
                high=high,
                low=low,
                close=price,
                volume=random.randint(10000, 100000)
            ))
        return bars


def check_rsi_condition(rsi_value: float, operator: str, threshold: float) -> bool:
    """Check RSI condition."""
    if operator in ["crosses_above", "greater_than", "above"]:
        return rsi_value > threshold
    elif operator in ["crosses_below", "less_than", "below"]:
        return rsi_value < threshold
    return False


def check_sma_condition(sma_value: float, price: float, operator: str) -> bool:
    """Check SMA condition."""
    if operator in ["above", "greater_than", "crosses_above"]:
        return sma_value > price
    elif operator in ["below", "less_than", "crosses_below"]:
        return sma_value < price
    return False


def check_macd_condition(macd_value: float, signal_value: float, operator: str, threshold: float = 0) -> bool:
    """Check MACD condition."""
    if operator in ["crosses_above", "above"]:
        return macd_value > threshold
    elif operator in ["crosses_below", "below"]:
        return macd_value < threshold
    return False


def evaluate_condition_group(group: Dict[str, Any], indicators: Dict[str, float], current_price: float) -> bool:
    """Evaluate a condition group."""
    if not group or not group.get("conditions"):
        return False
    
    logic = group.get("logic", "AND").upper()
    conditions = group.get("conditions", [])
    
    results = []
    for cond in conditions:
        result = evaluate_single_condition(cond, indicators, current_price)
        results.append(result)
    
    if logic == "AND":
        return all(results)
    else:  # OR
        return any(results)


def evaluate_single_condition(cond: Dict[str, Any], indicators: Dict[str, float], current_price: float) -> bool:
    """Evaluate a single condition."""
    if not cond or not isinstance(cond, dict):
        return False
    
    indicator = cond.get("indicator", "").upper()
    operator = cond.get("operator", "")
    value = cond.get("value")
    
    if indicator == "RSI":
        rsi = indicators.get("rsi", 50)
        threshold = float(value) if value else 50
        return check_rsi_condition(rsi, operator, threshold)
    
    elif indicator == "SMA":
        period = cond.get("period", 20)
        sma_key = f"sma_{period}"
        sma_value = indicators.get(sma_key, current_price)
        return check_sma_condition(sma_value, current_price, operator)
    
    elif indicator == "EMA":
        period = cond.get("period", 12)
        ema_key = f"ema_{period}"
        ema_value = indicators.get(ema_key, current_price)
        return check_sma_condition(ema_value, current_price, operator)
    
    elif indicator == "MACD":
        macd = indicators.get("macd", 0)
        threshold = float(value) if value else 0
        return check_macd_condition(macd, 0, operator, threshold)
    
    return False


class PaperTradingService:
    """Paper trading execution service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_data_cache: Dict[str, SimulatedMarketData] = {}
        self.indicator_calculator = IndicatorCalculator()
    
    def get_market_data(self, symbol: str, base_price: float = 100.0) -> SimulatedMarketData:
        """Get or create simulated market data for symbol."""
        if symbol not in self.market_data_cache:
            self.market_data_cache[symbol] = SimulatedMarketData(symbol, base_price)
        return self.market_data_cache[symbol]
    
    async def start_paper_trading(self, strategy_id: UUID, user_id: UUID, capital: float = 100000.0) -> UserStrategyInstance:
        """Start a new paper trading instance for a strategy."""
        instance = UserStrategyInstance(
            id=uuid4(),
            user_id=user_id,
            strategy_id=strategy_id,
            name=f"Paper Trading - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            capital=capital,
            allocated_capital=capital,
            status="running",
            mode="paper",
            started_at=datetime.now(timezone.utc),
        )
        
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        
        logger.info(f"Started paper trading instance {instance.id} for strategy {strategy_id}")
        return instance
    
    async def check_signals_and_trade(self, instance: UserStrategyInstance, strategy_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check strategy conditions and generate trade signals."""
        symbol = strategy_params.get("symbol", "NIFTY")
        position_type = strategy_params.get("position", "BUY")
        entry_conditions = strategy_params.get("entry_conditions", [])
        exit_conditions = strategy_params.get("exit_conditions", [])
        
        if not entry_conditions:
            return None
        
        market = self.get_market_data(symbol, 100.0 + random.uniform(-10, 10))
        
        historical_bars = market.get_historical_bars(200)
        current_bar = market.get_current_ohlcv()
        all_bars = historical_bars + [current_bar]
        
        indicators = self.indicator_calculator.calculate_all(all_bars, {"rsi": 14, "sma": 20, "ema": 12})
        
        current_indicators = {}
        for key, values in indicators.items():
            if isinstance(values, list) and len(values) > 0:
                current_indicators[key] = values[-1]
            else:
                current_indicators[key] = values
        
        entry_signal = False
        if isinstance(entry_conditions, list):
            for group in entry_conditions:
                if evaluate_condition_group(group, current_indicators, current_bar.close):
                    entry_signal = True
                    break
        
        has_position = await self._has_open_position(instance.id)
        
        if not has_position and entry_signal:
            stoploss = strategy_params.get("stoploss_pct", 2.0)
            target = strategy_params.get("target_pct", 5.0)
            
            return {
                "action": "BUY" if position_type == "BUY" else "SELL",
                "symbol": symbol,
                "price": current_bar.close,
                "quantity": self._calculate_quantity(instance.allocated_capital, current_bar.close),
                "stoploss": current_bar.close * (1 - stoploss / 100),
                "target": current_bar.close * (1 + target / 100),
                "signal": "entry",
                "reason": "Entry conditions met"
            }
        
        if has_position:
            position = await self._get_open_position(instance.id)
            if position:
                exit_signal = False
                if isinstance(exit_conditions, list):
                    for group in exit_conditions:
                        if evaluate_condition_group(group, current_indicators, current_bar.close):
                            exit_signal = True
                            break
                
                if exit_signal:
                    return {
                        "action": "SELL" if position.side == "BUY" else "BUY",
                        "symbol": symbol,
                        "price": current_bar.close,
                        "quantity": position.quantity,
                        "signal": "exit",
                        "reason": "Exit conditions met",
                        "position_id": position.id
                    }
                
                sl_hit = current_bar.close <= position.entry_price * (1 - strategy_params.get("stoploss_pct", 2.0) / 100)
                tgt_hit = current_bar.close >= position.entry_price * (1 + strategy_params.get("target_pct", 5.0) / 100)
                
                if sl_hit or tgt_hit:
                    return {
                        "action": "SELL" if position.side == "BUY" else "BUY",
                        "symbol": symbol,
                        "price": current_bar.close,
                        "quantity": position.quantity,
                        "signal": "stoploss" if sl_hit else "target",
                        "reason": "Stoploss hit" if sl_hit else "Target hit",
                        "position_id": position.id
                    }
        
        return None
    
    async def execute_trade(self, instance_id: UUID, user_id: UUID, trade_signal: Dict[str, Any]) -> InstanceTrade:
        """Execute a simulated trade."""
        trade = InstanceTrade(
            id=uuid4(),
            instance_id=instance_id,
            user_id=user_id,
            symbol=trade_signal["symbol"],
            exchange="NSE",
            side=trade_signal["action"],
            quantity=trade_signal["quantity"],
            entry_price=trade_signal["price"],
            commission=trade_signal["price"] * trade_signal["quantity"] * 0.001,
            slippage=trade_signal["price"] * trade_signal["quantity"] * 0.0001,
            entry_time=datetime.now(timezone.utc),
            entry_signal=trade_signal.get("reason", ""),
        )
        
        if trade_signal.get("position_id"):
            position = await self._get_position(trade_signal["position_id"])
            if position:
                position.exit_price = trade_signal["price"]
                position.exit_time = datetime.now(timezone.utc)
                position.is_open = False
                position.unrealized_pnl = 0
                
                pnl = (trade_signal["price"] - position.entry_price) * position.quantity
                if position.side == "SELL":
                    pnl = -pnl
                trade.pnl = pnl - trade.commission - trade.slippage
                trade.exit_reason = trade_signal.get("signal", "manual")
                
                await self._update_instance_stats(instance_id, trade.pnl)
        
        self.db.add(trade)
        
        if not trade_signal.get("position_id"):
            position = InstancePosition(
                id=uuid4(),
                instance_id=instance_id,
                user_id=user_id,
                symbol=trade_signal["symbol"],
                exchange="NSE",
                side=trade_signal["action"],
                quantity=trade_signal["quantity"],
                entry_price=trade_signal["price"],
                current_price=trade_signal["price"],
                unrealized_pnl=0,
                is_open=True,
                opened_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.db.add(position)
            await self._update_allocated_capital(instance_id, -trade_signal["price"] * trade_signal["quantity"])
        
        await self.db.commit()
        await self.db.refresh(trade)
        
        logger.info(f"Executed paper trade: {trade.side} {trade.quantity} {trade.symbol} @ {trade.entry_price}")
        return trade
    
    def _calculate_quantity(self, capital: float, price: float) -> int:
        """Calculate position size based on capital."""
        allocation = capital * 0.1
        return max(1, int(allocation / price / 100) * 100)
    
    async def _has_open_position(self, instance_id: UUID) -> bool:
        """Check if instance has open position."""
        result = await self.db.execute(
            select(InstancePosition).where(
                and_(
                    InstancePosition.instance_id == instance_id,
                    InstancePosition.is_open == True
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def _get_open_position(self, instance_id: UUID) -> Optional[InstancePosition]:
        """Get open position for instance."""
        result = await self.db.execute(
            select(InstancePosition).where(
                and_(
                    InstancePosition.instance_id == instance_id,
                    InstancePosition.is_open == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_position(self, position_id: UUID) -> Optional[InstancePosition]:
        """Get position by ID."""
        result = await self.db.execute(
            select(InstancePosition).where(InstancePosition.id == position_id)
        )
        return result.scalar_one_or_none()
    
    async def _update_instance_stats(self, instance_id: UUID, pnl: float):
        """Update instance statistics."""
        result = await self.db.execute(
            select(UserStrategyInstance).where(UserStrategyInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        if instance:
            instance.current_pnl = (instance.current_pnl or 0) + pnl
            instance.realized_pnl = (instance.realized_pnl or 0) + pnl
            instance.trades_count = (instance.trades_count or 0) + 1
            if pnl > 0:
                instance.winning_trades = (instance.winning_trades or 0) + 1
            else:
                instance.losing_trades = (instance.losing_trades or 0) + 1
    
    async def _update_allocated_capital(self, instance_id: UUID, amount: float):
        """Update allocated capital."""
        result = await self.db.execute(
            select(UserStrategyInstance).where(UserStrategyInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        if instance:
            instance.allocated_capital += amount
    
    async def update_positions(self, instance_id: UUID):
        """Update unrealized P&L for all positions."""
        result = await self.db.execute(
            select(InstancePosition).where(
                and_(
                    InstancePosition.instance_id == instance_id,
                    InstancePosition.is_open == True
                )
            )
        )
        positions = result.scalars().all()
        
        market = None
        for position in positions:
            if not market or market.symbol != position.symbol:
                market = self.get_market_data(position.symbol)
            
            current_bar = market.get_current_ohlcv()
            position.current_price = current_bar.close
            position.updated_at = datetime.now(timezone.utc)
            
            pnl = (current_bar.close - position.entry_price) * position.quantity
            if position.side == "SELL":
                pnl = -pnl
            position.unrealized_pnl = pnl
        
        await self.db.commit()
    
    async def pause_instance(self, instance_id: UUID):
        """Pause paper trading instance."""
        result = await self.db.execute(
            select(UserStrategyInstance).where(UserStrategyInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        if instance:
            instance.status = "paused"
            instance.paused_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.info(f"Paused paper trading instance {instance_id}")
    
    async def resume_instance(self, instance_id: UUID):
        """Resume paper trading instance."""
        result = await self.db.execute(
            select(UserStrategyInstance).where(UserStrategyInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        if instance:
            instance.status = "running"
            instance.paused_at = None
            await self.db.commit()
            logger.info(f"Resumed paper trading instance {instance_id}")
    
    async def stop_instance(self, instance_id: UUID):
        """Stop paper trading and close all positions."""
        result = await self.db.execute(
            select(UserStrategyInstance).where(UserStrategyInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        if instance:
            instance.status = "stopped"
            instance.stopped_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.info(f"Stopped paper trading instance {instance_id}")


async def run_paper_trading_tick(instance_id: UUID, db: AsyncSession):
    """Run a single paper trading tick for an instance."""
    service = PaperTradingService(db)
    
    result = await db.execute(
        select(UserStrategyInstance, Strategy).join(
            Strategy, UserStrategyInstance.strategy_id == Strategy.id
        ).where(UserStrategyInstance.id == instance_id)
    )
    row = result.one_or_none()
    
    if not row:
        return
    
    instance, strategy = row
    
    if instance.status != "running":
        return
    
    signal = await service.check_signals_and_trade(instance, strategy.parameters or {})
    
    if signal:
        await service.execute_trade(instance.id, instance.user_id, signal)
    
    await service.update_positions(instance.id)
