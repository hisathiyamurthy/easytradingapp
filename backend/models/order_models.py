"""Database models for orders and trades."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, Float, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.base import Base
from schemas.enums import UserRole
from risk_management.risk_manager import RiskRuleType, RiskAction


class Order(Base):
    """Order model for persistent order storage."""
    __tablename__ = "orders"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(PGUUID(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), index=True)
    broker_account_id = Column(PGUUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="SET NULL"), index=True)
    
    client_order_id = Column(String(100), unique=True, index=True)
    idempotency_key = Column(String(100), unique=True, index=True)
    
    broker_order_id = Column(String(100), index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), nullable=False, default="NSE")
    
    # Options trading fields
    option_type = Column(String(5), nullable=True)  # CE or PE for options
    strike_price = Column(Float, nullable=True)  # Strike price for options
    expiry_date = Column(String(20), nullable=True)  # Option expiry (e.g., "25APR2024")
    
    side = Column(String(10), nullable=False)
    order_type = Column(String(20), nullable=False)
    status = Column(String(30), nullable=False, default="pending", index=True)
    product_type = Column(String(10), nullable=False, default="MIS")
    validity = Column(String(10), nullable=False, default="DAY")
    
    quantity = Column(Integer, nullable=False)
    filled_quantity = Column(Integer, default=0)
    remaining_quantity = Column(Integer, default=0)
    cancelled_quantity = Column(Integer, default=0)
    
    price = Column(Float)
    trigger_price = Column(Float)
    avg_fill_price = Column(Float)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    submitted_at = Column(DateTime(timezone=True))
    filled_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))
    expired_at = Column(DateTime(timezone=True))
    
    error_message = Column(Text)
    notes = Column(Text)
    
    order_metadata = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="orders")
    strategy = relationship("Strategy")
    broker_account = relationship("BrokerAccount")
    trades = relationship("Trade", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, symbol={self.symbol}, status={self.status})>"


class Trade(Base):
    """Trade model for persistent trade storage."""
    __tablename__ = "trades"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(PGUUID(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), index=True)
    broker_account_id = Column(PGUUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="SET NULL"), index=True)
    
    trade_id = Column(String(100), index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), nullable=False)
    
    side = Column(String(10), nullable=False)
    
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    
    gross_amount = Column(Float)
    brokerage = Column(Float, default=0)
    taxes = Column(Float, default=0)
    net_amount = Column(Float)
    
    is_reconciled = Column(Boolean, default=False)
    reconciliation_status = Column(String(20), default="pending")
    
    executed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="trades")
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy")
    broker_account = relationship("BrokerAccount")

    def __repr__(self):
        return f"<Trade(id={self.id}, symbol={self.symbol}, quantity={self.quantity}, price={self.price})>"


class ExecutionAuditLog(Base):
    """Immutable audit log for order execution actions."""
    __tablename__ = "execution_audit_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    action = Column(String(50), nullable=False, index=True)
    details = Column(JSON, nullable=False)
    
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    order = relationship("Order")
    user = relationship("User")

    def __repr__(self):
        return f"<ExecutionAuditLog(id={self.id}, action={self.action}, order_id={self.order_id})>"


class Position(Base):
    """Position model for tracking current positions."""
    __tablename__ = "positions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(PGUUID(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), index=True)
    broker_account_id = Column(PGUUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="SET NULL"), index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), nullable=False)
    product_type = Column(String(10), nullable=False)
    
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    
    current_price = Column(Float)
    market_value = Column(Float)
    unrealized_pnl = Column(Float, default=0)
    realized_pnl = Column(Float, default=0)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    strategy = relationship("Strategy")
    broker_account = relationship("BrokerAccount")

    def __repr__(self):
        return f"<Position(id={self.id}, symbol={self.symbol}, quantity={self.quantity}, pnl={self.unrealized_pnl})>"


class RiskBreach(Base):
    """Risk breach tracking."""
    __tablename__ = "risk_breaches"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(PGUUID(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), index=True)
    order_id = Column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), index=True)
    
    rule_type = Column(String(50), nullable=False, index=True)
    threshold = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    
    action_taken = Column(String(30), nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True))
    
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User")
    strategy = relationship("Strategy")
    order = relationship("Order")

    def __repr__(self):
        return f"<RiskBreach(id={self.id}, rule_type={self.rule_type}, resolved={self.is_resolved})>"


class RiskRule(Base):
    """Risk rule configuration model."""
    __tablename__ = "risk_rules"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    broker_account_id = Column(PGUUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=True, index=True)
    strategy_id = Column(PGUUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=True, index=True)

    rule_type = Column(SQLEnum(RiskRuleType), nullable=False, index=True)
    rule_name = Column(String(100), nullable=False)
    description = Column(Text)

    threshold_value = Column(Float, nullable=False)
    threshold_percentage = Column(Float)

    action = Column(SQLEnum(RiskAction), nullable=False, default=RiskAction.ALERT)
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    is_hard = Column(Boolean, nullable=False, default=False)

    priority = Column(Integer, nullable=False, default=100)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="risk_rules")

    def __repr__(self):
        return f"<RiskRule(id={self.id}, rule_type={self.rule_type}, is_enabled={self.is_enabled})>"