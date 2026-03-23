"""
Strategy Instance Service - Manages strategy execution lifecycle.
Bridges parser → executor → persistence for paper and live trading.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from models.strategy_instance_models import (
    UserStrategyInstance, InstanceStatus, InstanceMode,
    InstanceTrade, InstancePosition, InstanceLog,
    StrategyPerformance, InstanceExitReason
)
from models.strategy_models import Strategy
from strategy_engine.executor import StrategyExecutor, TradingSignal, OHLCV
from trading_engine.paper_trading import SimulatedTradeEngine, OrderSide, OrderStatus
from services.market_data_service import get_market_data_service

logger = logging.getLogger(__name__)


class StrategyInstanceService:
    """
    Manages the lifecycle of strategy instances.
    Handles:
    - Creating new instances from strategies
    - Running paper trading loops
    - Persisting trades to database
    - Tracking performance metrics
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.executor = StrategyExecutor()
        self.paper_engines: Dict[str, SimulatedTradeEngine] = {}  # instance_id -> engine
    
    async def create_instance(
        self,
        user_id: UUID,
        strategy_id: UUID,
        name: str,
        capital: float = 100000.0,
        mode: InstanceMode = InstanceMode.PAPER,
    ) -> UserStrategyInstance:
        """Create a new strategy instance."""
        instance = UserStrategyInstance(
            user_id=user_id,
            strategy_id=strategy_id,
            name=name,
            capital=capital,
            allocated_capital=capital,
            mode=mode,
            status=InstanceStatus.DRAFT,
        )
        
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        
        await self._log(instance.id, "INFO", f"Strategy instance created with capital: {capital}")
        
        return instance
    
    async def start_instance(
        self,
        instance_id: UUID,
        initial_balance: Optional[float] = None,
    ) -> UserStrategyInstance:
        """Start a strategy instance (paper or live trading)."""
        instance = await self.get_instance(instance_id)
        
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")
        
        if instance.status == InstanceStatus.RUNNING:
            raise ValueError("Instance is already running")
        
        # Initialize paper trading engine if paper mode
        if instance.mode == InstanceMode.PAPER:
            balance = initial_balance or instance.allocated_capital
            self.paper_engines[str(instance_id)] = SimulatedTradeEngine(
                user_id=str(instance.user_id),
                initial_balance=balance,
                commission_rate=0.001,
                slippage_bps=1.0,
            )
        
        # Update instance status
        instance.status = InstanceStatus.RUNNING
        instance.started_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(instance)
        
        await self._log(instance.id, "INFO", f"Strategy instance started in {instance.mode.value} mode")
        
        return instance
    
    async def pause_instance(self, instance_id: UUID) -> UserStrategyInstance:
        """Pause a running strategy instance."""
        instance = await self.get_instance(instance_id)
        
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")
        
        if instance.status != InstanceStatus.RUNNING:
            raise ValueError("Instance is not running")
        
        instance.status = InstanceStatus.PAUSED
        instance.paused_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(instance)
        
        await self._log(instance.id, "INFO", "Strategy instance paused")
        
        return instance
    
    async def resume_instance(self, instance_id: UUID) -> UserStrategyInstance:
        """Resume a paused strategy instance."""
        instance = await self.get_instance(instance_id)
        
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")
        
        if instance.status != InstanceStatus.PAUSED:
            raise ValueError("Instance is not paused")
        
        instance.status = InstanceStatus.RUNNING
        instance.paused_at = None
        
        await self.db.commit()
        await self.db.refresh(instance)
        
        await self._log(instance.id, "INFO", "Strategy instance resumed")
        
        return instance
    
    async def stop_instance(self, instance_id: UUID) -> UserStrategyInstance:
        """Stop a strategy instance permanently."""
        instance = await self.get_instance(instance_id)
        
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")
        
        # Close any open positions
        if str(instance_id) in self.paper_engines:
            engine = self.paper_engines[str(instance_id)]
            for position in engine.get_all_positions():
                # Close position at current price
                pass  # Would need market data
            
            del self.paper_engines[str(instance_id)]
        
        instance.status = InstanceStatus.STOPPED
        instance.stopped_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(instance)
        
        await self._log(instance.id, "INFO", "Strategy instance stopped")
        
        return instance
    
    async def get_instance(self, instance_id: UUID) -> Optional[UserStrategyInstance]:
        """Get a strategy instance by ID."""
        result = await self.db.execute(
            select(UserStrategyInstance).where(
                UserStrategyInstance.id == instance_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_instances(
        self,
        user_id: UUID,
        status: Optional[InstanceStatus] = None,
    ) -> List[UserStrategyInstance]:
        """Get all instances for a user."""
        query = select(UserStrategyInstance).where(
            UserStrategyInstance.user_id == user_id
        )
        
        if status:
            query = query.where(UserStrategyInstance.status == status)
        
        query = query.order_by(UserStrategyInstance.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def execute_single_candle(
        self,
        instance_id: UUID,
        parsed_strategy: Dict[str, Any],
        symbol: str,
        exchange: str = "NSE",
        ohlcv: Optional[Dict] = None,
    ) -> Optional[TradingSignal]:
        """
        Execute a single candle for a strategy instance.
        Called by the execution loop.
        """
        instance = await self.get_instance(instance_id)
        
        if not instance or instance.status != InstanceStatus.RUNNING:
            return None
        
        try:
            # Generate signal
            signal = await self.executor.generate_signal(
                parsed_strategy=parsed_strategy,
                symbol=symbol,
                exchange=exchange,
            )
            
            if signal and signal.action != "hold":
                await self._log(
                    instance_id,
                    "INFO",
                    f"Signal generated: {signal.action} {symbol} @ {signal.entry_price}",
                    {"signal": signal.to_dict()}
                )
                
                # Execute trade
                await self._execute_trade(instance, signal, ohlcv)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error executing candle: {e}")
            await self._log(instance_id, "ERROR", f"Execution error: {e}")
            return None
    
    async def _execute_trade(
        self,
        instance: UserStrategyInstance,
        signal: TradingSignal,
        ohlcv: Optional[Dict] = None,
    ):
        """Execute a trade for a paper or live trading instance."""
        if instance.mode != InstanceMode.PAPER:
            # Live trading goes through live trading service
            try:
                await self._execute_live_trade(instance, signal)
                return
            except Exception as e:
                logger.error(f"Error executing live trade: {e}")
                await self._log(instance.id, "ERROR", f"Live trade execution error: {e}")
                return
        
        engine = self.paper_engines.get(str(instance.id))
        if not engine:
            logger.warning(f"No paper engine for instance {instance.id}")
            return
        
        try:
            current_price = ohlcv.get("close", signal.entry_price) if ohlcv else signal.entry_price
            
            if signal.action == "buy":
                trade = await engine.place_market_order(
                    symbol=signal.symbol,
                    exchange=signal.exchange,
                    side=OrderSide.BUY,
                    quantity=signal.quantity,
                    current_price=current_price,
                    strategy_id=str(instance.id),
                )
                
                # Persist to database
                await self._persist_trade(instance, signal, trade)
                
            elif signal.action == "sell":
                trade = await engine.place_market_order(
                    symbol=signal.symbol,
                    exchange=signal.exchange,
                    side=OrderSide.SELL,
                    quantity=signal.quantity,
                    current_price=current_price,
                    strategy_id=str(instance.id),
                )
                
                await self._persist_trade(instance, signal, trade)
            
            # Update instance metrics
            await self._update_instance_metrics(instance)
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            await self._log(instance.id, "ERROR", f"Trade execution error: {e}")
    
    async def _persist_trade(
        self,
        instance: UserStrategyInstance,
        signal: TradingSignal,
        trade_simulation,
    ):
        """Persist a paper trade to the database."""
        instance_trade = InstanceTrade(
            instance_id=instance.id,
            user_id=instance.user_id,
            symbol=signal.symbol,
            exchange=signal.exchange,
            side=signal.action,
            quantity=trade_simulation.quantity,
            entry_price=trade_simulation.fill_price,
            exit_price=trade_simulation.fill_price,
            pnl=trade_simulation.net_value,
            commission=trade_simulation.commission,
            slippage=trade_simulation.slippage,
            entry_time=datetime.now(timezone.utc),
            exit_time=datetime.now(timezone.utc),
            entry_signal=signal.reason,
        )
        
        self.db.add(instance_trade)
        
        # Update instance counters
        instance.trades_count += 1
        if trade_simulation.net_value > 0:
            instance.winning_trades += 1
        else:
            instance.losing_trades += 1
        
        await self.db.commit()
    
    async def _execute_live_trade(
        self,
        instance: UserStrategyInstance,
        signal: TradingSignal,
    ):
        """Execute a trade through the live trading broker with SL/TP support."""
        from services.live_trading_service import _broker_sessions
        from uuid import UUID
        from broker_integrations.base import OrderType, OrderSide, ProductType
        
        broker_session = _broker_sessions.get(str(instance.user_id))
        if not broker_session:
            logger.warning(f"No broker connected for user {instance.user_id}")
            await self._log(instance.id, "WARNING", "No broker connected for live trading")
            return
        
        broker = broker_session["broker"]
        
        try:
            current_price = signal.entry_price or 100.0
            
            # Place entry order
            entry_order = await broker.place_order(
                symbol=signal.symbol,
                side=signal.action.upper(),
                quantity=signal.quantity,
                order_type=OrderType.MARKET,
                price=current_price,
                product_type=ProductType.MIS,
            )
            
            if entry_order.get("status") in ["COMPLETE", "FILLED", "OPEN"]:
                entry_price = entry_order.get("average_price", current_price)
                commission = entry_price * signal.quantity * 0.001
                
                instance_trade = InstanceTrade(
                    instance_id=instance.id,
                    user_id=instance.user_id,
                    symbol=signal.symbol,
                    exchange=signal.exchange or "NSE",
                    side=signal.action.upper(),
                    quantity=signal.quantity,
                    entry_price=entry_price,
                    commission=commission,
                    slippage=0,
                    entry_time=datetime.now(timezone.utc),
                    entry_signal=signal.reason,
                    broker_order_id=entry_order.get("order_id"),
                )
                
                self.db.add(instance_trade)
                instance.trades_count += 1
                
                # Place stoploss order if defined
                sl_order_id = None
                tp_order_id = None
                
                if signal.action.upper() == "BUY" and signal.stop_loss:
                    # For BUY, SL is below entry price
                    sl_trigger = signal.stop_loss
                    if sl_trigger < entry_price:
                        sl_order = await broker.place_order(
                            symbol=signal.symbol,
                            side="SELL",
                            quantity=signal.quantity,
                            order_type=OrderType.SLM,  # SL-M triggers at or below trigger price
                            trigger_price=sl_trigger,
                            product_type=ProductType.MIS,
                        )
                        sl_order_id = sl_order.get("order_id")
                        await self._log(instance.id, "INFO", f"SL order placed: SELL {signal.quantity} {signal.symbol} @ trigger {sl_trigger}")
                        logger.info(f"SL order placed: SELL {signal.quantity} {signal.symbol} @ trigger {sl_trigger}")
                
                elif signal.action.upper() == "SELL" and signal.stop_loss:
                    # For SELL, SL is above entry price
                    sl_trigger = signal.stop_loss
                    if sl_trigger > entry_price:
                        sl_order = await broker.place_order(
                            symbol=signal.symbol,
                            side="BUY",
                            quantity=signal.quantity,
                            order_type=OrderType.SLM,
                            trigger_price=sl_trigger,
                            product_type=ProductType.MIS,
                        )
                        sl_order_id = sl_order.get("order_id")
                        await self._log(instance.id, "INFO", f"SL order placed: BUY {signal.quantity} {signal.symbol} @ trigger {sl_trigger}")
                        logger.info(f"SL order placed: BUY {signal.quantity} {signal.symbol} @ trigger {sl_trigger}")
                
                # Place target order if defined
                if signal.action.upper() == "BUY" and signal.take_profit:
                    tp_trigger = signal.take_profit
                    if tp_trigger > entry_price:
                        tp_order = await broker.place_order(
                            symbol=signal.symbol,
                            side="SELL",
                            quantity=signal.quantity,
                            order_type=OrderType.SLM,
                            trigger_price=tp_trigger,
                            product_type=ProductType.MIS,
                        )
                        tp_order_id = tp_order.get("order_id")
                        await self._log(instance.id, "INFO", f"Target order placed: SELL {signal.quantity} {signal.symbol} @ trigger {tp_trigger}")
                        logger.info(f"Target order placed: SELL {signal.quantity} {signal.symbol} @ trigger {tp_trigger}")
                
                elif signal.action.upper() == "SELL" and signal.take_profit:
                    tp_trigger = signal.take_profit
                    if tp_trigger < entry_price:
                        tp_order = await broker.place_order(
                            symbol=signal.symbol,
                            side="BUY",
                            quantity=signal.quantity,
                            order_type=OrderType.SLM,
                            trigger_price=tp_trigger,
                            product_type=ProductType.MIS,
                        )
                        tp_order_id = tp_order.get("order_id")
                        await self._log(instance.id, "INFO", f"Target order placed: BUY {signal.quantity} {signal.symbol} @ trigger {tp_trigger}")
                        logger.info(f"Target order placed: BUY {signal.quantity} {signal.symbol} @ trigger {tp_trigger}")
                
                # Create position tracking entry
                position = InstancePosition(
                    instance_id=instance.id,
                    user_id=instance.user_id,
                    symbol=signal.symbol,
                    exchange=signal.exchange or "NSE",
                    side=signal.action.upper(),
                    quantity=signal.quantity,
                    entry_price=entry_price,
                    current_price=entry_price,
                    unrealized_pnl=0,
                    is_open=True,
                    opened_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    broker_order_id=entry_order.get("order_id"),
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    sl_order_id=sl_order_id,
                    tp_order_id=tp_order_id,
                )
                self.db.add(position)
                
                await self.db.commit()
                
                sl_msg = f", SL@{signal.stop_loss}" if signal.stop_loss else ""
                tp_msg = f", TP@{signal.take_profit}" if signal.take_profit else ""
                await self._log(instance.id, "INFO", f"Live trade executed: {signal.action.upper()} {signal.quantity} {signal.symbol} @ {entry_price}{sl_msg}{tp_msg}")
                logger.info(f"Live trade executed: {signal.action.upper()} {signal.quantity} {signal.symbol} @ {entry_price}{sl_msg}{tp_msg}")
            else:
                await self._log(instance.id, "WARNING", f"Live order not filled: {entry_order.get('status')}")
                
        except Exception as e:
            logger.error(f"Error executing live trade: {e}")
            await self._log(instance.id, "ERROR", f"Live trade failed: {str(e)}")
    
    async def _update_instance_metrics(self, instance: UserStrategyInstance):
        """Update performance metrics for an instance."""
        engine = self.paper_engines.get(str(instance.id))
        
        if engine:
            summary = engine.get_performance_summary()
            instance.current_pnl = summary.get("total_pnl", 0)
            instance.realized_pnl = summary.get("realized_pnl", 0)
            instance.unrealized_pnl = summary.get("unrealized_pnl", 0)
        
        # Calculate drawdown
        if instance.current_pnl > instance.max_profit:
            instance.max_profit = instance.current_pnl
        
        drawdown = instance.max_profit - instance.current_pnl
        if drawdown > instance.max_drawdown:
            instance.max_drawdown = drawdown
        
        await self.db.commit()
    
    async def _log(
        self,
        instance_id: UUID,
        level: str,
        message: str,
        data: Optional[Dict] = None,
    ):
        """Add a log entry for an instance."""
        log = InstanceLog(
            instance_id=instance_id,
            level=level,
            message=message,
            data=data,
        )
        
        self.db.add(log)
        await self.db.commit()
    
    async def get_trades(
        self,
        instance_id: UUID,
        limit: int = 50,
    ) -> List[InstanceTrade]:
        """Get trades for an instance."""
        result = await self.db.execute(
            select(InstanceTrade)
            .where(InstanceTrade.instance_id == instance_id)
            .order_by(InstanceTrade.entry_time.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_performance_summary(
        self,
        instance_id: UUID,
    ) -> Dict[str, Any]:
        """Get performance summary for an instance."""
        instance = await self.get_instance(instance_id)
        
        if not instance:
            return {}
        
        trades = await self.get_trades(instance_id)
        
        return {
            "instance_id": str(instance.id),
            "name": instance.name,
            "status": instance.status.value,
            "mode": instance.mode.value,
            "capital": instance.capital,
            "allocated_capital": instance.allocated_capital,
            "current_pnl": instance.current_pnl,
            "realized_pnl": instance.realized_pnl,
            "unrealized_pnl": instance.unrealized_pnl,
            "trades_count": instance.trades_count,
            "winning_trades": instance.winning_trades,
            "losing_trades": instance.losing_trades,
            "win_rate": instance.win_rate,
            "max_drawdown": instance.max_drawdown,
            "max_profit": instance.max_profit,
            "return_percent": (instance.current_pnl / instance.allocated_capital * 100) if instance.allocated_capital > 0 else 0,
            "recent_trades": [
                {
                    "symbol": t.symbol,
                    "side": t.side,
                    "quantity": t.quantity,
                    "entry_price": t.entry_price,
                    "pnl": t.pnl,
                    "pnl_percent": t.pnl_percent,
                    "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                }
                for t in trades[:10]
            ],
        }
    
    async def close_position(
        self,
        instance_id: UUID,
        symbol: str,
        reason: InstanceExitReason = InstanceExitReason.MANUAL,
        current_price: Optional[float] = None,
    ) -> Optional[InstanceTrade]:
        """Close an open position for an instance."""
        instance = await self.get_instance(instance_id)
        
        if not instance or instance.mode != InstanceMode.PAPER:
            return None
        
        engine = self.paper_engines.get(str(instance_id))
        if not engine:
            return None
        
        position = engine.get_position(symbol)
        if not position:
            return None
        
        # Close at current price
        price = current_price or position.current_price
        
        if position.side.value == "long":
            trade = await engine.place_market_order(
                symbol=symbol,
                exchange=position.exchange,
                side=OrderSide.SELL,
                quantity=position.quantity,
                current_price=price,
            )
        else:
            trade = await engine.place_market_order(
                symbol=symbol,
                exchange=position.exchange,
                side=OrderSide.BUY,
                quantity=position.quantity,
                current_price=price,
            )
        
        # Create instance trade record
        instance_trade = InstanceTrade(
            instance_id=instance_id,
            user_id=instance.user_id,
            symbol=symbol,
            exchange=position.exchange,
            side="sell" if position.side.value == "long" else "buy",
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=trade.fill_price,
            pnl=trade.net_value,
            pnl_percent=(trade.net_value / (position.entry_price * position.quantity)) * 100,
            commission=trade.commission,
            exit_reason=reason,
            entry_time=position.opened_at,
            exit_time=datetime.now(timezone.utc),
        )
        
        self.db.add(instance_trade)
        await self._update_instance_metrics(instance)
        await self.db.commit()
        
        await self._log(
            instance_id,
            "INFO",
            f"Position closed: {symbol} @ {trade.fill_price}, PnL: {trade.net_value}"
        )
        
        return instance_trade

    async def exit_all_positions(
        self,
        instance_id: UUID,
        reason: str = "emergency_exit",
    ) -> Dict[str, Any]:
        """Exit all open positions for an instance (Emergency Exit All)."""
        from services.live_trading_service import _broker_sessions
        from broker_integrations.base import OrderType, OrderSide, ProductType
        from sqlalchemy import and_
        
        instance = await self.get_instance(instance_id)
        if not instance:
            return {"success": False, "message": "Instance not found", "closed_positions": []}
        
        results = {
            "success": True,
            "message": f"Emergency exit initiated",
            "closed_positions": [],
            "failed_positions": [],
        }
        
        try:
            if instance.mode == InstanceMode.PAPER:
                # Paper trading - close through engine
                engine = self.paper_engines.get(str(instance_id))
                if engine:
                    positions = engine.get_all_positions()
                    for pos in positions:
                        if pos.is_open:
                            try:
                                close_side = OrderSide.SELL if pos.side.value == "long" else OrderSide.BUY
                                trade = await engine.place_market_order(
                                    symbol=pos.symbol,
                                    exchange=pos.exchange,
                                    side=close_side,
                                    quantity=pos.quantity,
                                    current_price=pos.current_price,
                                )
                                results["closed_positions"].append({
                                    "symbol": pos.symbol,
                                    "quantity": pos.quantity,
                                    "exit_price": trade.fill_price,
                                    "pnl": trade.net_value,
                                })
                                await self._log(instance_id, "INFO", f"Emergency exit: Closed {pos.symbol} @ {trade.fill_price}")
                            except Exception as e:
                                results["failed_positions"].append({
                                    "symbol": pos.symbol,
                                    "error": str(e),
                                })
                
            elif instance.mode == InstanceMode.LIVE:
                # Live trading - close through broker
                broker_session = _broker_sessions.get(str(instance.user_id))
                if not broker_session:
                    results["success"] = False
                    results["message"] = "No broker connected"
                    return results
                
                broker = broker_session["broker"]
                
                # Get open positions from database
                pos_result = await self.db.execute(
                    select(InstancePosition).where(
                        and_(
                            InstancePosition.instance_id == instance_id,
                            InstancePosition.is_open == True,
                        )
                    )
                )
                positions = list(pos_result.scalars().all())
                
                # Also cancel any pending SL/TP orders first
                for pos in positions:
                    if pos.sl_order_id:
                        try:
                            await broker.cancel_order(pos.sl_order_id)
                            await self._log(instance_id, "INFO", f"Cancelled SL order: {pos.sl_order_id}")
                        except:
                            pass
                    if pos.tp_order_id:
                        try:
                            await broker.cancel_order(pos.tp_order_id)
                            await self._log(instance_id, "INFO", f"Cancelled TP order: {pos.tp_order_id}")
                        except:
                            pass
                
                # Close each position
                for pos in positions:
                    try:
                        close_side = OrderSide.SELL if pos.side == "BUY" else OrderSide.BUY
                        
                        exit_order = await broker.place_order(
                            symbol=pos.symbol,
                            side=close_side.value,
                            quantity=pos.quantity,
                            order_type=OrderType.MARKET,
                            product_type=ProductType.MIS,
                        )
                        
                        exit_price = exit_order.get("average_price", pos.current_price)
                        
                        # Update position
                        pos.is_open = False
                        pos.exit_price = exit_price
                        pos.exit_time = datetime.now(timezone.utc)
                        
                        results["closed_positions"].append({
                            "symbol": pos.symbol,
                            "quantity": pos.quantity,
                            "exit_price": exit_price,
                            "entry_price": pos.entry_price,
                            "broker_order_id": exit_order.get("order_id"),
                        })
                        
                        await self._log(instance_id, "INFO", f"Emergency exit: Closed {pos.symbol} {pos.quantity} @ {exit_price}")
                        logger.info(f"Emergency exit: Closed {pos.symbol} {pos.quantity} @ {exit_price}")
                        
                    except Exception as e:
                        results["failed_positions"].append({
                            "symbol": pos.symbol,
                            "error": str(e),
                        })
                        logger.error(f"Emergency exit failed for {pos.symbol}: {e}")
            
            await self.db.commit()
            
            results["message"] = f"Closed {len(results['closed_positions'])} positions"
            if results["failed_positions"]:
                results["message"] += f", {len(results['failed_positions'])} failed"
                results["success"] = False
            
            await self._log(instance_id, "WARNING", f"Emergency exit completed: {results['message']}")
            logger.info(f"Emergency exit completed for instance {instance_id}: {results['message']}")
            
        except Exception as e:
            results["success"] = False
            results["message"] = f"Emergency exit failed: {str(e)}"
            logger.error(f"Emergency exit failed for instance {instance_id}: {e}")
        
        return results


async def run_strategy_instance(
    instance_id: UUID,
    parsed_strategy: Dict[str, Any],
    symbols: List[str],
    interval_seconds: int = 300,  # 5 minutes
):
    """
    Background task to run a strategy instance continuously.
    Called by Celery worker.
    """
    from database.session import get_db
    
    async for db in get_db():
        service = StrategyInstanceService(db)
        
        instance = await service.get_instance(instance_id)
        if not instance or instance.status != InstanceStatus.RUNNING:
            break
        
        for symbol in symbols:
            await service.execute_single_candle(
                instance_id=instance_id,
                parsed_strategy=parsed_strategy,
                symbol=symbol,
            )
        
        # Sleep until next interval
        import asyncio
        await asyncio.sleep(interval_seconds)
