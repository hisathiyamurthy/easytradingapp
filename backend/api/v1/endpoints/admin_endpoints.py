"""Admin API endpoints."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from database.session import get_db
from core.security import require_admin, TokenData, UserRole
from models.auth_models import User, UserSession
from models.strategy_models import Strategy, StrategyStatus
from models.order_models import Order
from models.broker_account_models import BrokerAccount

router = APIRouter(prefix="/admin", tags=["Admin"])


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_strategies: int
    active_strategies: int
    total_orders_today: int
    total_trades_today: int
    total_volume_today: float


class BrokerStatusResponse(BaseModel):
    name: str
    broker_name: str
    connected: bool
    last_sync: Optional[str]
    is_paper_trading: bool


class ActiveSessionResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity_at: datetime
    is_active: bool


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin()),
):
    """Get admin dashboard statistics."""
    # Total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    # Active users (logged in last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.last_login_at >= week_ago)
    )
    active_users = active_users_result.scalar() or 0

    # Total strategies
    total_strategies_result = await db.execute(select(func.count(Strategy.id)))
    total_strategies = total_strategies_result.scalar() or 0

    # Active strategies
    from models.strategy_models import StrategyStatus
    active_strategies_result = await db.execute(
        select(func.count(Strategy.id)).where(Strategy.status == StrategyStatus.ACTIVE)
    )
    active_strategies = active_strategies_result.scalar() or 0

    # Today's orders
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    orders_today_result = await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    )
    total_orders_today = orders_today_result.scalar() or 0

    # Today's trades (filled orders)
    trades_today_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.created_at >= today_start,
            Order.status == "filled"
        )
    )
    total_trades_today = trades_today_result.scalar() or 0

    # Today's volume (rough estimate)
    total_volume_today = total_orders_today * 10000  # Placeholder

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_strategies=total_strategies,
        active_strategies=active_strategies,
        total_orders_today=total_orders_today,
        total_trades_today=total_trades_today,
        total_volume_today=total_volume_today,
    )


@router.get("/brokers", response_model=list[BrokerStatusResponse])
async def get_broker_status(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin()),
):
    """Get broker connection status."""
    result = await db.execute(select(BrokerAccount))
    brokers = result.scalars().all()

    return [
        BrokerStatusResponse(
            name=f"{b.broker_name.value} - {b.account_id}",
            broker_name=b.broker_name.value,
            connected=b.is_active,
            last_sync=b.last_sync_at.isoformat() if b.last_sync_at else None,
            is_paper_trading=b.is_paper_trading,
        )
        for b in brokers
    ]


@router.get("/active-users", response_model=list[ActiveSessionResponse])
async def get_active_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin()),
):
    """Get active user sessions."""
    result = await db.execute(
        select(UserSession)
        .join(User, UserSession.user_id == User.id)
        .where(UserSession.is_active == True)
        .order_by(UserSession.last_activity_at.desc())
        .limit(50)
    )
    sessions = result.scalars().all()

    # Get user emails
    user_ids = [s.user_id for s in sessions]
    users_result = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users = {u.id: u.email for u in users_result.scalars().all()}

    return [
        ActiveSessionResponse(
            id=str(s.id),
            user_id=str(s.user_id),
            user_email=users.get(s.user_id, "Unknown"),
            ip_address=s.ip_address or "Unknown",
            user_agent=s.user_agent or "Unknown",
            created_at=s.created_at,
            last_activity_at=s.last_activity_at,
            is_active=s.is_active,
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin()),
):
    """Revoke a user session."""
    from uuid import UUID
    
    result = await db.execute(
        select(UserSession).where(UserSession.id == UUID(session_id))
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_active = False
    await db.commit()
    
    return {"message": "Session revoked successfully"}


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    role: str
    status: str
    created_at: str


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


@router.get("/users", response_model=UserListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin()),
):
    """Get all users (admin only)."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    
    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name or "",
                "last_name": u.last_name or "",
                "is_active": u.is_active,
                "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
                "status": u.status,
                "created_at": u.created_at.isoformat() if u.created_at else "",
            }
            for u in users
        ],
        "total": len(users),
    }
