# Features Documentation

## 1. Strategy Builder (NLP)

### Purpose
Converts natural language descriptions into structured trading strategies.

### User Flow
1. User navigates to Strategy Builder page
2. Enters strategy description in natural language
3. Clicks "Generate Strategy"
4. System parses and displays parsed strategy
5. Admin can edit name and save strategy

### Supported Patterns

**Symbols:**
- NIFTY, BANKNIFTY, SENSEX, FINNIFTY, MIDCAP
- Custom stock symbols (e.g., RELIANCE, TCS)

**Indicators:**
- EMA (Exponential Moving Average)
- SMA (Simple Moving Average)
- RSI (Relative Strength Index)
- MACD, VWAP, Bollinger Bands

**Entry Patterns:**
- "Buy when RSI crosses above 30"
- "Buy when 13 EMA crosses above 34 EMA"
- "Buy NIFTY when price crosses above 20 SMA"
- "13 EMA and 34 EMA should above 200 EMA"

**Exit Patterns:**
- "Sell when RSI crosses below 70"
- "vice versa for sell"

### Example Input
```
Buy NIFTY 5 mins, 13 EMA and 34 EMA should above 200 EMA and buy when crossover 13 above 34 vice versa for SELL
```

### Example Output
```json
{
  "name": "NIFTY - Mins,",
  "description": "Strategy for NIFTY on NSE",
  "strategy_type": "custom",
  "parameters": {
    "symbol": "NIFTY",
    "exchange": "NSE",
    "timeframe": "5m"
  },
  "entry_conditions": [
    "{'indicator': 'ema_crossover', 'fast_period': 13, 'slow_period': 34, 'operator': 'crosses_above'}",
    "{'indicator': 'ema_above_ema', 'ema1_period': 13, 'ema2_period': 34, 'ema3_period': 200, 'operator': 'greater_than'}"
  ],
  "exit_conditions": [
    "{'indicator': 'ema_crossover', 'operator': 'crosses_below', 'description': 'Opposite of entry'}"
  ]
}
```

### Backend APIs
- `POST /api/v1/strategies/parse` - Parse natural language strategy

### Frontend Pages
- `/strategies/builder` - Strategy Builder page

### Dependencies
- `backend/strategy_engine/nl_parser.py` - NLP Parser

### Limitations
- Requires known symbol (NIFTY, BANKNIFTY, etc.) or uppercase stock code
- Complex conditions may not be fully parsed
- Best for simple single-condition strategies

---

## 2. Authentication Flow

### Registration
1. User submits email, password, name
2. Backend validates password (min 8 chars, 1 upper, 1 lower, 1 digit, 1 special)
3. User created with "pending" status
4. Admin must approve user

### Login
1. User submits email/password
2. Backend validates credentials
3. Returns JWT access token + refresh token
4. Frontend stores token

### Password Reset
1. User requests password reset via email
2. Backend generates reset token
3. User clicks reset link
4. Backend validates token and updates password

---

## 3. Admin User Management

### User Approval Flow
1. Admin views pending users
2. Admin approves or rejects user
3. User status changes to "active" or "rejected"

### Actions
- Approve user
- Reject user
- Suspend user
- Reactivate user

---

*Last Updated: March 2026*
