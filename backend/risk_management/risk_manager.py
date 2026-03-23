"""Risk Management System.

Features:
- Max daily loss limits
- Max trades per day
- Position size limits
- Global kill switch
- Per-strategy risk controls
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class RiskRuleType(str, Enum):
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    MAX_TRADES_PER_DAY = "max_trades_per_day"
    MAX_POSITION_SIZE = "max_position_size"
    MAX_PORTFOLIO_EXPOSURE = "max_portfolio_exposure"
    MIN_ACCOUNT_EQUITY = "min_account_equity"
    MAX_ORDERS_PER_MINUTE = "max_orders_per_minute"
    PER_ASSET_POSITION_LIMIT = "per_asset_position_limit"
    PER_ASSET_LOSS_LIMIT = "per_asset_loss_limit"
    PER_ASSET_DAILY_TRADES = "per_asset_daily_trades"
    RISK_PER_TRADE = "risk_per_trade"  # Max risk per trade as %
    TRAILING_STOPLOSS = "trailing_stoploss"  # Trailing SL percentage


class RiskAction(str, Enum):
    ALERT = "alert"
    PAUSE_STRATEGY = "pause_strategy"
    PAUSE_ALL_TRADING = "pause_all_trading"
    KILL_SWITCH = "kill_switch"
    REJECT_ORDER = "reject_order"


class RiskLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class RiskLimit:
    """Risk limit configuration."""
    rule_type: RiskRuleType
    threshold: float
    action: RiskAction = RiskAction.ALERT
    is_hard: bool = False  # Hard limits cannot be bypassed
    is_enabled: bool = True


@dataclass
class RiskCheckResult:
    """Result of risk check."""
    approved: bool
    risk_level: RiskLevel = RiskLevel.INFO
    message: str = ""
    action_taken: Optional[RiskAction] = None
    triggered_rules: list = field(default_factory=list)


@dataclass
class RiskBreach:
    """Record of risk limit breach."""
    id: str = field(default_factory=lambda: str(UUID()))
    user_id: str = ""
    strategy_id: Optional[str] = None
    rule_type: RiskRuleType = RiskRuleType.DAILY_LOSS_LIMIT
    threshold: float = 0
    actual_value: float = 0
    action_taken: RiskAction = RiskAction.ALERT
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PerAssetLimit:
    """Per-asset position and loss limits."""
    symbol: str
    max_position_value: float = 100000.0
    max_daily_loss: float = 10000.0
    max_daily_trades: int = 10
    is_enabled: bool = True


@dataclass
class PerAssetDailyStats:
    """Daily statistics per asset."""
    symbol: str
    trade_count: int = 0
    daily_pnl: float = 0.0
    last_trade_time: Optional[datetime] = None


class RiskManager:
    """Risk management system for trading."""

    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        
        # User risk limits
        self._user_limits: dict[str, list[RiskLimit]] = {}
        
        # Daily tracking
        self._daily_stats: dict[str, 'DailyStats'] = {}
        self._order_rate_tracker: dict[str, list[datetime]] = {}
        
        # Global kill switch
        self._global_kill_switch: bool = False
        self._user_kill_switches: dict[str, bool] = {}
        self._strategy_kill_switches: dict[str, bool] = {}
        
        # Per-asset limits
        self._per_asset_limits: dict[str, dict[str, PerAssetLimit]] = {}
        self._per_asset_daily_stats: dict[str, dict[str, 'PerAssetDailyStats']] = {}
        
        # Account balances and positions for exposure tracking
        self._account_balances: dict[str, float] = {}
        self._positions: dict[str, dict[str, dict]] = {}
        
        # Locks
        self._lock = asyncio.Lock()

    def set_user_limits(self, user_id: str, limits: list[RiskLimit]):
        """Set risk limits for a user."""
        self._user_limits[user_id] = limits
        logger.info(f"Risk limits set for user {user_id}: {[l.rule_type for l in limits]}")

    def add_limit(self, user_id: str, limit: RiskLimit):
        """Add a risk limit for a user."""
        if user_id not in self._user_limits:
            self._user_limits[user_id] = []
        
        # Replace existing limit of same type
        self._user_limits[user_id] = [
            l for l in self._user_limits[user_id]
            if l.rule_type != limit.rule_type
        ]
        self._user_limits[user_id].append(limit)

    def get_limits(self, user_id: str) -> list[RiskLimit]:
        """Get risk limits for a user."""
        return self._user_limits.get(user_id, [])

    def trigger_global_kill_switch(self, reason: str = "Manual trigger"):
        """Trigger global kill switch - stops all trading."""
        self._global_kill_switch = True
        logger.critical(f"GLOBAL KILL SWITCH TRIGGERED: {reason}")
        return True

    def reset_global_kill_switch(self):
        """Reset global kill switch."""
        self._global_kill_switch = False
        logger.info("Global kill switch reset")

    def is_global_kill_switch_active(self) -> bool:
        """Check if global kill switch is active."""
        return self._global_kill_switch

    def trigger_user_kill_switch(self, user_id: str, reason: str = "Manual trigger"):
        """Trigger kill switch for a specific user."""
        self._user_kill_switches[user_id] = True
        logger.warning(f"User {user_id} kill switch triggered: {reason}")

    def reset_user_kill_switch(self, user_id: str):
        """Reset user kill switch."""
        self._user_kill_switches[user_id] = False
        logger.info(f"User {user_id} kill switch reset")

    def is_user_kill_switch_active(self, user_id: str) -> bool:
        """Check if user kill switch is active."""
        return self._user_kill_switches.get(user_id, False)

    def trigger_strategy_kill_switch(
        self,
        user_id: str,
        strategy_id: str,
        reason: str = "Manual trigger"
    ):
        """Trigger kill switch for a specific strategy."""
        key = f"{user_id}:{strategy_id}"
        self._strategy_kill_switches[key] = True
        logger.warning(f"Strategy {strategy_id} kill switch triggered: {reason}")

    def reset_strategy_kill_switch(self, user_id: str, strategy_id: str):
        """Reset strategy kill switch."""
        key = f"{user_id}:{strategy_id}"
        self._strategy_kill_switches[key] = False
        logger.info(f"Strategy {strategy_id} kill switch reset")

    def is_strategy_kill_switch_active(self, user_id: str, strategy_id: str) -> bool:
        """Check if strategy kill switch is active."""
        key = f"{user_id}:{strategy_id}"
        return self._strategy_kill_switches.get(key, False)

    async def check_order_risk(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        strategy_id: Optional[str] = None,
        signal_stop_loss: Optional[float] = None,
    ) -> RiskCheckResult:
        """Check if order passes risk checks."""
        async with self._lock:
            # Check global kill switch
            if self._global_kill_switch:
                return RiskCheckResult(
                    approved=False,
                    risk_level=RiskLevel.EMERGENCY,
                    message="Global kill switch is active. All trading halted.",
                    action_taken=RiskAction.KILL_SWITCH,
                )

            # Check user kill switch
            if self.is_user_kill_switch_active(user_id):
                return RiskCheckResult(
                    approved=False,
                    risk_level=RiskLevel.CRITICAL,
                    message="User account is locked. Trading halted.",
                    action_taken=RiskAction.KILL_SWITCH,
                )

            # Check strategy kill switch
            if strategy_id and self.is_strategy_kill_switch_active(user_id, strategy_id):
                return RiskCheckResult(
                    approved=False,
                    risk_level=RiskLevel.CRITICAL,
                    message="Strategy kill switch is active.",
                    action_taken=RiskAction.KILL_SWITCH,
                )

            limits = self.get_limits(user_id)
            triggered = []

            for limit in limits:
                if not limit.is_enabled:
                    continue

                result = await self._check_limit(
                    user_id=user_id,
                    limit=limit,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                )

                if not result.approved:
                    triggered.append(result)
                    
                    if limit.is_hard or limit.action == RiskAction.REJECT_ORDER:
                        return result

            # Check configurable rate limiting
            rate_limit = 10  # default
            for limit in limits:
                if limit.rule_type == RiskRuleType.MAX_ORDERS_PER_MINUTE:
                    rate_limit = int(limit.threshold)
                    break
            
            rate_check = self._check_order_rate_limit(user_id, max_per_minute=rate_limit)
            if not rate_check:
                return RiskCheckResult(
                    approved=False,
                    risk_level=RiskLevel.WARNING,
                    message="Order rate limit exceeded. Please wait.",
                    action_taken=RiskAction.REJECT_ORDER,
                    triggered_rules=[RiskRuleType.MAX_ORDERS_PER_MINUTE],
                )

            return RiskCheckResult(approved=True)

    async def _check_limit(
        self,
        user_id: str,
        limit: RiskLimit,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
    ) -> RiskCheckResult:
        """Check a specific risk limit."""
        
        if limit.rule_type == RiskRuleType.MAX_POSITION_SIZE:
            order_value = (price or 0) * quantity
            if order_value > limit.threshold:
                return RiskCheckResult(
                    approved=limit.action != RiskAction.ALERT,
                    risk_level=RiskLevel.WARNING,
                    message=f"Order value {order_value} exceeds max position size {limit.threshold}",
                    action_taken=limit.action if limit.is_hard else None,
                    triggered_rules=[limit.rule_type],
                )

        elif limit.rule_type == RiskRuleType.MAX_TRADES_PER_DAY:
            stats = self._get_daily_stats(user_id)
            if stats.trade_count >= limit.threshold:
                return RiskCheckResult(
                    approved=limit.action != RiskAction.ALERT,
                    risk_level=RiskLevel.CRITICAL,
                    message=f"Max trades per day ({limit.threshold}) reached",
                    action_taken=limit.action,
                    triggered_rules=[limit.rule_type],
                )

        elif limit.rule_type == RiskRuleType.PER_ASSET_POSITION_LIMIT:
            asset_limit = self._get_per_asset_limit(user_id, symbol)
            if asset_limit:
                current_position = self._get_current_position(user_id, symbol)
                order_value = (price or 0) * quantity
                total_value = current_position + order_value
                
                if total_value > asset_limit.max_position_value:
                    return RiskCheckResult(
                        approved=limit.action != RiskAction.ALERT,
                        risk_level=RiskLevel.WARNING,
                        message=f"Order would exceed per-asset limit for {symbol}. Current: {current_position}, Limit: {asset_limit.max_position_value}",
                        action_taken=limit.action if limit.is_hard else None,
                        triggered_rules=[limit.rule_type],
                    )

        elif limit.rule_type == RiskRuleType.PER_ASSET_LOSS_LIMIT:
            asset_limit = self._get_per_asset_limit(user_id, symbol)
            if asset_limit:
                daily_loss = self._get_per_asset_daily_loss(user_id, symbol)
                if daily_loss < -asset_limit.max_daily_loss:
                    return RiskCheckResult(
                        approved=False,
                        risk_level=RiskLevel.CRITICAL,
                        message=f"Per-asset daily loss limit reached for {symbol}. Loss: {daily_loss}, Limit: {asset_limit.max_daily_loss}",
                        action_taken=limit.action,
                        triggered_rules=[limit.rule_type],
                    )

        elif limit.rule_type == RiskRuleType.PER_ASSET_DAILY_TRADES:
            asset_limit = self._get_per_asset_limit(user_id, symbol)
            if asset_limit:
                asset_trades = self._get_per_asset_daily_trades(user_id, symbol)
                if asset_trades >= asset_limit.max_daily_trades:
                    return RiskCheckResult(
                        approved=limit.action != RiskAction.ALERT,
                        risk_level=RiskLevel.WARNING,
                        message=f"Max daily trades for {symbol} reached ({asset_limit.max_daily_trades})",
                        action_taken=limit.action if limit.is_hard else None,
                        triggered_rules=[limit.rule_type],
                    )

        elif limit.rule_type == RiskRuleType.RISK_PER_TRADE:
            # Check if order risk exceeds configured risk per trade %
            if price and quantity > 0:
                order_value = price * quantity
                account_balance = self._get_account_balance(user_id)
                risk_amount = (limit.threshold / 100) * account_balance
                stop_loss_value = (price - (signal_stop_loss or 0)) * quantity if signal_stop_loss else 0
                
                if stop_loss_value > risk_amount:
                    return RiskCheckResult(
                        approved=limit.action != RiskAction.ALERT,
                        risk_level=RiskLevel.WARNING,
                        message=f"Trade risk {stop_loss_value:.2f} exceeds {limit.threshold}% of account ({risk_amount:.2f})",
                        action_taken=limit.action if limit.is_hard else None,
                        triggered_rules=[limit.rule_type],
                    )

        elif limit.rule_type == RiskRuleType.MAX_PORTFOLIO_EXPOSURE:
            # Check total portfolio exposure
            current_exposure = self._get_total_exposure(user_id)
            order_value = (price or 0) * quantity
            total_exposure = current_exposure + order_value
            account_balance = self._get_account_balance(user_id)
            max_exposure_pct = (limit.threshold / 100) * account_balance
            
            if total_exposure > max_exposure_pct:
                return RiskCheckResult(
                    approved=limit.action != RiskAction.ALERT,
                    risk_level=RiskLevel.WARNING,
                    message=f"Portfolio exposure {total_exposure:.2f} would exceed limit ({max_exposure_pct:.2f})",
                    action_taken=limit.action if limit.is_hard else None,
                    triggered_rules=[limit.rule_type],
                )

        return RiskCheckResult(approved=True)

    async def check_daily_loss(
        self,
        user_id: str,
        current_pnl: float,
        account_equity: float,
    ) -> RiskCheckResult:
        """Check daily loss limits."""
        async with self._lock:
            limits = self.get_limits(user_id)
            triggered = []

            for limit in limits:
                if not limit.is_enabled:
                    continue

                if limit.rule_type == RiskRuleType.DAILY_LOSS_LIMIT:
                    if current_pnl < -limit.threshold:
                        action_taken = limit.action
                        
                        # Auto-trigger kill switch for hard limits
                        if limit.is_hard:
                            self.trigger_user_kill_switch(
                                user_id,
                                f"Daily loss limit breach: {current_pnl} < {-limit.threshold}"
                            )
                            action_taken = RiskAction.KILL_SWITCH

                        return RiskCheckResult(
                            approved=not limit.is_hard,
                            risk_level=RiskLevel.CRITICAL,
                            message=f"Daily loss limit breached: {current_pnl} < {-limit.threshold}",
                            action_taken=action_taken,
                            triggered_rules=[limit.rule_type],
                        )

                elif limit.rule_type == RiskRuleType.MIN_ACCOUNT_EQUITY:
                    if account_equity < limit.threshold:
                        action_taken = limit.action
                        
                        if limit.is_hard:
                            self.trigger_user_kill_switch(
                                user_id,
                                f"Account equity below minimum: {account_equity} < {limit.threshold}"
                            )
                            action_taken = RiskAction.KILL_SWITCH

                        return RiskCheckResult(
                            approved=not limit.is_hard,
                            risk_level=RiskLevel.CRITICAL,
                            message=f"Account equity below minimum: {account_equity} < {limit.threshold}",
                            action_taken=action_taken,
                            triggered_rules=[limit.rule_type],
                        )

            return RiskCheckResult(approved=True)

    def record_trade(
        self,
        user_id: str,
        symbol: str,
        quantity: int,
        price: float,
        pnl: float = 0,
    ):
        """Record a trade for daily tracking."""
        stats = self._get_daily_stats(user_id)
        stats.trade_count += 1
        stats.total_volume += quantity * price
        
        if pnl > 0:
            stats.winning_trades += 1
        elif pnl < 0:
            stats.losing_trades += 1
        
        stats.daily_pnl += pnl
        stats.last_trade_at = datetime.utcnow()

    def _get_daily_stats(self, user_id: str) -> 'DailyStats':
        """Get or create daily stats for user."""
        today = datetime.utcnow().date()
        
        if user_id not in self._daily_stats:
            self._daily_stats[user_id] = DailyStats(date=today)
        
        stats = self._daily_stats[user_id]
        
        # Reset if new day
        if stats.date != today:
            self._daily_stats[user_id] = DailyStats(date=today)
        
        return self._daily_stats[user_id]

    def _get_account_balance(self, user_id: str) -> float:
        """Get account balance for user. Defaults to 100000 if not set."""
        return self._account_balances.get(user_id, 100000.0)

    def _get_total_exposure(self, user_id: str) -> float:
        """Calculate total portfolio exposure (sum of all position values)."""
        if user_id not in self._positions:
            return 0.0
        return sum(pos.get("value", 0) for pos in self._positions[user_id].values())

    def set_account_balance(self, user_id: str, balance: float):
        """Set account balance for a user."""
        self._account_balances[user_id] = balance

    def set_per_asset_limit(self, user_id: str, limit: PerAssetLimit):
        """Set per-asset position limit for a user."""
        if user_id not in self._per_asset_limits:
            self._per_asset_limits[user_id] = {}
        self._per_asset_limits[user_id][limit.symbol] = limit

    def get_per_asset_limits(self, user_id: str) -> list[PerAssetLimit]:
        """Get all per-asset limits for a user."""
        if user_id not in self._per_asset_limits:
            return []
        return list(self._per_asset_limits[user_id].values())

    def _get_per_asset_limit(self, user_id: str, symbol: str) -> Optional[PerAssetLimit]:
        """Get per-asset limit for a specific symbol."""
        if user_id not in self._per_asset_limits:
            return None
        return self._per_asset_limits[user_id].get(symbol)

    def _get_current_position(self, user_id: str, symbol: str) -> float:
        """Get current position value for a symbol. In production, this would query the database."""
        return 0.0

    def _get_per_asset_daily_stats(self, user_id: str, symbol: str) -> PerAssetDailyStats:
        """Get or create per-asset daily stats."""
        today = datetime.utcnow().date()
        
        if user_id not in self._per_asset_daily_stats:
            self._per_asset_daily_stats[user_id] = {}
        
        if symbol not in self._per_asset_daily_stats[user_id]:
            self._per_asset_daily_stats[user_id][symbol] = PerAssetDailyStats(symbol=symbol)
        
        stats = self._per_asset_daily_stats[user_id][symbol]
        if stats.last_trade_time and stats.last_trade_time.date() != today:
            self._per_asset_daily_stats[user_id][symbol] = PerAssetDailyStats(symbol=symbol)
            return self._per_asset_daily_stats[user_id][symbol]
        
        return stats

    def _get_per_asset_daily_loss(self, user_id: str, symbol: str) -> float:
        """Get daily loss for a specific asset."""
        stats = self._get_per_asset_daily_stats(user_id, symbol)
        return stats.daily_pnl

    def _get_per_asset_daily_trades(self, user_id: str, symbol: str) -> int:
        """Get daily trade count for a specific asset."""
        stats = self._get_per_asset_daily_stats(user_id, symbol)
        return stats.trade_count

    def _check_order_rate_limit(self, user_id: str, max_per_minute: int = 10) -> bool:
        """Check order rate limit."""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=1)
        
        if user_id not in self._order_rate_tracker:
            self._order_rate_tracker[user_id] = []
        
        # Filter to last minute
        self._order_rate_tracker[user_id] = [
            t for t in self._order_rate_tracker[user_id]
            if t > cutoff
        ]
        
        if len(self._order_rate_tracker[user_id]) >= max_per_minute:
            return False
        
        self._order_rate_tracker[user_id].append(now)
        return True

    def get_risk_status(self, user_id: str) -> dict:
        """Get current risk status for user."""
        stats = self._get_daily_stats(user_id)
        limits = self.get_limits(user_id)
        
        daily_loss_limit = None
        max_trades = None
        max_position = None
        
        for limit in limits:
            if limit.rule_type == RiskRuleType.DAILY_LOSS_LIMIT:
                daily_loss_limit = {
                    "threshold": limit.threshold,
                    "current": stats.daily_pnl,
                    "remaining": limit.threshold + stats.daily_pnl,
                }
            elif limit.rule_type == RiskRuleType.MAX_TRADES_PER_DAY:
                max_trades = {
                    "threshold": limit.threshold,
                    "current": stats.trade_count,
                    "remaining": limit.threshold - stats.trade_count,
                }
            elif limit.rule_type == RiskRuleType.MAX_POSITION_SIZE:
                max_position = {
                    "threshold": limit.threshold,
                }

        return {
            "kill_switch_active": self.is_user_kill_switch_active(user_id),
            "daily_loss_limit": daily_loss_limit,
            "max_trades_per_day": max_trades,
            "max_position_size": max_position,
            "daily_stats": {
                "trade_count": stats.trade_count,
                "winning_trades": stats.winning_trades,
                "losing_trades": stats.losing_trades,
                "daily_pnl": stats.daily_pnl,
                "total_volume": stats.total_volume,
            },
        }

    async def reset_daily_limits(self, user_id: str):
        """Reset daily limits (typically called at market open)."""
        if user_id in self._daily_stats:
            self._daily_stats[user_id] = DailyStats(date=datetime.utcnow().date())
        logger.info(f"Daily limits reset for user {user_id}")


@dataclass
class DailyStats:
    """Daily trading statistics."""
    date: datetime
    trade_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    daily_pnl: float = 0
    total_volume: float = 0
    last_trade_at: Optional[datetime] = None


class RiskLimitConfig:
    """Default risk limit configurations."""

    @staticmethod
    def conservative() -> list[RiskLimit]:
        """Conservative risk limits."""
        return [
            RiskLimit(
                rule_type=RiskRuleType.DAILY_LOSS_LIMIT,
                threshold=1000,
                action=RiskAction.PAUSE_ALL_TRADING,
                is_hard=True,
            ),
            RiskLimit(
                rule_type=RiskRuleType.MAX_TRADES_PER_DAY,
                threshold=10,
                action=RiskAction.ALERT,
                is_hard=False,
            ),
            RiskLimit(
                rule_type=RiskRuleType.MAX_POSITION_SIZE,
                threshold=50000,
                action=RiskAction.REJECT_ORDER,
                is_hard=True,
            ),
            RiskLimit(
                rule_type=RiskRuleType.MIN_ACCOUNT_EQUITY,
                threshold=5000,
                action=RiskAction.KILL_SWITCH,
                is_hard=True,
            ),
        ]

    @staticmethod
    def moderate() -> list[RiskLimit]:
        """Moderate risk limits."""
        return [
            RiskLimit(
                rule_type=RiskRuleType.DAILY_LOSS_LIMIT,
                threshold=2500,
                action=RiskAction.PAUSE_ALL_TRADING,
                is_hard=True,
            ),
            RiskLimit(
                rule_type=RiskRuleType.MAX_TRADES_PER_DAY,
                threshold=25,
                action=RiskAction.ALERT,
                is_hard=False,
            ),
            RiskLimit(
                rule_type=RiskRuleType.MAX_POSITION_SIZE,
                threshold=100000,
                action=RiskAction.REJECT_ORDER,
                is_hard=True,
            ),
            RiskLimit(
                rule_type=RiskRuleType.MIN_ACCOUNT_EQUITY,
                threshold=10000,
                action=RiskAction.KILL_SWITCH,
                is_hard=True,
            ),
        ]

    @staticmethod
    def aggressive() -> list[RiskLimit]:
        """Aggressive risk limits."""
        return [
            RiskLimit(
                rule_type=RiskRuleType.DAILY_LOSS_LIMIT,
                threshold=5000,
                action=RiskAction.PAUSE_ALL_TRADING,
                is_hard=True,
            ),
            RiskLimit(
                rule_type=RiskRuleType.MAX_TRADES_PER_DAY,
                threshold=50,
                action=RiskAction.ALERT,
                is_hard=False,
            ),
            RiskLimit(
                rule_type=RiskRuleType.MAX_POSITION_SIZE,
                threshold=200000,
                action=RiskAction.REJECT_ORDER,
                is_hard=True,
            ),
        ]


# Singleton instance
_risk_manager: Optional[RiskManager] = None


def get_risk_manager() -> RiskManager:
    """Get risk manager singleton."""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Create risk manager
        risk_manager = RiskManager()

        # Set conservative limits for user
        risk_manager.set_user_limits(
            "user123",
            RiskLimitConfig.conservative()
        )

        # Check order risk
        result = await risk_manager.check_order_risk(
            user_id="user123",
            symbol="NIFTY",
            side="buy",
            quantity=100,
            price=18000,
        )
        print(f"Order risk check: {result.approved}")
        print(f"Risk level: {result.risk_level.value}")
        print(f"Message: {result.message}")

        # Record a trade
        risk_manager.record_trade(
            user_id="user123",
            symbol="NIFTY",
            quantity=100,
            price=18000,
            pnl=-500,
        )

        # Check daily loss
        result = await risk_manager.check_daily_loss(
            user_id="user123",
            current_pnl=-1200,
            account_equity=20000,
        )
        print(f"\nDaily loss check: {result.approved}")
        print(f"Action taken: {result.action_taken}")

        # Get risk status
        status = risk_manager.get_risk_status("user123")
        print(f"\nRisk status: {status}")

    asyncio.run(main())
