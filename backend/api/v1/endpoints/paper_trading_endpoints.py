"""Paper Trading API endpoints."""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database.session import get_db
from core.security import get_current_user, TokenData, require_trader
from models.strategy_models import Strategy
from models.strategy_instance_models import UserStrategyInstance, InstanceTrade, InstancePosition
from services.paper_trading_service import PaperTradingService, run_paper_trading_tick

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])


class StartPaperTradingRequest(BaseModel):
    strategy_id: UUID
    capital: float = Field(default=100000.0, ge=1000.0, le=10000000.0)


class PaperTradingInstanceResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    name: str
    capital: float
    allocated_capital: float
    status: str
    mode: str
    current_pnl: Optional[float] = 0.0
    realized_pnl: Optional[float] = 0.0
    unrealized_pnl: Optional[float] = 0.0
    trades_count: Optional[int] = 0
    winning_trades: Optional[int] = 0
    losing_trades: Optional[int] = 0
    max_drawdown: Optional[float] = 0.0
    started_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaperTradingPositionResponse(BaseModel):
    id: UUID
    symbol: str
    exchange: str
    side: str
    quantity: int
    entry_price: float
    current_price: Optional[float] = 0.0
    unrealized_pnl: Optional[float] = 0.0
    is_open: bool
    opened_at: datetime

    class Config:
        from_attributes = True


class PaperTradingTradeResponse(BaseModel):
    id: UUID
    symbol: str
    exchange: str
    side: str
    quantity: int
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    commission: Optional[float] = 0.0
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_signal: Optional[str] = None
    exit_reason: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/start", response_model=PaperTradingInstanceResponse)
