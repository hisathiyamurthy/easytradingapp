# Backend Structure

## Directory Organization

```
backend/
├── api/
│   └── v1/
│       ├── endpoints/          # API route handlers
│       │   ├── auth_endpoints.py
│       │   ├── strategy_endpoints.py
│       │   ├── order_endpoints.py
│       │   ├── portfolio_endpoints.py
│       │   ├── broker_endpoints.py
│       │   ├── risk_endpoints.py
│       │   ├── admin_endpoints.py
│       │   ├── backtest_endpoints.py
│       │   ├── market_endpoints.py
│       │   ├── notification_endpoints.py
│       │   ├── mfa_endpoints.py
│       │   ├── oauth_endpoints.py
│       │   ├── session_endpoints.py
│       │   └── strategy_version_endpoints.py
│       └── router.py            # Main API router
├── core/
│   ├── config.py               # Configuration
│   ├── security.py            # Auth & security
│   └── rate_limiter.py        # Rate limiting
├── models/                     # SQLAlchemy models
│   ├── user_models.py
│   ├── strategy_models.py
│   ├── order_models.py
│   ├── portfolio_models.py
│   └── ...
├── schemas/                    # Pydantic schemas
│   ├── auth_schemas.py
│   ├── strategy_schemas.py
│   └── ...
├── services/                   # Business logic
│   └── ...
├── strategy_engine/            # Trading strategy engine
│   ├── nl_parser.py           # Natural language parser
│   ├── executor.py            # Strategy executor
│   ├── indicators.py          # Technical indicators
│   └── strategies/            # Strategy implementations
├── database/
│   └── session.py             # Database session
├── worker/                    # Background workers
└── main.py                    # FastAPI application
```

## API Endpoints Summary

| Module | Endpoints |
|--------|-----------|
| `auth_endpoints.py` | register, login, forgot-password, reset-password |
| `strategy_endpoints.py` | CRUD strategies, activate, deactivate, parse |
| `order_endpoints.py` | CRUD orders, cancel |
| `portfolio_endpoints.py` | portfolio, positions, summary |
| `broker_endpoints.py` | CRUD brokers, test connection |
| `risk_endpoints.py` | risk rules, kill switch |
| `admin_endpoints.py` | stats, brokers, sessions |
| `backtest_endpoints.py` | run backtest, export results |
| `market_endpoints.py` | quotes, historical, search |

## Database Models

### Core Models
- **User** - User accounts with role-based access
- **BrokerAccount** - Connected broker accounts
- **Strategy** - Trading strategies
- **Order** - Trade orders
- **Position** - Open positions
- **Trade** - Completed trades
- **RiskRule** - Risk management rules
- **Notification** - User notifications

## Authentication Flow

1. User registers → status = "pending"
2. Admin approves → status = "active"
3. User logs in → receives JWT access + refresh tokens
4. Access token expires → use refresh token to get new access token

## Strategy Engine

### NLP Parser
Located in `backend/strategy_engine/nl_parser.py`

Parses natural language strategy descriptions into structured strategy objects.

**Supported:**
- Symbol extraction (NIFTY, BANKNIFTY, SENSEX, etc.)
- Timeframe extraction (1m, 5m, 15m, 1h, 1d, etc.)
- Indicator parsing (EMA, SMA, RSI, MACD, VWAP)
- Entry/Exit condition extraction

---

*Last Updated: March 2026*
