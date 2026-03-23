"""Trade reconciliation service."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.order_models import Trade, Order
from models.broker_models import BrokerAccount
from services.order_repository import TradeRepository


@dataclass
class ReconciliationResult:
    """Result of trade reconciliation."""
    total_trades: int
    matched: int
    missing_in_broker: int
    missing_in_internal: int
    mismatched_quantity: int
    mismatched_price: int
    reconciled_trade_ids: List[UUID]
    missing_trades: List[dict]
    mismatched_trades: List[dict]


@dataclass
class ReconciliationReport:
    """Daily reconciliation report."""
    user_id: UUID
    broker_account_id: UUID
    report_date: datetime
    trades_analyzed: int
    trades_reconciled: int
    discrepancies: int
    total_volume: float
    total_pnl: float


class TradeReconciliationService:
    """Service for reconciling trades between broker and internal records."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.trade_repo = TradeRepository(db)
    
    async def reconcile_user_trades(
        self,
        user_id: UUID,
        broker_account_id: UUID,
        from_date: datetime,
        to_date: datetime,
    ) -> ReconciliationResult:
        """Reconcile trades for a user within a date range."""
        internal_trades = await self.trade_repo.get_user_trades(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            limit=10000,
        )
        
        broker_trades = await self._get_broker_trades(
            broker_account_id=broker_account_id,
            from_date=from_date,
            to_date=to_date,
        )
        
        internal_trade_map = {t.trade_id: t for t in internal_trades if t.trade_id}
        broker_trade_map = {t["trade_id"]: t for t in broker_trades if t.get("trade_id")}
        
        matched_ids = []
        missing_in_broker = []
        missing_in_internal = []
        mismatched_quantity = []
        mismatched_price = []
        
        for trade_id, internal_trade in internal_trade_map.items():
            if trade_id not in broker_trade_map:
                missing_in_broker.append({
                    "trade_id": trade_id,
                    "symbol": internal_trade.symbol,
                    "quantity": internal_trade.quantity,
                    "price": internal_trade.price,
                    "issue": "Not found in broker records",
                })
            else:
                broker_trade = broker_trade_map[trade_id]
                is_matched = True
                
                if internal_trade.quantity != broker_trade.get("quantity"):
                    mismatched_quantity.append({
                        "trade_id": trade_id,
                        "internal_quantity": internal_trade.quantity,
                        "broker_quantity": broker_trade.get("quantity"),
                    })
                    is_matched = False
                
                if abs(internal_trade.price - broker_trade.get("price", 0)) > 0.01:
                    mismatched_price.append({
                        "trade_id": trade_id,
                        "internal_price": internal_trade.price,
                        "broker_price": broker_trade.get("price"),
                    })
                    is_matched = False
                
                if is_matched:
                    matched_ids.append(internal_trade.id)
                    await self.trade_repo.mark_reconciled(internal_trade.id, "matched")
        
        for trade_id, broker_trade in broker_trade_map.items():
            if trade_id not in internal_trade_map:
                missing_in_internal.append({
                    "trade_id": trade_id,
                    "symbol": broker_trade.get("symbol"),
                    "quantity": broker_trade.get("quantity"),
                    "price": broker_trade.get("price"),
                    "issue": "Not found in internal records",
                })
        
        return ReconciliationResult(
            total_trades=len(internal_trades) + len(broker_trades),
            matched=len(matched_ids),
            missing_in_broker=len(missing_in_broker),
            missing_in_internal=len(missing_in_internal),
            mismatched_quantity=len(mismatched_quantity),
            mismatched_price=len(mismatched_price),
            reconciled_trade_ids=matched_ids,
            missing_trades=missing_in_broker + missing_in_internal,
            mismatched_trades=mismatched_quantity + mismatched_price,
        )
    
    async def _get_broker_trades(
        self,
        broker_account_id: UUID,
        from_date: datetime,
        to_date: datetime,
    ) -> List[dict]:
        """Get trades from broker API."""
        result = await self.db.execute(
            select(BrokerAccount).where(BrokerAccount.id == broker_account_id)
        )
        broker_account = result.scalar_one_or_none()
        
        if not broker_account:
            return []
        
        try:
            from broker_integrations.base import BrokerRegistry, BrokerName
            broker_class = BrokerRegistry.get_broker(BrokerName(broker_account.broker_name))
            from core.encryption import get_encryption_service
            from core.config import get_settings
            
            settings = get_settings()
            encryption = get_encryption_service()
            
            decrypted_api_key = encryption.decrypt(broker_account.api_key)
            decrypted_api_secret = encryption.decrypt(broker_account.api_secret)
            
            broker_config = BrokerConfig(
                broker_name=BrokerName(broker_account.broker_name),
                api_key=decrypted_api_key,
                api_secret=decrypted_api_secret,
            )
            
            broker = broker_class(broker_config, settings.ENCRYPTION_KEY.encode())
            
            await broker.authenticate(
                {"api_key": decrypted_api_key, "api_secret": decrypted_api_secret}
            )
            
            broker_trades = await broker.get_trades(from_date)
            return broker_trades
            
        except Exception as e:
            from core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to fetch broker trades: {e}")
            return []
    
    async def generate_daily_report(
        self,
        user_id: UUID,
        broker_account_id: UUID,
        report_date: datetime,
    ) -> ReconciliationReport:
        """Generate daily reconciliation report."""
        from_date = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        to_date = report_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        result = await self.reconcile_user_trades(
            user_id=user_id,
            broker_account_id=broker_account_id,
            from_date=from_date,
            to_date=to_date,
        )
        
        trades = await self.trade_repo.get_user_trades(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
        )
        
        total_volume = sum(t.quantity * t.price for t in trades)
        total_pnl = sum(t.net_amount or 0 for t in trades)
        
        return ReconciliationReport(
            user_id=user_id,
            broker_account_id=broker_account_id,
            report_date=report_date,
            trades_analyzed=result.total_trades,
            trades_reconciled=result.matched,
            discrepancies=(
                result.missing_in_broker 
                + result.missing_in_internal 
                + result.missing_in_internal
                + result.mismatched_price
            ),
            total_volume=total_volume,
            total_pnl=total_pnl,
        )


class ReconciliationScheduler:
    """Scheduler for running reconciliation jobs."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def run_daily_reconciliation(self) -> Dict[str, any]:
        """Run reconciliation for all active users."""
        from sqlalchemy import select
        from models.auth_models import User
        from models.broker_models import BrokerAccount
        
        result = await self.db.execute(
            select(User).where(User.is_active == True)
        )
        users = result.scalars().all()
        
        reports = []
        for user in users:
            broker_result = await self.db.execute(
                select(BrokerAccount).where(
                    and_(
                        BrokerAccount.user_id == user.id,
                        BrokerAccount.is_active == True,
                    )
                )
            )
            broker_accounts = broker_result.scalars().all()
            
            for broker_account in broker_accounts:
                service = TradeReconciliationService(self.db)
                report = await service.generate_daily_report(
                    user_id=user.id,
                    broker_account_id=broker_account.id,
                    report_date=datetime.now(timezone.utc),
                )
                reports.append(report)
        
        return {
            "users_processed": len(users),
            "reports_generated": len(reports),
            "total_discrepancies": sum(r.discrepancies for r in reports),
        }