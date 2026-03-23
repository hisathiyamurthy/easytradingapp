"""Strategy management API endpoints."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from database.session import get_db
from core.security import get_current_user, TokenData, require_trader, UserRole
from models.strategy_models import Strategy, StrategyParameter, StrategyLog, StrategyWatchlist
from schemas.strategy_schemas import (
    StrategyCreate,
    StrategyUpdate,
    StrategyResponse,
    StrategyListResponse,
    StrategyParameterCreate,
    StrategyParameterUpdate,
    StrategyParameterResponse,
    StrategyLogResponse,
    StrategyLogListResponse,
    StrategyActivateRequest,
    StrategyDeactivateRequest,
    StrategyCloneRequest,
    StrategyParseRequest,
    StrategyParseResponse,
)

router = APIRouter(prefix="/strategies", tags=["Strategy Management"])


# ==================== Strategy Assignment Pydantic Models ====================

class StrategyAssignmentRequest(BaseModel):
    strategy_ids: list[UUID]
    user_ids: list[UUID]
    is_default: bool = False
    assign_to_all: bool = False


class StrategyAssignmentResponse(BaseModel):
    assigned_count: int
    message: str
    assignments: list[dict]


# ==================== Parse Strategy Text ====================

@router.post("/parse", response_model=StrategyParseResponse)
async def parse_strategy_text(
    request: StrategyParseRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Parse natural language strategy text into structured strategy."""
    from strategy_engine.improved_parser import ImprovedStrategyParser
    
    placeholder = "e.g., Buy when RSI crosses above 30 and sell when it crosses below 70"
    if request.strategy_text.strip() == placeholder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a custom strategy description instead of using the placeholder example."
        )
    
    if not request.strategy_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a strategy description."
        )
    
    parser = ImprovedStrategyParser()
    try:
        strategy = parser.parse(request.strategy_text)
        
        # Validation
        validation_errors = []
        
        if strategy.symbol == "UNKNOWN":
            validation_errors.append("Could not identify trading symbol. Please specify NIFTY, BANKNIFTY, or a stock symbol.")
        
        if not strategy.entry_conditions:
            validation_errors.append("No entry conditions detected. Please specify when to buy.")
        
        # Add parser warnings/errors
        validation_errors.extend(parser.errors)
        
        is_valid = len(validation_errors) == 0 and len(strategy.entry_conditions) > 0
        
        return StrategyParseResponse(
            name=strategy.strategy_name,
            description=f"Strategy for {strategy.symbol} on {strategy.exchange}",
            strategy_type="custom",
            parameters={
                "symbol": strategy.symbol,
                "exchange": strategy.exchange,
                "timeframe": strategy.timeframe,
                "risk_management": strategy.risk_management.to_dict() if strategy.risk_management else {},
            },
            entry_conditions=strategy.entry_conditions,
            exit_conditions=strategy.exit_conditions,
            validation_errors=validation_errors,
            is_valid=is_valid
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse strategy: {str(e)}"
        )


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """
    Create a new trading strategy.
    
    RBAC: ADMIN only - Users cannot create strategies.
    """
    # RBAC: Only admins can create strategies
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create strategies. Contact your administrator.",
        )
    # Check for duplicate name
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.user_id == current_user.user_id,
                Strategy.name == strategy_data.name,
            )
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy with this name already exists",
        )

    # Create strategy
    strategy = Strategy(
        user_id=current_user.user_id,
        name=strategy_data.name,
        description=strategy_data.description,
        strategy_type=strategy_data.strategy_type,
        is_paper_trading=strategy_data.is_paper_trading,
        parameters=strategy_data.parameters or {},
    )
    
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)

    return strategy


