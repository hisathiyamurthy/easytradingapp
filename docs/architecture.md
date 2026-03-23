# EasyTradingApp Architecture

## Overview
Production-grade algorithmic trading platform with microservices architecture.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React + TS)                          │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │  Login   │  │   Strategy   │  │   Trading  │  │      Admin       │  │
│  │    UI    │  │   Dashboard  │  │  Dashboard │  │ Strategy Builder │  │
│  └────┬─────┘  └──────┬───────┘  └─────┬──────┘  └────────┬─────────┘  │
└───────┼───────────────┼────────────────┼─────────────────┼────────────┘
        │               │                │                 │
        └───────────────┴────────────────┴─────────────────┘
                                    │
                              [API Gateway]
                                    │
┌───────────────────────────────────┼────────────────────────────────────┐
│                           Backend Services                              │
│  ┌─────────────┐  ┌─────────────┐ │ ┌─────────────┐  ┌─────────────┐  │
│  │   Auth     │  │   User      │ │ │  Strategy   │  │   Order     │  │
│  │   Service  │  │   Service   │ │ │   Service   │  │   Service   │  │
│  └─────────────┘  └─────────────┘ │ └─────────────┘  └─────────────┘  │
│                                    │                                    │
│  ┌─────────────┐  ┌─────────────┐ │ ┌─────────────┐  ┌─────────────┐  │
│  │   Broker    │  │  Analytics  │ │ │  Position   │  │   Risk      │  │
│  │   Service   │  │   Service   │ │ │   Service   │  │   Service   │  │
│  └─────────────┘  └─────────────┘ │ └─────────────┘  └─────────────┘  │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼────────────────────────────────────┐
│                         Quant Engine (Python)                            │
│  ┌─────────────┐  ┌─────────────┐ │ ┌─────────────┐  ┌─────────────┐  │
│  │  Indicator  │  │   Strategy  │ │ │  Backtest   │  │    Risk     │  │
│  │   Library   │  │   Engine    │ │ │   Engine    │  │  Manager    │  │
│  └─────────────┘  └─────────────┘ │ └─────────────┘  └─────────────┘  │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │
                         ┌──────────┴──────────┐
                         │   Database (Postgres) │
                         │   Cache (Redis)       │
                         │   Message Queue (Kafka)│
                         └───────────────────────┘
```

## Service Boundaries

### Auth Service
- JWT token issuance/validation
- User registration/login
- Session management
- RBAC enforcement

### User Service
- User profile management
- Broker configuration (encrypted)
- API key management

### Strategy Service
- Strategy CRUD operations
- Strategy parameter management
- Strategy activation/deactivation

### Order Service
- Order submission
- Order tracking
- Order history

### Broker Service
- Broker integration abstraction
- Real-time market data
- Order execution

### Quant Engine
- Technical indicators calculation
- Strategy signal generation
- Risk evaluation
- Backtesting

## Data Models

### User
- id: UUID
- email: string
- password_hash: string
- role: enum (admin, trader, viewer)
- created_at: timestamp
- updated_at: timestamp

### BrokerConfig
- id: UUID
- user_id: UUID (FK)
- broker_name: string
- encrypted_api_key: bytes
- encrypted_api_secret: bytes
- is_active: boolean

### Strategy
- id: UUID
- user_id: UUID (FK)
- name: string
- type: enum (momentum, mean_reversion, breakout)
- parameters: JSON
- is_active: boolean
- kill_switch: boolean

### Order
- id: UUID
- user_id: UUID (FK)
- strategy_id: UUID (FK)
- symbol: string
- side: enum (buy, sell)
- quantity: decimal
- price: decimal
- status: enum (pending, filled, cancelled, rejected)
- created_at: timestamp

### Position
- id: UUID
- user_id: UUID (FK)
- symbol: string
- quantity: decimal
- avg_price: decimal
- unrealized_pnl: decimal

### RiskLimit
- id: UUID
- user_id: UUID (FK)
- daily_loss_limit: decimal
- max_position_size: decimal
- max_orders_per_minute: integer

### AuditLog
- id: UUID
- user_id: UUID (FK)
- action: string
- details: JSON
- ip_address: string
- timestamp: timestamp

## Security Architecture

### Authentication Flow
1. User submits credentials
2. Auth service validates and returns JWT
3. JWT includes user_id, role, expires
4. All API requests include JWT in header
5. Middleware validates JWT on each request

### Encryption
- API keys encrypted with AES-256-GCM
- Keys stored in secure vault
- Environment variables for secrets

### RBAC
- Admin: Full access
- Trader: Trade, view own strategies
- Viewer: Read-only access

## Trading Safety Controls

### Risk Limits
- Daily loss limit: Auto-stop trading
- Max position size: Reject oversized orders
- Strategy kill switch: Instant deactivation
- Rate limiting: Prevent abuse

### Monitoring
- Real-time P&L tracking
- Alert on limit breach
- Full audit trail

## Infrastructure

### Cloud: AWS/Azure
- EKS/AKS for orchestration
- RDS for database
- ElastiCache for Redis
- S3 for data storage

### Monitoring Stack
- Prometheus: Metrics collection
- Grafana: Visualization
- ELK: Log aggregation

### CI/CD
- GitHub Actions
- Automated tests
- Container scanning
- Blue-green deployment
