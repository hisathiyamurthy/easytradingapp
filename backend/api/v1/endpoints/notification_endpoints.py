"""Notification API endpoints."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.security import get_current_user, TokenData
from services.notification_service import NotificationService
from models.notification_models import NotificationType, NotificationPriority

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationPreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    webhook_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    whatsapp_enabled: Optional[bool] = None
    whatsapp_phone: Optional[str] = None
    whatsapp_webhook_url: Optional[str] = None
    trade_notifications: Optional[bool] = None
    risk_notifications: Optional[bool] = None
    strategy_notifications: Optional[bool] = None
    daily_summary: Optional[bool] = None


class NotificationPreferencesResponse(BaseModel):
    email_enabled: bool
    push_enabled: bool
    webhook_enabled: bool
    webhook_url: Optional[str]
    telegram_enabled: bool
    telegram_chat_id: Optional[str]
    telegram_bot_token: Optional[str]
    whatsapp_enabled: bool
    whatsapp_phone: Optional[str]
    whatsapp_webhook_url: Optional[str]
    trade_notifications: bool
    risk_notifications: bool
    strategy_notifications: bool
    daily_summary: bool

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: UUID
    notification_type: str
    priority: str
    title: str
    message: str
    data: dict
    is_read: bool
    created_at: str

    class Config:
        from_attributes = True


class MarkReadRequest(BaseModel):
    notification_ids: list[UUID]


@router.get("", response_model=list[NotificationResponse])
async def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get user notifications."""
    service = NotificationService(db)
    notifications = await service.get_user_notifications(
        current_user.user_id, unread_only, limit, offset
    )
    return [
        NotificationResponse(
            id=n.id,
            notification_type=n.notification_type.value,
            priority=n.priority.value,
            title=n.title,
            message=n.message,
            data=n.data,
            is_read=n.is_read,
            created_at=n.created_at.isoformat(),
        )
        for n in notifications
    ]


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get count of unread notifications."""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.user_id)
    return {"unread_count": count}


@router.post("/mark-read")
async def mark_notifications_read(
    request: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Mark specific notifications as read."""
    service = NotificationService(db)
    count = 0
    for notif_id in request.notification_ids:
        if await service.mark_as_read(notif_id, current_user.user_id):
            count += 1
    return {"marked_read": count}


@router.post("/mark-all-read")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Mark all notifications as read."""
    service = NotificationService(db)
    count = await service.mark_all_as_read(current_user.user_id)
    return {"marked_read": count}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get notification preferences."""
    service = NotificationService(db)
    prefs = await service.get_user_preferences(current_user.user_id)
    
    if not prefs:
        return NotificationPreferencesResponse(
            email_enabled=True,
            push_enabled=True,
            webhook_enabled=False,
            webhook_url=None,
            telegram_enabled=False,
            telegram_chat_id=None,
            telegram_bot_token=None,
            whatsapp_enabled=False,
            whatsapp_phone=None,
            whatsapp_webhook_url=None,
            trade_notifications=True,
            risk_notifications=True,
            strategy_notifications=True,
            daily_summary=True,
        )
    
    return NotificationPreferencesResponse(
        email_enabled=prefs.email_enabled,
        push_enabled=prefs.push_enabled,
        webhook_enabled=prefs.webhook_enabled,
        webhook_url=prefs.webhook_url,
        telegram_enabled=prefs.telegram_enabled,
        telegram_chat_id=prefs.telegram_chat_id,
        telegram_bot_token=prefs.telegram_bot_token,
        whatsapp_enabled=prefs.whatsapp_enabled,
        whatsapp_phone=prefs.whatsapp_phone,
        whatsapp_webhook_url=prefs.whatsapp_webhook_url,
        trade_notifications=prefs.trade_notifications,
        risk_notifications=prefs.risk_notifications,
        strategy_notifications=prefs.strategy_notifications,
        daily_summary=prefs.daily_summary,
    )


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences(
    preferences: NotificationPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Update notification preferences."""
    service = NotificationService(db)
    prefs = await service.update_preferences(
        user_id=current_user.user_id,
        **preferences.model_dump(exclude_none=True),
    )
    
    return NotificationPreferencesResponse(
        email_enabled=prefs.email_enabled,
        push_enabled=prefs.push_enabled,
        webhook_enabled=prefs.webhook_enabled,
        webhook_url=prefs.webhook_url,
        telegram_enabled=prefs.telegram_enabled,
        telegram_chat_id=prefs.telegram_chat_id,
        telegram_bot_token=prefs.telegram_bot_token,
        whatsapp_enabled=prefs.whatsapp_enabled,
        whatsapp_phone=prefs.whatsapp_phone,
        whatsapp_webhook_url=prefs.whatsapp_webhook_url,
        trade_notifications=prefs.trade_notifications,
        risk_notifications=prefs.risk_notifications,
        strategy_notifications=prefs.strategy_notifications,
        daily_summary=prefs.daily_summary,
    )
