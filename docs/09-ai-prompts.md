# AI Prompts Documentation

## Strategy Builder NLP Parser

### Purpose
Convert natural language strategy descriptions into structured JSON strategy rules.

### Input Format
Plain English text describing a trading strategy.

### Supported Patterns

**1. Symbol Specification:**
- "Buy NIFTY..."
- "Trade BANKNIFTY..."
- "On SENSEX..."

**2. Timeframe Specification:**
- "5 mins" / "5 minute" / "5m"
- "15 mins"
- "1 hour" / "1h"
- "daily" / "1d"

**3. Indicator Specifications:**

**EMA Crossover:**
- "13 EMA crosses above 34 EMA"
- "EMA 13 above EMA 34"
- "crossover 13 above 34"

**EMA Above Another EMA:**
- "13 EMA and 34 EMA above 200 EMA"
- "EMA 13 and EMA 34 should be above EMA 200"

**RSI:**
- "RSI crosses above 30"
- "RSI is below 30"
- "RSI(14) above 70"

**Price vs MA:**
- "price crosses above 20 SMA"
- "price below 50 EMA"

**4. Stop Loss:**
- "stop loss 20 points"
- "stop loss 2%"

**5. Target:**
- "target 40 points"
- "target 10%"

### Output Format
```json
{
  "name": "Strategy Name",
  "symbol": "NIFTY",
  "exchange": "NSE",
  "timeframe": "5m",
  "entry_rules": [...],
  "exit_rules": [...],
  "stop_loss": { ... },
  "take_profit": { ... }
}
```

### Example Inputs/Outputs

**Input:**
```
Buy NIFTY when 20 EMA crosses above 50 EMA. Stop loss 20 points. Target 40 points.
```

**Output:**
```json
{
  "name": "NIFTY - EMA",
  "symbol": "NIFTY",
  "exchange": "NSE",
  "timeframe": "1d",
  "entry_rules": [
    {"indicator": "ema_crossover", "fast_period": 20, "slow_period": 50}
  ],
  "stop_loss": {"type": "points", "value": 20},
  "take_profit": {"type": "points", "value": 40}
}
```

---

**Input:**
```
Buy RELIANCE when RSI crosses above 30. Sell when RSI crosses above 70. Stop loss 5%.
```

**Output:**
```json
{
  "name": "RELIANCE - Rsi",
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "timeframe": "1d",
  "entry_rules": [
    {"indicator": "rsi", "operator": "crosses_above", "value": 30}
  ],
  "exit_rules": [
    {"indicator": "rsi", "operator": "crosses_above", "value": 70}
  ],
  "stop_loss": {"type": "percentage", "value": 5}
}
```

### Limitations

1. **Symbol:** Requires known index symbols or uppercase stock codes
2. **Complexity:** Simple single-condition strategies work best
3. **Validation:** User must provide custom text, not placeholder examples

---

*Last Updated: March 2026*
