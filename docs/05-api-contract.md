# API Contract Reference

## Base URL
```
Production: http://localhost:8000
Local: http://localhost:8000
```

## Authentication

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

Token is obtained from `/api/v1/auth/login`

---

## Endpoints

### 1. Authentication

#### POST /api/v1/auth/register
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "Secure@123",
  "confirm_password": "Secure@123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "message": "Registration successful. Please wait for admin approval.",
  "user": { ... }
}
```

---

#### POST /api/v1/auth/login
Login and get tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "Secure@123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { ... }
}
```

---

#### POST /api/v1/auth/forgot-password
Request password reset.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Password reset email sent"
}
```

---

#### POST /api/v1/auth/reset-password
Reset password using token.

**Request:**
```json
{
  "token": "reset_token",
  "new_password": "NewSecure@123",
  "confirm_password": "NewSecure@123"
}
```

**Response:**
```json
{
  "message": "Password reset successful"
}
```

---

### 2. Strategy Management

#### POST /api/v1/strategies/parse
Parse natural language strategy (Requires Auth).

**Request:**
```json
{
  "strategy_text": "Buy NIFTY when RSI crosses above 30"
}
```

**Response:**
```json
{
  "name": "NIFTY - Rsi",
  "description": "Strategy for NIFTY on NSE",
  "strategy_type": "custom",
  "parameters": {
    "symbol": "NIFTY",
    "exchange": "NSE",
    "timeframe": "1d"
  },
  "entry_conditions": [...],
  "exit_conditions": [...],
  "validation_errors": [],
  "is_valid": true
}
```

---

#### POST /api/v1/strategies
Create a new strategy (Requires Auth).

**Request:**
```json
{
  "name": "My Strategy",
  "description": "Strategy description",
  "strategy_type": "momentum",
  "parameters": {
    "symbol": "NIFTY",
    "rsi_period": 14,
    "oversold": 30,
    "overbought": 70
  }
}
```

**Response:** `StrategyResponse`

---

#### GET /api/v1/strategies
List user's strategies (Requires Auth).

**Response:** `StrategyListResponse`

---

#### GET /api/v1/strategies/{strategy_id}
Get strategy details (Requires Auth).

**Response:** `StrategyResponse`

---

#### PUT /api/v1/strategies/{strategy_id}
Update strategy (Requires Auth).

**Request:** `StrategyUpdate`

**Response:** `StrategyResponse`

---

#### DELETE /api/v1/strategies/{strategy_id}
Delete strategy (Requires Auth).

**Response:** 204 No Content

---

#### POST /api/v1/strategies/{strategy_id}/activate
Activate strategy (Requires Auth).

**Request:**
```json
{
  "broker_id": "uuid"
}
```

**Response:** `StrategyResponse`

---

#### POST /api/v1/strategies/{strategy_id}/deactivate
Deactivate strategy (Requires Auth).

**Response:** `StrategyResponse`

---

### 3. Admin Endpoints

#### GET /api/v1/admin/pending-users
List pending users (Admin only).

**Response:** `list[PendingUserResponse]`

---

#### POST /api/v1/admin/users/{user_id}/approve
Approve user (Admin only).

**Response:** `ApprovalResponse`

---

#### POST /api/v1/admin/users/{user_id}/reject
Reject user (Admin only).

**Response:** `ApprovalResponse`

---

#### POST /api/v1/admin/users/{user_id}/suspend
Suspend user (Admin only).

**Response:** `ApprovalResponse`

---

#### POST /api/v1/admin/users/{user_id}/reactivate
Reactivate user (Admin only).

**Response:** `ApprovalResponse`

---

### 4. Portfolio

#### GET /api/v1/portfolio
Get portfolio details (Requires Auth).

**Response:** `PortfolioResponse`

---

#### GET /api/v1/portfolio/positions
Get open positions (Requires Auth).

**Response:** `list[PositionResponse]`

---

### 5. Orders

#### GET /api/v1/orders
List orders (Requires Auth).

**Response:** `OrderListResponse`

---

#### POST /api/v1/orders
Create order (Requires Auth).

**Request:**
```json
{
  "symbol": "NIFTY",
  "exchange": "NSE",
  "order_type": "MARKET",
  "side": "BUY",
  "quantity": 50
}
```

**Response:** `OrderResponse`

---

### 6. Brokers

#### GET /api/v1/brokers
List broker accounts (Requires Auth).

**Response:** `list[BrokerAccountResponse]`

---

#### POST /api/v1/brokers
Connect broker account (Requires Auth).

**Request:**
```json
{
  "broker_name": "ZERODHA",
  "api_key": "key",
  "api_secret": "secret",
  "is_paper_trading": true
}
```

**Response:** `BrokerAccountResponse`

---

### 7. Risk Management

#### GET /api/v1/risk/rules
Get risk rules (Requires Auth).

**Response:** `list[RiskRuleResponse]`

---

#### POST /api/v1/risk/rules
Create risk rule (Requires Auth).

**Request:** `RiskRuleCreate`

**Response:** `RiskRuleResponse`

---

#### POST /api/v1/risk/kill-switch
Trigger global kill switch (Requires Auth).

**Response:**
```json
{
  "message": "Global kill switch activated",
  "strategies_stopped": 5
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

---

*Last Updated: March 2026*
