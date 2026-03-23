"""Natural Language Strategy Parser - Converts English to structured JSON rules."""
import re
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"


class ComparisonOperator(str, Enum):
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"


class TimeFrame(str, Enum):
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"


class IndicatorType(str, Enum):
    SMA = "sma"
    EMA = "ema"
    RSI = "rsi"
    MACD = "macd"
    VWAP = "vwap"
    BOLLINGER = "bollinger"
    ATR = "atr"
    VOLUME = "volume"
    PRICE = "price"
    CLOSE = "close"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"


@dataclass
class ConditionRule:
    """A single condition rule."""
    indicator: str
    operator: str
    value: Optional[float] = None
    secondary_indicator: Optional[str] = None
    period: Optional[int] = None


@dataclass
class EntryRule:
    """Entry rule configuration."""
    signal: str
    conditions: list = field(default_factory=list)


@dataclass
class ExitRule:
    """Exit rule configuration."""
    signal: str
    conditions: list = field(default_factory=list)


@dataclass
class StopLossRule:
    """Stop loss configuration."""
    type: str = "points"  # points, percentage, atr
    value: float = 0


@dataclass
class TakeProfitRule:
    """Take profit configuration."""
    type: str = "points"  # points, percentage, rr (risk reward)
    value: float = 0
    risk_reward_ratio: Optional[float] = None


@dataclass
class StrategyRule:
    """Structured strategy rule."""
    name: str
    symbol: str
    exchange: str = "NSE"
    timeframe: str = "1d"
    entry_rules: list = field(default_factory=list)
    exit_rules: list = field(default_factory=list)
    stop_loss: Optional[dict] = None
    take_profit: Optional[dict] = None
    position_sizing: Optional[dict] = None
    max_positions: int = 1
    metadata: dict = field(default_factory=dict)


