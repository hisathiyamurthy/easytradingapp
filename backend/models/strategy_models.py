"""Strategy models."""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, ForeignKey, Text, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.base import Base


class StrategyType(str, Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    GRID = "grid"
    DCA = "dca"


class StrategyStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "validated"
    BACKTESTED = "backtested"
    PAPER_TRADING = "paper_trading"
    LIVE = "live"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(50), nullable=False)
    status = Column(String(20), default="DRAFT", nullable=False)
    
    parameters = Column(JSON, default=dict)
    is_paper_trading = Column(Boolean, default=True, nullable=False)
    approved = Column(Boolean, default=False, nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="strategies", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])


class StrategyParameter(Base):
    __tablename__ = "strategy_parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    value = Column(JSON)
    param_type = Column(String(50), default="string")
    
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)

    strategy = relationship("Strategy", back_populates="strategy_params")


class StrategyLog(Base):
    __tablename__ = "strategy_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    log_level = Column(String(20), default="INFO")
    message = Column(Text, nullable=False)
    data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)

    strategy = relationship("Strategy", back_populates="logs")


class StrategyWatchlist(Base):
    __tablename__ = "strategy_watchlist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)

    user = relationship("User", back_populates="watchlist")
    strategy = relationship("Strategy")


# Add relationships to Strategy model
Strategy.strategy_params = relationship("StrategyParameter", back_populates="strategy", cascade="all, delete-orphan")
Strategy.logs = relationship("StrategyLog", back_populates="strategy", cascade="all, delete-orphan")


class UserStrategyAssignment(Base):
    """
    Maps strategies to users - admin assigns strategies to users.
    Only assigned strategies can be accessed by users.
    """
    __tablename__ = "user_strategy_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Assignment details
    is_default = Column(Boolean, default=False, nullable=False)  # Auto-assigned to new users
    is_active = Column(Boolean, default=True, nullable=False)  # Can be deactivated without removing
    
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    strategy = relationship("Strategy")
    assigner = relationship("User", foreign_keys=[assigned_by])
