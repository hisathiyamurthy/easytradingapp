"""Live Trading API endpoints."""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.security import get_current_user, TokenData, require_trader
from services.live_trading_service import LiveTradingService
from models.strategy_instance_models import UserStrategyInstance, InstanceTrade

router = APIRouter(prefix="/live-trading", tags=["Live Trading"])


class ConnectBrokerRequest(BaseModel):
    broker: str = Field(..., description="Broker name: MOCK, ZERODHA, UPSTOX")
    api_key: str = Field(..., description="Broker API key")
    api_secret: str = Field(..., description="Broker API secret")
    request_token: Optional[str] = Field(None, description="Request token for OAuth")


class StartLiveTradingRequest(BaseModel):
    strategy_id: UUID
    capital: float = Field(default=100000.0, ge=1000.0, le=10000000.0)


class LiveTradingInstanceResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    broker_account_id: Optional[UUID] = None
    name: str
    capital: float
    allocated_capital: float
    status: str
    mode: str
    current_pnl: Optional[float] = 0.0
    realized_pnl: Optional[float] = 0.0
    unrealized_pnl: Optional[float] = 0.0
    trades_count: Optional[int] = 0
    started_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/connect")
async def connect_broker(
    request: ConnectBrokerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Connect to a broker account."""
    service = LiveTradingService(db)
    result = await service.connect_broker(
        user_id=current_user.user_id,
        broker_name=request.broker,
        api_key=request.api_key,
        api_secret=request.api_secret,
        request_token=request.request_token,
    )
    
    if result.get("connected"):
        return {
            "success": True,
            "message": f"Connected to {request.broker}",
            "profile": result.get("profile"),
            "balance": result.get("balance"),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to connect to broker")
        )


@router.post("/disconnect")
async def disconnect_broker(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Disconnect from broker."""
    service = LiveTradingService(db)
    success = await service.disconnect_broker(current_user.user_id)
    
    if success:
        return {"success": True, "message": "Disconnected from broker"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No broker connected"
        )


@router.get("/status")
async def get_broker_status(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Check broker connection status."""
    service = LiveTradingService(db)
    is_connected = await service.is_connected(current_user.user_id)
    
    if is_connected:
        broker = service.get_broker(current_user.user_id)
        if broker:
            profile = await broker.get_profile()
            balance = await broker.get_balance()
            
            return {
                "connected": True,
                "profile": profile,
                "balance": balance,
            }
    
    return {"connected": False}


@router.get("/balance")
async def get_balance(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get broker account balance."""
    service = LiveTradingService(db)
    
    if not await service.is_connected(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No broker connected"
        )
    
    broker = service.get_broker(current_user.user_id)
    if broker:
        balance = await broker.get_balance()
        return balance
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Broker error"
    )


@router.post("/instances", response_model=LiveTradingInstanceResponse)
async def start_live_trading(
    request: StartLiveTradingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Start live trading for a strategy."""
    service = LiveTradingService(db)
    
    if not await service.is_connected(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No broker connected. Please connect to a broker first."
        )
    
    try:
        instance = await service.start_live_trading(
            strategy_id=request.strategy_id,
            user_id=current_user.user_id,
            broker_account_id=None,
            capital=request.capital,
        )
        
        return LiveTradingInstanceResponse.model_validate(instance)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/instances")
async def list_live_instances(
    strategy_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """List all live trading instances."""
    from sqlalchemy import select, and_
    
    query = select(UserStrategyInstance).where(
        and_(
            UserStrategyInstance.user_id == current_user.user_id,
            UserStrategyInstance.mode == "live",
        )
    )
    
    if strategy_id:
        query = query.where(UserStrategyInstance.strategy_id == strategy_id)
    
    result = await db.execute(query)
    instances = result.scalars().all()
    
    return [LiveTradingInstanceResponse.model_validate(i) for i in instances]


@router.get("/instances/{instance_id}", response_model=LiveTradingInstanceResponse)
async def get_live_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get live trading instance details."""
    from sqlalchemy import select, and_
    
    result = await db.execute(
        select(UserStrategyInstance).where(
            and_(
                UserStrategyInstance.id == instance_id,
                UserStrategyInstance.user_id == current_user.user_id,
                UserStrategyInstance.mode == "live",
            )
        )
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Live trading instance not found"
        )
    
    return LiveTradingInstanceResponse.model_validate(instance)


@router.post("/instances/{instance_id}/pause")
async def pause_live_trading(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Pause live trading."""
    service = LiveTradingService(db)
    await service.pause_instance(instance_id)
    return {"status": "paused"}


@router.post("/instances/{instance_id}/resume")
async def resume_live_trading(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Resume live trading."""
    service = LiveTradingService(db)
    await service.resume_instance(instance_id)
    return {"status": "running"}


@router.post("/instances/{instance_id}/stop")
async def stop_live_trading(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Stop live trading."""
    service = LiveTradingService(db)
    await service.stop_instance(instance_id)
    return {"status": "stopped"}


@router.post("/instances/{instance_id}/sync")
async def sync_positions(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Sync positions with broker."""
    service = LiveTradingService(db)
    await service.sync_positions(instance_id, current_user.user_id)
    return {"status": "synced"}


@router.get("/instances/{instance_id}/orders")
async def get_broker_orders(
    instance_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get broker orders for an instance."""
    from sqlalchemy import select, and_
    
    result = await db.execute(
        select(InstanceTrade).where(
            and_(
                InstanceTrade.instance_id == instance_id,
                InstanceTrade.user_id == current_user.user_id,
            )
        ).order_by(InstanceTrade.entry_time.desc()).limit(limit)
    )
    trades = result.scalars().all()
    
    return [
        {
            "id": str(t.id),
            "symbol": t.symbol,
            "side": t.side,
            "quantity": t.quantity,
            "entry_price": t.entry_price,
            "pnl": t.pnl,
            "entry_time": t.entry_time.isoformat() if t.entry_time else None,
            "broker_order_id": t.broker_order_id,
        }
        for t in trades
    ]


@router.post("/instances/{instance_id}/exit-all")
async def exit_all_positions(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """
    Emergency Exit All - Close all open positions immediately.
    This should be used for emergency situations only.
    """
    from services.strategy_instance_service import StrategyInstanceService
    
    service = StrategyInstanceService(db)
    
    # Verify ownership
    instance = await service.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    if instance.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to exit positions for this instance"
        )
    
    # Exit all positions
    result = await service.exit_all_positions(instance_id, reason="emergency_exit")
    
    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "closed_positions": result["closed_positions"],
            "failed_positions": result.get("failed_positions", []),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to exit positions")
        )


class PositionUpdateRequest(BaseModel):
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[int] = None


@router.patch("/instances/{instance_id}/positions/{position_id}")
async def update_position(
    instance_id: UUID,
    position_id: UUID,
    update_data: PositionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Update stop loss, take profit, or quantity for an open position."""
    from services.strategy_instance_service import StrategyInstanceService
    from sqlalchemy import select, and_
    from models.strategy_instance_models import InstancePosition
    
    service = StrategyInstanceService(db)
    
    # Get position
    result = await db.execute(
        select(InstancePosition).where(
            and_(
                InstancePosition.id == position_id,
                InstancePosition.instance_id == instance_id,
                InstancePosition.user_id == current_user.user_id,
                InstancePosition.is_open == True,
            )
        )
    )
    position = result.scalar_one_or_none()
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found or already closed"
        )
    
    # Update fields
    if update_data.stop_loss is not None:
        position.stop_loss = update_data.stop_loss
    if update_data.take_profit is not None:
        position.take_profit = update_data.take_profit
    if update_data.quantity is not None and update_data.quantity > 0:
        position.quantity = update_data.quantity
    
    await db.commit()
    await db.refresh(position)
    
    # If broker connected, try to modify the SL/TP order
    from services.live_trading_service import _broker_sessions
    broker_session = _broker_sessions.get(str(current_user.user_id))
    if broker_session:
        broker = broker_session["broker"]
        try:
            # Cancel old SL order if exists and new SL set
            if update_data.stop_loss is not None and position.sl_order_id:
                try:
                    await broker.cancel_order(position.sl_order_id)
                except:
                    pass
                
                # Place new SL order
                side = "SELL" if position.side == "BUY" else "BUY"
                new_sl = await broker.place_order(
                    symbol=position.symbol,
                    side=side,
                    quantity=position.quantity,
                    order_type="SL-M",  # Use SL-M for stop loss
                    trigger_price=update_data.stop_loss,
                    product_type="MIS",
                )
                position.sl_order_id = new_sl.get("order_id")
                await db.commit()
                
        except Exception as e:
            logger.warning(f"Could not update broker SL order: {e}")
    
    return {
        "success": True,
        "message": "Position updated",
        "position": {
            "id": str(position.id),
            "symbol": position.symbol,
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit,
            "sl_order_id": position.sl_order_id,
            "tp_order_id": position.tp_order_id,
        }
    }
