"""
Live Trading Service - Real broker integration.
Connects to broker APIs for actual trade execution.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from abc import ABC, abstractmethod
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.strategy_models import Strategy
from models.strategy_instance_models import UserStrategyInstance, InstanceTrade, InstancePosition

logger = logging.getLogger(__name__)

_broker_sessions: Dict[str, Dict[str, Any]] = {}


class BaseBroker(ABC):
    """Abstract base class for broker integrations."""
    
    @abstractmethod
    async def connect(self, api_key: str, api_secret: str, **kwargs) -> bool:
        """Connect to broker API."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from broker."""
        pass
    
    @abstractmethod
    async def get_profile(self) -> Dict[str, Any]:
        """Get broker profile."""
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance."""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: str, quantity: int, 
                         order_type: str = "MARKET", price: float = None,
                         product: str = "MIS") -> Dict[str, Any]:
        """Place an order."""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions."""
        pass
    
    @abstractmethod
    async def get_ltp(self, symbol: str) -> float:
        """Get last traded price."""
        pass


class MockBroker(BaseBroker):
    """Mock broker for testing without real API."""
    
    def __init__(self):
        self.connected = False
        self.api_key = None
        self.balance = 100000.0
        self.positions = []
        self.orders = []
    
    async def connect(self, api_key: str, api_secret: str, **kwargs) -> bool:
        logger.info(f"Mock broker connecting with key: {api_key[:10]}...")
        self.connected = True
        self.api_key = api_key
        return True
    
    async def test_connection(self, api_key: str, api_secret: str, account_id: str = None) -> bool:
        """Test broker connection without establishing persistent connection."""
        logger.info(f"Testing mock broker connection for account: {account_id}")
        
        # Mock validates that credentials are non-empty
        if not api_key or not api_secret:
            logger.warning("Mock broker test failed: missing credentials")
            return False
        
        # For mock broker, any non-empty credentials work
        if api_key == "test" or api_key.startswith("TEST"):
            logger.info("Mock broker test failed: invalid test credentials")
            return False
            
        logger.info("Mock broker connection test successful")
        return True
    
    async def disconnect(self) -> bool:
        self.connected = False
        return True
    
    async def get_profile(self) -> Dict[str, Any]:
        return {
            "user_id": "mock_user",
            "user_name": "Mock Trader",
            "email": "mock@example.com",
            "broker": "MOCK",
            "avatar": None,
        }
    
    async def get_balance(self) -> Dict[str, float]:
        return {
            "equity": self.balance,
            "cash": self.balance * 0.5,
            "margin": self.balance * 2,
            "available_margin": self.balance * 1.5,
        }
    
    async def place_order(self, symbol: str, side: str, quantity: int,
                         order_type: str = "MARKET", price: float = None,
                         product: str = "MIS") -> Dict[str, Any]:
        if not self.connected:
            raise Exception("Broker not connected")
        
        current_price = price or (100 + random.uniform(-10, 10))
        
        order = {
            "order_id": f"MOCK_{uuid4().hex[:8]}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": current_price,
            "order_type": order_type,
            "product": product,
            "status": "COMPLETE",
            "filled_quantity": quantity,
            "average_price": current_price,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.orders.append(order)
        
        if side == "BUY":
            self.balance -= current_price * quantity
        else:
            self.balance += current_price * quantity
        
        return order
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        for order in self.orders:
            if order["order_id"] == order_id:
                return order
        raise Exception(f"Order not found: {order_id}")
    
    async def cancel_order(self, order_id: str) -> bool:
        for order in self.orders:
            if order["order_id"] == order_id and order["status"] == "PENDING":
                order["status"] = "CANCELLED"
                return True
        return False
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        return self.positions
    
    async def get_ltp(self, symbol: str) -> float:
        return 100 + random.uniform(-5, 5)


class LiveTradingService:
    """Live trading execution service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def connect_broker(self, user_id: UUID, broker_name: str, 
                           api_key: str, api_secret: str, **credentials) -> Dict[str, Any]:
        """Connect to a broker."""
        broker = MockBroker() if broker_name.upper() == "MOCK" else self._create_broker(broker_name)
        
        success = await broker.connect(api_key, api_secret, **credentials)
        
        if success:
            user_id_str = str(user_id)
            _broker_sessions[user_id_str] = {
                "broker": broker,
                "broker_name": broker_name,
                "connected_at": datetime.now(timezone.utc),
            }
            profile = await broker.get_profile()
            balance = await broker.get_balance()
            
            logger.info(f"User {user_id} connected to {broker_name}")
            
            return {
                "connected": True,
                "broker": broker_name,
                "profile": profile,
                "balance": balance,
            }
        
        return {"connected": False, "error": "Failed to connect"}
    
    def _create_broker(self, broker_name: str) -> BaseBroker:
        """Create broker instance based on name."""
        if broker_name.upper() == "ZERODHA":
            return ZerodhaBroker()
        elif broker_name.upper() == "UPSTOX":
            return UpstoxBroker()
        else:
            return MockBroker()
    
    async def disconnect_broker(self, user_id: UUID) -> bool:
        """Disconnect from broker."""
        user_id_str = str(user_id)
        if user_id_str in _broker_sessions:
            session = _broker_sessions[user_id_str]
            await session["broker"].disconnect()
            del _broker_sessions[user_id_str]
            logger.info(f"User {user_id} disconnected broker")
            return True
        return False
    
    async def is_connected(self, user_id: UUID) -> bool:
        """Check if user is connected to broker."""
        return str(user_id) in _broker_sessions
    
    def get_broker(self, user_id: UUID) -> Optional[BaseBroker]:
        """Get user's broker."""
        session = _broker_sessions.get(str(user_id))
        return session["broker"] if session else None
    
    async def start_live_trading(self, strategy_id: UUID, user_id: UUID, 
                                 broker_account_id: UUID, capital: float = 100000.0) -> UserStrategyInstance:
        """Start live trading for a strategy."""
        if user_id not in self.brokers:
            raise Exception("No broker connected. Please connect to a broker first.")
        
        instance = UserStrategyInstance(
            id=uuid4(),
            user_id=user_id,
            strategy_id=strategy_id,
            broker_account_id=broker_account_id,
            name=f"Live Trading - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            capital=capital,
            allocated_capital=capital,
            status="running",
            mode="live",
            started_at=datetime.now(timezone.utc),
        )
        
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        
        logger.info(f"Started live trading instance {instance.id} for strategy {strategy_id}")
        return instance
    
    async def execute_live_trade(self, instance_id: UUID, user_id: UUID,
                                trade_signal: Dict[str, Any]) -> Optional[InstanceTrade]:
        """Execute a live trade through the broker."""
        broker = self.get_broker(user_id)
        if not broker:
            raise Exception("No broker connected")
        
        order = await broker.place_order(
            symbol=trade_signal["symbol"],
            side=trade_signal["action"],
            quantity=trade_signal["quantity"],
            order_type="MARKET",
            product="MIS",
        )
        
        trade = InstanceTrade(
            id=uuid4(),
            instance_id=instance_id,
            user_id=user_id,
            symbol=trade_signal["symbol"],
            exchange="NSE",
            side=trade_signal["action"],
            quantity=trade_signal["quantity"],
            entry_price=order["average_price"],
            commission=order["average_price"] * trade_signal["quantity"] * 0.001,
            slippage=0,
            entry_time=datetime.now(timezone.utc),
            entry_signal=f"Live Order: {order['order_id']}",
            broker_order_id=order["order_id"],
        )
        
        if trade_signal.get("position_id"):
            position = await self._get_position(trade_signal["position_id"])
            if position:
                position.exit_price = order["average_price"]
                position.exit_time = datetime.now(timezone.utc)
                position.is_open = False
                
                pnl = (order["average_price"] - position.entry_price) * position.quantity
                if position.side == "SELL":
                    pnl = -pnl
                trade.pnl = pnl - trade.commission
                trade.exit_reason = trade_signal.get("signal", "manual")
        
        self.db.add(trade)
        
        if not trade_signal.get("position_id"):
            position = InstancePosition(
                id=uuid4(),
                instance_id=instance_id,
                user_id=user_id,
                symbol=trade_signal["symbol"],
                exchange="NSE",
                side=trade_signal["action"],
                quantity=trade_signal["quantity"],
                entry_price=order["average_price"],
                current_price=order["average_price"],
                unrealized_pnl=0,
                is_open=True,
                opened_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                broker_order_id=order["order_id"],
            )
            self.db.add(position)
        
        await self.db.commit()
        await self.db.refresh(trade)
        
        logger.info(f"Executed live trade: {trade.side} {trade.quantity} {trade.symbol} @ {trade.entry_price}")
        return trade
    
    async def execute_bracket_order(
        self,
        instance_id: UUID,
        user_id: UUID,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        product: str = "MIS",
    ) -> Dict[str, Any]:
        """
        Execute a bracket order: Entry + SL + Target all in one transaction.
        Returns dict with entry_order, sl_order, tp_order details.
        """
        from broker_integrations.base import OrderType, OrderSide, ProductType
        
        broker = self.get_broker(user_id)
        if not broker:
            raise Exception("No broker connected")
        
        results = {
            "entry_order": None,
            "sl_order": None,
            "tp_order": None,
            "position": None,
        }
        
        # Place entry order
        order_type = OrderType.LIMIT if entry_price else OrderType.MARKET
        entry_order = await broker.place_order(
            symbol=symbol,
            side=side.upper(),
            quantity=quantity,
            order_type=order_type,
            price=entry_price,
            product_type=ProductType.MIS if product == "MIS" else ProductType.NRML,
        )
        
        results["entry_order"] = entry_order
        actual_entry_price = entry_order.get("average_price", entry_price or 0)
        
        # If SL is defined, place SL order
        if stop_loss:
            sl_side = "SELL" if side.upper() == "BUY" else "BUY"
            sl_order = await broker.place_order(
                symbol=symbol,
                side=sl_side,
                quantity=quantity,
                order_type=OrderType.SLM,
                trigger_price=stop_loss,
                product_type=ProductType.MIS if product == "MIS" else ProductType.NRML,
            )
            results["sl_order"] = sl_order
            logger.info(f"Bracket SL order placed: {sl_side} {quantity} {symbol} @ trigger {stop_loss}")
        
        # If Target is defined, place target order
        if take_profit:
            tp_side = "SELL" if side.upper() == "BUY" else "BUY"
            tp_order = await broker.place_order(
                symbol=symbol,
                side=tp_side,
                quantity=quantity,
                order_type=OrderType.SLM,
                trigger_price=take_profit,
                product_type=ProductType.MIS if product == "MIS" else ProductType.NRML,
            )
            results["tp_order"] = tp_order
            logger.info(f"Bracket Target order placed: {tp_side} {quantity} {symbol} @ trigger {take_profit}")
        
        # Create position record
        position = InstancePosition(
            id=uuid4(),
            instance_id=instance_id,
            user_id=user_id,
            symbol=symbol,
            exchange="NSE",
            side=side.upper(),
            quantity=quantity,
            entry_price=actual_entry_price,
            current_price=actual_entry_price,
            unrealized_pnl=0,
            is_open=True,
            opened_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            broker_order_id=entry_order.get("order_id"),
            stop_loss=stop_loss,
            take_profit=take_profit,
            sl_order_id=results["sl_order"].get("order_id") if results["sl_order"] else None,
            tp_order_id=results["tp_order"].get("order_id") if results["tp_order"] else None,
        )
        
        self.db.add(position)
        await self.db.commit()
        
        results["position"] = {
            "id": str(position.id),
            "symbol": position.symbol,
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit,
        }
        
        logger.info(f"Bracket order executed: {side.upper()} {quantity} {symbol} @ {actual_entry_price}, SL: {stop_loss}, TP: {take_profit}")
        
        return results
    
    async def sync_positions(self, instance_id: UUID, user_id: UUID):
        """Sync positions with broker."""
        broker = self.get_broker(user_id)
        if not broker:
            return
        
        broker_positions = await broker.get_positions()
        
        result = await self.db.execute(
            select(InstancePosition).where(
                and_(
                    InstancePosition.instance_id == instance_id,
                    InstancePosition.is_open == True
                )
            )
        )
        db_positions = result.scalars().all()
        
        for db_pos in db_positions:
            ltp = await broker.get_ltp(db_pos.symbol)
            db_pos.current_price = ltp
            db_pos.updated_at = datetime.now(timezone.utc)
            
            pnl = (ltp - db_pos.entry_price) * db_pos.quantity
            if db_pos.side == "SELL":
                pnl = -pnl
            db_pos.unrealized_pnl = pnl
        
        await self.db.commit()
    
    async def _get_position(self, position_id: UUID) -> Optional[InstancePosition]:
        """Get position by ID."""
        result = await self.db.execute(
            select(InstancePosition).where(InstancePosition.id == position_id)
        )
        return result.scalar_one_or_none()
    
    async def pause_instance(self, instance_id: UUID):
        """Pause live trading."""
        result = await self.db.execute(
            select(UserStrategyInstance).where(UserStrategyInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        if instance:
            instance.status = "paused"
            instance.paused_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.info(f"Paused live trading instance {instance_id}")
    
    async def resume_instance(self, instance_id: UUID):
        """Resume live trading."""
        result = await self.db.execute(
            select(UserStrategyInstance).where(UserStrategyInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        if instance:
            instance.status = "running"
            instance.paused_at = None
            await self.db.commit()
            logger.info(f"Resumed live trading instance {instance_id}")
    
    async def stop_instance(self, instance_id: UUID):
        """Stop live trading."""
        result = await self.db.execute(
            select(UserStrategyInstance).where(UserStrategyInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        if instance:
            instance.status = "stopped"
            instance.stopped_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.info(f"Stopped live trading instance {instance_id}")

    async def check_trailing_stoploss(
        self,
        position: InstancePosition,
        current_price: float,
        user_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Check and update trailing stop loss.
        Returns dict with action taken (update_sl, exit) or None if no action needed.
        """
        if not position.is_open or not position.stop_loss:
            return None
        
        # Get trailing SL config from position or strategy
        trailing_pct = getattr(position, 'trailing_stop_loss', None)
        activation_pct = getattr(position, 'trailing_stop_activation', None)
        
        if not trailing_pct:
            return None
        
        entry_price = position.entry_price
        profit_pct = ((current_price - entry_price) / entry_price) * 100
        
        # Check if profit has reached activation threshold
        if activation_pct and profit_pct < activation_pct:
            return None  # Not yet activated
        
        # Calculate new SL based on trailing percentage
        if position.side == "BUY":
            new_sl = current_price * (1 - trailing_pct / 100)
            # Only update if new SL is higher than current SL
            if new_sl <= (position.stop_loss or 0):
                return None
        else:  # SELL
            new_sl = current_price * (1 + trailing_pct / 100)
            # Only update if new SL is lower than current SL
            if new_sl >= (position.stop_loss or float('inf')):
                return None
        
        # Update position SL
        position.stop_loss = new_sl
        await self.db.commit()
        
        # Update broker SL order if exists
        if position.sl_order_id and position.broker_order_id:
            try:
                broker = self.get_broker(user_id)
                if broker:
                    # Cancel old SL
                    await broker.cancel_order(position.sl_order_id)
                    # Place new SL
                    new_sl_side = "SELL" if position.side == "BUY" else "BUY"
                    new_sl_order = await broker.place_order(
                        symbol=position.symbol,
                        side=new_sl_side,
                        quantity=position.quantity,
                        order_type="SL-M",
                        trigger_price=new_sl,
                        product_type="MIS",
                    )
                    position.sl_order_id = new_sl_order.get("order_id")
                    await self.db.commit()
                    
                    logger.info(f"Trailing SL updated: {position.symbol} SL@{new_sl:.2f}")
                    return {"action": "update_sl", "new_sl": new_sl}
            except Exception as e:
                logger.error(f"Failed to update trailing SL: {e}")
        
        return {"action": "update_sl", "new_sl": new_sl}


class ZerodhaBroker(BaseBroker):
    """Zerodha Kite Connect integration."""
    
    def __init__(self):
        self.kite = None
        self.access_token = None
        self.connected = False
    
    async def connect(self, api_key: str, api_secret: str, **kwargs) -> bool:
        try:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=api_key)
            
            request_token = kwargs.get("request_token")
            if request_token:
                data = self.kite.generate_session(request_token, api_secret)
                self.access_token = data["access_token"]
                self.kite.set_access_token(self.access_token)
                self.connected = True
                return True
            return False
        except Exception as e:
            logger.error(f"Zerodha connection error: {e}")
            return False
    
    async def disconnect(self) -> bool:
        self.kite = None
        self.access_token = None
        self.connected = False
        return True
    
    async def get_profile(self) -> Dict[str, Any]:
        if not self.kite:
            raise Exception("Not connected")
        profile = self.kite.profile()
        return {
            "user_id": str(profile.get("user_id")),
            "user_name": profile.get("user_name"),
            "email": profile.get("email"),
            "broker": "ZERODHA",
            "avatar": profile.get("avatar"),
        }
    
    async def get_balance(self) -> Dict[str, Any]:
        if not self.kite:
            raise Exception("Not connected")
        margins = self.kite.margins()
        equity = margins.get("equity", {})
        return {
            "equity": equity.get("net", 0),
            "cash": equity.get("cash", 0),
            "margin": equity.get("margin_used", 0),
            "available_margin": equity.get("available", 0),
        }
    
    async def place_order(self, symbol: str, side: str, quantity: int,
                         order_type: str = "MARKET", price: float = None,
                         product: str = "MIS") -> Dict[str, Any]:
        if not self.kite:
            raise Exception("Not connected")
        
        transaction_type = "BUY" if side == "BUY" else "SELL"
        order = self.kite.place_order(
            exchange="NSE",
            tradingsymbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            price=price,
            product=product,
            variety="regular",
        )
        
        return {
            "order_id": str(order),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "status": "PENDING",
        }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self.kite:
            raise Exception("Not connected")
        orders = self.kite.order_history(order_id)
        return orders[-1] if orders else {}
    
    async def cancel_order(self, order_id: str) -> bool:
        if not self.kite:
            raise Exception("Not connected")
        self.kite.cancel_order(variety="regular", order_id=order_id)
        return True
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        if not self.kite:
            raise Exception("Not connected")
        positions = self.kite.positions()
        return positions.get("net", [])
    
    async def get_ltp(self, symbol: str) -> float:
        if not self.kite:
            raise Exception("Not connected")
        ltp_data = self.kite.ltp([f"NSE:{symbol}"])
        return ltp_data.get(f"NSE:{symbol}", {}).get("last_price", 0)


class UpstoxBroker(BaseBroker):
    """Upstox integration."""
    
    def __init__(self):
        self.api = None
        self.access_token = None
        self.connected = False
    
    async def connect(self, api_key: str, api_secret: str, **kwargs) -> bool:
        try:
            from upstox_api.live import Upstox
            self.api = Upstox(api_key)
            
            auth_code = kwargs.get("auth_code")
            if auth_code:
                data = self.api.generate_session(auth_code, api_secret)
                self.access_token = data.get("access_token")
                self.api.set_access_token(self.access_token)
                self.connected = True
                return True
            return False
        except Exception as e:
            logger.error(f"Upstox connection error: {e}")
            return False
    
    async def disconnect(self) -> bool:
        self.api = None
        self.access_token = None
        self.connected = False
        return True
    
    async def get_profile(self) -> Dict[str, Any]:
        if not self.api:
            raise Exception("Not connected")
        profile = self.api.get_profile()
        return {
            "user_id": profile.get("user_id"),
            "user_name": profile.get("name"),
            "email": profile.get("email"),
            "broker": "UPSTOX",
        }
    
    async def get_balance(self) -> Dict[str, Any]:
        if not self.api:
            raise Exception("Not connected")
        balance = self.api.get_balance()
        return {
            "equity": balance.get("equity", {}).get("net_value", 0),
            "available_margin": balance.get("equity", {}).get("available_margin", 0),
        }
    
    async def place_order(self, symbol: str, side: str, quantity: int,
                         order_type: str = "MARKET", price: float = None,
                         product: str = "D") -> Dict[str, Any]:
        if not self.api:
            raise Exception("Not connected")
        
        transaction_type = "BUY" if side == "BUY" else "SELL"
        order = self.api.place_order(
            exchange="NSE",
            symbol=symbol,
            quantity=quantity,
            transaction_type=transaction_type,
            order_type=order_type.upper(),
            product_type=product,
            price=price,
        )
        
        return {
            "order_id": str(order.get("order_id")),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "status": "PENDING",
        }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self.api:
            raise Exception("Not connected")
        return self.api.get_order_history(order_id)
    
    async def cancel_order(self, order_id: str) -> bool:
        if not self.api:
            raise Exception("Not connected")
        self.api.cancel_order(order_id)
        return True
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        if not self.api:
            raise Exception("Not connected")
        return self.api.get_positions()
    
    async def get_ltp(self, symbol: str) -> float:
        if not self.api:
            raise Exception("Not connected")
        ltp = self.api.get_ltp(f"NSE_EQ:{symbol}")
        return ltp
