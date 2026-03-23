# Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                       │
│  Port: 5300                                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                     │
│  Port: 8000                                                  │
│  ├── API Layer (v1)                                          │
│  ├── Business Logic                                          │
│  └── Strategy Engine                                         │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │  PostgreSQL  │   │  Redis   │    │  External │
        │    (db)     │   │ (cache)  │    │  Brokers  │
        └─────────┘     └─────────┘     └─────────┘
```

## Component Architecture

### Frontend (React + TypeScript)
- **Build Tool:** Vite
- **UI Framework:** Custom components with Tailwind CSS
- **State Management:** React hooks + Context
- **HTTP Client:** Fetch API

### Backend (Python FastAPI)
- **Framework:** FastAPI
- **ORM:** SQLAlchemy (async)
- **Authentication:** JWT + Refresh tokens
- **Database:** PostgreSQL
- **Cache:** Redis
- **Task Queue:** Celery (optional)

### Strategy Engine
- **Parser:** NL Parser (natural language to strategy)
- **Indicators:** EMA, SMA, RSI, MACD, VWAP, Bollinger
- **Execution:** Real-time and paper trading modes

## Security Architecture

1. **Authentication:** JWT tokens with 1-hour expiry
2. **Password:** Bcrypt hashing
3. **API Keys:** Encrypted storage
4. **CORS:** Configured allowed origins
5. **Rate Limiting:** Per-endpoint limits

## Data Flow

1. User → Frontend → Backend API
2. Backend → Validate → Process → Database
3. Strategy → Parser → Strategy Engine → Broker API

---

*Last Updated: March 2026*
