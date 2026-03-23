# Strategy Builder Documentation

## Overview

The Strategy Builder converts natural language trading strategies into structured JSON rules that can be used by the backtesting and trading engines.

## Strategy JSON Schema

```json
{
  "strategy_name": "Strategy Name",
  "timeframe": "5m",
  "symbol": "NIFTY",
  "exchange": "NSE",
  "entry_conditions": [
    {
      "logic": "AND",
      "conditions": [
        {
          "indicator": "ema_crossover",
          "operator": "crosses_above",
          "period": 13,
          "period2": 34
        }
      ]
    }
  ],
  "exit_conditions": [...],
  "risk_management": {
    "stop_loss": {"type": "percentage", "value": 2.0},
    "take_profit": {"type": "percentage", "value": 4.0}
  }
}
```

## Supported Indicators

| Indicator | Description | Parameters |
|-----------|-------------|------------|
| EMA | Exponential Moving Average | period, period2 |
| SMA | Simple Moving Average | period, value |
| RSI | Relative Strength Index | period, value, operator |
| MACD | MACD Crossover | operator |
| VWAP | Volume Weighted Average Price | - |
| Bollinger | Bollinger Bands | period, std_dev |
| ATR | Average True Range | period |
| Volume | Trading Volume | operator, value |

## Supported Operators

### Comparison Operators
- `greater_than` or `>`
- `less_than` or `<`
- `equals`
- `greater_or_equal`
- `less_or_equal`

### Crossover Operators
- `crosses_above` - Indicator crosses above threshold
- `crosses_below` - Indicator crosses below threshold

## Supported Timeframes

| Input | Output |
|-------|--------|
| 1 minute, 1 min, 1m | 1m |
| 5 minute, 5 min, 5m, 5 mins | 5m |
| 15 minute, 15 min, 15m | 15m |
| 30 minute, 30 min, 30m | 30m |
| 1 hour, 1 hr, 1h | 1h |
| 4 hour, 4 hr, 4h | 4h |
| daily, day, 1d | 1d |
| weekly, week, 1w | 1w |

## Example Strategies

### RSI Reversal Strategy
**Input:**
```
Buy NIFTY when RSI crosses above 30 and sell when RSI crosses below 70
```

**Output:**
```json
{
  "strategy_name": "Strategy: RSI",
  "symbol": "NIFTY",
  "timeframe": "1d",
  "entry_conditions": [{
    "logic": "AND",
    "conditions": [{
      "indicator": "rsi",
      "operator": "greater_than",
      "period": 14,
      "value": 30
    }]
  }],
  "exit_conditions": [{
    "logic": "AND", 
    "conditions": [{
      "indicator": "rsi",
      "operator": "less_than",
      "period": 14,
      "value": 70
    }]
  }]
}
```

### EMA Crossover Strategy with Trend Filter
**Input:**
```
Buy NIFTY when EMA 13 and EMA 34 above EMA 200 and EMA 13 crosses EMA 34, vice versa for SELL, stop loss 2%, target 4%
```

**Output:**
```json
{
  "strategy_name": "Strategy: EMA",
  "symbol": "NIFTY", 
  "timeframe": "1d",
  "entry_conditions": [{
    "logic": "AND",
    "conditions": [
      {"indicator": "ema_above_ema", "period": 13, "period2": 200, "operator": "greater_than"},
      {"indicator": "ema_above_ema", "period": 34, "period2": 200, "operator": "greater_than"},
      {"indicator": "ema_crossover", "period": 13, "period2": 34, "operator": "crosses_above"}
    ]
  }],
  "exit_conditions": [{
    "logic": "AND",
    "conditions": [
      {"indicator": "ema_crossover", "period": 13, "period2": 34, "operator": "crosses_below"}
    ]
  }],
  "risk_management": {
    "stop_loss": {"type": "percentage", "value": 2.0},
    "take_profit": {"type": "percentage", "value": 4.0}
  }
}
```

### Multi-Timeframe Strategy
**Input:**
```
Buy BANKNIFTY 5 min when price crosses above VWAP
```

## Pattern Syntax

### Entry/Exit Patterns
- `Buy when <condition>` - Entry condition
- `Sell when <condition>` - Exit condition
- `Enter long when <condition>` - Entry condition
- `Exit when <condition>` - Exit condition
- `Square off when <condition>` - Exit condition

### Indicator Patterns

**EMA Crossover:**
- `EMA 13 crosses EMA 34`
- `crossover 13 above 34`
- `EMA crosses above`

**EMA Above EMA:**
- `EMA 13 and EMA 34 above EMA 200`
- `13 EMA and 34 EMA should above 200 EMA`

**RSI:**
- `RSI crosses above 30`
- `RSI(14) above 70`
- `RSI below 30`

**MACD:**
- `MACD crosses above signal`
- `MACD crosses below signal`

### Risk Management Patterns

- `stop loss 20 points`
- `stop loss 2%`
- `target 40 points`
- `target 10%`
- `risk reward 2:1`

## API Endpoint

**POST** `/api/v1/strategies/parse`

**Request:**
```json
{
  "strategy_text": "Buy NIFTY when RSI crosses above 30"
}
```

**Response:**
```json
{
  "name": "Strategy: RSI",
  "description": "Strategy for NIFTY on NSE",
  "strategy_type": "custom",
  "parameters": {
    "symbol": "NIFTY",
    "exchange": "NSE", 
    "timeframe": "1d",
    "risk_management": {}
  },
  "entry_conditions": [...],
  "exit_conditions": [...],
  "validation_errors": [],
  "is_valid": true
}
```

## Validation Rules

1. **Symbol Required**: Must specify a trading symbol (NIFTY, BANKNIFTY, SENSEX, or stock code)
2. **Entry Conditions**: At least one entry condition must be detected
3. **Valid Operators**: Only supported operators are allowed

## Limitations

1. Complex nested conditions may not be fully parsed
2. Multiple timeframes in single strategy not fully supported
3. Some uncommon indicator combinations may require manual editing

---

*Last Updated: March 2026*
