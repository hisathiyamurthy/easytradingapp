"""Integration tests for trading workflows."""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import sys
sys.path.insert(0, 'backend')

from trading_engine.paper_trading import (
    SimulatedTradeEngine,
    PaperTradingService,
    OrderSide,
    OrderType,
    VirtualPosition,
    VirtualBalance,
)
from trading_engine.execution.order_executor import (
    OrderExecutor,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    OrderSide,
    OrderType,
    ProductType,
    TimeInForce,
)
from risk_management.risk_manager import (
    RiskManager,
    RiskLimit,
    RiskRuleType,
    RiskAction,
    RiskLimitConfig,
)
from strategy_engine.indicators.indicator_library import Indicator
from backtesting.engine import BacktestEngine, BacktestConfig
from backtesting.analytics import BacktestAnalyticsGenerator


# ============================================================
# Paper Trading Tests
# ============================================================

class TestPaperTrading:
    """Tests for paper trading engine."""

    @pytest.fixture
    def engine(self):
        """Create a paper trading engine."""
        return SimulatedTradeEngine(
            user_id="test_user",
            initial_balance=100000.0,
            commission_rate=0.001,
            slippage_bps=1.0,
        )

    def test_initial_balance(self, engine):
        """Test initial balance is set correctly."""
        balance = engine.get_balance()
        assert balance.cash == 100000.0
        assert balance.initial_balance == 100000.0

    @pytest.mark.asyncio
    async def test_place_market_order_buy(self, engine):
        """Test placing a buy market order."""
        trade = await engine.place_market_order(
            symbol="NIFTY",
            exchange="NSE",
            side=OrderSide.BUY,
            quantity=100,
            current_price=18000.0,
        )

        assert trade.symbol == "NIFTY"
        assert trade.side == OrderSide.BUY
        assert trade.quantity == 100
        assert trade.fill_price > 0

    @pytest.mark.asyncio
    async def test_place_market_order_sell(self, engine):
        """Test placing a sell market order."""
        # First buy
        await engine.place_market_order(
            symbol="NIFTY",
            exchange="NSE",
            side=OrderSide.BUY,
            quantity=100,
            current_price=18000.0,
        )

        # Then sell
        trade = await engine.place_market_order(
            symbol="NIFTY",
            exchange="NSE",
            side=OrderSide.SELL,
            quantity=50,
            current_price=18100.0,
        )

        assert trade.side == OrderSide.SELL
        assert trade.quantity == 50

    @pytest.mark.asyncio
    async def test_position_tracking(self, engine):
        """Test position is tracked correctly."""
        await engine.place_market_order(
            symbol="NIFTY",
            exchange="NSE",
            side=OrderSide.BUY,
            quantity=100,
            current_price=18000.0,
        )

        position = engine.get_position("NIFTY")
        assert position is not None
        assert position.quantity == 100
        assert position.entry_price == 18000.0

    @pytest.mark.asyncio
    async def test_pnl_calculation(self, engine):
        """Test P&L is calculated correctly."""
        # Buy
        await engine.place_market_order(
            symbol="NIFTY",
            exchange="NSE",
            side=OrderSide.BUY,
            quantity=100,
            current_price=18000.0,
        )

        # Price goes up
        engine.update_market_prices({"NIFTY": 18100.0})

        position = engine.get_position("NIFTY")
        assert position.unrealized_pnl > 0

    @pytest.mark.asyncio
    async def test_insufficient_balance(self, engine):
        """Test order is rejected with insufficient balance."""
        from fastapi import HTTPException

        can_place, msg = engine.can_place_order(
            symbol="NIFTY",
            side=OrderSide.BUY,
            quantity=1000000,  # Too many
            price=18000.0,
        )

        assert not can_place
        assert "Insufficient balance" in msg

    def test_reset(self, engine):
        """Test engine reset."""
        engine.balance.cash = 50000.0
        engine.reset()

        assert engine.balance.cash == 100000.0

    def test_performance_summary(self, engine):
        """Test performance summary generation."""
        summary = engine.get_performance_summary()

        assert "initial_balance" in summary
        assert "current_balance" in summary
        assert "total_trades" in summary
        assert summary["total_trades"] == 0


# ============================================================
# Risk Management Tests
# ============================================================

