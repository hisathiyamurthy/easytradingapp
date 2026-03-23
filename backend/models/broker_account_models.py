"""Database models for broker accounts."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, BYTEA
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.base import Base
from broker_integrations.base import BrokerName


class BrokerAccount(Base):
    """Broker account model for storing encrypted API credentials."""
    __tablename__ = "broker_accounts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_name = Column(SQLEnum(BrokerName), nullable=False, index=True)
    account_id = Column(String(100), nullable=False)
    account_name = Column(String(255))
    
    encrypted_api_key = Column(BYTEA, nullable=False)
    encrypted_api_secret = Column(BYTEA, nullable=False)
    encrypted_api_passphrase = Column(BYTEA)
    
    webhook_url = Column(String(500))
    
    is_paper_trading = Column(Boolean, nullable=False, default=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    last_sync_at = Column(DateTime(timezone=True))
    last_health_check_at = Column(DateTime(timezone=True))
    health_status = Column(String(20), default="unknown")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="broker_accounts")

    def __repr__(self):
        return f"<BrokerAccount(id={self.id}, broker_name={self.broker_name}, account_id={self.account_id})>"
