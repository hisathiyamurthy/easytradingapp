-- EasyTradingApp PostgreSQL Schema
-- Version: 1.0
-- Database: easytradingapp
-- Created: March 2026

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE user_role AS ENUM ('admin', 'trader', 'viewer');
CREATE TYPE broker_name AS ENUM ('alpaca', 'interactive_brokers', 'td_ameritrade', 'robinhood');
CREATE TYPE order_side AS ENUM ('buy', 'sell');
CREATE TYPE order_type AS ENUM ('market', 'limit', 'stop', 'stop_limit');
CREATE TYPE order_status AS ENUM ('pending', 'submitted', 'partially_filled', 'filled', 'cancelled', 'rejected', 'expired');
CREATE TYPE trade_side AS ENUM ('buy', 'sell');
CREATE TYPE strategy_status AS ENUM ('created', 'initializing', 'running', 'paused', 'stopped', 'error');
CREATE TYPE strategy_type AS ENUM ('momentum', 'mean_reversion', 'breakout', 'grid', 'dca', 'custom');
CREATE TYPE notification_type AS ENUM ('trade_executed', 'risk_alert', 'strategy_status', 'daily_summary', 'system_alert');
CREATE TYPE notification_channel AS ENUM ('in_app', 'email', 'sms', 'push');
CREATE TYPE risk_rule_type AS ENUM ('daily_loss_limit', 'max_position_size', 'max_orders_per_minute', 'max_portfolio_exposure', 'min_account_equity');

-- ============================================================
-- EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- ============================================================
-- USERS
-- ============================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'trader',
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT chk_password_hash_not_empty CHECK (char_length(password_hash) > 0),
    CONSTRAINT chk_failed_attempts CHECK (failed_login_attempts >= 0)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- ============================================================
-- BROKER ACCOUNTS
-- ============================================================

CREATE TABLE broker_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_name broker_name NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    account_name VARCHAR(255),
    encrypted_api_key BYTEA NOT NULL,
    encrypted_api_secret BYTEA NOT NULL,
    encrypted_api_passphrase BYTEA,
    webhook_url VARCHAR(500),
    is_paper_trading BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    last_health_check_at TIMESTAMPTZ,
    health_status VARCHAR(20) DEFAULT 'unknown',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_broker_account_per_user UNIQUE (user_id, broker_name, account_id, is_paper_trading)
);

CREATE INDEX idx_broker_accounts_user_id ON broker_accounts(user_id);
CREATE INDEX idx_broker_accounts_broker_name ON broker_accounts(broker_name);
CREATE INDEX idx_broker_accounts_is_active ON broker_accounts(is_active);
CREATE INDEX idx_broker_accounts_is_paper_trading ON broker_accounts(is_paper_trading);

-- ============================================================
-- STRATEGIES
-- ============================================================

CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_account_id UUID REFERENCES broker_accounts(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategy_type strategy_type NOT NULL,
    status strategy_status NOT NULL DEFAULT 'created',
    is_paper_trading BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Execution settings
    schedule_cron VARCHAR(100),
    execution_mode VARCHAR(50) DEFAULT 'realtime', -- realtime, scheduled, on_signal
    
    -- Error tracking
    error_message TEXT,
    error_count INTEGER NOT NULL DEFAULT 0,
    last_error_at TIMESTAMPTZ,
    
    -- Version control
    version INTEGER NOT NULL DEFAULT 1,
    parent_strategy_id UUID REFERENCES strategies(id),
    
    -- Kill switch
    kill_switch BOOLEAN NOT NULL DEFAULT FALSE,
    kill_switched_at TIMESTAMPTZ,
    
    -- Timestamps
    last_run_at TIMESTAMPTZ,
    last_signal_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_strategy_name_per_user UNIQUE (user_id, name),
    CONSTRAINT chk_version CHECK (version >= 1),
    CONSTRAINT chk_error_count CHECK (error_count >= 0)
);

CREATE INDEX idx_strategies_user_id ON strategies(user_id);
CREATE INDEX idx_strategies_broker_account_id ON strategies(broker_account_id);
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategies_strategy_type ON strategies(strategy_type);
CREATE INDEX idx_strategies_is_paper_trading ON strategies(is_paper_trading);
CREATE INDEX idx_strategies_kill_switch ON strategies(kill_switch) WHERE kill_switch = TRUE;
CREATE INDEX idx_strategies_created_at ON strategies(created_at DESC);
CREATE INDEX idx_strategies_last_run_at ON strategies(last_run_at DESC NULLS LAST);

