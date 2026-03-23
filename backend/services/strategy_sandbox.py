"""Strategy sandbox for isolated strategy testing."""
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.strategy_models import Strategy
from services.backtest_service import BacktestService

logger = logging.getLogger(__name__)


class StrategySandbox:
    """Sandbox for testing strategies in isolation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.backtest_service = BacktestService(db)
    
    async def validate_strategy(self, strategy: Strategy) -> Dict[str, Any]:
        """Validate strategy parameters and logic."""
        issues = []
        warnings = []
        
        if not strategy.entry_conditions:
            issues.append("No entry conditions defined")
        
        if not strategy.exit_conditions:
            warnings.append("No exit conditions defined")
        
        if strategy.parameters:
            for key, value in strategy.parameters.items():
                if isinstance(value, (int, float)):
                    if value < 0:
                        issues.append(f"Parameter {key} has negative value")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }
    
    async def dry_run(
        self,
        strategy_id: UUID,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000,
    ) -> Dict[str, Any]:
        """Run strategy in sandbox mode without real trading."""
        result = await self.db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            return {"error": "Strategy not found"}
        
        validation = await self.validate_strategy(strategy)
        if not validation["valid"]:
            return {
                "error": "Strategy validation failed",
                "issues": validation["issues"],
            }
        
        try:
            backtest_result = await self.backtest_service.run_backtest(
                strategy_id=strategy_id,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                is_sandbox=True,
            )
            
            return {
                "sandbox_mode": True,
                "strategy_id": str(strategy_id),
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "initial_capital": initial_capital,
                "results": backtest_result,
                "validation": validation,
            }
            
        except Exception as e:
            logger.error(f"Sandbox dry run failed: {e}")
            return {"error": str(e)}
    
    async def test_with_sample_data(
        self,
        strategy: Strategy,
        sample_data: List[Dict],
    ) -> Dict[str, Any]:
        """Test strategy with provided sample data."""
        validation = await self.validate_strategy(strategy)
        
        signals = []
        
        for i, data_point in enumerate(sample_data):
            try:
                signal = await self._evaluate_signal(strategy, data_point)
                if signal:
                    signals.append({
                        "index": i,
                        "timestamp": data_point.get("timestamp"),
                        "signal": signal,
                    })
            except Exception as e:
                logger.warning(f"Signal evaluation failed at {i}: {e}")
        
        return {
            "validation": validation,
            "signals_generated": len(signals),
            "signals": signals[:10],
        }
    
    async def _evaluate_signal(self, strategy: Strategy, data: Dict) -> Optional[str]:
        """Evaluate strategy signal on data point."""
        entry = strategy.entry_conditions
        
        if not entry:
            return None
        
        conditions_met = True
        
        if "indicators" in entry:
            for indicator, config in entry["indicators"].items():
                threshold = config.get("threshold")
                operator = config.get("operator", ">")
                value = data.get(indicator)
                
                if value is None:
                    conditions_met = False
                    break
                
                if operator == ">" and value <= threshold:
                    conditions_met = False
                elif operator == "<" and value >= threshold:
                    conditions_met = False
                elif operator == ">=" and value < threshold:
                    conditions_met = False
                elif operator == "<=" and value > threshold:
                    conditions_met = False
                elif operator == "==" and value != threshold:
                    conditions_met = False
        
        if conditions_met:
            return entry.get("action", "buy")
        
        return None
    
    async def create_sandbox_snapshot(
        self,
        user_id: UUID,
        strategy_id: UUID,
    ) -> Dict[str, Any]:
        """Create a snapshot of strategy for sandbox testing."""
        result = await self.db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == user_id,
                )
            )
        )
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            return {"error": "Strategy not found"}
        
        from models.strategy_models import StrategySnapshot
        
        snapshot = StrategySnapshot(
            user_id=user_id,
            original_strategy_id=strategy_id,
            name=f"{strategy.name} (Sandbox)",
            description=f"Sandbox copy of strategy {strategy.name}",
            strategy_type=strategy.strategy_type,
            parameters=strategy.parameters,
            entry_conditions=strategy.entry_conditions,
            exit_conditions=strategy.exit_conditions,
            is_sandbox=True,
            sandbox_config={
                "max_position_size": 10000,
                "max_daily_trades": 10,
                "allow_partial_fills": True,
                "simulation_mode": True,
            },
        )
        
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        
        return {
            "snapshot_id": str(snapshot.id),
            "created_at": snapshot.created_at.isoformat(),
            "sandbox_config": snapshot.sandbox_config,
        }