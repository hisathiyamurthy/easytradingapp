"""Portfolio API endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from database.session import get_db
from core.security import get_current_user, TokenData
from models.order_models import Order, Position

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


class PositionResponse(BaseModel):
    id: str
    symbol: str
    exchange: str
    quantity: int
    avg_price: float
    current_price: Optional[float]
    unrealized_pnl: float
    realized_pnl: float
    market_value: Optional[float]
    is_active: bool

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    total_value: float
    total_invested: float
    total_pnl: float
    total_pnl_percent: float
    position_count: int


class PortfolioResponse(BaseModel):
    positions: list[PositionResponse]
    summary: PortfolioSummary


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get user's portfolio with positions and summary."""
    # Get all active positions
    result = await db.execute(
        select(Position).where(
            Position.user_id == current_user.user_id,
            Position.is_active == True,
        )
    )
    positions = result.scalars().all()

    # Calculate summary
    total_invested = sum(p.avg_price * p.quantity for p in positions)
    total_value = sum((p.current_price or p.avg_price) * p.quantity for p in positions)
    total_unrealized = sum(p.unrealized_pnl for p in positions)
    total_realized = sum(p.realized_pnl for p in positions)
    total_pnl = total_unrealized + total_realized
    total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    return PortfolioResponse(
        positions=[
            PositionResponse(
                id=str(p.id),
                symbol=p.symbol,
                exchange=p.exchange,
                quantity=p.quantity,
                avg_price=p.avg_price,
                current_price=p.current_price,
                unrealized_pnl=p.unrealized_pnl,
                realized_pnl=p.realized_pnl,
                market_value=p.market_value,
                is_active=p.is_active,
            )
            for p in positions
        ],
        summary=PortfolioSummary(
            total_value=total_value,
            total_invested=total_invested,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            position_count=len(positions),
        ),
    )


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    is_active: bool = Query(True, description="Filter by active status"),
):
    """Get all positions for the user."""
    result = await db.execute(
        select(Position).where(
            Position.user_id == current_user.user_id,
            Position.is_active == is_active,
        )
    )
    positions = result.scalars().all()

    return [
        PositionResponse(
            id=str(p.id),
            symbol=p.symbol,
            exchange=p.exchange,
            quantity=p.quantity,
            avg_price=p.avg_price,
            current_price=p.current_price,
            unrealized_pnl=p.unrealized_pnl,
            realized_pnl=p.realized_pnl,
            market_value=p.market_value,
            is_active=p.is_active,
        )
        for p in positions
    ]


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get portfolio summary."""
    result = await db.execute(
        select(Position).where(
            Position.user_id == current_user.user_id,
            Position.is_active == True,
        )
    )
    positions = result.scalars().all()

    total_invested = sum(p.avg_price * p.quantity for p in positions)
    total_value = sum((p.current_price or p.avg_price) * p.quantity for p in positions)
    total_unrealized = sum(p.unrealized_pnl for p in positions)
    total_realized = sum(p.realized_pnl for p in positions)
    total_pnl = total_unrealized + total_realized
    total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    return PortfolioSummary(
        total_value=total_value,
        total_invested=total_invested,
        total_pnl=total_pnl,
        total_pnl_percent=total_pnl_percent,
        position_count=len(positions),
    )


@router.get("/positions/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get a specific position."""
    from uuid import UUID
    
    try:
        pos_uuid = UUID(position_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid position ID")

    result = await db.execute(
        select(Position).where(
            Position.id == pos_uuid,
            Position.user_id == current_user.user_id,
        )
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    return PositionResponse(
        id=str(position.id),
        symbol=position.symbol,
        exchange=position.exchange,
        quantity=position.quantity,
        avg_price=position.avg_price,
        current_price=position.current_price,
        unrealized_pnl=position.unrealized_pnl,
        realized_pnl=position.realized_pnl,
        market_value=position.market_value,
        is_active=position.is_active,
    )


@router.get("/dashboard-stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get stats for dashboard display."""
    # Today's date range
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get today's orders count
    orders_today_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.user_id == current_user.user_id,
            Order.created_at >= today_start,
        )
    )
    orders_today = orders_today_result.scalar() or 0

    # Get filled orders today
    trades_today_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.user_id == current_user.user_id,
            Order.created_at >= today_start,
            Order.status == "filled",
        )
    )
    trades_today = trades_today_result.scalar() or 0

    # Get positions count
    positions_result = await db.execute(
        select(func.count(Position.id)).where(
            Position.user_id == current_user.user_id,
            Position.is_active == True,
        )
    )
    positions_count = positions_result.scalar() or 0

    # Get portfolio value
    positions_res = await db.execute(
        select(Position).where(
            Position.user_id == current_user.user_id,
            Position.is_active == True,
        )
    )
    positions = positions_res.scalars().all()
    
    total_value = sum((p.current_price or p.avg_price) * p.quantity for p in positions)
    total_pnl = sum(p.unrealized_pnl for p in positions)

    # Get recent orders
    recent_orders_result = await db.execute(
        select(Order).where(
            Order.user_id == current_user.user_id,
        ).order_by(Order.created_at.desc()).limit(5)
    )
    recent_orders = recent_orders_result.scalars().all()

    return {
        "portfolio_value": total_value,
        "today_pnl": total_pnl,
        "open_positions": positions_count,
        "orders_today": orders_today,
        "trades_today": trades_today,
        "recent_orders": [
            {
                "id": str(o.id),
                "symbol": o.symbol,
                "side": o.side,
                "quantity": o.quantity,
                "price": o.price,
                "status": o.status,
                "created_at": o.created_at.isoformat(),
            }
            for o in recent_orders
        ],
    }
