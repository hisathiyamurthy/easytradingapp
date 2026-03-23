"""Order repository for database persistence."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.sql import func

from models.order_models import Order, Trade, ExecutionAuditLog, Position, RiskBreach


class OrderRepository:
    """Repository for order database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_order(self, order_data: dict) -> Order:
        """Create a new order in the database."""
        order = Order(**order_data)
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def get_order_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get order by ID."""
        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_order_by_client_id(self, client_order_id: str) -> Optional[Order]:
        """Get order by client order ID."""
        result = await self.db.execute(
            select(Order).where(Order.client_order_id == client_order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_order_by_idempotency_key(self, idempotency_key: str) -> Optional[Order]:
        """Get order by idempotency key to prevent duplicates."""
        result = await self.db.execute(
            select(Order).where(Order.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()
    
    async def update_order(self, order_id: UUID, updates: dict) -> Optional[Order]:
        """Update order fields."""
        order = await self.get_order_by_id(order_id)
        if not order:
            return None
        
        for key, value in updates.items():
            if hasattr(order, key):
                setattr(order, key, value)
        
        order.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def get_user_orders(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Order]:
        """Get user's orders with optional filters."""
        query = select(Order).where(Order.user_id == user_id)
        
        if status:
            query = query.where(Order.status == status)
        if symbol:
            query = query.where(Order.symbol == symbol)
        
        query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def add_audit_log(self, order_id: UUID, user_id: UUID, action: str, details: dict, ip_address: Optional[str] = None) -> ExecutionAuditLog:
        """Add an execution audit log entry."""
        audit_log = ExecutionAuditLog(
            order_id=order_id,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
        )
        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)
        return audit_log


class TradeRepository:
    """Repository for trade database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_trade(self, trade_data: dict) -> Trade:
        """Create a new trade in the database."""
        trade = Trade(**trade_data)
        self.db.add(trade)
        await self.db.commit()
        await self.db.refresh(trade)
        return trade
    
    async def get_trade_by_id(self, trade_id: UUID) -> Optional[Trade]:
        """Get trade by ID."""
        result = await self.db.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        return result.scalar_one_or_none()
    
    async def get_trade_by_broker_id(self, broker_trade_id: str) -> Optional[Trade]:
        """Get trade by broker trade ID."""
        result = await self.db.execute(
            select(Trade).where(Trade.trade_id == broker_trade_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_trades(
        self,
        user_id: UUID,
        symbol: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Trade]:
        """Get user's trades with optional filters."""
        query = select(Trade).where(Trade.user_id == user_id)
        
        if symbol:
            query = query.where(Trade.symbol == symbol)
        if from_date:
            query = query.where(Trade.executed_at >= from_date)
        if to_date:
            query = query.where(Trade.executed_at <= to_date)
        
        query = query.order_by(Trade.executed_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def mark_reconciled(self, trade_id: UUID, status: str = "matched") -> bool:
        """Mark trade as reconciled."""
        trade = await self.get_trade_by_id(trade_id)
        if not trade:
            return False
        
        trade.is_reconciled = True
        trade.reconciliation_status = status
        await self.db.commit()
        return True
    
    async def get_unreconciled_trades(self, user_id: UUID, limit: int = 100) -> List[Trade]:
        """Get unreconciled trades for reconciliation."""
        result = await self.db.execute(
            select(Trade)
            .where(
                and_(
                    Trade.user_id == user_id,
                    Trade.is_reconciled == False,
                )
            )
            .order_by(Trade.executed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class PositionRepository:
    """Repository for position database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def upsert_position(self, user_id: UUID, symbol: str, exchange: str, product_type: str, updates: dict) -> Position:
        """Create or update a position."""
        result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.user_id == user_id,
                    Position.symbol == symbol,
                    Position.exchange == exchange,
                    Position.product_type == product_type,
                    Position.is_active == True,
                )
            )
        )
        position = result.scalar_one_or_none()
        
        if not position:
            position = Position(
                user_id=user_id,
                symbol=symbol,
                exchange=exchange,
                product_type=product_type,
                **updates,
            )
            self.db.add(position)
        else:
            for key, value in updates.items():
                if hasattr(position, key):
                    setattr(position, key, value)
            position.last_updated = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(position)
        return position
    
    async def get_user_positions(self, user_id: UUID, active_only: bool = True) -> List[Position]:
        """Get user's positions."""
        query = select(Position).where(Position.user_id == user_id)
        
        if active_only:
            query = query.where(Position.is_active == True)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())


class RiskBreachRepository:
    """Repository for risk breach tracking."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_breach(self, breach_data: dict) -> RiskBreach:
        """Create a risk breach record."""
        breach = RiskBreach(**breach_data)
        self.db.add(breach)
        await self.db.commit()
        await self.db.refresh(breach)
        return breach
    
    async def resolve_breach(self, breach_id: UUID) -> bool:
        """Mark a risk breach as resolved."""
        result = await self.db.execute(
            select(RiskBreach).where(RiskBreach.id == breach_id)
        )
        breach = result.scalar_one_or_none()
        
        if not breach:
            return False
        
        breach.is_resolved = True
        breach.resolved_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True
    
    async def get_active_breaches(self, user_id: UUID) -> List[RiskBreach]:
        """Get active risk breaches for a user."""
        result = await self.db.execute(
            select(RiskBreach).where(
                and_(
                    RiskBreach.user_id == user_id,
                    RiskBreach.is_resolved == False,
                )
            )
        )
        return list(result.scalars().all())