-- ============================================================
-- STRATEGY PARAMETERS
-- ============================================================

CREATE TABLE strategy_parameters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    parameter_name VARCHAR(100) NOT NULL,
    parameter_value JSONB NOT NULL,
    parameter_type VARCHAR(50) NOT NULL, -- integer, float, string, boolean, array
    is_override BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_strategy_parameter_name UNIQUE (strategy_id, parameter_name)
);

CREATE INDEX idx_strategy_parameters_strategy_id ON strategy_parameters(strategy_id);
CREATE INDEX idx_strategy_parameters_parameter_name ON strategy_parameters(parameter_name);

-- ============================================================
-- STRATEGY WATCHLIST (symbols being traded)
-- ============================================================

CREATE TABLE strategy_watchlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_strategy_symbol UNIQUE (strategy_id, symbol)
);

CREATE INDEX idx_strategy_watchlist_strategy_id ON strategy_watchlist(strategy_id);
CREATE INDEX idx_strategy_watchlist_symbol ON strategy_watchlist(symbol);

-- ============================================================
-- ORDERS
-- ============================================================

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
    broker_account_id UUID REFERENCES broker_accounts(id) ON DELETE SET NULL,
    
    -- Order details
    broker_order_id VARCHAR(100),
    symbol VARCHAR(20) NOT NULL,
    side order_side NOT NULL,
    order_type order_type NOT NULL,
    quantity NUMERIC(18, 8) NOT NULL,
    filled_quantity NUMERIC(18, 8) NOT NULL DEFAULT 0,
    remaining_quantity NUMERIC(18, 8) GENERATED ALWAYS AS (quantity - filled_quantity) STORED,
    
    -- Price
    limit_price NUMERIC(18, 8),
    stop_price NUMERIC(18, 8),
    avg_fill_price NUMERIC(18, 8),
    
    -- Time
    time_in_force VARCHAR(10) DEFAULT 'day', -- day, gtc, ioc, fok
    
    -- Status
    status order_status NOT NULL DEFAULT 'pending',
    status_message TEXT,
    
    -- External
    broker_response JSONB,
    
    -- Timestamps
    submitted_at TIMESTAMPTZ,
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_filled_quantity CHECK (filled_quantity >= 0 AND filled_quantity <= quantity),
    CONSTRAINT chk_limit_price CHECK (limit_price > 0 OR limit_price IS NULL),
    CONSTRAINT chk_stop_price CHECK (stop_price > 0 OR stop_price IS NULL)
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_strategy_id ON orders(strategy_id);
CREATE INDEX idx_orders_broker_account_id ON orders(broker_account_id);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_side ON orders(side);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX idx_orders_submitted_at ON orders(submitted_at DESC);
CREATE INDEX idx_orders_broker_order_id ON orders(broker_order_id) WHERE broker_order_id IS NOT NULL;
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- ============================================================
-- TRADES (Fills)
-- ============================================================

CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
    broker_account_id UUID REFERENCES broker_accounts(id) ON DELETE SET NULL,
    
    -- Trade details
    trade_id VARCHAR(100), -- External broker trade ID
    symbol VARCHAR(20) NOT NULL,
    side trade_side NOT NULL,
    quantity NUMERIC(18, 8) NOT NULL,
    price NUMERIC(18, 8) NOT NULL,
    commission NUMERIC(18, 8) NOT NULL DEFAULT 0,
    fees NUMERIC(18, 8) NOT NULL DEFAULT 0,
    
    -- Calculated
    total_amount NUMERIC(18, 8) GENERATED ALWAYS AS (quantity * price) STORED,
    net_amount NUMERIC(18, 8) GENERATED ALWAYS AS ((quantity * price) + commission + fees) STORED,
    
    -- Timestamps
    executed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_trade_quantity CHECK (quantity > 0),
    CONSTRAINT chk_trade_price CHECK (price > 0),
    CONSTRAINT chk_trade_commission CHECK (commission >= 0),
    CONSTRAINT chk_trade_fees CHECK (fees >= 0)
);

