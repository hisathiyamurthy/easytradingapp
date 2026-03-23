"""Notification tasks for Celery worker."""
import logging
from datetime import datetime, timezone

from worker.celery import celery_app
from database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="worker.tasks.notifications.send_daily_summaries")
def send_daily_summaries(self):
    """Send daily summary emails to all users."""
    import asyncio
    
    async def _send():
        async with AsyncSessionLocal() as db:
            from services.notification_service import DailySummaryScheduler
            
            scheduler = DailySummaryScheduler(db)
            count = await scheduler.send_daily_summaries()
            
            logger.info(f"Sent {count} daily summaries")
            return {"summaries_sent": count}
    
    return asyncio.run(_send())


@celery_app.task(bind=True, name="worker.tasks.notifications.send_risk_alert")
def send_risk_alert(self, user_id: str, alert_type: str, message: str):
    """Send risk alert to user."""
    import asyncio
    from uuid import UUID
    
    async def _send():
        async with AsyncSessionLocal() as db:
            from services.notification_service import NotificationService
            from models.notification_models import NotificationType, NotificationPriority
            
            service = NotificationService(db)
            await service.send_notification(
                user_id=UUID(user_id),
                notification_type=NotificationType.RISK_ALERT,
                title=f"Risk Alert: {alert_type}",
                message=message,
                priority=NotificationPriority.CRITICAL,
            )
            
            return {"sent": True, "user_id": user_id}
    
    return asyncio.run(_send())


@celery_app.task(bind=True, name="worker.tasks.notifications.process_webhooks")
def process_webhooks(self):
    """Process pending webhook deliveries."""
    import asyncio
    
    async def _process():
        count = 0
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, and_
            from models.notification_models import WebhookDelivery
            
            result = await db.execute(
                select(WebhookDelivery).where(
                    and_(
                        WebhookDelivery.status == "pending",
                        WebhookDelivery.retry_count < 3,
                    )
                ).limit(100)
            )
            deliveries = result.scalars().all()
            
            for delivery in deliveries:
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            delivery.url,
                            json=delivery.payload,
                            timeout=10.0,
                        )
                        response.raise_for_status()
                    
                    delivery.status = "delivered"
                    delivery.delivered_at = datetime.now(timezone.utc)
                    count += 1
                except Exception as e:
                    logger.error(f"Webhook delivery failed: {e}")
                    delivery.retry_count += 1
                    delivery.last_error = str(e)
            
            await db.commit()
            return {"processed": count, "total": len(deliveries)}
    
    return asyncio.run(_process())