# EasyTradingApp - Local Development Environment

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/easytradingapp/easytradingapp.git
cd easytradingapp

# 2. Start local development
./scripts/dev.sh

# 3. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Redis: localhost:6379
# PostgreSQL: localhost:5432
# RabbitMQ: localhost:5672 (Management: http://localhost:15672)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LOCAL DEVELOPMENT                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│   │   Frontend  │     │   Backend   │     │   Worker   │       │
│   │   (React)   │◄───►│  (FastAPI)  │◄───►│  (Celery)   │       │
│   │  localhost  │     │  localhost  │     │  localhost  │       │
│   │    :3000    │     │    :8000    │     │             │       │
│   └─────────────┘     └──────┬──────┘     └─────────────┘       │
│                              │                                    │
│   ┌──────────────────────────┼──────────────────────────┐       │
│   │                    DOCKER NETWORK                   │       │
│   │                   easytrading-network              │       │
│   └──────────────────────────┬──────────────────────────┘       │
│                              │                                    │
│   ┌──────────┐    ┌────────┴────────┐    ┌──────────────┐    │
│   │  RabbitMQ │    │  PostgreSQL    │    │    Redis    │    │
│   │  :5672    │    │    :5432      │    │    :6379    │    │
│   └──────────┘    └────────────────┘    └──────────────┘    │
│                                                                     │
│   ┌──────────────┐                                               │
│   │ Mock Broker  │                                               │
│   │   :8001      │  (Simulates broker APIs for paper trading)   │
│   └──────────────┘                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| frontend | 3000 | React development server |
| backend | 8000 | FastAPI application |
| worker | - | Celery worker for async tasks |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache |
| rabbitmq | 5672 | RabbitMQ message broker |
| rabbitmq-admin | 15672 | RabbitMQ management UI |
| mock-broker | 8001 | Mock broker API |

## Development Workflow

### Prerequisites

- Docker Desktop / Docker Engine
- Docker Compose v2+
- Python 3.11+
- Node.js 20+
- Make (optional)

### Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
vim .env
```

### Running Services

```bash
# Start all services
make dev

# Or directly with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Reset all data
docker-compose down -v
```

### Hot Reload

- **Backend**: Changes to Python files auto-reload via uvicorn
- **Frontend**: Changes to React files auto-reload via Vite
- **Database**: Schema changes require migration:
  ```bash
  docker-compose exec backend alembic upgrade head
  ```

## Mock Broker API

The local environment includes a mock broker API that simulates real broker behavior for paper trading:

### Endpoints

```bash
# Get account balance
curl http://localhost:8001/api/v1/account/balance

# Get positions
curl http://localhost:8001/api/v1/positions

# Place order
curl -X POST http://localhost:8001/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NIFTY",
    "side": "buy",
    "quantity": 100,
    "order_type": "market"
  }'

# Get quotes
curl http://localhost:8001/api/v1/quotes/NIFTY
```

### Simulated Market Data

The mock broker generates realistic price movements using a random walk model. Prices update every second for active watchlists.

## Testing

```bash
# Run backend tests
docker-compose exec backend pytest

# Run frontend tests
docker-compose exec frontend npm test

# Run integration tests
docker-compose exec backend pytest tests/integration/
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d
```

### Port Conflicts

```bash
# Check what's using the port
lsof -i :8000

# Stop conflicting service
```

### Clear Cache

```bash
# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Rebuild containers
docker-compose build --no-cache
docker-compose up -d
```

## File Structure

```
easytradingapp/
├── docker/
│   ├── docker-compose.local.yml    # Local development
│   └── docker-compose.prod.yml     # Production
├── backend/
│   ├── app/
│   │   ├── api/                   # API endpoints
│   │   ├── core/                 # Configuration
│   │   ├── services/              # Business logic
│   │   └── models/                # Database models
│   ├── alembic/                   # Migrations
│   └── tests/
├── frontend/
│   └── src/
├── scripts/
│   └── dev.sh                     # Development script
└── .env.example                   # Environment template
```

## Production vs Local Differences

| Aspect | Local | Production |
|--------|-------|------------|
| Database | PostgreSQL in Docker | AWS RDS Multi-AZ |
| Cache | Redis in Docker | ElastiCache |
| Message Queue | RabbitMQ | MSK Kafka |
| Broker API | Mock | Real (Zerodha/Upstox) |
| Trading | Paper only | Paper + Live |
| Auth | JWT (dev secret) | JWT (secrets manager) |
| SSL | Not required | TLS 1.3 required |
| Scaling | Single instance | Auto-scaling |