CREATE INDEX idx_trades_order_id ON trades(order_id);
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_strategy_id ON trades(strategy_id);
CREATE INDEX idx_trades_broker_account_id ON trades(broker_account_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_executed_at ON trades(executed_at DESC);
CREATE INDEX idx_trades_trade_id ON trades(trade_id) WHERE trade_id IS NOT NULL;
CREATE INDEX idx_trades_user_executed ON trades(user_id, executed_at DESC);

-- ============================================================
-- POSITIONS
-- ============================================================

CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_account_id UUID REFERENCES broker_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    
    -- Quantity
    quantity NUMERIC(18, 8) NOT NULL DEFAULT 0,
    pending_buy_quantity NUMERIC(18, 8) NOT NULL DEFAULT 0,
    pending_sell_quantity NUMERIC(18, 8) NOT NULL DEFAULT 0,
    
    -- Average cost
    avg_entry_price NUMERIC(18, 8),
    
    -- Current market value
    current_price NUMERIC(18, 8),
    market_value NUMERIC(18, 8),
    
    -- P&L
    realized_pnl NUMERIC(18, 8) NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC(18, 8) NOT NULL DEFAULT 0,
    
    -- Timestamps
    opened_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_position_per_account UNIQUE (user_id, broker_account_id, symbol),
    CONSTRAINT chk_quantity CHECK (quantity >= 0),
    CONSTRAINT chk_pending_buy CHECK (pending_buy_quantity >= 0),
    CONSTRAINT chk_pending_sell CHECK (pending_sell_quantity >= 0),
    CONSTRAINT chk_realized_pnl CHECK (realized_pnl IS NULL OR realized_pnl IS NOT NULL)
);

CREATE INDEX idx_positions_user_id ON positions(user_id);
CREATE INDEX idx_positions_broker_account_id ON positions(broker_account_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_is_open ON positions(closed_at) WHERE closed_at IS NULL;
CREATE INDEX idx_positions_updated_at ON positions(updated_at DESC);

-- ============================================================
-- PROFIT LOGS (Daily P&L tracking)
-- ============================================================

CREATE TABLE profit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_account_id UUID REFERENCES broker_accounts(id) ON DELETE SET NULL,
    strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
    
    -- Date
    trading_date DATE NOT NULL,
    
    -- P&L
    opening_balance NUMERIC(18, 8) NOT NULL,
    closing_balance NUMERIC(18, 8) NOT NULL,
    realized_pnl NUMERIC(18, 8) NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC(18, 8) NOT NULL DEFAULT 0,
    commission NUMERIC(18, 8) NOT NULL DEFAULT 0,
    fees NUMERIC(18, 8) NOT NULL DEFAULT 0,
    net_pnl NUMERIC(18, 8) GENERATED ALWAYS AS (realized_pnl - commission - fees) STORED,
    pnl_percentage NUMERIC(10, 4),
    
    -- Metrics
    trades_count INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    win_rate NUMERIC(5, 2),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_profit_log_per_day UNIQUE (user_id, trading_date),
    CONSTRAINT uk_profit_log_strategy_day UNIQUE (strategy_id, trading_date),
    CONSTRAINT chk_trades_count CHECK (trades_count >= 0),
    CONSTRAINT chk_winning_trades CHECK (winning_trades >= 0),
    CONSTRAINT chk_losing_trades CHECK (losing_trades >= 0)
);

CREATE INDEX idx_profit_logs_user_id ON profit_logs(user_id);
CREATE INDEX idx_profit_logs_broker_account_id ON profit_logs(broker_account_id);
CREATE INDEX idx_profit_logs_strategy_id ON profit_logs(strategy_id);
CREATE INDEX idx_profit_logs_trading_date ON profit_logs(trading_date DESC);
CREATE INDEX idx_profit_logs_user_date ON profit_logs(user_id, trading_date DESC);

-- ============================================================
-- BACKTEST RUNS
-- ============================================================

CREATE TABLE backtest_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
    
    -- Configuration
    name VARCHAR(255),
    description TEXT,
    
    -- Date range
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    timeframe VARCHAR(20) NOT NULL DEFAULT '1d', -- 1m, 5m, 15m, 1h, 1d
    
    -- Initial capital
    initial_capital NUMERIC(18, 2) NOT NULL DEFAULT 100000,
    
    -- Results
    final_capital NUMERIC(18, 2),
    total_return NUMERIC(18, 8),
    total_return_pct NUMERIC(10, 4),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate NUMERIC(5, 2),
    max_drawdown NUMERIC(18, 8),
    max_drawdown_pct NUMERIC(10, 4),
    sharpe_ratio NUMERIC(10, 4),
    sortino_ratio NUMERIC(10, 4),
    profit_factor NUMERIC(10, 4),
    avg_trade_pnl NUMERIC(18, 8),
    avg_win NUMERIC(18, 8),
    avg_loss NUMERIC(18, 8),
    largest_win NUMERIC(18, 8),
    largest_loss NUMERIC(18, 8),
    
    -- Execution
    execution_time_seconds NUMERIC(10, 2),
    bars_processed INTEGER,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    error_message TEXT,
    
    -- Results data (JSON for flexibility)
    equity_curve JSONB,
    trades JSONB,
    
    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_date_range CHECK (end_date >= start_date),
    CONSTRAINT chk_initial_capital CHECK (initial_capital > 0)
);

