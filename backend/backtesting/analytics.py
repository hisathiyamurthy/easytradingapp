"""Backtest Analytics Module.

Generates comprehensive analytics for backtest results:
- Profit analysis
- Drawdown analysis
- Win rate metrics
- Profit factor
- Trade history analysis
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ProfitAnalytics:
    """Profit analysis metrics."""
    total_profit: float = 0
    total_loss: float = 0
    net_profit: float = 0
    profit_margin: float = 0
    avg_profit_per_trade: float = 0
    avg_loss_per_trade: float = 0
    expectancy: float = 0  # Expected value per trade
    
    # Monthly breakdown
    monthly_profits: dict = field(default_factory=dict)
    
    # Best/worst
    best_trade: float = 0
    worst_trade: float = 0
    best_day: float = 0
    worst_day: float = 0


@dataclass
class DrawdownAnalytics:
    """Drawdown analysis metrics."""
    max_drawdown: float = 0
    max_drawdown_pct: float = 0
    max_drawdown_duration_days: int = 0
    current_drawdown: float = 0
    current_drawdown_pct: float = 0
    
    # Recovery
    avg_recovery_time_days: float = 0
    longest_recovery_days: int = 0
    
    # Drawdown periods
    drawdown_periods: list = field(default_factory=list)


@dataclass
class WinRateAnalytics:
    """Win rate and trade distribution metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    
    win_rate: float = 0
    loss_rate: float = 0
    breakeven_rate: float = 0
    
    # Consecutive
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    current_streak: int = 0
    current_streak_type: str = ""  # win or loss
    
    # Distribution
    win_distribution: dict = field(default_factory=dict)
    loss_distribution: dict = field(default_factory=dict)


@dataclass
class TradeHistoryAnalytics:
    """Trade history analysis."""
    trades: list = field(default_factory=list)
    
    # Time analysis
    avg_trade_duration_hours: float = 0
    longest_trade_hours: float = 0
    shortest_trade_hours: float = 0
    
    # Entry/exit
    best_entry: dict = field(default_factory=dict)
    worst_entry: dict = field(default_factory=dict)
    best_exit: dict = field(default_factory=dict)
    worst_exit: dict = field(default_factory=dict)
    
    # By day
    trades_by_day: dict = field(default_factory=dict)
    trades_by_hour: dict = field(default_factory=dict)
    
    # Symbol analysis
    trades_by_symbol: dict = field(default_factory=dict)


@dataclass
class RiskAnalytics:
    """Risk-adjusted performance metrics."""
    sharpe_ratio: float = 0
    sortino_ratio: float = 0
    calmar_ratio: float = 0
    omega_ratio: float = 0
    
    # Volatility
    volatility_annualized: float = 0
    downside_volatility: float = 0
    
    # VaR
    value_at_risk_95: float = 0
    value_at_risk_99: float = 0
    
    # Risk of ruin
    probability_of_ruin: float = 0


@dataclass
class BacktestAnalytics:
    """Complete backtest analytics."""
    # Summary
    initial_capital: float = 0
    final_capital: float = 0
    total_return: float = 0
    total_return_pct: float = 0
    annualized_return: float = 0
    
    # Components
    profit: Optional[ProfitAnalytics] = None
    drawdown: Optional[DrawdownAnalytics] = None
    win_rate: Optional[WinRateAnalytics] = None
    risk: Optional[RiskAnalytics] = None
    trade_history: Optional[TradeHistoryAnalytics] = None
    
    # Additional
    execution_time_seconds: float = 0
    bars_processed: int = 0
    generated_at: datetime = field(default_factory=datetime.utcnow)


