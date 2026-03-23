"""Reconciliation tasks for Celery worker."""
import logging
from datetime import datetime, timezone

from worker.celery import celery_app
from database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="worker.tasks.reconciliation.run_daily_reconciliation")
def run_daily_reconciliation(self):
    """Run daily trade reconciliation for all users."""
    import asyncio
    
    async def _run():
        async with AsyncSessionLocal() as db:
            from services.trade_reconciliation import ReconciliationScheduler
            
            scheduler = ReconciliationScheduler(db)
            result = await scheduler.run_daily_reconciliation()
            
            logger.info(f"Reconciliation complete: {result}")
            return result
    
    return asyncio.run(_run())


@celery_app.task(bind=True, name="worker.tasks.reconciliation.reconcile_user")
def reconcile_user(self, user_id: str, broker_account_id: str):
    """Reconcile trades for a specific user."""
    import asyncio
    from uuid import UUID
    
    async def _reconcile():
        async with AsyncSessionLocal() as db:
            from services.trade_reconciliation import TradeReconciliationService
            
            service = TradeReconciliationService(db)
            result = await service.reconcile_user_trades(
                user_id=UUID(user_id),
                broker_account_id=UUID(broker_account_id),
                from_date=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0),
                to_date=datetime.now(timezone.utc),
            )
            
            return {
                "user_id": user_id,
                "matched": result.matched,
                "discrepancies": result.missing_in_broker + result.missing_in_internal,
            }
    
    return asyncio.run(_reconcile())