CREATE INDEX idx_backtest_runs_user_id ON backtest_runs(user_id);
CREATE INDEX idx_backtest_runs_strategy_id ON backtest_runs(strategy_id);
CREATE INDEX idx_backtest_runs_status ON backtest_runs(status);
CREATE INDEX idx_backtest_runs_created_at ON backtest_runs(created_at DESC);
CREATE INDEX idx_backtest_runs_start_date ON backtest_runs(start_date);
CREATE INDEX idx_backtest_runs_user_created ON backtest_runs(user_id, created_at DESC);

-- ============================================================
-- STRATEGY LOGS
-- ============================================================

CREATE TABLE strategy_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Log level
    level VARCHAR(20) NOT NULL DEFAULT 'info', -- debug, info, warning, error
    
    -- Message
    message TEXT NOT NULL,
    details JSONB,
    
    -- Context
    symbol VARCHAR(20),
    signal_type VARCHAR(20), -- buy, sell, hold
    order_id UUID REFERENCES orders(id),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_log_level CHECK (level IN ('debug', 'info', 'warning', 'error', 'critical'))
);

CREATE INDEX idx_strategy_logs_strategy_id ON strategy_logs(strategy_id);
CREATE INDEX idx_strategy_logs_user_id ON strategy_logs(user_id);
CREATE INDEX idx_strategy_logs_level ON strategy_logs(level);
CREATE INDEX idx_strategy_logs_created_at ON strategy_logs(created_at DESC);
CREATE INDEX idx_strategy_logs_strategy_created ON strategy_logs(strategy_id, created_at DESC);

-- ============================================================
-- RISK RULES
-- ============================================================

CREATE TABLE risk_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE, -- NULL = global rule
    broker_account_id UUID REFERENCES broker_accounts(id) ON DELETE CASCADE,
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Rule definition
    rule_type risk_rule_type NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Values
    threshold_value NUMERIC(18, 8) NOT NULL,
    threshold_percentage NUMERIC(5, 2), -- For percentage-based rules
    
    -- Behavior
    action VARCHAR(50) NOT NULL DEFAULT 'alert', -- alert, pause, stop
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_hard BOOLEAN NOT NULL DEFAULT FALSE, -- Hard rules cannot be bypassed
    
    -- Priority (lower = higher priority)
    priority INTEGER NOT NULL DEFAULT 100,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_risk_rule_scope UNIQUE (user_id, broker_account_id, strategy_id, rule_type),
    CONSTRAINT chk_priority CHECK (priority >= 1 AND priority <= 1000),
    CONSTRAINT chk_action CHECK (action IN ('alert', 'pause', 'stop'))
);

CREATE INDEX idx_risk_rules_user_id ON risk_rules(user_id);
CREATE INDEX idx_risk_rules_broker_account_id ON risk_rules(broker_account_id);
CREATE INDEX idx_risk_rules_strategy_id ON risk_rules(strategy_id);
CREATE INDEX idx_risk_rules_rule_type ON risk_rules(rule_type);
CREATE INDEX idx_risk_rules_is_enabled ON risk_rules(is_enabled) WHERE is_enabled = TRUE;

-- ============================================================
-- RISK BREACHES
-- ============================================================

CREATE TABLE risk_breaches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    risk_rule_id UUID REFERENCES risk_rules(id) ON DELETE SET NULL,
    broker_account_id UUID REFERENCES broker_accounts(id) ON DELETE SET NULL,
    strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
    
    -- Breach details
    rule_type risk_rule_type NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    threshold_value NUMERIC(18, 8) NOT NULL,
    actual_value NUMERIC(18, 8) NOT NULL,
    breach_percentage NUMERIC(5, 2),
    
    -- Action taken
    action_taken VARCHAR(50) NOT NULL,
    action_details JSONB,
    
    -- Resolution
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    
    -- Timestamps
    breached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_breach_action CHECK (action_taken IN ('alert', 'paused_trading', 'stopped_strategy', 'stopped_all'))
);

