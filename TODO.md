# EasyTradingApp - TODO Roadmap

## Executive Summary

The EasyTradingApp is a partially implemented algorithmic trading platform with:
- **Backend**: ~70% complete (core services, trading engine, risk management, broker integrations)
- **Frontend**: ~30% complete (UI scaffold exists but most pages use mock data)
- **Infrastructure**: ~60% complete (Docker, monitoring, but needs production hardening)

---

## MODULE: Frontend - Data Integration

### CRITICAL - Connect All Pages to Backend APIs

#### P0 - High Priority
- [ ] **Dashboard Page** - Replace mock data with real API calls
  - Description: Dashboard currently uses hardcoded mock data for portfolio, P&L, positions
  - Affected files: `frontend/src/pages/dashboard/Dashboard.tsx`
  - Implementation: Fetch from `/api/v1/portfolio`, `/api/v1/positions`, `/api/v1/orders` endpoints

- [ ] **Portfolio Page** - Connect to positions API
  - Description: Portfolio page displays mock positions
  - Affected files: `frontend/src/pages/portfolio/Portfolio.tsx`
  - Implementation: Use `/api/v1/positions` endpoint, add real-time price updates

- [ ] **Orders Page** - Connect to orders API
  - Description: Orders page shows mock order data
  - Affected files: `frontend/src/pages/orders/Orders.tsx`
  - Implementation: Fetch from `/api/v1/orders` endpoint with filters

- [ ] **Strategies Hook** - Implement useStrategies hook
  - Description: `useStrategies` hook returns empty array, doesn't connect to backend
  - Affected files: `frontend/src/hooks/useStrategies.ts`
  - Implementation: Add API calls to `/api/v1/strategies` endpoints

#### P1 - Medium Priority
- [ ] **Analytics Page** - Connect to trading analytics API
  - Description: Need to verify what's implemented and connect
  - Affected files: `frontend/src/pages/analytics/Analytics.tsx`

- [ ] **Strategy Builder** - Full implementation
  - Description: Connect to strategy create/update endpoints
  - Affected files: `frontend/src/pages/strategies/StrategyBuilder.tsx`

---

## MODULE: Authentication & Authorization

### Status: PARTIALLY IMPLEMENTED

#### Completed
- [x] User login (just fixed)
- [x] Admin initialization
- [x] JWT token handling

#### P0 - High Priority
- [ ] **User Registration Flow** - Complete registration with email verification
  - Description: Registration endpoint exists but email verification not implemented
  - Affected files: `backend/api/v1/endpoints/auth_endpoints.py`
  - Implementation: Add email verification token, email sending service

- [ ] **Password Reset** - Implement password reset flow
  - Description: Endpoints exist but not connected to frontend
  - Affected files: `backend/services/auth_service.py`, `frontend/src/pages/auth/`

- [ ] **Admin Approval Workflow** - Users wait for admin approval
  - Description: Status is PENDING but no approval UI/workflow
  - Affected files: `backend/api/v1/endpoints/auth_endpoints.py`
  - Implementation: Complete pending user list, approve/reject endpoints

#### P1 - Medium Priority
- [ ] **Session Management** - Implement session tracking and termination
  - Affected files: `backend/api/v1/endpoints/session_endpoints.py`

- [ ] **MFA/TOTP** - Multi-factor authentication
  - Affected files: `backend/api/v1/endpoints/mfa_endpoints.py`, `backend/services/totp_service.py`

---

## MODULE: Broker Integration

### Status: BACKEND COMPLETE, FRONTEND MISSING

#### Completed
- [x] Zerodha integration
- [x] Angel One integration
- [x] Upstox integration
- [x] Kotak Neo integration
- [x] BrokerAccount model
- [x] Order execution service

#### P0 - High Priority
- [ ] **Broker Connection UI** - Frontend for adding broker accounts
  - Description: Settings page has broker connections placeholder
  - Affected files: `frontend/src/pages/settings/BrokerConnections.tsx`
  - Implementation: Create form for API key input, test connection, save encrypted credentials

- [ ] **Broker Health Monitoring** - Display broker connection status
  - Affected files: `backend/services/trade_reconciliation.py`

---

## MODULE: Trading Engine

### Status: ~80% COMPLETE

#### Completed
- [x] Event-driven architecture
- [x] Signal generation
- [x] Order placement
- [x] Paper trading mode
- [x] Order executor with retry logic
- [x] Position tracking