class StrategyParser:
    """Parser for converting natural language to strategy rules."""

    # Common patterns
    SYMBOL_PATTERN = r'\b([A-Z]{2,5})\b'
    NUMBER_PATTERN = r'(\d+(?:\.\d+)?)'
    PERIOD_PATTERN = r'(\d+)\s*(?:period|day|minute|min|hour|hr|week|candle|candles)?s?'
    
    # Indicator patterns
    EMA_PATTERN = r'EMA\s*(\d+)'
    SMA_PATTERN = r'SMA\s*(\d+)'
    RSI_PATTERN = r'RSI(?:\s*(\d+))?'
    MACD_PATTERN = r'MACD'
    VWAP_PATTERN = r'VWAP'
    BOLLINGER_PATTERN = r'Bollinger(?:\s*Bands?)?(?:\s*(\d+))?'
    ATR_PATTERN = r'ATR(?:\s*(\d+))?'

    # Operator patterns
    CROSSES_ABOVE = [
        r'crosses?\s+(?:above|over)\s+',
        r'goes?\s+above\s+',
        r'moves?\s+above\s+',
        r'breaks?\s+above\s+',
        r'>',
    ]
    CROSSES_BELOW = [
        r'crosses?\s+(?:below|under)\s+',
        r'goes?\s+below\s+',
        r'moves?\s+below\s+',
        r'drops?\s+below\s+',
        r'<',
    ]
    GREATER_THAN = [
        r'(?:is\s+)?(?:greater\s+than|above|over)\s+',
        r'>\s*',
    ]
    LESS_THAN = [
        r'(?:is\s+)?(?:less\s+than|below|under)\s+',
        r'<\s*',
    ]

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def parse(self, text: str) -> StrategyRule:
        """Parse natural language text to strategy rule."""
        text = text.strip()
        self.errors = []
        self.warnings = []

        # Extract components
        symbol = self._extract_symbol(text)
        timeframe = self._extract_timeframe(text)
        entry_conditions = self._extract_entry_conditions(text)
        exit_conditions = self._extract_exit_conditions(text)
        stop_loss = self._extract_stop_loss(text)
        take_profit = self._extract_take_profit(text)
        position_sizing = self._extract_position_sizing(text)

        # Validate
        if not symbol:
            self.errors.append("Could not identify trading symbol")

        if stop_loss is None:
            self.warnings.append("No stop loss specified")

        if take_profit is None:
            self.warnings.append("No take profit specified")

        # Build strategy rule
        strategy = StrategyRule(
            name=self._generate_strategy_name(text, symbol),
            symbol=symbol or "UNKNOWN",
            exchange="NSE",
            timeframe=timeframe,
            entry_rules=entry_conditions,
            exit_rules=exit_conditions,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_sizing=position_sizing,
            max_positions=1,
            metadata={
                "original_text": text,
                "parsed_at": datetime.utcnow().isoformat(),
            },
        )

        return strategy

    def _extract_symbol(self, text: str) -> Optional[str]:
        """Extract trading symbol from text."""
        # Common index symbols
        index_map = {
            "nifty": "NIFTY",
            "nifty 50": "NIFTY",
            "sensex": "SENSEX",
            "bank nifty": "BANKNIFTY",
            "fin nifty": "FINNIFTY",
            "midcap": "MIDCAP",
        }
        
        text_lower = text.lower()
        for key, value in index_map.items():
            if key in text_lower:
                return value

        # Extract from pattern like "Buy NIFTY" or "NIFTY when" (only uppercase symbols)
        match = re.search(r'\b(BUY|SELL)\s+([A-Z]{2,5})\b', text)
        if match:
            return match.group(2)

        # Try to find any uppercase word that looks like a symbol (but exclude common words)
        common_words = ['EMA', 'SMA', 'RSI', 'MACD', 'VWAP', 'ATR', 'STOP', 'LOSS', 'TARGET', 'BUY', 'SELL']
        match = re.search(r'\b([A-Z]{2,5})\b', text)
        if match and match.group(1) not in common_words:
            return match.group(1)

        return None

    def _extract_timeframe(self, text: str) -> str:
        """Extract timeframe from text."""
        text_lower = text.lower()
        
        if "minute" in text_lower or "min" in text_lower:
            match = re.search(r'(\d+)\s*min', text_lower)
            if match:
                mins = int(match.group(1))
                if mins in [1, 5, 15, 30]:
                    return f"{mins}m"
        
        if "hour" in text_lower or "hr" in text_lower:
            match = re.search(r'(\d+)\s*hour', text_lower)
            if match:
                hours = int(match.group(1))
                if hours in [1, 4]:
                    return f"{hours}h"
        
        if "daily" in text_lower or "day" in text_lower or "1d" in text_lower:
            return "1d"
        
        if "weekly" in text_lower or "week" in text_lower:
            return "1w"
        
        return "1d"  # Default

    def _extract_entry_conditions(self, text: str) -> list[dict]:
        """Extract entry conditions from text."""
        conditions = []
        text_lower = text.lower()

        # Pattern: Buy when [indicator] crosses above/below [value/indicator]
        buy_patterns = [
            r'buy\s+when\s+(.+?)(?:stop|target|stoploss|take profit|exit|sell)',
            r'buy\s+if\s+(.+?)(?:stop|target|stoploss|take profit|exit|sell)',
            r'enter\s+(?:long\s+)?when\s+(.+?)(?:stop|target|stoploss|take profit|exit|sell)',
            r'buy\s+(.+?)(?:and|then|if|when)',
        ]

        sell_patterns = [
            r'sell\s+when\s+(.+?)(?:stop|target|stoploss|take profit|exit|buy)',
            r'sell\s+if\s+(.+?)(?:stop|target|stoploss|take profit|exit|buy)',
            r'exit\s+when\s+(.+?)(?:stop|target|stoploss|take profit|buy)',
            r'sell\s+(.+?)(?:and|then|if|when)',
        ]

        # Try to extract indicator conditions
        for pattern in buy_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                condition_text = match.group(1).strip()
                condition = self._parse_indicator_condition(condition_text, "buy")
                if condition:
                    conditions.append(condition)
                break

        # Check for simple RSI conditions - multiple patterns
        if "rsi" in text_lower:
            # Pattern: "RSI crosses above 30" or "RSI above 30"
            rsi_match = re.search(r'rsi\s*(?:period\s*)?(\d+)?\s*(?:crosses?)?\s*(?:above|over|below|under)?\s*(\d+)', text_lower, re.IGNORECASE)
            if rsi_match:
                period = int(rsi_match.group(1)) if rsi_match.group(1) else 14
                # Determine operator based on context
                if "crosses above" in text_lower or "cross above" in text_lower or "above" in text_lower:
                    operator = "greater_than"
                elif "crosses below" in text_lower or "cross below" in text_lower or "below" in text_lower:
                    operator = "less_than"
                else:
                    operator = "greater_than"  # default
                value = int(rsi_match.group(2))
                conditions.append({
                    "indicator": "rsi",
                    "period": period,
                    "operator": operator,
                    "value": value,
                })

        # Extract EMA periods that should be above another EMA (e.g., "13 EMA and 34 EMA above 200 EMA")
        # Parse as TWO separate conditions: ema1 above ema3 AND ema2 above ema3
        ema_above = re.search(r'(\d+)\s*ema\s+\w+\s+(\d+)\s*ema\s+\w+\s+(?:above|over)\s+(\d+)\s*ema', text_lower, re.IGNORECASE)
        if ema_above:
            ema1 = int(ema_above.group(1))
            ema2 = int(ema_above.group(2))
            ema3 = int(ema_above.group(3))
            # Add both EMAs above the third EMA
            conditions.append({
                "indicator": "ema_above_ema",
                "ema1": ema1,
                "ema2": ema3,
            })
            conditions.append({
                "indicator": "ema_above_ema",
                "ema1": ema2,
                "ema2": ema3,
            })
        
        # Check for EMA crossover AFTER the ema_above pattern
        # Look specifically for "crossover X above Y" pattern which is different from "EMA above EMA"
        ema_cross = re.search(r'crossover\s+(\d+)\s+(?:above|over)\s+(\d+)', text_lower)
        if ema_cross:
            conditions.append({
                "indicator": "ema_crossover",
                "fast_ema": int(ema_cross.group(1)),
                "slow_ema": int(ema_cross.group(2)),
                "operator": "crosses_above",
            })
        else:
            # Try pattern: "13 EMA crosses above 34 EMA" but NOT "EMA above EMA"
            ema_cross2 = re.search(r'(\d+)\s*ema\s+(?:crosses?\s+)?(?:above|over)\s+(?:\d+\s*ema\s+)?(\d+)\s*ema(?!\s+(?:above|over|should))', text_lower)
            if ema_cross2:
                # Verify it's not an "above" pattern
                conditions.append({
                    "indicator": "ema_crossover",
                    "fast_ema": int(ema_cross2.group(1)),
                    "slow_ema": int(ema_cross2.group(2)),
                    "operator": "crosses_above",
                })

        # Check for MACD crossover
        macd_cross = re.search(r'macd\s*(?:crosses?|signal)?\s*(?:above|over)\s*(?:signal\s*line)?', text_lower, re.IGNORECASE)
        if macd_cross:
            conditions.append({
                "indicator": "macd_crossover",
                "operator": "crosses_above",
            })

        # Check for SMA conditions
        sma_match = re.search(r'(\d+)\s*SMA\s*(?:is\s*)?(?:above|below|over|under)\s*(\d+)', text_lower, re.IGNORECASE)
        if sma_match:
            conditions.append({
                "indicator": "sma",
                "period": int(sma_match.group(1)),
                "operator": "greater_than" if "above" in text_lower else "less_than",
                "value": int(sma_match.group(2)),
            })

        if not conditions:
            self.warnings.append("Could not parse entry conditions clearly")

        return conditions

    def _extract_exit_conditions(self, text: str) -> list[dict]:
        """Extract exit conditions from text."""
        conditions = []
        text_lower = text.lower()

        # Pattern: Sell when [condition]
        sell_patterns = [
            r'sell\s+when\s+(.+?)(?:stop|target|stoploss|take profit|$)',
            r'exit\s+(?:when|long)\s+when\s+(.+?)(?:stop|target|stoploss|take profit|$)',
            r'square\s+off\s+when\s+(.+)',
            r'vice\s+versa\s+for\s+(?:sell|exit)',
        ]

        for pattern in sell_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                condition_text = match.group(1).strip() if match.lastindex else ""
                if condition_text:
                    condition = self._parse_indicator_condition(condition_text, "sell")
                    if condition:
                        conditions.append(condition)
                    break
                else:
                    # "vice versa for sell" - copy the opposite of entry conditions
                    conditions.append({
                        "indicator": "ema_crossover",
                        "operator": "crosses_below",
                        "description": "Opposite of entry - EMA crossover in reverse",
                    })
                    break

        # Check for EMA crossover in exit (e.g., "sell when 13 EMA crosses below 34 EMA")
        ema_cross = re.search(r'(\d+)\s*EMA\s*(?:crosses?|should\s+be\s+(?:below|under))\s*(\d+)\s*EMA', text_lower, re.IGNORECASE)
        if ema_cross:
            conditions.append({
                "indicator": "ema_crossover",
                "fast_ema": int(ema_cross.group(1)),
                "slow_ema": int(ema_cross.group(2)),
                "operator": "crosses_below",
            })
        
        # Also check for RSI exit conditions
        rsi_exit = re.search(r'sell\s+when\s+rsi\s*(?:crosses?)?\s*(?:below|under|above|over)?\s*(\d+)', text_lower, re.IGNORECASE)
        if rsi_exit:
            conditions.append({
                "indicator": "rsi",
                "period": 14,
                "operator": "less_than",
                "value": int(rsi_exit.group(1)),
            })
        
        # Check for MACD exit
        macd_exit = re.search(r'macd\s*(?:crosses?|signal)?\s*(?:below|under)\s*(?:signal\s*line)?', text_lower, re.IGNORECASE)
        if macd_exit:
            conditions.append({
                "indicator": "macd_crossover",
                "operator": "crosses_below",
            })

        return conditions

    def _parse_indicator_condition(self, text: str, signal: str) -> Optional[dict]:
        """Parse a single indicator condition."""
        text_lower = text.lower()

        # EMA/SMA crossover
        ema_cross = re.search(r'(\d+)\s*ema\s*(crosses?)\s*(above|below)\s*(\d+)\s*ema', text_lower)
        if ema_cross:
            return {
                "signal": signal,
                "type": "crossover",
                "indicator1": {
                    "type": "ema",
                    "period": int(ema_cross.group(1)),
                },
                "operator": "crosses_above" if ema_cross.group(3) == "above" else "crosses_below",
                "indicator2": {
                    "type": "ema",
                    "period": int(ema_cross.group(4)),
                },
            }

        # Price vs Moving Average
        ma_match = re.search(r'(?:price|crosses?)\s*(?:above|below)\s*(\d+)\s*(?:sma|ema|ma)', text_lower)
        if ma_match:
            return {
                "signal": signal,
                "type": "price_ma",
                "ma_period": int(ma_match.group(1)),
                "operator": "crosses_above" if "above" in text_lower else "crosses_below",
            }

        # Simple indicator value
        indicator_match = re.search(r'(sma|ema|rsi|macd|vwap)', text_lower)
        if indicator_match:
            indicator = indicator_match.group(1)
            
            # Extract comparison
            operator = "greater_than"
            if "below" in text_lower or "under" in text_lower:
                operator = "less_than"
            
            # Extract value
            value_match = re.search(r'(?:is\s+)?(?:a|at)?\s*(\d+(?:\.\d+)?)', text_lower)
            value = float(value_match.group(1)) if value_match else None
            
            return {
                "signal": signal,
                "type": "indicator",
                "indicator": indicator,
                "operator": operator,
                "value": value,
            }

        return None

    def _extract_stop_loss(self, text: str) -> Optional[dict]:
        """Extract stop loss configuration."""
        text_lower = text.lower()
        
        # Pattern: stop loss X points
        sl_points = re.search(r'stop\s*loss\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*(?:points?|pts?)', text_lower)
        if sl_points:
            return {
                "type": "points",
                "value": float(sl_points.group(1)),
            }

        # Pattern: stop loss X%
        sl_percent = re.search(r'stop\s*loss\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*%', text_lower)
        if sl_percent:
            return {
                "type": "percentage",
                "value": float(sl_percent.group(1)),
            }

        # Pattern: stop loss X ATR
        sl_atr = re.search(r'stop\s*loss\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*atr', text_lower)
        if sl_atr:
            return {
                "type": "atr",
                "multiplier": float(sl_atr.group(1)),
            }

        return None

    def _extract_take_profit(self, text: str) -> Optional[dict]:
        """Extract take profit configuration."""
        text_lower = text.lower()
        
        # Pattern: target X points
        tp_points = re.search(r'(?:target|take profit|tp)\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*(?:points?|pts?)', text_lower)
        if tp_points:
            return {
                "type": "points",
                "value": float(tp_points.group(1)),
            }

        # Pattern: target X%
        tp_percent = re.search(r'(?:target|take profit|tp)\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*%', text_lower)
        if tp_percent:
            return {
                "type": "percentage",
                "value": float(tp_percent.group(1)),
            }

        # Pattern: target 2:1 or risk reward 2:1
        rr_match = re.search(r'(?:target|risk\s*reward|rr)\s*(?:ratio\s*)?(\d+(?:\.\d+)?)\s*:\s*1', text_lower)
        if rr_match:
            return {
                "type": "rr",
                "risk_reward_ratio": float(rr_match.group(1)),
            }

        # Pattern: stop loss X target Y (2:1)
        sl_tp = re.search(r'stop\s*loss\s*(\d+).*target\s*(\d+)', text_lower)
        if sl_tp:
            sl = float(sl_tp.group(1))
            tp = float(sl_tp.group(2))
            rr = tp / sl if sl > 0 else 0
            return {
                "type": "rr",
                "value": sl,
                "risk_reward_ratio": rr,
            }

        return None

    def _extract_position_sizing(self, text: str) -> Optional[dict]:
        """Extract position sizing configuration."""
        text_lower = text.lower()
        
        # Pattern: quantity X or qty X
        qty_match = re.search(r'(?:quantity|qty)\s*(?:of)?\s*(\d+)', text_lower)
        if qty_match:
            return {
                "type": "fixed",
                "quantity": int(qty_match.group(1)),
            }

        # Pattern: X% of capital
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*of\s*(?:capital|account)', text_lower)
        if pct_match:
            return {
                "type": "percent_capital",
                "percentage": float(pct_match.group(1)),
            }

        return None

    def _generate_strategy_name(self, text: str, symbol: Optional[str]) -> str:
        """Generate a strategy name from the text."""
        # Try to extract a meaningful name
        if symbol:
            # Find first significant word
            words = text.split()
            for word in words:
                if word.upper() != symbol and len(word) > 2 and word.lower() not in ['buy', 'sell', 'when', 'if', 'then', 'target', 'stop', 'loss']:
                    return f"{symbol} - {word.title()}"
            return f"{symbol} Strategy"
        
        return "Custom Strategy"

    def to_json(self, text: str, pretty: bool = True) -> str:
        """Parse and return JSON."""
        strategy = self.parse(text)
        return strategy.model_dump_json() if pretty else json.dumps(strategy, indent=2)


def parse_strategy(text: str) -> dict:
    """Convenience function to parse strategy text."""
    parser = StrategyParser()
    strategy = parser.parse(text)
    return json.loads(strategy.model_dump_json())


# Example usage and tests
if __name__ == "__main__":
    # Test cases
    test_cases = [
        "Buy NIFTY when 20 EMA crosses above 50 EMA. Stop loss 20 points. Target 40 points.",
        "Buy RELIANCE when RSI crosses above 30. Sell when RSI crosses above 70. Stop loss 5%.",
        "Buy NIFTY when price crosses above 20 SMA. Target 100 points with stop loss 50 points.",
        "Enter long on BANKNIFTY when 9 EMA crosses above 21 EMA. Stop loss 100 points. Target 200 points.",
        "Buy when RSI(14) is below 30. Sell when RSI crosses above 70. Stop loss 2%.",
    ]

    parser = StrategyParser()
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Input: {test}")
        print(f"{'='*60}")
        
        strategy = parser.parse(test)
        print(json.dumps(json.loads(strategy.model_dump_json()), indent=2))
        
        if parser.errors:
            print(f"Errors: {parser.errors}")
        if parser.warnings:
            print(f"Warnings: {parser.warnings}")
