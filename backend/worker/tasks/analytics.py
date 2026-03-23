"""Analytics tasks for Celery worker."""
import logging
from datetime import datetime, timezone, timedelta

from worker.celery import celery_app
from database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="worker.tasks.analytics.generate_daily_analytics")
def generate_daily_analytics(self):
    """Generate daily analytics for all users."""
    import asyncio
    
    async def _generate():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from models.auth_models import User
            
            result = await db.execute(
                select(User).where(User.is_active == True)
            )
            users = result.scalars().all()
            
            generated = 0
            for user in users:
                try:
                    await generate_user_analytics.delay(str(user.id))
                    generated += 1
                except Exception as e:
                    logger.error(f"Failed to generate analytics for user {user.id}: {e}")
            
            return {"analytics_generated": generated, "total_users": len(users)}
    
    return asyncio.run(_generate())


@celery_app.task(bind=True, name="worker.tasks.analytics.generate_user_analytics")
def generate_user_analytics(self, user_id: str):
    """Generate analytics for a specific user."""
    import asyncio
    from uuid import UUID
    
    async def _generate():
        async with AsyncSessionLocal() as db:
            from services.report_service import ReportService
            
            service = ReportService(db)
            today = datetime.now(timezone.utc)
            
            summary = await service.get_daily_summary(UUID(user_id), today.strftime("%Y-%m-%d"))
            
            return {
                "user_id": user_id,
                "date": today.isoformat(),
                "total_trades": summary.get("total_trades", 0),
                "total_pnl": summary.get("total_pnl", 0),
                "win_rate": summary.get("win_rate", 0),
            }
    
    return asyncio.run(_generate())


@celery_app.task(bind=True, name="worker.tasks.analytics.calculate_portfolio_metrics")
def calculate_portfolio_metrics(self, user_id: str):
    """Calculate portfolio-level metrics."""
    import asyncio
    from uuid import UUID
    
    async def _calculate():
        async with AsyncSessionLocal() as db:
            from services.portfolio_service import PortfolioService
            
            service = PortfolioService(db)
            metrics = await service.calculate_portfolio_metrics(UUID(user_id))
            
            return metrics
    
    return asyncio.run(_calculate())


@celery_app.task(bind=True, name="worker.tasks.market_data.update_cache")
def update_market_data_cache(self):
    """Update cached market data."""
    import asyncio
    
    async def _update():
        async with AsyncSessionLocal() as db:
            from services.price_cache_service import PriceCacheService
            
            cache_service = PriceCacheService(use_redis=True)
            await cache_service.cleanup_expired()
            
            return {"status": "success"}
    
    return asyncio.run(_update())


@celery_app.task(bind=True, name="worker.tasks.auth.cleanup_expired_sessions")
def cleanup_expired_sessions(self):
    """Clean up expired user sessions."""
    import asyncio
    
    async def _cleanup():
        async with AsyncSessionLocal() as db:
            from services.auth_service import SessionManager
            
            session_manager = SessionManager(db)
            count = await session_manager.cleanup_expired_sessions()
            
            logger.info(f"Cleaned up {count} expired sessions")
            return {"sessions_cleaned": count}
    
    return asyncio.run(_cleanup())