#### P0 - High Priority
- [ ] **Strategy Execution Loop** - Start/stop strategies
  - Description: Backend has engine but no worker tasks to run strategies
  - Affected files: `backend/worker/tasks/trading.py`
  - Implementation: Add Celery tasks for strategy execution, market data subscription

- [ ] **Real-time Order Updates** - WebSocket for order status
  - Affected files: `backend/services/websocket_service.py`
  - Implementation: Connect order status updates to WebSocket

- [ ] **Broker Order Sync** - Sync orders with broker
  - Affected files: `backend/services/trade_reconciliation.py`
  - Implementation: Add periodic sync task

#### P1 - Medium Priority
- [ ] **Advanced Order Types** - Bracket orders, cover orders
- [ ] **Order Modification** - Modify pending orders
- [ ] **Position Squaring** - Square off positions manually

---

## MODULE: Market Data

### Status: BACKEND COMPLETE, FRONTEND PARTIAL

#### Completed
- [x] Quote API
- [x] Historical OHLCV
- [x] Symbol search
- [x] Price caching with Redis
- [x] Multiple data provider support

#### P0 - High Priority
- [ ] **Real-time Price Updates** - WebSocket streaming
  - Affected files: `backend/services/streaming_service.py`
  - Implementation: Add frontend WebSocket client, subscribe to symbols

- [ ] **Market Watchlist** - User's watched symbols
  - Affected files: `backend/models/strategy_models.py`, `frontend/src/pages/`

- [ ] **Live Charts** - Real-time candle updates
  - Affected files: `frontend/src/pages/trading/TradingDashboard.tsx`

---

## MODULE: Risk Management

### Status: ~70% COMPLETE

#### Completed
- [x] RiskRule model
- [x] Risk limit checking
- [x] Daily loss limits
- [x] Position size limits
- [x] Risk breach logging

#### P0 - High Priority
- [ ] **Risk Rule Configuration UI** - Set risk limits per strategy
  - Affected files: `frontend/src/pages/settings/`, `backend/api/v1/endpoints/`
  - Implementation: Add UI for creating/editing risk rules

- [ ] **Kill Switch** - Emergency stop all trading
  - Affected files: `backend/risk_management/risk_manager.py`
  - Implementation: Add API endpoint, connect to frontend

- [ ] **Margin Calculation** - Real-time margin requirements
  - Affected files: `backend/risk_management/margin_calculator.py`

---

## MODULE: Backtesting

### Status: ~50% COMPLETE

#### Completed
- [x] Backtest engine
- [x] Historical data loader
- [x] Basic analytics

#### P0 - High Priority
- [ ] **Backtest Configuration UI** - Run backtests from frontend
  - Affected files: `frontend/src/pages/`, `backend/api/v1/endpoints/backtest_endpoints.py`
  - Implementation: Create form for symbol, date range, strategy selection

- [ ] **Backtest Results Visualization** - Charts and metrics
  - Affected files: `backend/backtesting/analytics.py`
  - Implementation: Connect to frontend charts

- [ ] **Historical Data Management** - Download and store historical data
  - Affected files: `backend/services/market_data_service.py`

---

## MODULE: Admin Panel

### Status: PARTIALLY IMPLEMENTED

#### Completed
- [x] User list endpoint
- [x] Pending users endpoint
- [x] Approve/reject endpoints

#### P0 - High Priority
- [ ] **Admin API Endpoints** - Add missing endpoints
  - Description: Frontend calls `/admin/stats`, `/admin/brokers`, `/admin/active-users` which don't exist
  - Affected files: `backend/api/v1/endpoints/`
  - Implementation: Create admin router with stats, broker status, active sessions

- [ ] **Admin User Management** - Fix user management page
  - Affected files: `frontend/src/pages/admin/AdminUserManagement.tsx`
  - Implementation: Connect to user approval endpoints

- [ ] **Platform Settings** - System configuration UI
  - Affected files: `frontend/src/pages/settings/Settings.tsx`

#### P1 - Medium Priority
- [ ] **Audit Logs** - View all admin actions
- [ ] **Broker Management** - View all broker connections
- [ ] **System Health Dashboard** - Real-time metrics

---

## MODULE: Notifications

### Status: PARTIALLY IMPLEMENTED

#### Completed
- [x] Notification model
- [x] Notification endpoints
- [x] Notification service

