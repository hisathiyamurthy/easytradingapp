"""Historical Backtesting Engine.

Features:
- Historical data replay
- Strategy execution simulation
- Performance metrics calculation
- Transaction cost modeling
- Equity curve generation
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable
from uuid import UUID
import json

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtest configuration."""
    initial_capital: float = 100000.0
    start_date: datetime = None
    end_date: datetime = None
    timeframe: str = "1d"  # 1m, 5m, 15m, 1h, 1d
    symbol: str = ""
    exchange: str = "NSE"
    
    # Costs
    commission_rate: float = 0.001  # 0.1%
    slippage_bps: float = 1.0  # 1 basis point
    stamp_duty: float = 0.0  # Indian markets
    exchange_fee: float = 0.0
    
    # Execution
    maker_fee: float = 0.0
    taker_fee: float = 0.0
    
    # Position
    default_quantity: int = 1
    
    def __post_init__(self):
        if self.start_date is None:
            self.start_date = datetime.utcnow() - timedelta(days=365)
        if self.end_date is None:
            self.end_date = datetime.utcnow()


@dataclass
class BacktestSignal:
    """Trading signal generated during backtest."""
    timestamp: datetime
    symbol: str
    signal_type: str  # buy, sell, close
    price: float
    quantity: int
    reason: str = ""
    confidence: float = 1.0


@dataclass
class BacktestTrade:
    """Executed trade in backtest."""
    entry_timestamp: datetime
    exit_timestamp: Optional[datetime]
    symbol: str
    side: str  # long, short
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    pnl: float = 0
    pnl_percent: float = 0
    commission: float = 0
    holding_period: int = 0  # bars


@dataclass
class BacktestPosition:
    """Current position during backtest."""
    symbol: str
    side: str  # long, short, flat
    quantity: int
    entry_price: float
    current_price: float = 0
    unrealized_pnl: float = 0


@dataclass
class BacktestMetrics:
    """Backtest performance metrics."""
    # Returns
    total_return: float = 0
    total_return_pct: float = 0
    annualized_return: float = 0
    
    # Trades
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0
    
    # Profit/Loss
    gross_profit: float = 0
    gross_loss: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    largest_win: float = 0
    largest_loss: float = 0
    avg_trade_pnl: float = 0
    
    # Risk
    max_drawdown: float = 0
    max_drawdown_pct: float = 0
    sharpe_ratio: float = 0
    sortino_ratio: float = 0
    calmar_ratio: float = 0
    
    # Other
    profit_factor: float = 0
    avg_holding_period: int = 0
    total_commission: float = 0
    
    # Trade analysis
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)
    drawdown_curve: list = field(default_factory=list)


