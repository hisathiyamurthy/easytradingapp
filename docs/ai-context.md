# AI Agent Context

## System Overview
EasyTradingApp is an algorithmic trading platform with React frontend and FastAPI backend.

## Key Modules

### Authentication
- **Location:** `backend/core/security.py`, `backend/api/v1/endpoints/auth_endpoints.py`
- **Token:** JWT with 1-hour expiry
- **Storage:** `localStorage.getItem('token')` (not `access_token`)
- **Roles:** Admin, Trader, Pending

### Strategy Builder (NLP)
- **Location:** `backend/strategy_engine/nl_parser.py`, `frontend/src/pages/strategies/StrategyBuilder.tsx`
- **Endpoint:** `POST /api/v1/strategies/parse`
- **Requires:** Authentication
- **Supported:** EMA, SMA, RSI patterns, symbol extraction

### API Patterns
- **Frontend calls:** `fetch()` with `Authorization: Bearer <token>`
- **Token retrieval:** `localStorage.getItem('token')`
- **User role:** `JSON.parse(localStorage.getItem('user')).role`

## Critical Constraints

1. **Security:** Never log secrets, always use parameterized queries
2. **Validation:** Validate all inputs, especially passwords (special char required)
3. **Testing:** Playwright E2E tests in `tests/e2e/`
4. **Admin-only:** Strategy save, user management require admin role

## Important Workflows

### Password Requirements
- Minimum 8 characters
- At least: uppercase, lowercase, digit, special character (!@#$%^&* etc.)

### User Registration Flow
1. User registers → status = "pending"
2. Admin approves → status = "active"
3. User can login

### Strategy Builder Flow
1. User enters natural language strategy
2. System parses via NLP parser
3. Parsed strategy displayed
4. Admin can save to database

## Docker Services
- Frontend: port 5300
- Backend: port 8000
- PostgreSQL: port 5432
- Redis: port 6379

## Documentation
- `docs/01-project-overview.md` - Project overview
- `docs/05-api-contract.md` - API reference
- `docs/07-frontend-structure.md` - Frontend docs
- `docs/08-backend-structure.md` - Backend docs

## Test Credentials
- Admin: hisathiyamurthy@gmail.com / Zero@123
- Test user: testuser999@test.com / NewPass@123