@router.get("", response_model=StrategyListResponse)
async def list_strategies(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
    strategy_type: Optional[str] = Query(None),
    is_paper_trading: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List all strategies for the current user."""
    query = select(Strategy).where(Strategy.user_id == current_user.user_id)
    
    # Apply filters
    if status_filter:
        query = query.where(Strategy.status == status_filter)
    if strategy_type:
        query = query.where(Strategy.strategy_type == strategy_type)
    if is_paper_trading is not None:
        query = query.where(Strategy.is_paper_trading == is_paper_trading)
    
    # Get total count
    count_result = await db.execute(
        select(Strategy).where(Strategy.user_id == current_user.user_id)
    )
    total = len(count_result.scalars().all())
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Strategy.created_at.desc())
    result = await db.execute(query)
    strategies = result.scalars().all()
    
    return StrategyListResponse(
        strategies=strategies,
        total=total,
        skip=skip,
        limit=limit,
    )


# ==================== User's Assigned Strategies Endpoint ====================

@router.get("/my-strategies", response_model=list[dict])
async def get_my_assigned_strategies(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """
    Get strategies assigned to the current user.
    Users only see their assigned strategies.
    """
    from models.strategy_models import UserStrategyAssignment
    
    # Get user's active assignments
    result = await db.execute(
        select(UserStrategyAssignment).where(
            and_(
                UserStrategyAssignment.user_id == current_user.user_id,
                UserStrategyAssignment.is_active == True,
            )
        )
    )
    assignments = result.scalars().all()
    
    # Get strategy details
    strategy_ids = [a.strategy_id for a in assignments]
    
    if not strategy_ids:
        return []
    
    result = await db.execute(
        select(Strategy).where(Strategy.id.in_(strategy_ids))
    )
    strategies = result.scalars().all()
    
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "description": s.description,
            "strategy_type": s.strategy_type,
            "status": s.status,
            "is_default": next((a.is_default for a in assignments if a.strategy_id == s.id), False),
            "assigned_at": next((a.assigned_at.isoformat() for a in assignments if a.strategy_id == s.id), None),
        }
        for s in strategies
    ]


# ==================== Strategy Assignment Routes (Admin Only) ====================

@router.post("/assign", response_model=StrategyAssignmentResponse)
async def assign_strategies_to_users(
    request: StrategyAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """
    Admin only: Assign strategies to users.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can assign strategies.",
        )
    
    from models.strategy_models import UserStrategyAssignment
    from models.auth_models import User
    
    assignments_created = []
    
    # Get target users
    if request.assign_to_all:
        result = await db.execute(
            select(User).where(User.role == UserRole.TRADER)
        )
        target_users = result.scalars().all()
    else:
        result = await db.execute(
            select(User).where(User.id.in_(request.user_ids))
        )
        target_users = result.scalars().all()
    
    # Get target strategies
    result = await db.execute(
        select(Strategy).where(Strategy.id.in_(request.strategy_ids))
    )
    target_strategies = result.scalars().all()
    
    # Create assignments
    for user in target_users:
        for strategy in target_strategies:
            # Check if assignment already exists
            existing = await db.execute(
                select(UserStrategyAssignment).where(
                    and_(
                        UserStrategyAssignment.user_id == user.id,
                        UserStrategyAssignment.strategy_id == strategy.id,
                    )
                )
            )
            
            if not existing.scalar_one_or_none():
                assignment = UserStrategyAssignment(
                    user_id=user.id,
                    strategy_id=strategy.id,
                    assigned_by=current_user.user_id,
                    is_default=request.is_default,
                    is_active=True,
                )
                db.add(assignment)
                assignments_created.append({
                    "user_id": str(user.id),
                    "strategy_id": str(strategy.id),
                    "strategy_name": strategy.name,
                    "user_email": user.email,
                })
    
    await db.commit()
    
    return StrategyAssignmentResponse(
        assigned_count=len(assignments_created),
        message=f"Assigned {len(assignments_created)} strategy(ies) to {len(target_users)} user(s)",
        assignments=assignments_created,
    )


