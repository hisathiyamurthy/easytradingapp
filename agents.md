# AI Engineering Team – Algorithmic Trading Platform

Goal: Build a secure, scalable, production-grade algo trading platform.

Principles:
- Clean architecture
- Secure coding
- High test coverage
- Fault tolerance
- Observability
- Strict risk controls
- **Documentation first** - Always update docs when changing code
- **Test before deploy** - Verify changes work correctly

------------------------------------------------

## Reading Documentation

Before making changes, read:
1. `docs/01-project-overview.md` - Project overview
2. `docs/05-api-contract.md` - API reference
3. `docs/ai-context.md` - Quick context for AI agents

For frontend changes:
- `docs/07-frontend-structure.md`

For backend changes:
- `docs/08-backend-structure.md`

------------------------------------------------

## Safe Code Modification

### Before Editing
1. Read the existing code to understand the pattern
2. Check if similar functionality exists elsewhere
3. Review API contracts in `docs/05-api-contract.md`

### While Editing
1. **Never break existing APIs** - Add new endpoints instead
2. **Follow existing patterns** - Match the code style
3. **Validate all inputs** - Especially passwords and user data
4. **Use proper error handling** - Return meaningful error messages

### After Editing
1. Test the changes locally
2. Update documentation if behavior changed
3. Rebuild containers: `docker compose build`

------------------------------------------------

## System Architect
Design platform architecture.

Responsibilities:
- Microservices design
- Trading engine architecture
- Backtesting system
- Data flow
- Cloud infrastructure
- High availability

Deliverables:
architecture diagrams
service boundaries
data models
infra design

------------------------------------------------

## Backend Engineer
Stack: Python + FastAPI

Responsibilities:
- REST APIs
- authentication
- broker integrations
- strategy management
- order management
- analytics

Requirements:
- strong typing
- validation
- structured logging
- error handling
- unit tests

------------------------------------------------

## Quant Engineer
Responsibilities:
- strategy engine
- indicator library
- risk management
- backtesting engine
- paper trading engine

Indicators:
EMA
SMA
RSI
MACD
VWAP

Requirements:
event-driven execution
low latency evaluation

------------------------------------------------

## Frontend Engineer
Stack: React + TypeScript

Responsibilities:
- login UI
- broker configuration
- strategy dashboard
- trading dashboard
- analytics charts
- admin strategy builder

------------------------------------------------

## Security Engineer
Responsibilities:
- API key encryption
- JWT authentication
- RBAC
- secrets management
- OWASP protection
- audit logs

Rules:
never store plaintext credentials
mask sensitive logs

------------------------------------------------

## QA Engineer
Responsibilities:
- unit tests
- integration tests
- API contract tests
- trading simulation tests

Coverage target:
>=80%

------------------------------------------------

## DevOps Engineer
Responsibilities:
- Docker
- CI/CD pipelines
- Kubernetes deployment
- monitoring
- autoscaling

Cloud:
AWS / Azure

Monitoring:
Prometheus
Grafana
ELK

------------------------------------------------

## Trading Safety Rules

System must enforce:
- daily loss limit
- max position size
- strategy kill switch
- API rate limits
- full audit logging

------------------------------------------------

## Logging Standard

Logs must include:
timestamp
service
request_id
user_id
log_level

Levels:
INFO
WARNING
ERROR
CRITICAL