class BacktestEngine:
    """Historical backtesting engine."""

    def __init__(
        self,
        config: BacktestConfig,
        strategy_executor: Callable,
        data_provider: Optional[Callable] = None,
    ):
        self.config = config
        self.strategy_executor = strategy_executor
        self.data_provider = data_provider
        
        # State
        self.position: Optional[BacktestPosition] = None
        self.trades: list[BacktestTrade] = []
        self.signals: list[BacktestSignal] = []
        
        # Capital tracking
        self.initial_capital = config.initial_capital
        self.current_capital = config.initial_capital
        self.equity_curve: list[float] = []
        self.peak_capital = config.initial_capital
        self.max_drawdown = 0
        
        # Metrics
        self.winning_trades: list[float] = []
        self.losing_trades: list[float] = []
        
        # Bar counter
        self.bar_count = 0
        self._running = False

    async def run(self) -> BacktestMetrics:
        """Run backtest."""
        self._running = True
        logger.info(
            f"Starting backtest: {self.config.symbol} "
            f"{self.config.start_date} to {self.config.end_date}"
        )

        # Load historical data
        data = await self._load_data()
        
        if not data:
            logger.error("No historical data available")
            return BacktestMetrics()

        # Run backtest
        for bar in data:
            if not self._running:
                break
            
            await self._process_bar(bar)

        # Close any open position
        if self.position and self.position.quantity > 0:
            await self._close_position(
                bar['timestamp'],
                bar['close'],
                "End of backtest",
            )

        # Calculate metrics
        metrics = self._calculate_metrics()
        
        logger.info(
            f"Backtest completed: {metrics.total_trades} trades, "
            f"Return: {metrics.total_return_pct:.2f}%, "
            f"Win Rate: {metrics.win_rate:.2f}%"
        )

        return metrics

    async def _load_data(self) -> list[dict]:
        """Load historical data."""
        if self.data_provider:
            return await self.data_provider(
                symbol=self.config.symbol,
                exchange=self.config.exchange,
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                timeframe=self.config.timeframe,
            )
        
        # Return empty if no data provider
        return []

    async def _process_bar(self, bar: dict):
        """Process a single bar of data."""
        self.bar_count += 1
        
        # Update position P&L
        if self.position and self.position.quantity > 0:
            self.position.current_price = bar['close']
            self.position.unrealized_pnl = (
                (bar['close'] - self.position.entry_price)
                * self.position.quantity
                * (1 if self.position.side == "long" else -1)
            )
        
        # Update equity
        self._update_equity(bar['close'])
        
        # Get signal from strategy
        signal = await self.strategy_executor(bar, self.position)
        
        if signal:
            await self._handle_signal(signal, bar)

    async def _handle_signal(self, signal: BacktestSignal, bar: dict):
        """Handle trading signal."""
        self.signals.append(signal)
        
        # Apply slippage to signal price
        fill_price = self._apply_slippage(signal.price, signal.signal_type)
        
        if signal.signal_type == "buy":
            await self._open_position(signal, fill_price)
        elif signal.signal_type == "sell":
            await self._close_position(
                bar['timestamp'],
                fill_price,
                signal.reason,
            )

    async def _open_position(self, signal: BacktestSignal, price: float):
        """Open a new position."""
        # Calculate position size
        quantity = signal.quantity or self.config.default_quantity
        position_value = price * quantity
        commission = self._calculate_commission(position_value)
        required_capital = position_value + commission
        
        # Check if we have enough capital
        if required_capital > self.current_capital:
            logger.warning(
                f"Insufficient capital to open position: "
                f"required {required_capital}, available {self.current_capital}"
            )
            return
        
        # Deduct capital
        self.current_capital -= commission
        
        # Create position
        self.position = BacktestPosition(
            symbol=signal.symbol,
            side="long",
            quantity=quantity,
            entry_price=price,
            current_price=price,
        )

    async def _close_position(
        self,
        timestamp: datetime,
        price: float,
        reason: str,
    ):
        """Close existing position."""
        if not self.position or self.position.quantity == 0:
            return
        
        # Calculate P&L
        quantity = self.position.quantity
        position_value = price * quantity
        commission = self._calculate_commission(position_value)
        
        pnl = (price - self.position.entry_price) * quantity
        pnl_percent = ((price - self.position.entry_price) 
                       / self.position.entry_price * 100)
        
        # Record trade
        trade = BacktestTrade(
            entry_timestamp=self.signals[-1].timestamp if self.signals else timestamp,
            exit_timestamp=timestamp,
            symbol=self.position.symbol,
            side=self.position.side,
            entry_price=self.position.entry_price,
            exit_price=price,
            quantity=quantity,
            pnl=pnl - commission,
            pnl_percent=pnl_percent,
            commission=commission,
            holding_period=self.bar_count,
        )
        
        self.trades.append(trade)
        
        # Update capital
        self.current_capital += position_value - commission
        
        # Track win/loss
        if pnl > 0:
            self.winning_trades.append(pnl)
        else:
            self.losing_trades.append(abs(pnl))
        
        # Clear position
        self.position = None

    def _apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to price."""
        slippage = price * (self.config.slippage_bps / 10000)
        
        if side == "buy":
            return price + slippage
        else:
            return price - slippage

    def _calculate_commission(self, position_value: float) -> float:
        """Calculate commission for trade."""
        commission = position_value * self.config.commission_rate
        commission += self.config.exchange_fee
        return commission

    def _update_equity(self, current_price: float):
        """Update equity curve and drawdown."""
        # Calculate current equity
        position_value = 0
        if self.position and self.position.quantity > 0:
            position_value = self.position.unrealized_pnl
        
        equity = self.current_capital + position_value
        self.equity_curve.append(equity)
        
        # Update peak and drawdown
        if equity > self.peak_capital:
            self.peak_capital = equity
        
        drawdown = self.peak_capital - equity
        drawdown_pct = (drawdown / self.peak_capital * 100) if self.peak_capital > 0 else 0
        
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

    def _calculate_metrics(self) -> BacktestMetrics:
        """Calculate performance metrics."""
        metrics = BacktestMetrics()
        
        # Basic info
        metrics.total_trades = len(self.trades)
        
        if metrics.total_trades == 0:
            return metrics
        
        # Returns
        final_equity = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        metrics.total_return = final_equity - self.initial_capital
        metrics.total_return_pct = (
            (final_equity / self.initial_capital - 1) * 100
        )
        
        # Annualized return
        days = (self.config.end_date - self.config.start_date).days
        if days > 0:
            years = days / 365
            if years > 0:
                metrics.annualized_return = (
                    ((final_equity / self.initial_capital) ** (1/years) - 1) * 100
                )
        
        # Win/Loss
        metrics.winning_trades = len(self.winning_trades)
        metrics.losing_trades = len(self.losing_trades)
        metrics.win_rate = (
            (metrics.winning_trades / metrics.total_trades * 100)
            if metrics.total_trades > 0 else 0
        )
        
        # P&L
        metrics.gross_profit = sum(self.winning_trades)
        metrics.gross_loss = sum(self.losing_trades)
        
        if metrics.winning_trades > 0:
            metrics.avg_win = metrics.gross_profit / metrics.winning_trades
            metrics.largest_win = max(self.winning_trades)
        
        if metrics.losing_trades > 0:
            metrics.avg_loss = metrics.gross_loss / metrics.losing_trades
            metrics.largest_loss = max(self.losing_trades)
        
        metrics.avg_trade_pnl = (
            (metrics.gross_profit - metrics.gross_loss) / metrics.total_trades
        )
        
        # Profit factor
        metrics.profit_factor = (
            metrics.gross_profit / metrics.gross_loss
            if metrics.gross_loss > 0 else 0
        )
        
        # Drawdown
        metrics.max_drawdown = self.max_drawdown
        metrics.max_drawdown_pct = (
            (self.max_drawdown / self.peak_capital * 100)
            if self.peak_capital > 0 else 0
        )
        
        # Risk metrics
        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            
            # Sharpe Ratio (assuming 0% risk-free rate)
            if np.std(returns) > 0:
                metrics.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
            
            # Sortino Ratio (downside deviation)
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0 and np.std(downside_returns) > 0:
                metrics.sortino_ratio = (
                    np.mean(returns) / np.std(downside_returns) * np.sqrt(252)
                )
        
        # Calmar Ratio
        if metrics.max_drawdown > 0:
            metrics.calmar_ratio = metrics.annualized_return / metrics.max_drawdown_pct
        
        # Holding period
        if metrics.total_trades > 0:
            metrics.avg_holding_period = sum(
                t.holding_period for t in self.trades
            ) / metrics.total_trades
        
        # Commission
        metrics.total_commission = sum(t.commission for t in self.trades)
        
        # Curves
        metrics.equity_curve = [
            {"timestamp": i, "equity": e}
            for i, e in enumerate(self.equity_curve)
        ]
        
        metrics.trades = [
            {
                "entry_timestamp": t.entry_timestamp.isoformat(),
                "exit_timestamp": t.exit_timestamp.isoformat() if t.exit_timestamp else None,
                "symbol": t.symbol,
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "pnl": t.pnl,
                "pnl_percent": t.pnl_percent,
                "commission": t.commission,
                "holding_period": t.holding_period,
            }
            for t in self.trades
        ]

        return metrics

    def stop(self):
        """Stop backtest."""
        self._running = False


class MultiStrategyBacktester:
    """Backtest multiple strategies simultaneously."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.results: dict[str, BacktestMetrics] = {}

    async def run_comparison(
        self,
        strategies: dict[str, Callable],
        data: list[dict],
    ) -> dict[str, BacktestMetrics]:
        """Run backtest for multiple strategies."""
        results = {}
        
        for name, strategy in strategies.items():
            logger.info(f"Backtesting strategy: {name}")
            
            engine = BacktestEngine(
                config=self.config,
                strategy_executor=strategy,
            )
            
            # Inject data directly
            engine._load_data = lambda **kwargs: data
            
            result = await engine.run()
            results[name] = result
        
        self.results = results
        return results


