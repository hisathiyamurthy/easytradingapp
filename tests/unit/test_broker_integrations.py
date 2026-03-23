"""Unit tests for broker integrations."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
sys.path.insert(0, 'backend')

from broker_integrations.base import (
    BrokerName,
    OrderSide,
    OrderType,
    OrderStatus,
    ProductType,
    BrokerConfig,
    OrderRequest,
    BrokerRegistry,
)
from broker_integrations.zerodha import ZerodhaBroker


class TestBrokerEnums:
    """Tests for broker enum values."""

    def test_broker_name_values(self):
        """Test BrokerName enum values."""
        assert BrokerName.ZERODHA.value == "zerodha"
        assert BrokerName.KOTAK_NEO.value == "kotak_neo"
        assert BrokerName.UPSTOX.value == "upstox"
        assert BrokerName.ANGEL_ONE.value == "angel_one"

    def test_order_side_values(self):
        """Test OrderSide enum values."""
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"

    def test_order_type_values(self):
        """Test OrderType enum values."""
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.SL.value == "sl"
        assert OrderType.SLM.value == "slm"

    def test_order_status_values(self):
        """Test OrderStatus enum values."""
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.SUBMITTED.value == "submitted"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.CANCELLED.value == "cancelled"
        assert OrderStatus.REJECTED.value == "rejected"

    def test_product_type_values(self):
        """Test ProductType enum values."""
        assert ProductType.CNC.value == "cnc"
        assert ProductType.MIS.value == "mis"
        assert ProductType.NRML.value == "nrml"


class TestBrokerConfig:
    """Tests for BrokerConfig."""

    def test_broker_config_creation(self):
        """Test creating a broker config."""
        config = BrokerConfig(
            broker_name=BrokerName.ZERODHA,
            api_key="test_key",
            api_secret="test_secret",
        )

        assert config.broker_name == BrokerName.ZERODHA
        assert config.api_key == "test_key"
        assert config.api_secret == "test_secret"

    def test_broker_config_with_additional_fields(self):
        """Test broker config with additional fields."""
        config = BrokerConfig(
            broker_name=BrokerName.ZERODHA,
            api_key="test_key",
            api_secret="test_secret",
            additional_fields={"totp_secret": "secret123"},
        )

        assert config.additional_fields["totp_secret"] == "secret123"


class TestOrderRequest:
    """Tests for OrderRequest."""

    def test_order_request_market_order(self):
        """Test creating a market order request."""
        order = OrderRequest(
            symbol="RELIANCE",
            exchange="NSE",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
        )

        assert order.symbol == "RELIANCE"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == 100

    def test_order_request_limit_order(self):
        """Test creating a limit order request."""
        order = OrderRequest(
            symbol="TCS",
            exchange="NSE",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=50,
            price=3500.0,
        )

        assert order.price == 3500.0
        assert order.side == OrderSide.SELL

    def test_order_request_with_stop_loss(self):
        """Test creating a stop loss order."""
        order = OrderRequest(
            symbol="INFY",
            exchange="NSE",
            side=OrderSide.BUY,
            order_type=OrderType.SL,
            quantity=100,
            price=1500.0,
            trigger_price=1490.0,
        )

        assert order.trigger_price == 1490.0


class TestBrokerRegistry:
    """Tests for BrokerRegistry."""

    def test_broker_registry_register(self):
        """Test registering a broker."""
        @BrokerRegistry.register(BrokerName.ZERODHA)
        class TestBroker:
            pass

        assert BrokerName.ZERODHA in BrokerRegistry._brokers

    def test_broker_registry_get(self):
        """Test getting a registered broker."""
        broker_class = BrokerRegistry.get_broker(BrokerName.ZERODHA)
        assert broker_class is not None


class TestZerodhaBroker:
    """Tests for ZerodhaBroker."""

    @pytest.fixture
    def broker_config(self):
        """Create broker config for testing."""
        return BrokerConfig(
            broker_name=BrokerName.ZERODHA,
            api_key="test_api_key",
            api_secret="test_api_secret",
        )

    @pytest.fixture
    def encryption_key(self):
        """Create encryption key for testing."""
        return b"0123456789abcdef" * 2  # 32 bytes

    def test_zerodha_broker_creation(self, broker_config, encryption_key):
        """Test creating Zerodha broker instance."""
        broker = ZerodhaBroker(broker_config, encryption_key)

        assert broker.api_key == "test_api_key"
        assert broker.api_secret == "test_api_secret"

    def test_zerodha_get_credential_fields(self):
        """Test getting credential fields."""
        fields = ZerodhaBroker.get_credential_fields()

        assert len(fields) == 3
        assert fields[0].name == "api_key"
        assert fields[1].name == "api_secret"
        assert fields[2].name == "totp_secret"

    def test_zerodha_get_required_scopes(self):
        """Test getting required scopes."""
        scopes = ZerodhaBroker.get_required_scopes()

        assert "order" in scopes
        assert "trade" in scopes
        assert "position" in scopes
        assert "portfolio" in scopes

    def test_zerodha_encrypt_decrypt(self, broker_config, encryption_key):
        """Test encryption and decryption."""
        broker = ZerodhaBroker(broker_config, encryption_key)

        original = "test_password"
        encrypted = broker._encrypt(original)
        decrypted = broker._decrypt(encrypted)

        assert decrypted == original
        assert encrypted != original

    @pytest.mark.asyncio
    async def test_zerodha_test_connection_failure(self, broker_config, encryption_key):
        """Test connection failure handling."""
        broker = ZerodhaBroker(broker_config, encryption_key)

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response

            result = await broker.test_connection()

            assert result.is_connected is False

    @pytest.mark.asyncio
    async def test_zerodha_place_order(self, broker_config, encryption_key):
        """Test placing an order."""
        broker = ZerodhaBroker(broker_config, encryption_key)
        broker._access_token = "test_token"

        order_request = OrderRequest(
            symbol="RELIANCE",
            exchange="NSE",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            product_type=ProductType.MIS,
        )

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "order_id": "12345",
                    "tradingsymbol": "RELIANCE",
                    "exchange": "NSE",
                    "transaction_type": "BUY",
                    "status": "COMPLETE",
                    "quantity": 100,
                    "filled_quantity": 100,
                    "average_price": 2500.0,
                    "order_timestamp": "2026-03-09T10:00:00",
                }
            }
            mock_post.return_value = mock_response

            result = await broker.place_order(order_request)

            assert result.broker_order_id == "12345"
            assert result.status == OrderStatus.FILLED

    def test_zerodha_generate_signature(self, broker_config, encryption_key):
        """Test signature generation."""
        broker = ZerodhaBroker(broker_config, encryption_key)

        signature = broker._generate_signature(
            "GET",
            "/orders",
            {"order_id": "123"}
        )

        assert signature is not None
        assert isinstance(signature, str)


class TestOrderStatusMapping:
    """Tests for order status mapping."""

    def test_map_order_status_completed(self):
        """Test mapping COMPLETED status."""
        broker = ZerodhaBroker(
            BrokerConfig(
                broker_name=BrokerName.ZERODHA,
                api_key="test",
                api_secret="test",
            ),
            b"0123456789abcdef" * 2
        )

        status = broker._map_order_status("COMPLETE")
        assert status == OrderStatus.FILLED

    def test_map_order_status_cancelled(self):
        """Test mapping CANCELLED status."""
        broker = ZerodhaBroker(
            BrokerConfig(
                broker_name=BrokerName.ZERODHA,
                api_key="test",
                api_secret="test",
            ),
            b"0123456789abcdef" * 2
        )

        status = broker._map_order_status("CANCELLED")
        assert status == OrderStatus.CANCELLED

    def test_map_order_status_rejected(self):
        """Test mapping REJECTED status."""
        broker = ZerodhaBroker(
            BrokerConfig(
                broker_name=BrokerName.ZERODHA,
                api_key="test",
                api_secret="test",
            ),
            b"0123456789abcdef" * 2
        )

        status = broker._map_order_status("REJECTED")
        assert status == OrderStatus.REJECTED

    def test_map_order_status_unknown(self):
        """Test mapping unknown status."""
        broker = ZerodhaBroker(
            BrokerConfig(
                broker_name=BrokerName.ZERODHA,
                api_key="test",
                api_secret="test",
            ),
            b"0123456789abcdef" * 2
        )

        status = broker._map_order_status("UNKNOWN_STATUS")
        assert status == OrderStatus.PENDING