class BacktestAnalyticsGenerator:
    """Generate comprehensive analytics from backtest data."""

    def __init__(self):
        pass

    def generate(
        self,
        equity_curve: list[dict],
        trades: list[dict],
        config: dict,
    ) -> BacktestAnalytics:
        """Generate complete analytics from backtest results."""
        
        analytics = BacktestAnalytics(
            initial_capital=config.get('initial_capital', 100000),
            final_capital=equity_curve[-1]['equity'] if equity_curve else config.get('initial_capital', 100000),
        )

        # Calculate total return
        analytics.total_return = analytics.final_capital - analytics.initial_capital
        analytics.total_return_pct = (
            (analytics.final_capital / analytics.initial_capital - 1) * 100
            if analytics.initial_capital > 0 else 0
        )

        # Generate component analytics
        analytics.profit = self._analyze_profit(trades)
        analytics.drawdown = self._analyze_drawdown(equity_curve, config)
        analytics.win_rate = self._analyze_win_rate(trades)
        analytics.risk = self._analyze_risk(equity_curve, config)
        analytics.trade_history = self._analyze_trade_history(trades)

        return analytics

    def _analyze_profit(self, trades: list[dict]) -> ProfitAnalytics:
        """Analyze profit metrics."""
        if not trades:
            return ProfitAnalytics()

        profits = [t['pnl'] for t in trades if 'pnl' in t]
        
        if not profits:
            return ProfitAnalytics()

        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p < 0]

        analytics = ProfitAnalytics(
            total_profit=sum(winning) if winning else 0,
            total_loss=sum(losing) if losing else 0,
            net_profit=sum(profits),
            best_trade=max(winning) if winning else 0,
            worst_trade=min(losing) if losing else 0,
        )

        # Averages
        if winning:
            analytics.avg_profit_per_trade = sum(winning) / len(winning)
        if losing:
            analytics.avg_loss_per_trade = sum(losing) / len(losing)

        # Expectancy
        total_trades = len(trades)
        if total_trades > 0:
            analytics.expectancy = sum(profits) / total_trades

        # Profit margin
        if analytics.total_profit > 0:
            analytics.profit_margin = (
                (analytics.total_profit + analytics.total_loss) / analytics.total_profit * 100
                if analytics.total_profit > 0 else 0
            )

        return analytics

    def _analyze_drawdown(
        self,
        equity_curve: list[dict],
        config: dict,
    ) -> DrawdownAnalytics:
        """Analyze drawdown metrics."""
        if not equity_curve:
            return DrawdownAnalytics()

        equity_values = [e['equity'] for e in equity_curve]
        
        analytics = DrawdownAnalytics()
        
        peak = equity_values[0]
        peak_idx = 0
        
        in_drawdown = False
        drawdown_start = 0
        max_duration = 0
        current_duration = 0
        
        drawdown_periods = []
        
        for i, equity in enumerate(equity_values):
            # Update peak
            if equity > peak:
                peak = equity
                peak_idx = i
                
                if in_drawdown:
                    # End of drawdown period
                    duration = i - drawdown_start
                    drawdown_periods.append({
                        'start': drawdown_start,
                        'end': i,
                        'duration': duration,
                        'depth': analytics.max_drawdown,
                        'depth_pct': analytics.max_drawdown_pct,
                    })
                    in_drawdown = False
                    max_duration = max(max_duration, duration)
            else:
                # In drawdown
                in_drawdown = True
                if current_duration == 0:
                    drawdown_start = i
                current_duration += 1
                
                drawdown = peak - equity
                drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0
                
                if drawdown > analytics.max_drawdown:
                    analytics.max_drawdown = drawdown
                    analytics.max_drawdown_pct = drawdown_pct

        # Current drawdown
        current = equity_values[-1]
        analytics.current_drawdown = peak - current
        analytics.current_drawdown_pct = (
            (analytics.current_drawdown / peak * 100) if peak > 0 else 0
        )

        # Duration
        analytics.max_drawdown_duration_days = max_duration

        # Average recovery time
        if drawdown_periods:
            recoveries = [p['duration'] for p in drawdown_periods]
            analytics.avg_recovery_time_days = sum(recoveries) / len(recoveries)
            analytics.longest_recovery_days = max(recoveries)

        analytics.drawdown_periods = drawdown_periods

        return analytics

    def _analyze_win_rate(self, trades: list[dict]) -> WinRateAnalytics:
        """Analyze win rate metrics."""
        if not trades:
            return WinRateAnalytics()

        analytics = WinRateAnalytics(total_trades=len(trades))
        
        wins = []
        losses = []
        streaks = []
        current_streak = 0
        
        for trade in trades:
            pnl = trade.get('pnl', 0)
            
            if pnl > 0:
                analytics.winning_trades += 1
                wins.append(pnl)
                streak_type = 'win'
            elif pnl < 0:
                analytics.losing_trades += 1
                losses.append(abs(pnl))
                streak_type = 'loss'
            else:
                analytics.breakeven_trades += 1
                streak_type = 'breakeven'
            
            # Track streaks
            if streak_type == analytics.current_streak_type:
                current_streak += 1
            else:
                streaks.append(current_streak)
                current_streak = 1
                analytics.current_streak_type = streak_type
        
        streaks.append(current_streak)
        
        # Calculate rates
        if analytics.total_trades > 0:
            analytics.win_rate = (analytics.winning_trades / analytics.total_trades) * 100
            analytics.loss_rate = (analytics.losing_trades / analytics.total_trades) * 100
            analytics.breakeven_rate = (analytics.breakeven_trades / analytics.total_trades) * 100

        # Max streaks
        analytics.max_consecutive_wins = max([s for s in streaks if wins])
        analytics.max_consecutive_losses = max([s for s in streaks if losses])

        # Current streak
        analytics.current_streak = current_streak

        # Distribution
        if wins:
            analytics.win_distribution = {
                'min': min(wins),
                'max': max(wins),
                'avg': sum(wins) / len(wins),
                'median': sorted(wins)[len(wins) // 2],
            }
        
        if losses:
            analytics.loss_distribution = {
                'min': min(losses),
                'max': max(losses),
                'avg': sum(losses) / len(losses),
                'median': sorted(losses)[len(losses) // 2],
            }

        return analytics

    def _analyze_risk(
        self,
        equity_curve: list[dict],
        config: dict,
    ) -> RiskAnalytics:
        """Analyze risk-adjusted metrics."""
        if len(equity_curve) < 2:
            return RiskAnalytics()

        analytics = RiskAnalytics()
        
        # Calculate returns
        equity_values = [e['equity'] for e in equity_curve]
        returns = np.diff(equity_values) / equity_values[:-1]
        
        if len(returns) == 0:
            return analytics
        
        # Volatility (annualized)
        daily_vol = np.std(returns)
        analytics.volatility_annualized = daily_vol * np.sqrt(252) * 100
        
        # Downside volatility
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            analytics.downside_volatility = np.std(downside_returns) * np.sqrt(252) * 100
        
        # Sharpe Ratio
        if daily_vol > 0:
            analytics.sharpe_ratio = (np.mean(returns) / daily_vol) * np.sqrt(252)
        
        # Sortino Ratio
        if analytics.downside_volatility > 0:
            analytics.sortino_ratio = (np.mean(returns) / analytics.downside_volatility) * np.sqrt(252)
        
        # Calmar Ratio (using max drawdown)
        # Would need drawdown info, simplified here
        max_dd_pct = self._get_max_drawdown_pct(equity_curve)
        if max_dd_pct > 0:
            # Annualized return / max drawdown
            total_return = (equity_values[-1] / equity_values[0] - 1)
            days = len(equity_curve)
            years = days / 252
            annualized = ((1 + total_return) ** (1/years) - 1) if years > 0 else 0
            analytics.calmar_ratio = annualized / (max_dd_pct / 100)
        
        # Value at Risk
        analytics.value_at_risk_95 = np.percentile(returns, 5) * equity_values[-1]
        analytics.value_at_risk_99 = np.percentile(returns, 1) * equity_values[-1]
        
        # Omega Ratio
        threshold = 0
        if len(returns) > 0:
            gains = returns[returns > threshold]
            losses = abs(returns[returns < threshold])
            
            if len(losses) > 0 and np.sum(losses) > 0:
                analytics.omega_ratio = np.sum(gains) / np.sum(losses)

        return analytics

    def _analyze_trade_history(self, trades: list[dict]) -> TradeHistoryAnalytics:
        """Analyze trade history."""
        analytics = TradeHistoryAnalytics(trades=trades)
        
        if not trades:
            return analytics

        durations = []
        by_symbol = {}
        by_day = {}
        by_hour = {}
        
        for trade in trades:
            # Duration
            if 'entry_timestamp' in trade and 'exit_timestamp' in trade:
                entry = trade.get('entry_timestamp')
                exit = trade.get('exit_timestamp')
                
                if isinstance(entry, str):
                    entry = datetime.fromisoformat(entry)
                if isinstance(exit, str):
                    exit = datetime.fromisoformat(exit)
                
                if entry and exit:
                    duration = (exit - entry).total_seconds() / 3600
                    durations.append(duration)
                    
                    # By hour
                    hour = entry.hour
                    by_hour[hour] = by_hour.get(hour, 0) + 1
            
            # By day of week
            if 'entry_timestamp' in trade:
                entry = trade.get('entry_timestamp')
                if isinstance(entry, str):
                    entry = datetime.fromisoformat(entry)
                if entry:
                    day = entry.strftime('%A')
                    by_day[day] = by_day.get(day, 0) + 1
            
            # By symbol
            symbol = trade.get('symbol', 'UNKNOWN')
            by_symbol[symbol] = by_symbol.get(symbol, 0) + 1

        # Duration stats
        if durations:
            analytics.avg_trade_duration_hours = sum(durations) / len(durations)
            analytics.longest_trade_hours = max(durations)
            analytics.shortest_trade_hours = min(durations)

        analytics.trades_by_day = by_day
        analytics.trades_by_hour = by_hour
        analytics.trades_by_symbol = by_symbol

        # Best/worst entries
        if trades:
            sorted_by_entry = sorted(
                trades,
                key=lambda t: t.get('entry_price', 0)
            )
            analytics.worst_entry = sorted_by_entry[0] if sorted_by_entry else {}
            analytics.best_entry = sorted_by_entry[-1] if sorted_by_entry else {}
            
            sorted_by_exit = sorted(
                trades,
                key=lambda t: t.get('exit_price', 0),
                reverse=True
            )
            analytics.best_exit = sorted_by_exit[0] if sorted_by_exit else {}
            analytics.worst_exit = sorted_by_exit[-1] if sorted_by_exit else {}

        return analytics

    def _get_max_drawdown_pct(self, equity_curve: list[dict]) -> float:
        """Calculate max drawdown percentage."""
        if not equity_curve:
            return 0
        
        equity_values = [e['equity'] for e in equity_curve]
        peak = equity_values[0]
        max_dd = 0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            
            dd = (peak - equity) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        
        return max_dd

    def generate_report(self, analytics: BacktestAnalytics) -> str:
        """Generate human-readable analytics report."""
        lines = []
        
        lines.append("=" * 60)
        lines.append("BACKTEST ANALYTICS REPORT")
        lines.append("=" * 60)
        
        # Summary
        lines.append("\n📊 SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Initial Capital:    ${analytics.initial_capital:,.2f}")
        lines.append(f"Final Capital:     ${analytics.final_capital:,.2f}")
        lines.append(f"Total Return:      ${analytics.total_return:,.2f} ({analytics.total_return_pct:.2f}%)")
        
        if analytics.profit:
            lines.append("\n💰 PROFIT ANALYSIS")
            lines.append("-" * 40)
            lines.append(f"Total Profit:      ${analytics.profit.total_profit:,.2f}")
            lines.append(f"Total Loss:        ${analytics.profit.total_loss:,.2f}")
            lines.append(f"Net Profit:        ${analytics.profit.net_profit:,.2f}")
            lines.append(f"Expectancy:        ${analytics.profit.expectancy:.2f}/trade")
            lines.append(f"Best Trade:        ${analytics.profit.best_trade:,.2f}")
            lines.append(f"Worst Trade:       ${analytics.profit.worst_trade:,.2f}")
        
        if analytics.win_rate:
            lines.append("\n🎯 WIN RATE")
            lines.append("-" * 40)
            lines.append(f"Total Trades:      {analytics.win_rate.total_trades}")
            lines.append(f"Winning Trades:    {analytics.win_rate.winning_trades}")
            lines.append(f"Losing Trades:     {analytics.win_rate.losing_trades}")
            lines.append(f"Win Rate:          {analytics.win_rate.win_rate:.2f}%")
            lines.append(f"Max Consecutive Wins:  {analytics.win_rate.max_consecutive_wins}")
            lines.append(f"Max Consecutive Losses: {analytics.win_rate.max_consecutive_losses}")
        
        if analytics.drawdown:
            lines.append("\n📉 DRAWDOWN")
            lines.append("-" * 40)
            lines.append(f"Max Drawdown:      ${analytics.drawdown.max_drawdown:,.2f}")
            lines.append(f"Max Drawdown:       {analytics.drawdown.max_drawdown_pct:.2f}%")
            lines.append(f"Current Drawdown:   ${analytics.drawdown.current_drawdown:,.2f}")
            lines.append(f"Max Duration:       {analytics.drawdown.max_drawdown_duration_days} days")
        
        if analytics.risk:
            lines.append("\n⚠️ RISK METRICS")
            lines.append("-" * 40)
            lines.append(f"Sharpe Ratio:      {analytics.risk.sharpe_ratio:.2f}")
            lines.append(f"Sortino Ratio:     {analytics.risk.sortino_ratio:.2f}")
            lines.append(f"Calmar Ratio:      {analytics.risk.calmar_ratio:.2f}")
            lines.append(f"Volatility:        {analytics.risk.volatility_annualized:.2f}%")
            lines.append(f"VaR (95%):         ${analytics.risk.value_at_risk_95:,.2f}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    # Sample backtest data
    equity_curve = [
        {'timestamp': i, 'equity': 100000 + i * 100}
        for i in range(100)
    ]
    
    # Add some drawdown
    for i in range(50, 70):
        equity_curve[i]['equity'] = 100000 - 5000 + (i - 50) * 200
    
    trades = [
        {
            'entry_timestamp': '2024-01-01T10:00:00',
            'exit_timestamp': '2024-01-01T14:30:00',
            'symbol': 'NIFTY',
            'pnl': 500,
            'entry_price': 18000,
            'exit_price': 18100,
        },
        {
            'entry_timestamp': '2024-01-02T10:00:00',
            'exit_timestamp': '2024-01-02T15:00:00',
            'symbol': 'NIFTY',
            'pnl': -300,
            'entry_price': 18100,
            'exit_price': 18070,
        },
        {
            'entry_timestamp': '2024-01-03T10:00:00',
            'exit_timestamp': '2024-01-03T14:00:00',
            'symbol': 'BANKNIFTY',
            'pnl': 800,
            'entry_price': 42000,
            'exit_price': 42800,
        },
    ]
    
    config = {
        'initial_capital': 100000,
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
    }
    
    # Generate analytics
    generator = BacktestAnalyticsGenerator()
    analytics = generator.generate(equity_curve, trades, config)
    
    # Print report
    print(generator.generate_report(analytics))
