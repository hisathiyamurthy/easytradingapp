"""Strategy Instance API endpoints."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.security import get_current_user, TokenData
from schemas.strategy_schemas import (
    InstanceCreate,
    InstanceResponse,
    InstanceListResponse,
    InstanceTradesResponse,
    InstancePerformanceResponse,
    InstanceStartRequest,
    InstanceClosePositionRequest,
    InstanceStatus,
    InstanceMode,
)
from models.strategy_models import Strategy
from models.strategy_instance_models import InstanceTrade
from services.strategy_instance_service import StrategyInstanceService

router = APIRouter(prefix="/instances", tags=["Strategy Instances"])


@router.post("", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    request: InstanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Create a new strategy instance."""
    service = StrategyInstanceService(db)
    
    instance = await service.create_instance(
        user_id=current_user.user_id,
        strategy_id=request.strategy_id,
        name=request.name,
        capital=request.capital,
        mode=InstanceMode[request.mode.upper()].value if hasattr(request.mode, 'upper') else request.mode,
    )
    
    return instance


@router.get("", response_model=InstanceListResponse)
async def list_instances(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """List all strategy instances for the current user."""
    service = StrategyInstanceService(db)
    
    status_enum = None
    if status_filter:
        try:
            status_enum = InstanceStatus[status_filter.upper()]
        except KeyError:
            pass
    
    instances = await service.get_user_instances(
        user_id=current_user.user_id,
        status=status_enum,
    )
    
    return InstanceListResponse(
        instances=instances,
        total=len(instances),
    )


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get a specific strategy instance."""
    service = StrategyInstanceService(db)
    instance = await service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )
    
    if instance.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this instance",
        )
    
    return instance


@router.get("/{instance_id}/performance", response_model=InstancePerformanceResponse)
async def get_instance_performance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get performance summary for an instance."""
    service = StrategyInstanceService(db)
    instance = await service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )
    
    if instance.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this instance",
        )
    
    performance = await service.get_performance_summary(instance_id)
    return performance


@router.get("/{instance_id}/trades", response_model=InstanceTradesResponse)
async def get_instance_trades(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=500),
):
    """Get trades for an instance."""
    service = StrategyInstanceService(db)
    instance = await service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )
    
    if instance.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this instance",
        )
    
    trades = await service.get_trades(instance_id, limit=limit)
    
    return InstanceTradesResponse(
        trades=trades,
        total=len(trades),
    )


@router.post("/{instance_id}/start", response_model=InstanceResponse)
async def start_instance(
    instance_id: UUID,
    request: InstanceStartRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Start a strategy instance (begin paper/live trading)."""
    service = StrategyInstanceService(db)
    instance = await service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )
    
    if instance.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this instance",
        )
    
    if instance.status == InstanceStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance is already running",
        )
    
    try:
        await service.start_instance(
            instance_id=instance_id,
            initial_balance=request.initial_balance if request else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return await service.get_instance(instance_id)


@router.post("/{instance_id}/pause", response_model=InstanceResponse)
async def pause_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Pause a running strategy instance."""
    service = StrategyInstanceService(db)
    instance = await service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )
    
    if instance.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this instance",
        )
    
    try:
        await service.pause_instance(instance_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return await service.get_instance(instance_id)


@router.post("/{instance_id}/resume", response_model=InstanceResponse)
async def resume_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Resume a paused strategy instance."""
    service = StrategyInstanceService(db)
    instance = await service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )
    
    if instance.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this instance",
        )
    
    try:
        await service.resume_instance(instance_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return await service.get_instance(instance_id)


@router.post("/{instance_id}/stop", response_model=InstanceResponse)
async def stop_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Stop a strategy instance permanently."""
    service = StrategyInstanceService(db)
    instance = await service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )
    
    if instance.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this instance",
        )
    
    try:
        await service.stop_instance(instance_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return await service.get_instance(instance_id)


@router.post("/{instance_id}/close-position")
async def close_position(
    instance_id: UUID,
    request: InstanceClosePositionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Close an open position in a strategy instance."""
    service = StrategyInstanceService(db)
    instance = await service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )
    
    if instance.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this instance",
        )
    
    trade = await service.close_position(
        instance_id=instance_id,
        symbol=request.symbol,
        reason=request.reason,
    )
    
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No open position found for this symbol",
        )
    
    return {"message": "Position closed", "trade": trade}


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Delete a strategy instance."""
    service = StrategyInstanceService(db)
    instance = await service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )
    
    if instance.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this instance",
        )
    
    if instance.status == InstanceStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running instance. Stop it first.",
        )
    
    await db.delete(instance)
    await db.commit()
    
    return None