class WalkForwardBacktester:
    """Walk-forward analysis for robust backtesting."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.results: list[BacktestMetrics] = []

    async def run(
        self,
        strategy_executor: Callable,
        train_window_days: int = 252,
        test_window_days: int = 63,
        step_days: int = 21,
    ) -> list[BacktestMetrics]:
        """Run walk-forward analysis."""
        results = []
        
        current_date = self.config.start_date + timedelta(days=train_window_days)
        
        while current_date < self.config.end_date:
            # Define train and test periods
            train_start = current_date - timedelta(days=train_window_days)
            test_end = min(
                current_date + timedelta(days=test_window_days),
                self.config.end_date
            )
            
            # Configure backtest
            config = BacktestConfig(
                initial_capital=self.config.initial_capital,
                start_date=train_start,
                end_date=test_end,
                timeframe=self.config.timeframe,
                symbol=self.config.symbol,
                exchange=self.config.exchange,
                commission_rate=self.config.commission_rate,
                slippage_bps=self.config.slippage_bps,
            )
            
            # Run backtest
            engine = BacktestEngine(
                config=config,
                strategy_executor=strategy_executor,
            )
            
            metrics = await engine.run()
            results.append(metrics)
            
            logger.info(
                f"Walk-forward: {train_start.date()} to {test_end.date()} - "
                f"Return: {metrics.total_return_pct:.2f}%"
            )
            
            # Move to next window
            current_date += timedelta(days=step_days)
        
        self.results = results
        return results


class MultiAssetBacktestEngine:
    """Multi-asset backtesting engine.
    
    Supports testing strategies across multiple symbols simultaneously.
    """
    
    def __init__(
        self,
        config: BacktestConfig,
        symbols: list[str],
        strategy_executor: Callable,
        data_provider: Optional[Callable] = None,
    ):
        self.config = config
        self.symbols = symbols
        self.strategy_executor = strategy_executor
        self.data_provider = data_provider
        
        self.engines: dict[str, BacktestEngine] = {}
        self.results: dict[str, BacktestMetrics] = {}
        
        # Portfolio-level tracking
        self.initial_capital = config.initial_capital
        self.portfolio_value = config.initial_capital
        self.equity_curve: list[float] = []
    
    async def run(self) -> dict:
        """Run multi-asset backtest."""
        logger.info(f"Starting multi-asset backtest for symbols: {self.symbols}")
        
        # Create engines for each symbol
        for symbol in self.symbols:
            config = BacktestConfig(
                initial_capital=self.initial_capital / len(self.symbols),
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                timeframe=self.config.timeframe,
                symbol=symbol,
                exchange=self.config.exchange,
                commission_rate=self.config.commission_rate,
                slippage_bps=self.config.slippage_bps,
                stamp_duty=self.config.stamp_duty,
                exchange_fee=self.config.exchange_fee,
                default_quantity=self.config.default_quantity,
            )
            
            engine = BacktestEngine(
                config=config,
                strategy_executor=self.strategy_executor,
                data_provider=self._create_data_provider(symbol),
            )
            self.engines[symbol] = engine
        
        # Run all engines
        for symbol, engine in self.engines.items():
            logger.info(f"Running backtest for {symbol}")
            metrics = await engine.run()
            self.results[symbol] = metrics
        
        # Calculate portfolio-level metrics
        portfolio_metrics = self._calculate_portfolio_metrics()
        
        return {
            "individual_results": {
                symbol: self._metrics_to_dict(metrics) 
                for symbol, metrics in self.results.items()
            },
            "portfolio_metrics": portfolio_metrics,
        }
    
    def _create_data_provider(self, symbol: str) -> Callable:
        """Create a symbol-specific data provider."""
        if not self.data_provider:
            return lambda **kwargs: []
        
        async def provider(**kwargs):
            return await self.data_provider(symbol=symbol, **kwargs)
        
        return provider
    
    def _calculate_portfolio_metrics(self) -> dict:
        """Calculate portfolio-level metrics."""
        # Aggregate trades
        all_trades = []
        total_commission = 0
        winning_trades = 0
        losing_trades = 0
        gross_profit = 0
        gross_loss = 0
        
        for metrics in self.results.values():
            all_trades.extend(metrics.trades)
            total_commission += metrics.total_commission
            winning_trades += metrics.winning_trades
            losing_trades += metrics.losing_trades
            gross_profit += metrics.gross_profit
            gross_loss += metrics.gross_loss
        
        total_trades = winning_trades + losing_trades
        
        # Calculate portfolio returns
        final_value = sum(
            self.engines[s].equity_curve[-1] if self.engines[s].equity_curve else self.config.initial_capital
            for s in self.symbols
        )
        
        total_return = final_value - self.initial_capital
        total_return_pct = (total_return / self.initial_capital * 100) if self.initial_capital > 0 else 0
        
        # Calculate portfolio equity curve
        max_length = max(
            len(self.engines[s].equity_curve) 
            for s in self.symbols 
            if self.engines[s].equity_curve
        ) if self.engines else 0
        
        portfolio_equity = []
        for i in range(max_length):
            value = 0
            for s in self.symbols:
                if self.engines[s].equity_curve and i < len(self.engines[s].equity_curve):
                    value += self.engines[s].equity_curve[i]
                elif i == 0:
                    value += self.config.initial_capital / len(self.symbols)
            portfolio_equity.append(value)
        
        # Calculate max drawdown
        peak = portfolio_equity[0] if portfolio_equity else self.initial_capital
        max_dd = 0
        for value in portfolio_equity:
            if value > peak:
                peak = value
            dd = peak - value
            if dd > max_dd:
                max_dd = dd
        
        max_dd_pct = (max_dd / peak * 100) if peak > 0 else 0
        
        # Calculate Sharpe ratio
        sharpe = 0
        if len(portfolio_equity) > 1:
            import numpy as np
            returns = np.diff(portfolio_equity) / portfolio_equity[:-1]
            if np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else 0,
            "total_commission": total_commission,
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd_pct,
            "sharpe_ratio": sharpe,
            "final_portfolio_value": final_value,
            "equity_curve": [{"timestamp": i, "value": v} for i, v in enumerate(portfolio_equity)],
            "asset_count": len(self.symbols),
            "symbols": self.symbols,
        }
    
    def _metrics_to_dict(self, metrics: BacktestMetrics) -> dict:
        """Convert BacktestMetrics to dictionary."""
        return {
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades,
            "win_rate": metrics.win_rate,
            "total_return": metrics.total_return,
            "total_return_pct": metrics.total_return_pct,
            "annualized_return": metrics.annualized_return,
            "gross_profit": metrics.gross_profit,
            "gross_loss": metrics.gross_loss,
            "profit_factor": metrics.profit_factor,
            "max_drawdown": metrics.max_drawdown,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "sharpe_ratio": metrics.sharpe_ratio,
            "sortino_ratio": metrics.sortino_ratio,
            "calmar_ratio": metrics.calmar_ratio,
            "total_commission": metrics.total_commission,
        }


# Example strategy executor
async def example_ema_crossover_strategy(
    bar: dict,
    position: Optional[BacktestPosition],
    fast_period: int = 20,
    slow_period: int = 50,
) -> Optional[BacktestSignal]:
    """Example EMA crossover strategy."""
    # This would normally maintain EMA state
    # For demonstration, returning None
    return None


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Sample historical data
        async def mock_data_provider(**kwargs):
            import random
            data = []
            price = 18000
            
            for i in range(500):
                price = price * (1 + random.uniform(-0.02, 0.02))
                data.append({
                    'timestamp': datetime.utcnow() - timedelta(days=500-i),
                    'open': price * 0.99,
                    'high': price * 1.01,
                    'low': price * 0.98,
                    'close': price,
                    'volume': random.randint(1000000, 5000000),
                })
            
            return data

        # Configure backtest
        config = BacktestConfig(
            initial_capital=100000,
            start_date=datetime.utcnow() - timedelta(days=365),
            end_date=datetime.utcnow(),
            symbol="NIFTY",
            exchange="NSE",
            timeframe="1d",
            commission_rate=0.001,
            slippage_bps=1.0,
        )

        # Run backtest
        engine = BacktestEngine(
            config=config,
            strategy_executor=example_ema_crossover_strategy,
            data_provider=mock_data_provider,
        )

        metrics = await engine.run()

        print("\n=== Backtest Results ===")
        print(f"Total Trades: {metrics.total_trades}")
        print(f"Win Rate: {metrics.win_rate:.2f}%")
        print(f"Total Return: {metrics.total_return_pct:.2f}%")
        print(f"Max Drawdown: {metrics.max_drawdown_pct:.2f}%")
        print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"Profit Factor: {metrics.profit_factor:.2f}")

    asyncio.run(main())
