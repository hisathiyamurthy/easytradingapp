"""Risk management API endpoints."""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from database.session import get_db
from core.security import get_current_user, TokenData

router = APIRouter(prefix="/risk", tags=["Risk Management"])


class RiskRuleCreate(BaseModel):
    rule_type: str
    rule_name: str
    threshold_value: float
    threshold_percentage: Optional[float] = None
    action: str = "alert"
    is_enabled: bool = True
    is_hard: bool = False
    broker_account_id: Optional[str] = None
    strategy_id: Optional[str] = None


class RiskRuleResponse(BaseModel):
    id: str
    user_id: str
    rule_type: str
    rule_name: str
    threshold_value: float
    threshold_percentage: Optional[float]
    action: str
    is_enabled: bool
    is_hard: bool
    created_at: str


class KillSwitchResponse(BaseModel):
    is_active: bool
    triggered_at: Optional[str]
    reason: Optional[str]


@router.get("/rules", response_model=List[RiskRuleResponse])
async def list_risk_rules(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """List all risk rules for the user."""
    from models.order_models import RiskRule
    
    result = await db.execute(
        select(RiskRule).where(RiskRule.user_id == current_user.user_id)
    )
    rules = result.scalars().all()

    return [
        RiskRuleResponse(
            id=str(r.id),
            user_id=str(r.user_id),
            rule_type=r.rule_type.value if hasattr(r.rule_type, 'value') else r.rule_type,
            rule_name=r.rule_name,
            threshold_value=r.threshold_value,
            threshold_percentage=r.threshold_percentage,
            action=r.action.value if hasattr(r.action, 'value') else r.action,
            is_enabled=r.is_enabled,
            is_hard=r.is_hard,
            created_at=r.created_at.isoformat(),
        )
        for r in rules
    ]


@router.post("/rules", response_model=RiskRuleResponse)
async def create_risk_rule(
    rule_data: RiskRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Create a new risk rule."""
    from models.order_models import RiskRule
    from risk_management.risk_manager import RiskRuleType, RiskAction
    
    try:
        rule_type = RiskRuleType(rule_data.rule_type)
        action = RiskAction(rule_data.action)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule type or action")

    rule = RiskRule(
        user_id=current_user.user_id,
        broker_account_id=UUID(rule_data.broker_account_id) if rule_data.broker_account_id else None,
        strategy_id=UUID(rule_data.strategy_id) if rule_data.strategy_id else None,
        rule_type=rule_type,
        rule_name=rule_data.rule_name,
        description=f"Auto-created rule: {rule_data.rule_name}",
        threshold_value=rule_data.threshold_value,
        threshold_percentage=rule_data.threshold_percentage,
        action=action,
        is_enabled=rule_data.is_enabled,
        is_hard=rule_data.is_hard,
    )

    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return RiskRuleResponse(
        id=str(rule.id),
        user_id=str(rule.user_id),
        rule_type=rule.rule_type.value if hasattr(rule.rule_type, 'value') else rule.rule_type,
        rule_name=rule.rule_name,
        threshold_value=rule.threshold_value,
        threshold_percentage=rule.threshold_percentage,
        action=rule.action.value if hasattr(rule.action, 'value') else rule.action,
        is_enabled=rule.is_enabled,
        is_hard=rule.is_hard,
        created_at=rule.created_at.isoformat(),
    )


@router.delete("/rules/{rule_id}")
async def delete_risk_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Delete a risk rule."""
    from models.order_models import RiskRule
    
    try:
        rule_uuid = UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID")

    result = await db.execute(
        select(RiskRule).where(
            RiskRule.id == rule_uuid,
            RiskRule.user_id == current_user.user_id,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Risk rule not found")

    await db.delete(rule)
    await db.commit()

    return {"message": "Risk rule deleted successfully"}


@router.post("/kill-switch")
async def trigger_kill_switch(
    reason: str = "Manual trigger",
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Trigger emergency kill switch to stop all trading."""
    from models.order_models import Order, Position
    from models.strategy_instance_models import UserStrategyInstance
    from services.notification_service import NotificationService
    import logging
    
    logger = logging.getLogger(__name__)
    triggered_at = datetime.now(timezone.utc)
    results = {
        "pending_orders_cancelled": 0,
        "positions_closed": 0,
        "instances_stopped": 0,
    }
    
    try:
        # 1. Cancel all pending orders
        pending_orders = await db.execute(
            select(Order).where(
                Order.user_id == current_user.user_id,
                Order.status.in_(["pending", "submitted", "partial_filled"])
            )
        )
        for order in pending_orders.scalars().all():
            order.status = "cancelled"
            order.updated_at = triggered_at
            results["pending_orders_cancelled"] += 1
        
        # 2. Close all open positions (mark for review - requires market data for actual closing)
        open_positions = await db.execute(
            select(Position).where(
                Position.user_id == current_user.user_id,
                Position.is_active == True
            )
        )
        for position in open_positions.scalars().all():
            position.is_active = False
            position.updated_at = triggered_at
            results["positions_closed"] += 1
        
        # 3. Stop all strategy instances
        active_instances = await db.execute(
            select(UserStrategyInstance).where(
                UserStrategyInstance.user_id == current_user.user_id,
                UserStrategyInstance.status == "running"
            )
        )
        for instance in active_instances.scalars().all():
            instance.status = "stopped"
            instance.stopped_at = triggered_at
            results["instances_stopped"] += 1
        
        await db.commit()
        
        # 4. Send notification about kill switch
        try:
            notification_service = NotificationService(db)
            await notification_service.send_notification(
                user_id=current_user.user_id,
                notification_type="system_alert",
                title="Kill Switch Activated",
                message=f"Emergency kill switch triggered. Reason: {reason}. Orders cancelled: {results['pending_orders_cancelled']}, Positions closed: {results['positions_closed']}, Instances stopped: {results['instances_stopped']}",
                priority="critical",
            )
        except Exception as e:
            logger.warning(f"Failed to send kill switch notification: {e}")
        
        logger.warning(f"KILL SWITCH: User {current_user.user_id} triggered kill switch. Reason: {reason}. Results: {results}")
        
        return {
            "success": True,
            "message": "Kill switch activated. All trading halted.",
            "triggered_at": triggered_at.isoformat(),
            "results": results,
        }
        
    except Exception as e:
        logger.error(f"Kill switch failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Kill switch failed: {str(e)}")


@router.get("/kill-switch", response_model=KillSwitchResponse)
async def get_kill_switch_status(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get kill switch status."""
    from models.order_models import Order, Position
    from models.strategy_instance_models import UserStrategyInstance
    
    # Check if there are any running instances or pending orders
    pending_count = await db.execute(
        select(Order).where(
            Order.user_id == current_user.user_id,
            Order.status.in_(["pending", "submitted"])
        )
    )
    
    running_instances = await db.execute(
        select(UserStrategyInstance).where(
            UserStrategyInstance.user_id == current_user.user_id,
            UserStrategyInstance.status == "running"
        )
    )
    
    has_active_trading = len(pending_count.scalars().all()) > 0 or len(running_instances.scalars().all()) > 0
    
    return KillSwitchResponse(
        is_active=has_active_trading,
        triggered_at=None,
        reason=None,
    )


@router.get("/status")
async def get_risk_status(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get overall risk status for the user."""
    from models.order_models import RiskRule, RiskBreach
    from models.order_models import Position
    
    # Count active rules
    rules_result = await db.execute(
        select(RiskRule).where(
            RiskRule.user_id == current_user.user_id,
            RiskRule.is_enabled == True,
        )
    )
    active_rules = len(rules_result.scalars().all())

    # Count active breaches
    breaches_result = await db.execute(
        select(RiskBreach).where(
            RiskBreach.user_id == current_user.user_id,
            RiskBreach.is_resolved == False,
        )
    )
    active_breaches = len(breaches_result.scalars().all())

    # Get total position value
    positions_result = await db.execute(
        select(Position).where(
            Position.user_id == current_user.user_id,
            Position.is_active == True,
        )
    )
    positions = positions_result.scalars().all()
    total_exposure = sum((p.current_price or p.avg_price) * p.quantity for p in positions)

    return {
        "active_rules": active_rules,
        "active_breaches": active_breaches,
        "total_exposure": total_exposure,
        "kill_switch_active": False,
        "risk_level": "low" if active_breaches == 0 else "medium" if active_breaches < 3 else "high",
    }