@router.get("/assignments", response_model=list[dict])
async def get_strategy_assignments(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Admin only: Get all strategy assignments."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view assignments.",
        )
    
    from models.strategy_models import UserStrategyAssignment
    
    result = await db.execute(
        select(UserStrategyAssignment).order_by(UserStrategyAssignment.assigned_at.desc())
    )
    assignments = result.scalars().all()
    
    return [
        {
            "id": str(a.id),
            "user_id": str(a.user_id),
            "strategy_id": str(a.strategy_id),
            "is_default": a.is_default,
            "is_active": a.is_active,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        }
        for a in assignments
    ]


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_strategy_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Admin only: Remove a strategy assignment."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove assignments.",
        )
    
    from models.strategy_models import UserStrategyAssignment
    
    result = await db.execute(
        select(UserStrategyAssignment).where(UserStrategyAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    
    # Soft delete - just deactivate
    assignment.is_active = False
    assignment.deactivated_at = datetime.utcnow()
    
    await db.commit()


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get a specific strategy by ID."""
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )
    
    return strategy


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    strategy_data: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """
    Update a strategy.
    
    RBAC: ADMIN only - Users cannot edit strategies.
    """
    # RBAC: Only admins can update strategies
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update strategies.",
        )
    
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Check if strategy can be edited (not running)
    if strategy.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit a running strategy. Stop it first.",
        )

    # Update fields
    update_data = strategy_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(strategy, field, value)

    strategy.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(strategy)
    
    return strategy


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """
    Delete a strategy (soft delete).
    
    RBAC: ADMIN only - Users cannot delete strategies.
    """
    # RBAC: Only admins can delete strategies
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete strategies.",
        )
    
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Check if strategy is running
    if strategy.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running strategy. Stop it first.",
        )

    # Soft delete - deactivate instead
    strategy.is_active = False
    await db.commit()
    
    return None


@router.post("/{strategy_id}/activate", response_model=StrategyResponse)
async def activate_strategy(
    strategy_id: UUID,
    request: StrategyActivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Activate a strategy."""
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    if strategy.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is already running",
        )

    if strategy.status == "error":
        # Reset error state if requested
        strategy.error_count = 0
        strategy.error_message = None

    # Verify broker account exists and is active
    if strategy.broker_account_id:
        broker_result = await db.execute(
            select(BrokerAccount).where(
                and_(
                    BrokerAccount.id == strategy.broker_account_id,
                    BrokerAccount.user_id == current_user.user_id,
                    BrokerAccount.is_active == True,
                )
            )
        )
        broker = broker_result.scalar_one_or_none()
        if not broker:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Broker account is not active",
            )

    # Activate strategy
    strategy.status = "running"
    strategy.kill_switch = False
    strategy.last_run_at = datetime.utcnow()
    await db.commit()
    await db.refresh(strategy)
    
    return strategy


