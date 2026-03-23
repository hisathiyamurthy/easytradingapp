"""Notification models."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.base import Base


class NotificationType(str, Enum):
    TRADE_EXECUTION = "trade_execution"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    RISK_ALERT = "risk_alert"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STOPPED = "strategy_stopped"
    STRATEGY_ERROR = "strategy_error"
    SYSTEM_ALERT = "system_alert"
    DAILY_SUMMARY = "daily_summary"
    ACCOUNT_ALERT = "account_alert"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    WEBHOOK = "webhook"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.MEDIUM, nullable=False)
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    data = Column(JSON, default=dict)
    
    is_read = Column(Boolean, default=False, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)
    read_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.notification_type}, user_id={self.user_id})>"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    email_enabled = Column(Boolean, default=True, nullable=False)
    push_enabled = Column(Boolean, default=True, nullable=False)
    webhook_enabled = Column(Boolean, default=False, nullable=False)
    webhook_url = Column(String(500))
    
    telegram_enabled = Column(Boolean, default=False, nullable=False)
    telegram_chat_id = Column(String(100))
    telegram_bot_token = Column(String(255))
    
    whatsapp_enabled = Column(Boolean, default=False, nullable=False)
    whatsapp_phone = Column(String(20))
    whatsapp_webhook_url = Column(String(500))
    
    trade_notifications = Column(Boolean, default=True, nullable=False)
    risk_notifications = Column(Boolean, default=True, nullable=False)
    strategy_notifications = Column(Boolean, default=True, nullable=False)
    daily_summary = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)

    def __repr__(self):
        return f"<NotificationPreference(user_id={self.user_id})>"


class WebhookConfig(Base):
    __tablename__ = "webhook_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(255))
    
    events = Column(JSON, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)

    def __repr__(self):
        return f"<WebhookConfig(id={self.id}, name={self.name})>"