CREATE INDEX idx_risk_breaches_user_id ON risk_breaches(user_id);
CREATE INDEX idx_risk_breaches_risk_rule_id ON risk_breaches(risk_rule_id);
CREATE INDEX idx_risk_breaches_strategy_id ON risk_breaches(strategy_id);
CREATE INDEX idx_risk_breaches_is_resolved ON risk_breaches(is_resolved);
CREATE INDEX idx_risk_breaches_breached_at ON risk_breaches(breached_at DESC);
CREATE INDEX idx_risk_breaches_user_breached ON risk_breaches(user_id, breached_at DESC);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification details
    type notification_type NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'normal', -- low, normal, high, critical
    
    -- Channel
    channel notification_channel NOT NULL DEFAULT 'in_app',
    is_sent BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    
    -- Delivery
    email_status VARCHAR(20) DEFAULT 'pending',
    sms_status VARCHAR(20) DEFAULT 'pending',
    push_status VARCHAR(20) DEFAULT 'pending',
    
    -- Read status
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    
    -- Action
    action_url VARCHAR(500),
    action_type VARCHAR(50),
    
    -- Reference
    reference_id UUID, -- Can reference order_id, trade_id, etc.
    reference_type VARCHAR(50),
    
    -- Context data
    context JSONB,
    
    -- Timestamps
    scheduled_for TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_priority CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    CONSTRAINT chk_channel CHECK (channel IN ('in_app', 'email', 'sms', 'push'))
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_is_sent ON notifications(is_sent);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_notifications_user_read ON notifications(user_id, is_read, created_at DESC);
CREATE INDEX idx_notifications_scheduled ON notifications(scheduled_for) WHERE scheduled_for IS NOT NULL AND is_sent = FALSE;

-- ============================================================
-- USER SESSIONS
-- ============================================================

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session details
    token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ NOT NULL,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_user_sessions_is_active ON user_sessions(is_active) WHERE is_active = TRUE;

-- ============================================================
-- AUDIT LOGS
-- ============================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Action details
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    
    -- Change data
    old_values JSONB,
    new_values JSONB,
    
    -- Request context
    ip_address INET,
    user_agent TEXT,
    request_id UUID,
    
    -- Result
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_user_created ON audit_logs(user_id, created_at DESC);

-- ============================================================
-- MARKET DATA TABLES (TimescaleDB hypertable)
-- ============================================================

-- OHLCV 1-minute data
CREATE TABLE ohlcv_1m (
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open NUMERIC(18, 8) NOT NULL,
    high NUMERIC(18, 8) NOT NULL,
    low NUMERIC(18, 8) NOT NULL,
    close NUMERIC(18, 8) NOT NULL,
    volume BIGINT NOT NULL,
    vwap NUMERIC(18, 8),
    
    PRIMARY KEY (symbol, timestamp)
);