@router.post("/{strategy_id}/deactivate", response_model=StrategyResponse)
async def deactivate_strategy(
    strategy_id: UUID,
    request: StrategyDeactivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Deactivate a strategy."""
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    if strategy.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is not running",
        )

    # Deactivate strategy
    strategy.status = "paused"
    await db.commit()
    await db.refresh(strategy)
    
    return strategy


@router.post("/{strategy_id}/kill-switch", response_model=StrategyResponse)
async def trigger_kill_switch(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Trigger kill switch for a strategy - immediately stops all trading."""
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Activate kill switch
    strategy.kill_switch = True
    strategy.status = "stopped"
    strategy.kill_switched_at = datetime.utcnow()
    await db.commit()
    await db.refresh(strategy)
    
    return strategy


@router.post("/{strategy_id}/clone", response_model=StrategyResponse)
async def clone_strategy(
    strategy_id: UUID,
    request: StrategyCloneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Clone a strategy."""
    # Get original strategy
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    original = result.scalar_one_or_none()
    
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Create new strategy
    new_name = request.new_name or f"{original.name} (Copy)"
    
    # Check for duplicate name
    check_result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.user_id == current_user.user_id,
                Strategy.name == new_name,
            )
        )
    )
    if check_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy with this name already exists",
        )

    new_strategy = Strategy(
        user_id=current_user.user_id,
        name=new_name,
        description=original.description,
        strategy_type=original.strategy_type,
        broker_account_id=original.broker_account_id,
        is_paper_trading=original.is_paper_trading,
        schedule_cron=original.schedule_cron,
        execution_mode=original.execution_mode,
        parent_strategy_id=original.id,
        version=1,
    )
    
    db.add(new_strategy)
    await db.commit()
    await db.refresh(new_strategy)

    # Copy parameters
    param_result = await db.execute(
        select(StrategyParameter).where(
            StrategyParameter.strategy_id == original.id
        )
    )
    for param in param_result.scalars():
        new_param = StrategyParameter(
            strategy_id=new_strategy.id,
            parameter_name=param.parameter_name,
            parameter_value=param.parameter_value,
            parameter_type=param.parameter_type,
        )
        db.add(new_param)

    # Copy watchlist
    watchlist_result = await db.execute(
        select(StrategyWatchlist).where(
            StrategyWatchlist.strategy_id == original.id
        )
    )
    for item in watchlist_result.scalars():
        new_item = StrategyWatchlist(
            strategy_id=new_strategy.id,
            symbol=item.symbol,
        )
        db.add(new_item)

    await db.commit()
    await db.refresh(new_strategy)
    
    return new_strategy


# ==================== Strategy Parameters ====================

@router.post("/{strategy_id}/parameters", response_model=StrategyParameterResponse)
async def add_parameter(
    strategy_id: UUID,
    param_data: StrategyParameterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Add a parameter to a strategy."""
    # Verify ownership
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Check for duplicate
    check_result = await db.execute(
        select(StrategyParameter).where(
            and_(
                StrategyParameter.strategy_id == strategy_id,
                StrategyParameter.parameter_name == param_data.parameter_name,
            )
        )
    )
    if check_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parameter with this name already exists",
        )

    param = StrategyParameter(
        strategy_id=strategy_id,
        parameter_name=param_data.parameter_name,
        parameter_value=param_data.parameter_value,
        parameter_type=param_data.parameter_type,
    )
    
    db.add(param)
    await db.commit()
    await db.refresh(param)
    
    return param


@router.put("/{strategy_id}/parameters/{param_id}", response_model=StrategyParameterResponse)
async def update_parameter(
    strategy_id: UUID,
    param_id: UUID,
    param_data: StrategyParameterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Update a strategy parameter."""
    result = await db.execute(
        select(StrategyParameter).where(
            and_(
                StrategyParameter.id == param_id,
                StrategyParameter.strategy_id == strategy_id,
            )
        )
    )
    param = result.scalar_one_or_none()
    
    if not param:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parameter not found",
        )

    update_data = param_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(param, field, value)

    await db.commit()
    await db.refresh(param)
    
    return param


@router.delete("/{strategy_id}/parameters/{param_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parameter(
    strategy_id: UUID,
    param_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Delete a strategy parameter."""
    result = await db.execute(
        select(StrategyParameter).where(
            and_(
                StrategyParameter.id == param_id,
                StrategyParameter.strategy_id == strategy_id,
            )
        )
    )
    param = result.scalar_one_or_none()
    
    if not param:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parameter not found",
        )

    await db.delete(param)
    await db.commit()
    
    return None


# ==================== Strategy Logs ====================

@router.get("/{strategy_id}/logs", response_model=StrategyLogListResponse)
async def get_strategy_logs(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    level: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """Get logs for a strategy."""
    # Verify ownership
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Get logs
    query = select(StrategyLog).where(StrategyLog.strategy_id == strategy_id)
    
    if level:
        query = query.where(StrategyLog.level == level)
    
    # Get total count
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(StrategyLog.created_at.desc())
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return StrategyLogListResponse(
        logs=logs,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/{strategy_id}/logs", response_model=StrategyLogResponse)
async def create_log_entry(
    strategy_id: UUID,
    log_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Create a log entry for a strategy."""
    # Verify ownership
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    log = StrategyLog(
        strategy_id=strategy_id,
        user_id=current_user.user_id,
        level=log_data.get("level", "info"),
        message=log_data.get("message", ""),
        details=log_data.get("details"),
        symbol=log_data.get("signal_type"),
        signal_type=log_data.get("signal_type"),
        order_id=log_data.get("order_id"),
    )
    
    db.add(log)
    await db.commit()
    await db.refresh(log)
    
    return log


# ==================== Global Kill Switch ====================

@router.post("/global-kill-switch", response_model=dict)
async def trigger_global_kill_switch(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Trigger global kill switch - stops all running strategies."""
    # Get all running strategies for user
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.user_id == current_user.user_id,
                Strategy.status == "running",
            )
        )
    )
    strategies = result.scalars().all()
    
    count = 0
    for strategy in strategies:
        strategy.kill_switch = True
        strategy.status = "stopped"
        strategy.kill_switched_at = datetime.utcnow()
        count += 1
    
    await db.commit()
    
    return {
        "message": f"Global kill switch activated. {count} strategies stopped.",
        "strategies_stopped": count,
    }


# ==================== Strategy Validation ====================

@router.post("/{strategy_id}/validate")
async def validate_strategy(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Validate a strategy before running."""
    from services.strategy_backtest_service import StrategyValidator, StrategyLifecycleManager
    
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )
    
    # Get parsed parameters
    parsed = strategy.parameters or {}
    
    # Validate
    is_valid, errors, warnings = StrategyValidator.validate(parsed)
    can_run_backtest = is_valid
    can_start_paper = is_valid and not any("stoploss" in str(w).lower() for w in warnings)
    can_start_live = is_valid and len(errors) == 0 and "stoploss" in str(parsed.get("exit", {})).lower()
    
    return {
        "strategy_id": str(strategy_id),
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "can_run_backtest": can_run_backtest,
        "can_start_paper_trading": can_start_paper,
        "can_start_live": can_start_live,
        "lifecycle_state": strategy.status or "draft",
        "allowed_transitions": StrategyLifecycleManager.get_next_states(strategy.status or "draft"),
    }


# ==================== Strategy Backtest ====================

@router.post("/backtest-text")
async def backtest_strategy_text(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
):
    """Run backtest directly from strategy text."""
    from services.strategy_backtest_service import run_strategy_backtest
    
    strategy_text = request.get("strategy_text", "")
    symbol = request.get("symbol", "NIFTY")
    initial_capital = request.get("initial_capital", 100000)
    
    if not strategy_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy text is required",
        )
    
    # Run backtest
    result = await run_strategy_backtest(
        strategy_text=strategy_text,
        symbol=symbol,
        initial_capital=initial_capital,
    )
    
    return result


@router.post("/{strategy_id}/backtest")
async def backtest_strategy(
    strategy_id: UUID,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Run backtest for a saved strategy."""
    from services.strategy_backtest_service import StrategyBacktester, StrategyValidator
    
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )
    
    # Get parameters
    parsed = strategy.parameters or {}
    
    # Validate first
    is_valid, errors, warnings = StrategyValidator.validate(parsed)
    
    if not is_valid:
        return {
            "validation": {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
            },
            "backtest": None,
        }
    
    # Run backtest
    backtester = StrategyBacktester(db)
    
    metrics = await backtester.run_backtest(
        parsed_strategy=parsed,
        symbol=request.get("symbol", "NIFTY"),
        exchange=request.get("exchange", "NSE"),
        start_date=request.get("start_date"),
        end_date=request.get("end_date"),
        timeframe=request.get("timeframe", "1d"),
        initial_capital=request.get("initial_capital", 100000),
    )
    
    # Update strategy status if backtest succeeds
    if metrics.total_trades > 0:
        strategy.status = "backtested"
        await db.commit()
    
    return {
        "strategy_id": str(strategy_id),
        "validation": {
            "is_valid": True,
            "errors": [],
            "warnings": warnings,
        },
        "backtest": {
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades,
            "win_rate": metrics.win_rate,
            "total_return": metrics.total_return,
            "total_return_pct": metrics.total_return_pct,
            "annualized_return": metrics.annualized_return,
            "max_drawdown": metrics.max_drawdown,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "sharpe_ratio": metrics.sharpe_ratio,
            "sortino_ratio": metrics.sortino_ratio,
            "profit_factor": metrics.profit_factor,
            "avg_trade_pnl": metrics.avg_trade_pnl,
            "total_commission": metrics.total_commission,
            "trades": metrics.trades[:10],
        },
    }


# ==================== Strategy Lifecycle ====================

@router.get("/{strategy_id}/lifecycle")
async def get_strategy_lifecycle(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get strategy lifecycle state and allowed transitions."""
    from services.strategy_backtest_service import StrategyLifecycleManager
    
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )
    
    current_state = strategy.status or "draft"
    
    return {
        "strategy_id": str(strategy_id),
        "current_state": current_state,
        "allowed_transitions": StrategyLifecycleManager.get_next_states(current_state),
        "requirements": {
            state: StrategyLifecycleManager.get_requirements(state)
            for state in StrategyLifecycleManager.get_next_states(current_state)
        },
    }


@router.post("/{strategy_id}/transition")
async def transition_strategy_state(
    strategy_id: UUID,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Transition strategy to a new lifecycle state."""
    from services.strategy_backtest_service import StrategyLifecycleManager, StrategyValidator
    
    result = await db.execute(
        select(Strategy).where(
            and_(
                Strategy.id == strategy_id,
                Strategy.user_id == current_user.user_id,
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )
    
    target_state = request.get("target_state", "")
    current_state = strategy.status or "draft"
    
    # Check if transition is allowed
    if not StrategyLifecycleManager.can_transition(current_state, target_state):
        return {
            "success": False,
            "from_state": current_state,
            "to_state": target_state,
            "message": f"Transition from {current_state} to {target_state} is not allowed",
            "requirements_met": [],
            "requirements_missing": [],
        }
    
    # Check requirements
    requirements = StrategyLifecycleManager.get_requirements(target_state)
    parsed = strategy.parameters or {}
    requirements_met = []
    requirements_missing = []
    
    for req in requirements:
        if req == "has_valid_conditions":
            is_valid, errors, _ = StrategyValidator.validate(parsed)
            if is_valid:
                requirements_met.append(req)
            else:
                requirements_missing.append(f"{req}: {errors}")
        elif req == "passed_validation":
            if strategy.status == "validated":
                requirements_met.append(req)
            else:
                requirements_missing.append(f"{req}: strategy not validated")
        elif req == "has_backtest_results":
            # Check if strategy has conditions that would allow backtesting
            if strategy.status == "backtested" or (strategy.parameters and strategy.parameters.get("entry_conditions")):
                requirements_met.append(req)
            else:
                requirements_missing.append(f"{req}: run backtest first")
        elif req == "has_stoploss":
            if "stoploss" in str(parsed.get("exit", {})).lower():
                requirements_met.append(req)
            else:
                requirements_missing.append(f"{req}: add stoploss to strategy")
        elif req == "admin_approved":
            if strategy.approved:
                requirements_met.append(req)
            else:
                requirements_missing.append(f"{req}: requires admin approval")
    
    # Perform transition if all requirements met
    if not requirements_missing:
        strategy.status = target_state
        await db.commit()
        
        return {
            "success": True,
            "from_state": current_state,
            "to_state": target_state,
            "message": f"Successfully transitioned to {target_state}",
            "requirements_met": requirements_met,
            "requirements_missing": [],
        }
    else:
        return {
            "success": False,
            "from_state": current_state,
            "to_state": target_state,
            "message": "Requirements not met",
            "requirements_met": requirements_met,
            "requirements_missing": requirements_missing,
        }


# ==================== Admin Approval ====================

@router.get("/admin/pending-approval")
async def get_pending_approval_strategies(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get strategies pending admin approval for live trading."""
    from core.security import require_role, UserRole
    
    # Verify admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    # Get strategies that passed backtest but need approval
    result = await db.execute(
        select(Strategy).where(
            Strategy.status == "backtested"
        )
    )
    strategies = result.scalars().all()
    
    return {
        "strategies": [
            {
                "id": str(s.id),
                "name": s.name,
                "user_id": str(s.user_id),
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in strategies
        ],
        "total": len(strategies),
    }


@router.post("/{strategy_id}/approve")
async def approve_strategy_live_trading(
    strategy_id: UUID,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Approve strategy for live trading (admin only)."""
    from core.security import require_role, UserRole
    
    # Verify admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )
    
    approved = request.get("approved", True)
    reason = request.get("reason")
    
    strategy.approved = approved
    strategy.approved_by = current_user.user_id
    strategy.approved_at = datetime.utcnow()
    
    if approved:
        strategy.status = "live"
    
    await db.commit()
    
    return {
        "strategy_id": str(strategy_id),
        "approved": approved,
        "approved_by": str(current_user.user_id),
        "approved_at": datetime.utcnow().isoformat(),
        "new_status": strategy.status,
        "reason": reason,
    }
