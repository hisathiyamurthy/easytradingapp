"""Strategy version history models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.base import Base


class StrategyVersion(Base):
    """Stores strategy version history."""

    __tablename__ = "strategy_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    version = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(50))
    
    parameters = Column(JSON, default=dict)
    entry_conditions = Column(JSON, default=list)
    exit_conditions = Column(JSON, default=list)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    change_summary = Column(Text, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)

    def __repr__(self):
        return f"<StrategyVersion(id={self.id}, strategy_id={self.strategy_id}, version={self.version})>"
