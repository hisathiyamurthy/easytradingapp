"""
Test cases demonstrating the NL Strategy Parser output.

Input: "Buy NIFTY when 20 EMA crosses above 50 EMA. Stop loss 20 points. Target 40 points."
"""
{
  "name": "NIFTY - EMA Strategy",
  "symbol": "NIFTY",
  "exchange": "NSE",
  "timeframe": "1d",
  "entry_rules": [
    {
      "signal": "buy",
      "type": "crossover",
      "indicator1": {
        "type": "ema",
        "period": 20
      },
      "operator": "crosses_above",
      "indicator2": {
        "type": "ema",
        "period": 50
      }
    }
  ],
  "exit_rules": [],
  "stop_loss": {
    "type": "points",
    "value": 20
  },
  "take_profit": {
    "type": "points",
    "value": 40
  },
  "position_sizing": null,
  "max_positions": 1,
  "metadata": {
    "original_text": "Buy NIFTY when 20 EMA crosses above 50 EMA. Stop loss 20 points. Target 40 points.",
    "parsed_at": "2026-03-07T12:00:00"
  }
}

---
"""
Test case 2

Input: "Buy RELIANCE when RSI crosses above 30. Sell when RSI crosses above 70. Stop loss 5%."
"""
{
  "name": "RELIANCE - RSI Strategy",
  "symbol": "RELIANCE",
  "exchange": "NSE", 
  "timeframe": "1d",
  "entry_rules": [
    {
      "signal": "buy",
      "type": "indicator",
      "indicator": "rsi",
      "operator": "greater_than",
      "value": 30
    }
  ],
  "exit_rules": [
    {
      "signal": "sell",
      "type": "indicator", 
      "indicator": "rsi",
      "operator": "greater_than",
      "value": 70
    }
  ],
  "stop_loss": {
    "type": "percentage",
    "value": 5
  },
  "take_profit": null,
  "position_sizing": null,
  "max_positions": 1,
  "metadata": {}
}

---
"""
Test case 3

Input: "Buy NIFTY when price crosses above 20 SMA. Target 100 points with stop loss 50 points."
"""
{
  "name": "NIFTY - Price SMA Strategy",
  "symbol": "NIFTY",
  "exchange": "NSE",
  "timeframe": "1d",
  "entry_rules": [
    {
      "signal": "buy",
      "type": "price_ma",
      "ma_period": 20,
      "operator": "crosses_above"
    }
  ],
  "exit_rules": [],
  "stop_loss": {
    "type": "points",
    "value": 50
  },
  "take_profit": {
    "type": "points",
    "value": 100
  },
  "position_sizing": null,
  "max_positions": 1,
  "metadata": {}
}

---
"""
Test case 4

Input: "Buy 100 shares of INFY when RSI below 30. Stop loss 500 points. Target 1000 points."
"""
{
  "name": "INFY - RSI Strategy",
  "symbol": "INFY",
  "exchange": "NSE",
  "timeframe": "1d",
  "entry_rules": [
    {
      "signal": "buy",
      "type": "indicator",
      "indicator": "rsi",
      "operator": "less_than",
      "value": 30
    }
  ],
  "exit_rules": [],
  "stop_loss": {
    "type": "points",
    "value": 500
  },
  "take_profit": {
    "type": "points",
    "value": 1000
  },
  "position_sizing": {
    "type": "fixed",
    "quantity": 100
  },
  "max_positions": 1,
  "metadata": {}
}

---
"""
Test case 5

Input: "Enter long on BANKNIFTY when 9 EMA crosses above 21 EMA. Use 20% of capital. Stop loss 2%. Target 6%."
"""
{
  "name": "BANKNIFTY - EMA Strategy",
  "symbol": "BANKNIFTY",
  "exchange": "NSE",
  "timeframe": "1d",
  "entry_rules": [
    {
      "signal": "buy",
      "type": "crossover",
      "indicator1": {
        "type": "ema",
        "period": 9
      },
      "operator": "crosses_above",
      "indicator2": {
        "type": "ema",
        "period": 21
      }
    }
  ],
  "exit_rules": [],
  "stop_loss": {
    "type": "percentage",
    "value": 2
  },
  "take_profit": {
    "type": "percentage",
    "value": 6
  },
  "position_sizing": {
    "type": "percent_capital",
    "percentage": 20
  },
  "max_positions": 1,
  "metadata": {}
}
