"""Trading tasks for Celery worker."""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from worker.celery import celery_app
from database.session import AsyncSessionLocal
from services.order_repository import OrderRepository, TradeRepository
from services.trade_reconciliation import TradeReconciliationService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="worker.tasks.trading.run_strategy")
def run_strategy(self, strategy_id: str):
    """Execute a trading strategy."""
    import asyncio
    
    async def _run():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from models.strategy_models import Strategy, StrategyStatus
            from models.order_models import Order
            
            # Get strategy
            result = await db.execute(
                select(Strategy).where(Strategy.id == UUID(strategy_id))
            )
            strategy = result.scalar_one_or_none()
            
            if not strategy:
                return {"error": "Strategy not found"}
            
            if strategy.status != StrategyStatus.ACTIVE:
                return {"error": f"Strategy is not active (status: {strategy.status})"}
            
            # Get watchlist symbols
            watchlist_result = await db.execute(
                select(Strategy).where(Strategy.id == UUID(strategy_id))
            )
            
            # Mark strategy as running
            strategy.status = StrategyStatus.ACTIVE
            await db.commit()
            
            try:
                # Import strategy engine
                from strategy_engine.executor import StrategyExecutor
                
                executor = StrategyExecutor(db)
                signals = await executor.generate_signals(strategy)
                
                executed_orders = 0
                for signal in signals:
                    if signal.action == "buy" or signal.action == "sell":
                        # Create order
                        order = Order(
                            user_id=strategy.user_id,
                            strategy_id=strategy.id,
                            broker_account_id=strategy.broker_account_id,
                            symbol=signal.symbol,
                            exchange=signal.exchange or "NSE",
                            side=signal.action,
                            order_type="market",
                            product_type="MIS",
                            validity="DAY",
                            quantity=signal.quantity or 1,
                            status="pending",
                        )
                        db.add(order)
                        executed_orders += 1
                
                await db.commit()
                
                return {
                    "status": "success",
                    "strategy_id": strategy_id,
                    "signals_generated": len(signals),
                    "orders_created": executed_orders,
                }
                
            except Exception as e:
                logger.error(f"Strategy execution error: {e}")
                strategy.status = StrategyStatus.ERROR
                await db.commit()
                return {"error": str(e)}
    
    return asyncio.run(_run())


@celery_app.task(bind=True, name="worker.tasks.trading.sync_order_status")
def sync_order_status(self, order_id: str):
    """Sync order status with broker."""
    import asyncio
    
    async def _sync():
        async with AsyncSessionLocal() as db:
            from services.broker_service import BrokerService
            from sqlalchemy import select
            from models.order_models import Order
            
            result = await db.execute(
                select(Order).where(Order.id == UUID(order_id))
            )
            order = result.scalar_one_or_none()
            
            if not order or not order.broker_account_id:
                return {"error": "Order not found"}
            
            broker_service = BrokerService(db)
            status = await broker_service.get_order_status(
                str(order.broker_account_id),
                order.broker_order_id,
            )
            
            order_repo = OrderRepository(db)
            await order_repo.update_order(
                UUID(order_id),
                {
                    "status": status.get("status"),
                    "filled_quantity": status.get("filled_quantity", 0),
                    "avg_fill_price": status.get("avg_fill_price"),
                },
            )
            
            return {"status": "success", "order_id": order_id}
    
    return asyncio.run(_sync())


@celery_app.task(bind=True, name="worker.tasks.trading.process_pending_orders")
def process_pending_orders(self):
    """Process all pending orders."""
    import asyncio
    
    async def _process():
        count = 0
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from models.order_models import Order
            
            result = await db.execute(
                select(Order).where(Order.status == "pending")
            )
            orders = result.scalars().all()
            
            for order in orders:
                try:
                    sync_order_status.delay(str(order.id))
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to sync order {order.id}: {e}")
            
            return {"processed": count, "total": len(orders)}
    
    return asyncio.run(_process())


@celery_app.task(bind=True, name="worker.tasks.trading.calculate_positions")
def calculate_positions(self, user_id: str):
    """Calculate and update user positions."""
    import asyncio
    
    async def _calculate():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from models.order_models import Trade
            from services.order_repository import PositionRepository
            
            result = await db.execute(
                select(Trade).where(Trade.user_id == UUID(user_id))
            )
            trades = result.scalars().all()
            
            position_repo = PositionRepository(db)
            
            symbol_positions = {}
            for trade in trades:
                key = (trade.symbol, trade.exchange, trade.side)
                if key not in symbol_positions:
                    symbol_positions[key] = {"quantity": 0, "total_cost": 0}
                
                if trade.side == "buy":
                    symbol_positions[key]["quantity"] += trade.quantity
                    symbol_positions[key]["total_cost"] += trade.quantity * trade.price
                else:
                    symbol_positions[key]["quantity"] -= trade.quantity
                    symbol_positions[key]["total_cost"] -= trade.quantity * trade.price
            
            for (symbol, exchange, side), data in symbol_positions.items():
                if data["quantity"] > 0:
                    avg_price = data["total_cost"] / data["quantity"] if data["quantity"] > 0 else 0
                    await position_repo.upsert_position(
                        UUID(user_id),
                        symbol,
                        exchange,
                        "MIS",
                        {"quantity": data["quantity"], "avg_price": avg_price},
                    )
            
            return {"positions_updated": len(symbol_positions)}
    
    return asyncio.run(_calculate())