async def start_paper_trading(
    request: StartPaperTradingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Start paper trading for a strategy."""
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == request.strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if strategy.status != "backtested" and strategy.status != "paper_trading":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strategy must be backtested or already in paper trading. Current status: {strategy.status}"
        )
    
    service = PaperTradingService(db)
    instance = await service.start_paper_trading(
        strategy_id=request.strategy_id,
        user_id=current_user.user_id,
        capital=request.capital,
    )
    
    return PaperTradingInstanceResponse(
        id=instance.id,
        strategy_id=instance.strategy_id,
        name=instance.name,
        capital=instance.capital,
        allocated_capital=instance.allocated_capital,
        status=instance.status,
        mode=instance.mode,
        current_pnl=instance.current_pnl,
        realized_pnl=instance.realized_pnl,
        unrealized_pnl=instance.unrealized_pnl,
        trades_count=instance.trades_count,
        winning_trades=instance.winning_trades,
        losing_trades=instance.losing_trades,
        started_at=instance.started_at,
        created_at=instance.created_at,
    )


@router.get("/instances", response_model=List[PaperTradingInstanceResponse])
async def list_paper_trading_instances(
    strategy_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """List all paper trading instances for the user."""
    query = select(UserStrategyInstance).where(
        and_(
            UserStrategyInstance.user_id == current_user.user_id,
            UserStrategyInstance.mode == "paper",
        )
    )
    
    if strategy_id:
        query = query.where(UserStrategyInstance.strategy_id == strategy_id)
    
    if status_filter:
        query = query.where(UserStrategyInstance.status == status_filter)
    
    query = query.order_by(UserStrategyInstance.created_at.desc())
    
    result = await db.execute(query)
    instances = result.scalars().all()
    
    return [
        PaperTradingInstanceResponse(
            id=inst.id,
            strategy_id=inst.strategy_id,
            name=inst.name,
            capital=inst.capital,
            allocated_capital=inst.allocated_capital,
            status=inst.status,
            mode=inst.mode,
            current_pnl=inst.current_pnl,
            realized_pnl=inst.realized_pnl,
            unrealized_pnl=inst.unrealized_pnl,
            trades_count=inst.trades_count,
            winning_trades=inst.winning_trades,
            losing_trades=inst.losing_trades,
            started_at=inst.started_at,
            created_at=inst.created_at,
        )
        for inst in instances
    ]


@router.get("/instances/{instance_id}", response_model=PaperTradingInstanceResponse)
async def get_paper_trading_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get paper trading instance details."""
    result = await db.execute(
        select(UserStrategyInstance).where(
            and_(
                UserStrategyInstance.id == instance_id,
                UserStrategyInstance.user_id == current_user.user_id,
            )
        )
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper trading instance not found"
        )
    
    return PaperTradingInstanceResponse(
        id=instance.id,
        strategy_id=instance.strategy_id,
        name=instance.name,
        capital=instance.capital,
        allocated_capital=instance.allocated_capital,
        status=instance.status,
        mode=instance.mode,
        current_pnl=instance.current_pnl,
        realized_pnl=instance.realized_pnl,
        unrealized_pnl=instance.unrealized_pnl,
        trades_count=instance.trades_count,
        winning_trades=instance.winning_trades,
        losing_trades=instance.losing_trades,
        started_at=instance.started_at,
        created_at=instance.created_at,
    )


@router.post("/instances/{instance_id}/tick")
async def run_tick(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Run a single trading tick for the instance."""
    result = await db.execute(
        select(UserStrategyInstance).where(
            and_(
                UserStrategyInstance.id == instance_id,
                UserStrategyInstance.user_id == current_user.user_id,
            )
        )
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper trading instance not found"
        )
    
    if instance.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance must be running. Current status: {instance.status}"
        )
    
    await run_paper_trading_tick(instance_id, db)
    
    return {"status": "tick_executed"}


@router.post("/instances/{instance_id}/pause")
async def pause_paper_trading(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Pause paper trading."""
    result = await db.execute(
        select(UserStrategyInstance).where(
            and_(
                UserStrategyInstance.id == instance_id,
                UserStrategyInstance.user_id == current_user.user_id,
            )
        )
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper trading instance not found"
        )
    
    service = PaperTradingService(db)
    await service.pause_instance(instance_id)
    
    return {"status": "paused"}


@router.post("/instances/{instance_id}/resume")
async def resume_paper_trading(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Resume paper trading."""
    result = await db.execute(
        select(UserStrategyInstance).where(
            and_(
                UserStrategyInstance.id == instance_id,
                UserStrategyInstance.user_id == current_user.user_id,
            )
        )
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper trading instance not found"
        )
    
    service = PaperTradingService(db)
    await service.resume_instance(instance_id)
    
    return {"status": "running"}


@router.post("/instances/{instance_id}/stop")
async def stop_paper_trading(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Stop paper trading."""
    result = await db.execute(
        select(UserStrategyInstance).where(
            and_(
                UserStrategyInstance.id == instance_id,
                UserStrategyInstance.user_id == current_user.user_id,
            )
        )
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper trading instance not found"
        )
    
    service = PaperTradingService(db)
    await service.stop_instance(instance_id)
    
    return {"status": "stopped"}


@router.get("/instances/{instance_id}/positions", response_model=List[PaperTradingPositionResponse])
async def get_positions(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get open positions for an instance."""
    result = await db.execute(
        select(InstancePosition).where(
            and_(
                InstancePosition.instance_id == instance_id,
                InstancePosition.user_id == current_user.user_id,
            )
        )
    )
    positions = result.scalars().all()
    
    return [PaperTradingPositionResponse.model_validate(p) for p in positions]


@router.get("/instances/{instance_id}/trades", response_model=List[PaperTradingTradeResponse])
async def get_trades(
    instance_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get trade history for an instance."""
    result = await db.execute(
        select(InstanceTrade).where(
            and_(
                InstanceTrade.instance_id == instance_id,
                InstanceTrade.user_id == current_user.user_id,
            )
        ).order_by(InstanceTrade.entry_time.desc()).limit(limit)
    )
    trades = result.scalars().all()
    
    return [PaperTradingTradeResponse.model_validate(t) for t in trades]
