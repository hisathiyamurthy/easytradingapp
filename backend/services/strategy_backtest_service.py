"""
Strategy Backtest Service - Connects parser to backtest engine.
Handles strategy validation and backtest execution.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backtesting.engine import (
    BacktestEngine, BacktestConfig, BacktestMetrics,
    BacktestSignal, BacktestPosition
)
from strategy_engine.executor import IndicatorCalculator, ConditionEvaluator, OHLCV
from strategy_engine.improved_parser import parse_strategy

logger = logging.getLogger(__name__)


class StrategyValidator:
    """Validates strategies before backtesting or live trading."""
    
    @staticmethod
    def validate(parsed_strategy: dict) -> tuple[bool, List[str], List[str]]:
        """
        Validate a parsed strategy.
        
        Returns:
            (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check entry conditions (support both formats)
        entry = parsed_strategy.get("entry", []) or parsed_strategy.get("entry_conditions", [])
        if isinstance(entry, str) and not entry.strip():
            errors.append("No entry conditions defined")
        elif isinstance(entry, list) and len(entry) == 0:
            errors.append("No entry conditions defined")
        
        # Check exit conditions (support both formats)
        exit_conditions = parsed_strategy.get("exit", {}) or parsed_strategy.get("exit_conditions", {})
        if isinstance(exit_conditions, str) and not exit_conditions.strip():
            warnings.append("No exit conditions defined")
        elif isinstance(exit_conditions, list) and len(exit_conditions) == 0:
            warnings.append("No exit conditions defined")
        
        # Check for stoploss
        if isinstance(exit_conditions, dict):
            if not exit_conditions.get("stoploss"):
                warnings.append("No stoploss defined - high risk")
            if not exit_conditions.get("target"):
                warnings.append("No take profit target defined")
        
        # Check for ambiguous conditions
        entry_str = str(entry).lower()
        if "low" in entry_str or "high" in entry_str or "strong" in entry_str:
            if not any(char.isdigit() for char in entry_str):
                errors.append("Ambiguous condition: threshold values not specified")
        
        # Check for conflicting logic
        position = parsed_strategy.get("position", "").upper()
        entry_str = str(entry).lower()
        
        if position == "BUY" and "sell" in entry_str:
            errors.append("Conflicting logic: BUY position with SELL entry condition")
        if position == "SELL" and "buy" in entry_str:
            errors.append("Conflicting logic: SELL position with BUY entry condition")
        
        is_valid = len(errors) == 0
        
        return is_valid, errors, warnings
    
    @staticmethod
    def validate_for_live(parsed_strategy: dict) -> tuple[bool, List[str]]:
        """
        Additional validation for live trading.
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # Live trading requires stoploss
        exit_conditions = parsed_strategy.get("exit", {})
        if isinstance(exit_conditions, dict):
            if not exit_conditions.get("stoploss"):
                errors.append("Live trading requires stoploss")
        
        # Check for measurable conditions
        entry = parsed_strategy.get("entry", [])
        entry_str = str(entry).lower()
        
        subjective_words = ["strong", "weak", "bullish", "bearish", "volatile"]
        for word in subjective_words:
            if word in entry_str:
                errors.append(f"Subjective condition not allowed for live trading: '{word}'")
        
        return len(errors) == 0, errors


class StrategyBacktester:
    """
    Service that connects parsed strategies to the backtest engine.
    """
    
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.indicator_calc = IndicatorCalculator()
    
    async def run_backtest(
        self,
        parsed_strategy: dict,
        symbol: str,
        exchange: str = "NSE",
        start_date: datetime = None,
        end_date: datetime = None,
        timeframe: str = "1d",
        initial_capital: float = 100000,
        data: List[dict] = None,
    ) -> BacktestMetrics:
        """
        Run backtest for a parsed strategy.
        
        Args:
            parsed_strategy: Strategy JSON from parser
            symbol: Trading symbol
            exchange: Exchange
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Candle timeframe
            initial_capital: Starting capital
            data: Optional pre-loaded OHLCV data
        
        Returns:
            BacktestMetrics with performance results
        """
        # Set default dates
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        # Create config
        config = BacktestConfig(
            initial_capital=initial_capital,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            symbol=symbol,
            exchange=exchange,
            commission_rate=0.001,
            slippage_bps=1.0,
        )
        
        # Create data provider
        if data is None:
            data = await self._generate_mock_data(symbol, start_date, end_date, timeframe)
        
        # Create strategy executor
        async def strategy_executor(bar: dict, position: BacktestPosition) -> Optional[BacktestSignal]:
            return await self._evaluate_strategy(parsed_strategy, bar, position)
        
        # Inject data provider
        async def data_provider(**kwargs):
            return data
        
        # Create and run engine
        engine = BacktestEngine(
            config=config,
            strategy_executor=strategy_executor,
            data_provider=data_provider,
        )
        
        # Run backtest
        metrics = await engine.run()
        
        return metrics
    
    async def _evaluate_strategy(
        self,
        strategy: dict,
        bar: dict,
        position: BacktestPosition,
    ) -> Optional[BacktestSignal]:
        """Evaluate strategy conditions on a single bar."""
        try:
            # Get historical data for indicator calculation
            # In production, this would fetch from a data store
            # For now, use closing prices
            closes = [bar.get('close', 0)]
            volumes = [bar.get('volume', 0)]
            
            # Calculate indicators
            indicators = {
                'close': closes,
                'volume': volumes,
                'rsi': self.indicator_calc.calculate_rsi(closes, 14),
                'ema_12': self.indicator_calc.calculate_ema(closes, 12),
                'ema_26': self.indicator_calc.calculate_ema(closes, 26),
                'sma_20': self.indicator_calc.calculate_sma(closes, 20),
                'sma_50': self.indicator_calc.calculate_sma(closes, 50),
            }
            
            current_price = bar.get('close', 0)
            prev_price = closes[-2] if len(closes) > 1 else current_price
            
            evaluator = ConditionEvaluator(indicators, current_price, prev_price)
            
            # Check entry conditions
            entry = strategy.get("entry", [])
            if isinstance(entry, str):
                entry = [entry]
            
            position_side = strategy.get("position", "BUY").upper()
            
            entry_met = all(evaluator.evaluate(cond) for cond in entry)
            
            # Determine action
            if not position or position.quantity == 0:
                # No position - check for entry
                if entry_met:
                    return BacktestSignal(
                        timestamp=bar.get('timestamp', datetime.now()),
                        symbol=bar.get('symbol', strategy.get('symbol', 'UNKNOWN')),
                        signal_type="buy" if position_side == "BUY" else "sell",
                        price=current_price,
                        quantity=1,
                        reason=f"Entry: {', '.join(str(e) for e in entry)}",
                    )
            else:
                # Have position - check for exit
                exit_conditions = strategy.get("exit", {})
                
                should_exit = False
                exit_reason = "signal"
                
                # Check stoploss
                if isinstance(exit_conditions, dict):
                    sl = exit_conditions.get("stoploss")
                    if sl and isinstance(sl, (int, float)):
                        if position_side == "BUY" and current_price < bar.get('entry_price', current_price) * (1 - sl/100):
                            should_exit = True
                            exit_reason = "stoploss"
                        elif position_side == "SELL" and current_price > bar.get('entry_price', current_price) * (1 + sl/100):
                            should_exit = True
                            exit_reason = "stoploss"
                    
                    # Check target
                    tp = exit_conditions.get("target")
                    if tp and isinstance(tp, (int, float)):
                        if position_side == "BUY" and current_price > bar.get('entry_price', current_price) * (1 + tp/100):
                            should_exit = True
                            exit_reason = "target"
                        elif position_side == "SELL" and current_price < bar.get('entry_price', current_price) * (1 - tp/100):
                            should_exit = True
                            exit_reason = "target"
                
                if should_exit:
                    return BacktestSignal(
                        timestamp=bar.get('timestamp', datetime.now()),
                        symbol=bar.get('symbol', strategy.get('symbol', 'UNKNOWN')),
                        signal_type="sell" if position_side == "BUY" else "buy",
                        price=current_price,
                        quantity=1,
                        reason=exit_reason,
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating strategy: {e}")
            return None
    
    async def _generate_mock_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str,
    ) -> List[dict]:
        """Generate mock OHLCV data for backtesting."""
        import random
        random.seed(42)
        
        data = []
        
        # Determine intervals
        interval_hours = {
            "1m": 1/60, "5m": 5/60, "15m": 15/60, "30m": 0.5,
            "1h": 1, "4h": 4, "1d": 24, "daily": 24
        }
        hours = interval_hours.get(timeframe, 24)
        
        current_date = start_date
        base_price = 100
        
        while current_date < end_date:
            # Random price movement
            change = random.uniform(-0.02, 0.025)
            base_price *= (1 + change)
            
            high = base_price * (1 + random.uniform(0, 0.01))
            low = base_price * (1 - random.uniform(0, 0.01))
            open_price = base_price * (1 + random.uniform(-0.005, 0.005))
            close_price = base_price
            volume = random.randint(100000, 1000000)
            
            data.append({
                'timestamp': current_date,
                'symbol': symbol,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume,
            })
            
            current_date += timedelta(hours=hours)
        
        return data


class StrategyLifecycleManager:
    """
    Manages strategy lifecycle: Draft → Backtested → Paper Trading → Live.
    """
    
    STATES = [
        "draft",           # Initial creation
        "validated",       # Passed validation
        "backtested",      # Backtest completed successfully
        "paper_trading",   # Running in paper mode
        "live",            # Running with real money
        "paused",          # Temporarily stopped
        "stopped",         # Permanently stopped
    ]
    
    # Allowed transitions
    TRANSITIONS = {
        "DRAFT": ["validated"],
        "validated": ["DRAFT", "backtested"],
        "backtested": ["validated", "paper_trading"],
        "paper_trading": ["backtested", "live", "PAUSED", "STOPPED"],
        "live": ["paper_trading", "PAUSED", "STOPPED"],
        "PAUSED": ["paper_trading", "live", "STOPPED"],
        "STOPPED": [],  # Terminal state
    }
    
    # Requirements for each state
    REQUIREMENTS = {
        "validated": ["has_valid_conditions"],
        "backtested": ["passed_validation", "has_backtest_results"],
        "paper_trading": ["passed_backtest", "has_stoploss"],
        "live": ["admin_approved", "passed_paper_trading", "has_stoploss"],
        "PAUSED": ["is_running"],
    }
    
    @classmethod
    def can_transition(cls, from_state: str, to_state: str) -> bool:
        """Check if transition is allowed."""
        allowed = cls.TRANSITIONS.get(from_state, [])
        return to_state in allowed
    
    @classmethod
    def get_requirements(cls, to_state: str) -> List[str]:
        """Get requirements for reaching a state."""
        return cls.REQUIREMENTS.get(to_state, [])
    
    @classmethod
    def get_next_states(cls, current_state: str) -> List[str]:
        """Get possible next states."""
        return cls.TRANSITIONS.get(current_state, [])


async def run_strategy_backtest(
    strategy_text: str,
    symbol: str = "NIFTY",
    start_date: datetime = None,
    end_date: datetime = None,
    initial_capital: float = 100000,
) -> Dict[str, Any]:
    """
    Convenience function to run backtest from strategy text.
    
    Args:
        strategy_text: Natural language strategy
        symbol: Trading symbol
        start_date: Backtest start
        end_date: Backtest end
        initial_capital: Starting capital
    
    Returns:
        dict with backtest results and validation
    """
    # Parse strategy
    parsed = parse_strategy(strategy_text)
    
    # Validate
    is_valid, errors, warnings = StrategyValidator.validate(parsed)
    
    result = {
        "strategy_text": strategy_text,
        "parsed_strategy": parsed,
        "validation": {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
        },
    }
    
    if not is_valid:
        result["backtest"] = None
        return result
    
    # Run backtest
    backtester = StrategyBacktester()
    
    metrics = await backtester.run_backtest(
        parsed_strategy=parsed,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
    )
    
    # Convert metrics to dict
    result["backtest"] = {
        "total_trades": metrics.total_trades,
        "winning_trades": metrics.winning_trades,
        "losing_trades": metrics.losing_trades,
        "win_rate": metrics.win_rate,
        "total_return": metrics.total_return,
        "total_return_pct": metrics.total_return_pct,
        "annualized_return": metrics.annualized_return,
        "max_drawdown": metrics.max_drawdown,
        "max_drawdown_pct": metrics.max_drawdown_pct,
        "sharpe_ratio": metrics.sharpe_ratio,
        "sortino_ratio": metrics.sortino_ratio,
        "profit_factor": metrics.profit_factor,
        "avg_trade_pnl": metrics.avg_trade_pnl,
        "total_commission": metrics.total_commission,
        "trades": metrics.trades[:10],  # First 10 trades
    }
    
    return result