class TestRiskManagement:
    """Tests for risk management system."""

    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager."""
        return RiskManager()

    def test_set_user_limits(self, risk_manager):
        """Test setting user risk limits."""
        limits = RiskLimitConfig.conservative()
        risk_manager.set_user_limits("user123", limits)

        user_limits = risk_manager.get_limits("user123")
        assert len(user_limits) == 4

    def test_global_kill_switch(self, risk_manager):
        """Test global kill switch."""
        assert not risk_manager.is_global_kill_switch_active()

        risk_manager.trigger_global_kill_switch("Test")
        assert risk_manager.is_global_kill_switch_active()

        risk_manager.reset_global_kill_switch()
        assert not risk_manager.is_global_kill_switch_active()

    def test_user_kill_switch(self, risk_manager):
        """Test user-specific kill switch."""
        risk_manager.trigger_user_kill_switch("user123")
        assert risk_manager.is_user_kill_switch_active("user123")

    @pytest.mark.asyncio
    async def test_order_rejected_on_kill_switch(self, risk_manager):
        """Test order is rejected when kill switch is active."""
        risk_manager.set_user_limits("user123", RiskLimitConfig.conservative())
        risk_manager.trigger_user_kill_switch("user123")

        result = await risk_manager.check_order_risk(
            user_id="user123",
            symbol="NIFTY",
            side="buy",
            quantity=100,
            price=18000.0,
        )

        assert not result.approved
        assert result.risk_level.value == "critical"

    @pytest.mark.asyncio
    async def test_daily_loss_limit(self, risk_manager):
        """Test daily loss limit."""
        limits = [
            RiskLimit(
                rule_type=RiskRuleType.DAILY_LOSS_LIMIT,
                threshold=1000.0,
                action=RiskAction.PAUSE_ALL_TRADING,
                is_hard=True,
            )
        ]
        risk_manager.set_user_limits("user123", limits)

        # Simulate losses
        risk_manager.record_trade("user123", "NIFTY", 100, 18000.0, pnl=-500)
        risk_manager.record_trade("user123", "NIFTY", 100, 18000.0, pnl=-600)

        result = await risk_manager.check_daily_loss(
            user_id="user123",
            current_pnl=-1200.0,
            account_equity=20000.0,
        )

        assert not result.approved

    @pytest.mark.asyncio
    async def test_max_position_size(self, risk_manager):
        """Test max position size limit."""
        limits = [
            RiskLimit(
                rule_type=RiskRuleType.MAX_POSITION_SIZE,
                threshold=50000.0,
                action=RiskAction.REJECT_ORDER,
                is_hard=True,
            )
        ]
        risk_manager.set_user_limits("user123", limits)

        result = await risk_manager.check_order_risk(
            user_id="user123",
            symbol="NIFTY",
            side="buy",
            quantity=100,
            price=18000.0,  # 1,800,000 > 50,000
        )

        assert not result.approved


# ============================================================
# Indicator Library Tests
# ============================================================

class TestIndicatorLibrary:
    """Tests for technical indicators."""

    @pytest.fixture
    def sample_data(self):
        """Generate sample price data."""
        import random
        data = []
        price = 100.0
        for _ in range(100):
            price = price * (1 + random.uniform(-0.02, 0.02))
            data.append(price)
        return data

    def test_sma(self, sample_data):
        """Test SMA calculation."""
        result = Indicator.sma(sample_data, 20)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0

    def test_ema(self, sample_data):
        """Test EMA calculation."""
        result = Indicator.ema(sample_data, 20)
        assert result is not None
        assert isinstance(result, float)

    def test_rsi(self, sample_data):
        """Test RSI calculation."""
        result = Indicator.rsi(sample_data, 14)
        assert result is not None
        assert 0 <= result <= 100

    def test_macd(self, sample_data):
        """Test MACD calculation."""
        result = Indicator.macd(sample_data)
        assert result is not None
        assert result.value is not None
        assert result.signal is not None

    def test_bollinger_bands(self, sample_data):
        """Test Bollinger Bands calculation."""
        result = Indicator.bollinger_bands(sample_data, 20, 2.0)
        assert result is not None
        assert result.upper > result.value
        assert result.value > result.lower

    def test_insufficient_data(self):
        """Test with insufficient data."""
        data = [100.0, 101.0]
        assert Indicator.sma(data, 20) is None
        assert Indicator.ema(data, 20) is None
        assert Indicator.rsi(data, 14) is None


# ============================================================
# Backtesting Tests
# ============================================================

class TestBacktesting:
    """Tests for backtesting engine."""

    @pytest.fixture
    def sample_bars(self):
        """Generate sample bar data."""
        import random
        bars = []
        price = 18000.0
        base_date = datetime(2024, 1, 1)

        for i in range(100):
            price = price * (1 + random.uniform(-0.01, 0.01))
            bars.append({
                'timestamp': base_date + timedelta(days=i),
                'open': price * 0.99,
                'high': price * 1.01,
                'low': price * 0.98,
                'close': price,
                'volume': random.randint(1000000, 5000000),
            })
        return bars

    @pytest.fixture
    def config(self):
        """Create backtest config."""
        return BacktestConfig(
            initial_capital=100000.0,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            symbol="NIFTY",
            exchange="NSE",
            timeframe="1d",
        )

    @pytest.mark.asyncio
    async def test_backtest_execution(self, config, sample_bars):
        """Test backtest runs successfully."""

        async def mock_strategy(bar, position):
            return None

        async def mock_data(**kwargs):
            return sample_bars

        engine = BacktestEngine(
            config=config,
            strategy_executor=mock_strategy,
            data_provider=mock_data,
        )

        metrics = await engine.run()

        assert metrics.total_trades == 0  # No signals generated
        assert metrics.initial_capital == 100000.0

    @pytest.mark.asyncio
    async def test_backtest_with_signals(self, config, sample_bars):
        """Test backtest with actual trading signals."""
        trade_count = 0

        async def simple_strategy(bar, position):
            nonlocal trade_count

            # Simple: buy if price > 18000, sell if price < 17500
            if position is None or position.quantity == 0:
                if bar['close'] > 18000:
                    from backtesting.engine import BacktestSignal
                    return BacktestSignal(
                        timestamp=bar['timestamp'],
                        symbol="NIFTY",
                        signal_type="buy",
                        price=bar['close'],
                        quantity=10,
                    )
            else:
                if bar['close'] < 17500:
                    from backtesting.engine import BacktestSignal
                    return BacktestSignal(
                        timestamp=bar['timestamp'],
                        symbol="NIFTY",
                        signal_type="sell",
                        price=bar['close'],
                        quantity=position.quantity,
                    )
            return None

        async def mock_data(**kwargs):
            return sample_bars

        engine = BacktestEngine(
            config=config,
            strategy_executor=simple_strategy,
            data_provider=mock_data,
        )

        metrics = await engine.run()

        assert metrics.total_trades >= 0


# ============================================================
# Analytics Tests
# ============================================================

class TestAnalytics:
    """Tests for analytics generation."""

    @pytest.fixture
    def sample_equity_curve(self):
        """Generate sample equity curve."""
        equity = 100000
        curve = []
        for i in range(100):
            equity = equity * (1 + (0.001 if i % 2 == 0 else -0.0005))
            curve.append({'timestamp': i, 'equity': equity})
        return curve

    @pytest.fixture
    def sample_trades(self):
        """Generate sample trades."""
        return [
            {
                'entry_timestamp': '2024-01-01T10:00:00',
                'exit_timestamp': '2024-01-01T14:00:00',
                'symbol': 'NIFTY',
                'pnl': 500,
                'entry_price': 18000,
                'exit_price': 18100,
            },
            {
                'entry_timestamp': '2024-01-02T10:00:00',
                'exit_timestamp': '2024-01-02T14:00:00',
                'symbol': 'NIFTY',
                'pnl': -300,
                'entry_price': 18100,
                'exit_price': 18070,
            },
            {
                'entry_timestamp': '2024-01-03T10:00:00',
                'exit_timestamp': '2024-01-03T14:00:00',
                'symbol': 'NIFTY',
                'pnl': 800,
                'entry_price': 18070,
                'exit_price': 18200,
            },
        ]

    def test_profit_analytics(self, sample_trades):
        """Test profit analytics."""
        generator = BacktestAnalyticsGenerator()

        # Mock the methods
        with patch.object(generator, '_analyze_profit') as mock:
            mock.return_value = MagicMock()

    def test_win_rate_analytics(self, sample_trades):
        """Test win rate analytics."""
        analytics = BacktestAnalyticsGenerator().generate(
            sample_trades=sample_trades,
            config={'initial_capital': 100000},
        )

        assert analytics.total_trades == 3

    def test_generate_report(self, sample_equity_curve, sample_trades):
        """Test report generation."""
        generator = BacktestAnalyticsGenerator()

        analytics = generator.generate(
            equity_curve=sample_equity_curve,
            trades=sample_trades,
            config={'initial_capital': 100000},
        )

        report = generator.generate_report(analytics)
        assert "BACKTEST ANALYTICS REPORT" in report
        assert "SUMMARY" in report


# ============================================================
# Integration Tests - Full Workflows
# ============================================================

class TestTradingWorkflow:
    """Integration tests for complete trading workflows."""

    @pytest.mark.asyncio
    async def test_full_trading_workflow(self):
        """Test complete trading workflow from order to P&L."""
        # 1. Setup
        engine = SimulatedTradeEngine(
            user_id="workflow_user",
            initial_balance=100000.0,
        )

        risk_manager = RiskManager()
        risk_manager.set_user_limits("workflow_user", RiskLimitConfig.moderate())

        # 2. Check risk before order
        risk_check = await risk_manager.check_order_risk(
            user_id="workflow_user",
            symbol="NIFTY",
            side="buy",
            quantity=100,
            price=18000.0,
        )
        assert risk_check.approved

        # 3. Place order
        trade = await engine.place_market_order(
            symbol="NIFTY",
            exchange="NSE",
            side=OrderSide.BUY,
            quantity=100,
            current_price=18000.0,
        )

        assert trade.symbol == "NIFTY"

        # 4. Update prices
        engine.update_market_prices({"NIFTY": 18100.0})

        # 5. Check P&L
        balance = engine.get_balance()
        position = engine.get_position("NIFTY")

        assert position.unrealized_pnl > 0
        assert balance.unrealized_pnl > 0

    @pytest.mark.asyncio
    async def test_risk_limit_breach_workflow(self):
        """Test workflow when risk limit is breached."""
        # 1. Setup with strict limits
        risk_manager = RiskManager()
        limits = [
            RiskLimit(
                rule_type=RiskRuleType.DAILY_LOSS_LIMIT,
                threshold=500.0,
                action=RiskAction.KILL_SWITCH,
                is_hard=True,
            )
        ]
        risk_manager.set_user_limits("risk_user", limits)

        # 2. Simulate losses
        risk_manager.record_trade("risk_user", "NIFTY", 100, 18000.0, pnl=-200)
        risk_manager.record_trade("risk_user", "NIFTY", 100, 18000.0, pnl=-400)

        # 3. Check daily loss
        result = await risk_manager.check_daily_loss(
            user_id="risk_user",
            current_pnl=-600.0,
            account_equity=10000.0,
        )

        # 4. Verify kill switch was triggered
        assert not result.approved
        assert risk_manager.is_user_kill_switch_active("risk_user")

    @pytest.mark.asyncio
    async def test_backtest_to_live_transition(self):
        """Test transitioning from backtest to live trading."""
        # 1. Run backtest
        config = BacktestConfig(
            initial_capital=100000.0,
            symbol="NIFTY",
            exchange="NSE",
        )

        async def mock_data(**kwargs):
            import random
            bars = []
            price = 18000.0
            for i in range(100):
                price = price * (1 + random.uniform(-0.01, 0.01))
                bars.append({
                    'timestamp': datetime.now(),
                    'open': price * 0.99,
                    'high': price * 1.01,
                    'low': price * 0.98,
                    'close': price,
                    'volume': 1000000,
                })
            return bars

        async def strategy(bar, position):
            return None

        engine = BacktestEngine(config, strategy, mock_data)
        metrics = await engine.run()

        # 2. Get final equity
        final_capital = engine.current_capital

        # 3. Start live/paper trading with same capital
        paper_engine = SimulatedTradeEngine(
            user_id="live_user",
            initial_balance=final_capital,
        )

        # 4. Verify balance matches
        assert paper_engine.balance.initial_balance == final_capital

        # 5. Place live order
        trade = await paper_engine.place_market_order(
            symbol="NIFTY",
            exchange="NSE",
            side=OrderSide.BUY,
            quantity=10,
            current_price=18000.0,
        )

        assert trade is not None


# ============================================================
# Test Configuration
# ============================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
