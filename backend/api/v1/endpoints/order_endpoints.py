"""Order management API endpoints."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from database.session import get_db
from core.security import get_current_user, TokenData
from models.order_models import Order
from models.auth_models import User

router = APIRouter(prefix="/orders", tags=["Orders"])


class OrderResponse(BaseModel):
    id: str
    order_id: str
    client_order_id: Optional[str]
    broker_order_id: Optional[str]
    user_id: str
    strategy_id: Optional[str]
    broker_account_id: Optional[str]
    symbol: str
    exchange: str
    side: str
    order_type: str
    product_type: str
    validity: str
    quantity: int
    filled_quantity: int
    remaining_quantity: int
    cancelled_quantity: int
    price: Optional[float]
    trigger_price: Optional[float]
    avg_fill_price: Optional[float]
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime]
    filled_at: Optional[datetime]
    cancelled_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    symbol: str
    exchange: str = "NSE"
    side: str
    order_type: str
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    product_type: str = "MIS"
    validity: str = "DAY"
    broker_account_id: Optional[str] = None
    strategy_id: Optional[str] = None


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=OrderListResponse)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
    symbol: Optional[str] = None,
    from_date: Optional[str] = Query(None, alias="from_date"),
    to_date: Optional[str] = Query(None, alias="to_date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all orders for the current user."""
    query = select(Order).where(Order.user_id == current_user.user_id)

    # Apply filters
    if status_filter:
        query = query.where(Order.status == status_filter)
    if symbol:
        query = query.where(Order.symbol.ilike(f"%{symbol}%"))
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            query = query.where(Order.created_at >= from_dt)
        except ValueError:
            pass
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            query = query.where(Order.created_at <= to_dt)
        except ValueError:
            pass

    # Get total count
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())

    # Apply pagination and sorting
    query = query.order_by(desc(Order.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        orders=[
            OrderResponse(
                id=str(o.id),
                order_id=str(o.id),
                client_order_id=o.client_order_id,
                broker_order_id=o.broker_order_id,
                user_id=str(o.user_id),
                strategy_id=str(o.strategy_id) if o.strategy_id else None,
                broker_account_id=str(o.broker_account_id) if o.broker_account_id else None,
                symbol=o.symbol,
                exchange=o.exchange,
                side=o.side,
                order_type=o.order_type,
                product_type=o.product_type,
                validity=o.validity,
                quantity=o.quantity,
                filled_quantity=o.filled_quantity,
                remaining_quantity=o.remaining_quantity,
                cancelled_quantity=o.cancelled_quantity,
                price=o.price,
                trigger_price=o.trigger_price,
                avg_fill_price=o.avg_fill_price,
                status=o.status,
                error_message=o.error_message,
                created_at=o.created_at,
                updated_at=o.updated_at,
                submitted_at=o.submitted_at,
                filled_at=o.filled_at,
                cancelled_at=o.cancelled_at,
            )
            for o in orders
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get a specific order by ID."""
    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    result = await db.execute(
        select(Order).where(
            and_(
                Order.id == order_uuid,
                Order.user_id == current_user.user_id,
            )
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse(
        id=str(order.id),
        order_id=str(order.id),
        client_order_id=order.client_order_id,
        broker_order_id=order.broker_order_id,
        user_id=str(order.user_id),
        strategy_id=str(order.strategy_id) if order.strategy_id else None,
        broker_account_id=str(order.broker_account_id) if order.broker_account_id else None,
        symbol=order.symbol,
        exchange=order.exchange,
        side=order.side,
        order_type=order.order_type,
        product_type=order.product_type,
        validity=order.validity,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        remaining_quantity=order.remaining_quantity,
        cancelled_quantity=order.cancelled_quantity,
        price=order.price,
        trigger_price=order.trigger_price,
        avg_fill_price=order.avg_fill_price,
        status=order.status,
        error_message=order.error_message,
        created_at=order.created_at,
        updated_at=order.updated_at,
        submitted_at=order.submitted_at,
        filled_at=order.filled_at,
        cancelled_at=order.cancelled_at,
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Create a new order."""
    import uuid
    
    # Validate order data
    if order_data.side not in ["buy", "sell"]:
        raise HTTPException(status_code=400, detail="Side must be 'buy' or 'sell'")
    if order_data.order_type not in ["market", "limit", "stop_loss", "stop_loss_limit"]:
        raise HTTPException(status_code=400, detail="Invalid order type")
    if order_data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    # Create order
    order = Order(
        user_id=current_user.user_id,
        strategy_id=UUID(order_data.strategy_id) if order_data.strategy_id else None,
        broker_account_id=UUID(order_data.broker_account_id) if order_data.broker_account_id else None,
        client_order_id=str(uuid.uuid4()),
        symbol=order_data.symbol.upper(),
        exchange=order_data.exchange.upper(),
        side=order_data.side.lower(),
        order_type=order_data.order_type.lower(),
        product_type=order_data.product_type.upper(),
        validity=order_data.validity.upper(),
        quantity=order_data.quantity,
        filled_quantity=0,
        remaining_quantity=order_data.quantity,
        cancelled_quantity=0,
        price=order_data.price,
        trigger_price=order_data.trigger_price,
        status="pending",
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)

    return OrderResponse(
        id=str(order.id),
        order_id=str(order.id),
        client_order_id=order.client_order_id,
        broker_order_id=order.broker_order_id,
        user_id=str(order.user_id),
        strategy_id=str(order.strategy_id) if order.strategy_id else None,
        broker_account_id=str(order.broker_account_id) if order.broker_account_id else None,
        symbol=order.symbol,
        exchange=order.exchange,
        side=order.side,
        order_type=order.order_type,
        product_type=order.product_type,
        validity=order.validity,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        remaining_quantity=order.remaining_quantity,
        cancelled_quantity=order.cancelled_quantity,
        price=order.price,
        trigger_price=order.trigger_price,
        avg_fill_price=order.avg_fill_price,
        status=order.status,
        error_message=order.error_message,
        created_at=order.created_at,
        updated_at=order.updated_at,
        submitted_at=order.submitted_at,
        filled_at=order.filled_at,
        cancelled_at=order.cancelled_at,
    )


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Cancel an order."""
    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    result = await db.execute(
        select(Order).where(
            and_(
                Order.id == order_uuid,
                Order.user_id == current_user.user_id,
            )
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in ["filled", "cancelled", "rejected"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel order with status '{order.status}'")

    # Cancel the order
    order.status = "cancelled"
    order.cancelled_quantity = order.remaining_quantity
    order.remaining_quantity = 0
    order.cancelled_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(order)

    return OrderResponse(
        id=str(order.id),
        order_id=str(order.id),
        client_order_id=order.client_order_id,
        broker_order_id=order.broker_order_id,
        user_id=str(order.user_id),
        strategy_id=str(order.strategy_id) if order.strategy_id else None,
        broker_account_id=str(order.broker_account_id) if order.broker_account_id else None,
        symbol=order.symbol,
        exchange=order.exchange,
        side=order.side,
        order_type=order.order_type,
        product_type=order.product_type,
        validity=order.validity,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        remaining_quantity=order.remaining_quantity,
        cancelled_quantity=order.cancelled_quantity,
        price=order.price,
        trigger_price=order.trigger_price,
        avg_fill_price=order.avg_fill_price,
        status=order.status,
        error_message=order.error_message,
        created_at=order.created_at,
        updated_at=order.updated_at,
        submitted_at=order.submitted_at,
        filled_at=order.filled_at,
        cancelled_at=order.cancelled_at,
    )
