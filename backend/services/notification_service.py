"""Notification service for sending alerts via multiple channels."""
import json
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.notification_models import (
    Notification,
    NotificationPreference,
    WebhookConfig,
    NotificationType,
    NotificationPriority,
)
from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing and sending notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        data: dict = None,
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            data=data or {},
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def send_notification(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        data: dict = None,
    ) -> Notification:
        """Create and send a notification through enabled channels."""
        notification = await self.create_notification(
            user_id, notification_type, title, message, priority, data
        )
        
        preferences = await self.get_user_preferences(user_id)
        
        if not preferences:
            return notification
        
        # Determine which category this notification belongs to
        category_enabled = self._check_category_enabled(preferences, notification_type)
        if not category_enabled:
            notification.is_sent = True
            await self.db.commit()
            return notification
        
        # Send via enabled channels
        email_types = [
            NotificationType.TRADE_EXECUTION,
            NotificationType.ORDER_FILLED,
            NotificationType.ORDER_CANCELLED,
            NotificationType.ORDER_REJECTED,
            NotificationType.RISK_ALERT,
            NotificationType.RISK_LIMIT_BREACH,
            NotificationType.DAILY_LOSS_LIMIT,
            NotificationType.DAILY_SUMMARY,
            NotificationType.ACCOUNT_ALERT,
        ]
        
        if preferences.email_enabled and notification_type in email_types:
            await self._send_email(user_id, title, message)
        
        if preferences.push_enabled:
            await self._send_push(user_id, title, message)
        
        if preferences.webhook_enabled:
            await self._send_webhook(user_id, notification)
        
        if preferences.telegram_enabled and preferences.telegram_chat_id and preferences.telegram_bot_token:
            await self._send_telegram(user_id, title, message, notification_type, priority)
        
        if preferences.whatsapp_enabled and preferences.whatsapp_webhook_url:
            await self._send_whatsapp(user_id, title, message, notification_type, priority)
        
        notification.is_sent = True
        notification.sent_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return notification

    def _check_category_enabled(
        self, preferences: NotificationPreference, notification_type: NotificationType
    ) -> bool:
        """Check if notification category is enabled."""
        trade_types = [
            NotificationType.TRADE_EXECUTION,
            NotificationType.ORDER_FILLED,
            NotificationType.ORDER_CANCELLED,
            NotificationType.ORDER_REJECTED,
        ]
        risk_types = [
            NotificationType.RISK_ALERT,
            NotificationType.RISK_LIMIT_BREACH,
            NotificationType.DAILY_LOSS_LIMIT,
            NotificationType.ACCOUNT_ALERT,
        ]
        strategy_types = [
            NotificationType.STRATEGY_STARTED,
            NotificationType.STRATEGY_STOPPED,
            NotificationType.STRATEGY_ERROR,
        ]
        summary_types = [
            NotificationType.DAILY_SUMMARY,
            NotificationType.SYSTEM_ALERT,
        ]
        
        if notification_type in trade_types:
            return preferences.trade_notifications
        elif notification_type in risk_types:
            return preferences.risk_notifications
        elif notification_type in strategy_types:
            return preferences.strategy_notifications
        elif notification_type in summary_types:
            return preferences.daily_summary
        
        return True

    async def get_user_preferences(self, user_id: UUID) -> Optional[NotificationPreference]:
        """Get user notification preferences."""
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def update_preferences(
        self,
        user_id: UUID,
        email_enabled: bool = None,
        push_enabled: bool = None,
        webhook_enabled: bool = None,
        webhook_url: str = None,
        telegram_enabled: bool = None,
        telegram_chat_id: str = None,
        telegram_bot_token: str = None,
        whatsapp_enabled: bool = None,
        whatsapp_phone: str = None,
        whatsapp_webhook_url: str = None,
        trade_notifications: bool = None,
        risk_notifications: bool = None,
        strategy_notifications: bool = None,
        daily_summary: bool = None,
    ) -> NotificationPreference:
        """Update user notification preferences."""
        prefs = await self.get_user_preferences(user_id)
        
        if not prefs:
            prefs = NotificationPreference(user_id=user_id)
            self.db.add(prefs)
        
        if email_enabled is not None:
            prefs.email_enabled = email_enabled
        if push_enabled is not None:
            prefs.push_enabled = push_enabled
        if webhook_enabled is not None:
            prefs.webhook_enabled = webhook_enabled
        if webhook_url is not None:
            prefs.webhook_url = webhook_url
        if telegram_enabled is not None:
            prefs.telegram_enabled = telegram_enabled
        if telegram_chat_id is not None:
            prefs.telegram_chat_id = telegram_chat_id
        if telegram_bot_token is not None:
            prefs.telegram_bot_token = telegram_bot_token
        if whatsapp_enabled is not None:
            prefs.whatsapp_enabled = whatsapp_enabled
        if whatsapp_phone is not None:
            prefs.whatsapp_phone = whatsapp_phone
        if whatsapp_webhook_url is not None:
            prefs.whatsapp_webhook_url = whatsapp_webhook_url
        if trade_notifications is not None:
            prefs.trade_notifications = trade_notifications
        if risk_notifications is not None:
            prefs.risk_notifications = risk_notifications
        if strategy_notifications is not None:
            prefs.strategy_notifications = strategy_notifications
        if daily_summary is not None:
            prefs.daily_summary = daily_summary
        
        await self.db.commit()
        await self.db.refresh(prefs)
        return prefs

    async def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Get user notifications."""
        query = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """Mark a notification as read."""
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if notification:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.db.commit()
            return True
        return False

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all user notifications as read."""
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
        )
        notifications = result.scalars().all()
        
        count = 0
        for notif in notifications:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            count += 1
        
        await self.db.commit()
        return count

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications."""
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
        )
        return len(result.scalars().all())

    async def _send_email(self, user_id: UUID, title: str, message: str) -> bool:
        """Send email notification via SendGrid or SMTP."""
        from sqlalchemy import select
        from models.auth_models import User
        
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.email:
            return False
        
        if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
            return await self._send_smtp_email(user.email, title, message)
        elif settings.SENDGRID_API_KEY:
            return await self._sendgrid_email(user.email, title, message)
        
        logger.info(f"[EMAIL] To {user.email}: {title} - {message}")
        return True
    
    async def _send_smtp_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email via SMTP."""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.EMAIL_FROM or settings.SMTP_USER
            msg["To"] = to_email
            msg["Subject"] = subject
            
            msg.attach(MIMEText(body, "html"))
            
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"[SMTP] Email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"[SMTP] Failed to send email: {e}")
            return False
    
    async def _sendgrid_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email via SendGrid API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "personalizations": [{"to": [{"email": to_email}]}],
                        "from": {"email": settings.EMAIL_FROM or "noreply@easytradingapp.com"},
                        "subject": subject,
                        "content": [{"type": "text/html", "value": body}],
                    },
                    timeout=10.0,
                )
                return response.status_code in [200, 202, 201]
        except Exception as e:
            logger.error(f"[SendGrid] Failed to send email: {e}")
            return False

    async def _send_push(self, user_id: UUID, title: str, message: str) -> bool:
        """Send push notification (placeholder - integrate with Firebase)."""
        logger.info(f"[PUSH] To user {user_id}: {title} - {message}")
        return True

    async def _send_webhook(self, user_id: UUID, notification: Notification) -> bool:
        """Send webhook notification to configured endpoints."""
        result = await self.db.execute(
            select(WebhookConfig).where(
                and_(
                    WebhookConfig.user_id == user_id,
                    WebhookConfig.is_active == True,
                )
            )
        )
        webhooks = result.scalars().all()
        
        payload = {
            "id": str(notification.id),
            "type": notification.notification_type.value,
            "priority": notification.priority.value,
            "title": notification.title,
            "message": notification.message,
            "data": notification.data,
            "timestamp": notification.created_at.isoformat(),
        }
        
        for webhook in webhooks:
            if notification.notification_type.value in webhook.events or not webhook.events:
                await self._deliver_webhook(webhook, payload)
        
        return True

    async def _deliver_webhook(self, webhook: WebhookConfig, payload: dict) -> bool:
        """Deliver webhook payload to endpoint."""
        try:
            body = json.dumps(payload)
            signature = ""
            
            if webhook.secret:
                signature = hmac.new(
                    webhook.secret.encode(),
                    body.encode(),
                    hashlib.sha256,
                ).hexdigest()
            
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
                "X-Webhook-Event": payload["type"],
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    content=body,
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
            
            logger.info(f"Webhook delivered to {webhook.url}")
            return True
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
            return False

    async def _send_telegram(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority,
    ) -> bool:
        """Send notification via Telegram bot."""
        prefs = await self.get_user_preferences(user_id)
        if not prefs or not prefs.telegram_bot_token or not prefs.telegram_chat_id:
            return False
        
        try:
            priority_emoji = {
                NotificationPriority.CRITICAL: "🔴",
                NotificationPriority.HIGH: "🟠",
                NotificationPriority.MEDIUM: "🟡",
                NotificationPriority.LOW: "⚪",
            }.get(priority, "")
            
            type_emoji = {
                NotificationType.TRADE_EXECUTION: "📊",
                NotificationType.ORDER_FILLED: "✅",
                NotificationType.ORDER_CANCELLED: "❌",
                NotificationType.ORDER_REJECTED: "🚫",
                NotificationType.RISK_ALERT: "⚠️",
                NotificationType.RISK_LIMIT_BREACH: "🚨",
                NotificationType.DAILY_LOSS_LIMIT: "📉",
                NotificationType.STRATEGY_STARTED: "🚀",
                NotificationType.STRATEGY_STOPPED: "⏹️",
                NotificationType.STRATEGY_ERROR: "💥",
                NotificationType.DAILY_SUMMARY: "📋",
                NotificationType.ACCOUNT_ALERT: "💰",
            }.get(notification_type, "📬")
            
            text = f"{priority_emoji} *{title}*\n\n{message}\n\n_{type_emoji} EasyTradingApp_"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{prefs.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": prefs.telegram_chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                    timeout=10.0,
                )
                
                if response.status_code == 200:
                    logger.info(f"[TELEGRAM] Notification sent to chat {prefs.telegram_chat_id}")
                    return True
                else:
                    logger.warning(f"[TELEGRAM] Failed to send: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"[TELEGRAM] Error sending notification: {e}")
            return False

    async def _send_whatsapp(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority,
    ) -> bool:
        """Send notification via WhatsApp webhook."""
        prefs = await self.get_user_preferences(user_id)
        if not prefs or not prefs.whatsapp_webhook_url:
            return False
        
        try:
            priority_text = {
                NotificationPriority.CRITICAL: "CRITICAL",
                NotificationPriority.HIGH: "HIGH",
                NotificationPriority.MEDIUM: "MEDIUM",
                NotificationPriority.LOW: "LOW",
            }.get(priority, "MEDIUM")
            
            payload = {
                "phone": prefs.whatsapp_phone or "",
                "title": title,
                "message": message,
                "priority": priority_text,
                "type": notification_type.value,
                "source": "EasyTradingApp",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            headers = {
                "Content-Type": "application/json",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    prefs.whatsapp_webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info(f"[WHATSAPP] Notification sent via webhook")
                    return True
                else:
                    logger.warning(f"[WHATSAPP] Failed to send: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"[WHATSAPP] Error sending notification: {e}")
            return False


class TradeNotificationHelper:
    """Helper class for sending trade-related notifications."""

    def __init__(self, notification_service: NotificationService):
        self.service = notification_service

    async def notify_order_filled(
        self, user_id: UUID, symbol: str, quantity: int, side: str, price: float
    ):
        """Send notification when order is filled."""
        await self.service.send_notification(
            user_id=user_id,
            notification_type=NotificationType.ORDER_FILLED,
            title=f"Order Filled",
            message=f"Your {side} order for {quantity} {symbol} has been filled at ₹{price}",
            priority=NotificationPriority.HIGH,
            data={"symbol": symbol, "quantity": quantity, "side": side, "price": price},
        )

    async def notify_order_rejected(
        self, user_id: UUID, symbol: str, reason: str
    ):
        """Send notification when order is rejected."""
        await self.service.send_notification(
            user_id=user_id,
            notification_type=NotificationType.ORDER_REJECTED,
            title=f"Order Rejected",
            message=f"Your order for {symbol} was rejected: {reason}",
            priority=NotificationPriority.HIGH,
            data={"symbol": symbol, "reason": reason},
        )

    async def notify_risk_alert(
        self, user_id: UUID, message: str, limit_type: str
    ):
        """Send risk alert notification."""
        await self.service.send_notification(
            user_id=user_id,
            notification_type=NotificationType.RISK_ALERT,
            title=f"Risk Alert: {limit_type}",
            message=message,
            priority=NotificationPriority.CRITICAL,
            data={"limit_type": limit_type},
        )

    async def notify_daily_summary(
        self, user_id: UUID, trades: int, pnl: float, day: str
    ):
        """Send daily trading summary."""
        pnl_str = f"+₹{pnl}" if pnl >= 0 else f"-₹{abs(pnl)}"
        await self.service.send_notification(
            user_id=user_id,
            notification_type=NotificationType.DAILY_SUMMARY,
            title=f"Daily Summary - {day}",
            message=f"Trades: {trades} | P&L: {pnl_str}",
            priority=NotificationPriority.MEDIUM,
            data={"trades": trades, "pnl": pnl, "day": day},
        )


class DailySummaryScheduler:
    """Scheduler for sending daily summary emails."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_service = NotificationService(db)
    
    async def send_daily_summaries(self) -> int:
        """Send daily summary to all active users who have it enabled."""
        from sqlalchemy import select
        from models.auth_models import User
        from models.notification_models import NotificationPreference
        
        result = await self.db.execute(
            select(User).where(User.is_active == True)
        )
        users = result.scalars().all()
        
        count = 0
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        for user in users:
            prefs = await self.notification_service.get_user_preferences(user.id)
            
            if prefs and prefs.daily_summary and prefs.email_enabled:
                from services.report_service import ReportService
                report_service = ReportService(self.db)
                
                summary_data = await report_service.get_daily_summary(user.id, today)
                
                html_body = self._generate_daily_summary_html(user, summary_data)
                
                await self.notification_service._send_email(
                    user.id,
                    f"Daily Trading Summary - {today}",
                    html_body,
                )
                count += 1
        
        return count
    
    def _generate_daily_summary_html(self, user, data) -> str:
        """Generate HTML email body for daily summary."""
        trades = data.get("total_trades", 0)
        pnl = data.get("total_pnl", 0)
        pnl_str = f"+₹{pnl:.2f}" if pnl >= 0 else f"-₹{abs(pnl):.2f}"
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Daily Trading Summary</h2>
            <p>Hello {user.first_name or 'Trader'},</p>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Performance</h3>
                <p><strong>Total Trades:</strong> {trades}</p>
                <p><strong>P&L:</strong> <span style="color: {'green' if pnl >= 0 else 'red'}; font-size: 18px;">{pnl_str}</span></p>
                <p><strong>Win Rate:</strong> {data.get('win_rate', 0):.1f}%</p>
            </div>
            
            <p style="color: #666; font-size: 12px;">
                This is an automated message from EasyTradingApp.<br>
                To unsubscribe, update your notification preferences in the app.
            </p>
        </body>
        </html>
        """