#### P0 - High Priority
- [ ] **Notification UI** - Implement notification page
  - Affected files: `frontend/src/pages/notifications/Notifications.tsx`
  - Implementation: Connect to notification API, add real-time updates

- [ ] **In-app Notifications** - Toast notifications for events
  - Affected files: `frontend/src/components/ui/`
  - Implementation: Create notification component, integrate with WebSocket

- [ ] **Email/SMS Alerts** - External notification delivery
  - Affected files: `backend/services/notification_service.py`

---

## MODULE: Frontend - UI Components

### Status: ~60% COMPLETE

#### P1 - Medium Priority
- [ ] **Missing Components** - Complete UI library
  - Select component (needs proper implementation)
  - Dialog component
  - Dropdown menu
  - Tabs component (partially used but may need fixes)
  - Toast notifications
  - Date picker
  - Modal component

- [ ] **Loading States** - Add skeleton loaders to all pages
- [ ] **Error Handling** - Add error boundaries and user-friendly error messages
- [ ] **Empty States** - Better UX when no data

---

## MODULE: Infrastructure & DevOps

### Status: ~70% COMPLETE

#### Completed
- [x] Docker compose for local development
- [x] Backend Dockerfile
- [x] Frontend Dockerfile
- [x] PostgreSQL database
- [x] Redis cache
- [x] Prometheus monitoring

#### P0 - High Priority
- [ ] **Production Deployment** - Production-ready configs
  - Affected files: `docker/docker-compose.yml`, `infra/`
  - Implementation: Add production overrides, TLS, secrets management

- [ ] **Environment Configuration** - Proper env var management
  - Affected files: `backend/core/config.py`, `.env.example`
  - Implementation: Document all required env vars, add validation

- [ ] **Logging** - Centralized logging
  - Affected files: `backend/core/logging.py`
  - Implementation: Add structured logging, log aggregation

- [ ] **CI/CD Pipeline** - Complete automation
  - Affected files: `.github/workflows/`
  - Implementation: Add testing, security scanning, deployment

#### P1 - Medium Priority
- [ ] **Database Migrations** - Alembic setup
  - Affected files: `backend/alembic/`
- [ ] **Backup & Recovery** - Database backup strategy
- [ ] **Auto-scaling** - K8s deployment configs

---

## MODULE: Testing

### Status: MINIMAL

#### P1 - Medium Priority
- [ ] **Backend Tests** - Unit and integration tests
  - Priority: Cover auth, trading engine, risk management
  
- [ ] **Frontend Tests** - React component tests
  - Affected files: `frontend/src/test/`
  
- [ ] **E2E Tests** - Cypress/Playwright tests for critical flows
  - Login flow
  - Order placement
  - Strategy creation

---

## Development Priority Order

### Phase 1: Core Functionality (Week 1-2)
1. Fix Dashboard, Portfolio, Orders to use real data
2. Implement useStrategies hook with API calls
3. Complete broker connection UI
4. Fix admin API endpoints

### Phase 2: Trading (Week 3-4)
1. Strategy execution loop
2. Real-time order updates via WebSocket
3. Position tracking
4. Paper trading

### Phase 3: Risk & Backtesting (Week 5-6)
1. Risk rule configuration UI
2. Kill switch
3. Backtest configuration and results

### Phase 4: Polish (Week 7-8)
1. Notifications
2. Error handling
3. Loading states
4. Testing

---

## Missing Core Modules Summary

| Module | Backend | Frontend | Priority |
|--------|---------|----------|----------|
| Dashboard Data | Partial | Mock | P0 |
| Portfolio | Partial | Mock | P0 |
| Orders | Complete | Mock | P0 |
| Strategies | Complete | Hooks Empty | P0 |
| Broker Connection | Complete | Missing | P0 |
| Admin Stats API | Missing | Called | P0 |
| Strategy Execution | Partial | Missing | P0 |
| Real-time Updates | Partial | Missing | P1 |
| Backtesting UI | Partial | Missing | P1 |
| Risk Rules UI | Complete | Missing | P1 |
| Notifications | Partial | Placeholder | P2 |

---

## Notes

- The trading engine is well-designed with event-driven architecture
- Risk management is comprehensive with multiple limit types
- Broker integrations exist for major Indian brokers
- Market data service has caching and multiple provider support
- Main gaps are in frontend data integration and real-time updates