SELECT create_hypertable('ohlcv_1m', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

CREATE INDEX idx_ohlcv_1m_timestamp ON ohlcv_1m(timestamp DESC);
CREATE INDEX idx_ohlcv_1m_symbol_timestamp ON ohlcv_1m(symbol, timestamp DESC);

-- OHLCV hourly data
CREATE TABLE ohlcv_1h (
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open NUMERIC(18, 8) NOT NULL,
    high NUMERIC(18, 8) NOT NULL,
    low NUMERIC(18, 8) NOT NULL,
    close NUMERIC(18, 8) NOT NULL,
    volume BIGINT NOT NULL,
    vwap NUMERIC(18, 8),
    
    PRIMARY KEY (symbol, timestamp)
);

SELECT create_hypertable('ohlcv_1h', 'timestamp', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);

-- OHLCV daily data
CREATE TABLE ohlcv_1d (
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open NUMERIC(18, 8) NOT NULL,
    high NUMERIC(18, 8) NOT NULL,
    low NUMERIC(18, 8) NOT NULL,
    close NUMERIC(18, 8) NOT NULL,
    volume BIGINT NOT NULL,
    vwap NUMERIC(18, 8),
    
    PRIMARY KEY (symbol, timestamp)
);

SELECT create_hypertable('ohlcv_1d', 'timestamp', chunk_time_interval => INTERVAL '90 days', if_not_exists => TRUE);

-- ============================================================
-- TRIGGER FUNCTIONS
-- ============================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_broker_accounts_updated_at BEFORE UPDATE ON broker_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_strategy_parameters_updated_at BEFORE UPDATE ON strategy_parameters FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_risk_rules_updated_at BEFORE UPDATE ON risk_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- SEQUENCES
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS strategy_version_seq;
CREATE SEQUENCE IF NOT EXISTS order_seq;
CREATE SEQUENCE IF NOT EXISTS trade_seq;

-- ============================================================
-- VIEWS
-- ============================================================

-- Active positions view
CREATE OR REPLACE VIEW v_active_positions AS
SELECT 
    p.*,
    u.email as user_email,
    b.broker_name
FROM positions p
JOIN users u ON p.user_id = u.id
LEFT JOIN broker_accounts b ON p.broker_account_id = b.id
WHERE p.closed_at IS NULL;

-- User portfolio summary
CREATE OR REPLACE VIEW v_portfolio_summary AS
SELECT 
    p.user_id,
    u.email,
    COUNT(p.id) as position_count,
    SUM(p.market_value) as total_market_value,
    SUM(p.realized_pnl) as total_realized_pnl,
    SUM(p.unrealized_pnl) as total_unrealized_pnl,
    SUM(p.quantity) as total_shares
FROM positions p
JOIN users u ON p.user_id = u.id
WHERE p.closed_at IS NULL
GROUP BY p.user_id, u.email;

-- Daily P&L summary
CREATE OR REPLACE VIEW v_daily_pnl AS
SELECT 
    pl.trading_date,
    pl.user_id,
    u.email,
    SUM(pl.net_pnl) as total_pnl,
    SUM(pl.trades_count) as total_trades,
    AVG(pl.win_rate) as avg_win_rate
FROM profit_logs pl
JOIN users u ON pl.user_id = u.id
GROUP BY pl.trading_date, pl.user_id, u.email;

-- Strategy performance
CREATE OR REPLACE VIEW v_strategy_performance AS
SELECT 
    s.id as strategy_id,
    s.name as strategy_name,
    s.user_id,
    u.email,
    s.status,
    s.strategy_type,
    COUNT(DISTINCT o.id) as total_orders,
    COUNT(DISTINCT t.id) as total_trades,
    SUM(t.quantity * t.price) as total_volume,
    AVG(t.price) as avg_fill_price,
    MAX(o.created_at) as last_order_at
FROM strategies s
JOIN users u ON s.user_id = u.id
LEFT JOIN orders o ON o.strategy_id = s.id
LEFT JOIN trades t ON t.strategy_id = s.id
GROUP BY s.id, s.name, s.user_id, u.email, s.status, s.strategy_type;

-- ============================================================
-- POLICIES (Row-Level Security)
-- ============================================================

-- Enable RLS on user-facing tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE broker_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE profit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategy_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- User can see their own data
CREATE POLICY user_own_data ON users FOR ALL USING (auth.uid() = id);
CREATE POLICY user_broker_accounts ON broker_accounts FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_strategies ON strategies FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_orders ON orders FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_trades ON trades FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_positions ON positions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_profit_logs ON profit_logs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_backtest_runs ON backtest_runs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_strategy_logs ON strategy_logs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_risk_rules ON risk_rules FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY user_notifications ON notifications FOR ALL USING (auth.uid() = user_id);

-- Admin can see all data (handled by check function)
CREATE POLICY admin_all_users ON users FOR ALL USING (role = 'admin');
CREATE POLICY admin_all_broker_accounts ON broker_accounts FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE users.id = broker_accounts.user_id AND users.role = 'admin')
);

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE users IS 'User accounts and authentication';
COMMENT ON TABLE broker_accounts IS 'Broker API credentials (encrypted)';
COMMENT ON TABLE strategies IS 'Trading strategy configurations';
COMMENT ON TABLE orders IS 'Order requests to brokers';
COMMENT ON TABLE trades IS 'Executed trades (fills)';
COMMENT ON TABLE positions IS 'Current open positions';
COMMENT ON TABLE profit_logs IS 'Daily profit and loss tracking';
COMMENT ON TABLE backtest_runs IS 'Historical backtest executions';
COMMENT ON TABLE strategy_logs IS 'Strategy execution logs';
COMMENT ON TABLE risk_rules IS 'Risk management rules';
COMMENT ON TABLE risk_breaches IS 'Risk limit breach history';
COMMENT ON TABLE notifications IS 'User notifications';
COMMENT ON TABLE ohlcv_1m IS '1-minute OHLCV market data';
COMMENT ON TABLE ohlcv_1h IS '1-hour OHLCV market data';
COMMENT ON TABLE ohlcv_1d IS 'Daily OHLCV market data';
