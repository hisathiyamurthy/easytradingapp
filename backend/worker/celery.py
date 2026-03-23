"""Celery configuration and worker tasks."""
import os
import logging
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "easytradingapp",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "worker.tasks.trading",
        "worker.tasks.notifications",
        "worker.tasks.reconciliation",
        "worker.tasks.risk",
        "worker.tasks.analytics",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    beat_schedule={
        "run-daily-reconciliation": {
            "task": "worker.tasks.reconciliation.run_daily_reconciliation",
            "schedule": crontab(hour=23, minute=30),
        },
        "cleanup-expired-sessions": {
            "task": "worker.tasks.auth.cleanup_expired_sessions",
            "schedule": crontab(hour="*", minute=0),
        },
        "send-daily-summaries": {
            "task": "worker.tasks.notifications.send_daily_summaries",
            "schedule": crontab(hour=18, minute=0),
        },
        "update-market-data-cache": {
            "task": "worker.tasks.market_data.update_cache",
            "schedule": 60.0,
        },
        "check-risk-limits": {
            "task": "worker.tasks.risk.check_all_limits",
            "schedule": 300.0,
        },
        "generate-daily-analytics": {
            "task": "worker.tasks.analytics.generate_daily_analytics",
            "schedule": crontab(hour=23, minute=45),
        },
    },
)


@celery_app.task(bind=True, name="health_check")
def health_check(self):
    """Health check task."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    celery_app.start()