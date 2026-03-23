"""Performance reports service for daily and monthly reports."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Optional
import json


@dataclass
class TradeSummary:
    """Summary of a single trade."""
    trade_id: str
    symbol: str
    side: str
    quantity: int
    entry_price: float
    exit_price: float
    pnl: float
    pnl_percent: float
    entry_time: datetime
    exit_time: datetime


@dataclass
class DailyReport:
    """Daily performance report."""
    date: date
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percent: float
    best_trade: float
    worst_trade: float
    avg_win: float
    avg_loss: float
    largest_winner: str
    largest_loser: str
    trading_days: int
    symbols_traded: list[str]
    trade_details: list[TradeSummary] = field(default_factory=list)


@dataclass
class MonthlyReport:
    """Monthly performance report."""
    year: int
    month: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percent: float
    best_day: date
    best_day_pnl: float
    worst_day: date
    worst_day_pnl: float
    avg_daily_pnl: float
    trading_days: int
    daily_reports: list[DailyReport] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    """Performance metrics summary."""
    total_pnl: float
    total_return_percent: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_percent: float
    win_rate: float
    profit_factor: float
    avg_trade_duration: float
    total_trades: int
    trading_days: int


@dataclass
class YearlyReport:
    """Yearly performance report."""
    year: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percent: float
    best_month: tuple[int, float]
    worst_month: tuple[int, float]
    avg_monthly_pnl: float
    trading_days: int
    monthly_reports: list[MonthlyReport] = field(default_factory=list)


class ReportGenerator:
    """Generate performance reports."""

    def __init__(self, trades: list[dict] = None):
        self.trades = trades or []

    def generate_yearly_report(self, year: int = None) -> YearlyReport:
        """Generate yearly performance report."""
        now = datetime.now()
        year = year or now.year
        
        year_start = datetime(year, 1, 1)
        year_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        
        year_trades = [
            t for t in self.trades
            if year_start <= datetime.fromisoformat(t.get('exit_time', t.get('entry_time'))) <= year_end
        ]
        
        monthly_pnl = {}
        for t in year_trades:
            trade_date = datetime.fromisoformat(t.get('exit_time', t.get('entry_time')))
            month_key = trade_date.month
            monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + t.get('pnl', 0)
        
        winning = [t for t in year_trades if t.get('pnl', 0) > 0]
        losing = [t for t in year_trades if t.get('pnl', 0) < 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in year_trades)
        total_invested = sum(t.get('entry_price', 0) * t.get('quantity', 0) for t in year_trades)
        
        best_month = max(monthly_pnl.items(), key=lambda x: x[1]) if monthly_pnl else (1, 0)
        worst_month = min(monthly_pnl.items(), key=lambda x: x[1]) if monthly_pnl else (1, 0)
        
        monthly_reports = []
        for month in range(1, 13):
            if month in [m.month for m in [datetime.fromisoformat(t.get('exit_time', t.get('entry_time'))) for t in year_trades]]:
                monthly_reports.append(self.generate_monthly_report(year, month))
        
        unique_days = len(set(
            datetime.fromisoformat(t.get('entry_time')).date() 
            for t in year_trades
        ))
        
        return YearlyReport(
            year=year,
            total_trades=len(year_trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(year_trades) * 100 if year_trades else 0,
            total_pnl=total_pnl,
            total_pnl_percent=(total_pnl / total_invested * 100) if total_invested > 0 else 0,
            best_month=best_month,
            worst_month=worst_month,
            avg_monthly_pnl=sum(monthly_pnl.values()) / len(monthly_pnl) if monthly_pnl else 0,
            trading_days=unique_days,
            monthly_reports=monthly_reports,
        )

    def generate_daily_report(self, target_date: date = None) -> DailyReport:
        """Generate daily performance report."""
        target_date = target_date or date.today()
        
        day_trades = [
            t for t in self.trades
            if datetime.fromisoformat(t.get('exit_time', t.get('entry_time'))).date() == target_date
        ]
        
        if not day_trades:
            return DailyReport(
                date=target_date,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                total_pnl=0,
                total_pnl_percent=0,
                best_trade=0,
                worst_trade=0,
                avg_win=0,
                avg_loss=0,
                largest_winner="N/A",
                largest_loser="N/A",
                trading_days=0,
                symbols_traded=[],
            )
        
        winning = [t for t in day_trades if t.get('pnl', 0) > 0]
        losing = [t for t in day_trades if t.get('pnl', 0) < 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in day_trades)
        total_invested = sum(t.get('entry_price', 0) * t.get('quantity', 0) for t in day_trades)
        
        return DailyReport(
            date=target_date,
            total_trades=len(day_trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(day_trades) * 100 if day_trades else 0,
            total_pnl=total_pnl,
            total_pnl_percent=(total_pnl / total_invested * 100) if total_invested > 0 else 0,
            best_trade=max(t.get('pnl', 0) for t in day_trades),
            worst_trade=min(t.get('pnl', 0) for t in day_trades),
            avg_win=sum(t.get('pnl', 0) for t in winning) / len(winning) if winning else 0,
            avg_loss=sum(t.get('pnl', 0) for t in losing) / len(losing) if losing else 0,
            largest_winner=max(winning, key=lambda x: x.get('pnl', 0)).get('symbol', 'N/A') if winning else 'N/A',
            largest_loser=max(losing, key=lambda x: x.get('pnl', 0)).get('symbol', 'N/A') if losing else 'N/A',
            trading_days=1,
            symbols_traded=list(set(t.get('symbol', '') for t in day_trades)),
        )

    def generate_monthly_report(self, year: int = None, month: int = None) -> MonthlyReport:
        """Generate monthly performance report."""
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        month_trades = [
            t for t in self.trades
            if month_start <= datetime.fromisoformat(t.get('exit_time', t.get('entry_time'))) <= month_end
        ]
        
        daily_pnl = {}
        for t in month_trades:
            trade_date = datetime.fromisoformat(t.get('exit_time', t.get('entry_time'))).date()
            daily_pnl[trade_date] = daily_pnl.get(trade_date, 0) + t.get('pnl', 0)
        
        winning = [t for t in month_trades if t.get('pnl', 0) > 0]
        losing = [t for t in month_trades if t.get('pnl', 0) < 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in month_trades)
        total_invested = sum(t.get('entry_price', 0) * t.get('quantity', 0) for t in month_trades)
        
        best_day = max(daily_pnl.items(), key=lambda x: x[1]) if daily_pnl else (date.today(), 0)
        worst_day = min(daily_pnl.items(), key=lambda x: x[1]) if daily_pnl else (date.today(), 0)
        
        daily_reports = []
        for day in sorted(daily_pnl.keys()):
            daily_reports.append(self.generate_daily_report(day))
        
        return MonthlyReport(
            year=year,
            month=month,
            total_trades=len(month_trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(month_trades) * 100 if month_trades else 0,
            total_pnl=total_pnl,
            total_pnl_percent=(total_pnl / total_invested * 100) if total_invested > 0 else 0,
            best_day=best_day[0],
            best_day_pnl=best_day[1],
            worst_day=worst_day[0],
            worst_day_pnl=worst_day[1],
            avg_daily_pnl=sum(daily_pnl.values()) / len(daily_pnl) if daily_pnl else 0,
            trading_days=len(daily_pnl),
            daily_reports=daily_reports,
        )

    def generate_performance_metrics(self) -> PerformanceMetrics:
        """Generate overall performance metrics."""
        if not self.trades:
            return PerformanceMetrics(
                total_pnl=0,
                total_return_percent=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                max_drawdown=0,
                max_drawdown_percent=0,
                win_rate=0,
                profit_factor=0,
                avg_trade_duration=0,
                total_trades=0,
                trading_days=0,
            )
        
        winning = [t for t in self.trades if t.get('pnl', 0) > 0]
        losing = [t for t in self.trades if t.get('pnl', 0) < 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        total_invested = sum(t.get('entry_price', 0) * t.get('quantity', 0) for t in self.trades)
        
        trades_with_pnl = [t for t in self.trades if t.get('pnl', 0) != 0]
        
        pnl_values = [t.get('pnl', 0) for t in trades_with_pnl]
        avg_pnl = sum(pnl_values) / len(pnl_values) if pnl_values else 0
        std_pnl = (sum((p - avg_pnl) ** 2 for p in pnl_values) / len(pnl_values)) ** 0.5 if pnl_values else 1
        
        sharpe_ratio = (avg_pnl / std_pnl * (252 ** 0.5)) if std_pnl > 0 else 0
        
        downside = [p for p in pnl_values if p < 0]
        downside_std = (sum(p ** 2 for p in downside) / len(downside)) ** 0.5 if downside else 1
        sortino_ratio = (avg_pnl / downside_std * (252 ** 0.5)) if downside_std > 0 else 0
        
        equity_curve = []
        running_pnl = 0
        for t in sorted(self.trades, key=lambda x: x.get('entry_time', '')):
            running_pnl += t.get('pnl', 0)
            equity_curve.append(running_pnl)
        
        max_drawdown = 0
        peak = equity_curve[0] if equity_curve else 0
        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        total_wins = sum(t.get('pnl', 0) for t in winning)
        total_losses = abs(sum(t.get('pnl', 0) for t in losing))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        trade_durations = []
        for t in self.trades:
            entry = datetime.fromisoformat(t.get('entry_time'))
            exit_time = t.get('exit_time')
            if exit_time:
                exit_dt = datetime.fromisoformat(exit_time)
                duration = (exit_dt - entry).total_seconds() / 3600
                trade_durations.append(duration)
        
        avg_duration = sum(trade_durations) / len(trade_durations) if trade_durations else 0
        
        unique_days = len(set(
            datetime.fromisoformat(t.get('entry_time')).date() 
            for t in self.trades
        ))
        
        return PerformanceMetrics(
            total_pnl=total_pnl,
            total_return_percent=(total_pnl / total_invested * 100) if total_invested > 0 else 0,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_percent=(max_drawdown / total_invested * 100) if total_invested > 0 else 0,
            win_rate=len(winning) / len(self.trades) * 100 if self.trades else 0,
            profit_factor=profit_factor,
            avg_trade_duration=avg_duration,
            total_trades=len(self.trades),
            trading_days=unique_days,
        )

    def export_to_json(self) -> str:
        """Export all reports as JSON."""
        metrics = self.generate_performance_metrics()
        
        return json.dumps({
            "metrics": {
                "total_pnl": metrics.total_pnl,
                "total_return_percent": metrics.total_return_percent,
                "sharpe_ratio": metrics.sharpe_ratio,
                "sortino_ratio": metrics.sortino_ratio,
                "max_drawdown": metrics.max_drawdown,
                "max_drawdown_percent": metrics.max_drawdown_percent,
                "win_rate": metrics.win_rate,
                "profit_factor": metrics.profit_factor,
                "avg_trade_duration": metrics.avg_trade_duration,
                "total_trades": metrics.total_trades,
                "trading_days": metrics.trading_days,
            },
            "generated_at": datetime.now().isoformat(),
        }, indent=2)
