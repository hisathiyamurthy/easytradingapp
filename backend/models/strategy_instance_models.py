"""Database models for strategy instances and trading."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, Float, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.base import Base


class InstanceStatus(str, Enum):
    """Status of a strategy instance."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"


class InstanceMode(str, Enum):
    """Trading mode for strategy instance."""
    PAPER = "paper"
    LIVE = "live"


class InstanceExitReason(str, Enum):
    """Reason for closing a trade."""
    TARGET = "target"
    STOPLOSS = "stoploss"
    SIGNAL = "signal"
    END_OF_DATA = "end_of_data"
    MANUAL = "manual"
    ERROR = "error"


class UserStrategyInstance(Base):
    """
    Per-user strategy instance - tracks a running strategy for a specific user.
    
    Each user can run multiple strategies, each tracked as a separate instance
    with its own capital allocation and performance metrics.
    """
    __tablename__ = "user_strategy_instances"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(PGUUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Instance configuration
    name = Column(String(255), nullable=False)
    capital = Column(Float, nullable=False, default=100000.0)
    allocated_capital = Column(Float, nullable=False, default=100000.0)
    
    # Status and mode
    status = Column(SQLEnum(InstanceStatus), default=InstanceStatus.DRAFT, nullable=False, index=True)
    mode = Column(SQLEnum(InstanceMode), default=InstanceMode.PAPER, nullable=False)
    
    # Execution settings
    execution_mode = Column(String(20), default="realtime")  # realtime, candle_close, delayed
    execution_delay_seconds = Column(Integer, default=0)  # Delay in seconds for delayed mode
    
    # Performance tracking
    current_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    
    trades_count = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    max_drawdown = Column(Float, default=0.0)
    max_profit = Column(Float, default=0.0)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True))
    paused_at = Column(DateTime(timezone=True))
    stopped_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="strategy_instances")
    strategy = relationship("Strategy")
    trades = relationship("InstanceTrade", back_populates="instance", cascade="all, delete-orphan")
    positions = relationship("InstancePosition", back_populates="instance", cascade="all, delete-orphan")
    logs = relationship("InstanceLog", back_populates="instance", cascade="all, delete-orphan")

    @property
    def win_rate(self) -> float:
        if self.trades_count == 0:
            return 0.0
        return (self.winning_trades / self.trades_count) * 100

    def __repr__(self):
        return f"<UserStrategyInstance(id={self.id}, user_id={self.user_id}, status={self.status})>"


class InstanceTrade(Base):
    """
    Trade record for a strategy instance.
    Persists paper trading results to the database.
    """
    __tablename__ = "instance_trades"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(PGUUID(as_uuid=True), ForeignKey("user_strategy_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), nullable=False, default="NSE")
    
    side = Column(String(10), nullable=False)  # buy, sell
    
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    
    # P&L
    pnl = Column(Float)
    pnl_percent = Column(Float)
    commission = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)
    
    # Exit info
    exit_reason = Column(SQLEnum(InstanceExitReason))
    
    # Timestamps
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True))
    
    # Strategy context
    entry_signal = Column(Text)
    exit_signal = Column(Text)
    
    # Broker info (for live trading)
    broker_order_id = Column(String(50), index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    instance = relationship("UserStrategyInstance", back_populates="trades")
    user = relationship("User")

    def __repr__(self):
        return f"<InstanceTrade(id={self.id}, symbol={self.symbol}, side={self.side}, pnl={self.pnl})>"


class InstancePosition(Base):
    """
    Open position for a strategy instance.
    Tracks current holdings in paper trading.
    """
    __tablename__ = "instance_positions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(PGUUID(as_uuid=True), ForeignKey("user_strategy_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), nullable=False, default="NSE")
    
    side = Column(String(10), nullable=False)  # long, short
    
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float)
    
    unrealized_pnl = Column(Float, default=0.0)
    
    is_open = Column(Boolean, default=True, nullable=False)
    
    # Broker info (for live trading)
    broker_order_id = Column(String(50), index=True)
    
    # Stop loss and target (for live trading)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    sl_order_id = Column(String(50), nullable=True, index=True)
    tp_order_id = Column(String(50), nullable=True, index=True)
    
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    instance = relationship("UserStrategyInstance", back_populates="positions")
    user = relationship("User")

    def __repr__(self):
        return f"<InstancePosition(id={self.id}, symbol={self.symbol}, quantity={self.quantity})>"


class InstanceLog(Base):
    """
    Log entries for a strategy instance.
    Tracks execution events, errors, and signals.
    """
    __tablename__ = "instance_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(PGUUID(as_uuid=True), ForeignKey("user_strategy_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    
    level = Column(String(20), default="INFO")  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    
    data = Column(JSON)  # Additional context
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    instance = relationship("UserStrategyInstance", back_populates="logs")

    def __repr__(self):
        return f"<InstanceLog(id={self.id}, level={self.level})>"


class StrategyPerformance(Base):
    """
    Aggregated daily performance metrics for strategy instances.
    Used for analytics and reporting.
    """
    __tablename__ = "strategy_performance"
    __table_args__ = (
        UniqueConstraint('instance_id', 'date', name='uq_instance_date'),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(PGUUID(as_uuid=True), ForeignKey("user_strategy_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Daily metrics
    trades_count = Column(Integer, default=0)
    pnl = Column(Float, default=0.0)
    pnl_percent = Column(Float, default=0.0)
    
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    open_positions = Column(Integer, default=0)
    closed_positions = Column(Integer, default=0)
    
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)
    
    # Cumulative metrics
    cumulative_pnl = Column(Float, default=0.0)
    cumulative_return = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    instance = relationship("UserStrategyInstance")
    user = relationship("User")

    def __repr__(self):
        return f"<StrategyPerformance(id={self.id}, date={self.date}, pnl={self.pnl})>"


# Add relationships to User model
from models.auth_models import User
User.strategy_instances = relationship("UserStrategyInstance", back_populates="user", cascade="all, delete-orphan")
