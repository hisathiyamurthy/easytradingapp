"""Risk tasks for Celery worker."""
import logging
from datetime import datetime, timezone

from worker.celery import celery_app
from database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="worker.tasks.risk.check_all_limits")
def check_all_limits(self):
    """Check risk limits for all active users."""
    import asyncio
    
    async def _check():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from models.auth_models import User
            
            result = await db.execute(
                select(User).where(User.is_active == True)
            )
            users = result.scalars().all()
            
            checked = 0
            for user in users:
                try:
                    await check_user_limits.delay(str(user.id))
                    checked += 1
                except Exception as e:
                    logger.error(f"Failed to check limits for user {user.id}: {e}")
            
            return {"users_checked": checked, "total": len(users)}
    
    return asyncio.run(_check())


@celery_app.task(bind=True, name="worker.tasks.risk.check_user_limits")
def check_user_limits(self, user_id: str):
    """Check risk limits for a specific user."""
    import asyncio
    from uuid import UUID
    
    async def _check():
        async with AsyncSessionLocal() as db:
            from risk_management.risk_manager import RiskManager, RiskRuleType
            
            risk_manager = RiskManager(db)
            
            breaches = await risk_manager.check_daily_loss_limit(UUID(user_id))
            if breaches:
                await risk_manager.log_breach(UUID(user_id), RiskRuleType.DAILY_LOSS_LIMIT, breaches)
            
            breaches = await risk_manager.check_order_rate_limit(UUID(user_id))
            if breaches:
                await risk_manager.log_breach(UUID(user_id), RiskRuleType.MAX_ORDERS_PER_MINUTE, breaches)
            
            return {"user_id": user_id, "breaches": len(breaches)}
    
    return asyncio.run(_check())


@celery_app.task(bind=True, name="worker.tasks.risk.check_position_limits")
def check_position_limits(self, user_id: str, symbol: str, quantity: int, price: float):
    """Check position limits for a new order."""
    import asyncio
    from uuid import UUID
    
    async def _check():
        async with AsyncSessionLocal() as db:
            from risk_management.risk_manager import RiskManager
            
            risk_manager = RiskManager(db)
            result = await risk_manager.check_position_limit(
                UUID(user_id),
                symbol,
                quantity,
                price,
            )
            
            return {"approved": result.approved, "message": result.message}
    
    return asyncio.run(_check())