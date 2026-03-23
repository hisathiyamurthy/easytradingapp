"""
Improved Natural Language Strategy Parser
Supports multi-condition strategies with AND/OR logic

Features:
- Normalizes input (lowercase, expand abbreviations)
- Handles flexible grammar patterns
- Extracts indicators, entry/exit conditions
- Maps SL to stoploss, not position
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import Enum


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
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"


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


class LogicType(str, Enum):
    AND = "AND"
    OR = "OR"


# Abbreviation expansion map - word boundaries matter!
ABBREVIATIONS = {
    # These should only expand when standalone (not part of another word)
    'tp': 'target',
    'tgt': 'target',
    'ce': 'call',
    'pe': 'put',
}


def normalize_text(text: str) -> str:
    """
    Normalize input text:
    1. Convert to lowercase
    2. Expand specific abbreviations (context-aware)
    3. Remove duplicate consecutive words
    4. Clean up extra whitespace
    
    Note: sl, stl, ema, sma etc. are left as-is because they're 
    commonly used as-is in trading language
    """
    # First, lowercase the entire text
    text = text.lower().strip()
    
    # Expand specific abbreviations only when standalone (surrounded by spaces or at boundaries)
    # SL → stoploss (only when followed by number, e.g., "SL 2%" or "SL 100")
    text = re.sub(r'\bsl\s+(\d)', r'stoploss \1', text)
    text = re.sub(r'\bstl\s+(\d)', r'stoploss \1', text)
    
    # STP → stoploss (for "STP 2%")
    text = re.sub(r'\bstp\s+(\d)', r'stoploss \1', text)
    
    # EMA, SMA, RSI, MACD, VWAP, ATR are kept as-is (standard)
    
    # Remove duplicate consecutive words (case insensitive)
    words = text.split()
    deduped = []
    prev = None
    for word in words:
        if word != prev:
            deduped.append(word)
            prev = word
    text = ' '.join(deduped)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def parse_strategy(text: str) -> dict:
    """
    Parse trading strategy text into structured JSON.
    
    Returns:
        dict with keys: market, timeframe, indicators, entry, exit, position
        If unclear: returns warning, not failure
    """
    parser = ImprovedStrategyParser()
    strategy = parser.parse(text)
    return strategy.to_dict()


@dataclass
class ConditionRule:
    indicator: str
    operator: str
    value: Optional[float] = None
    period: Optional[int] = None
    period2: Optional[int] = None
    secondary_indicator: Optional[str] = None
    secondary_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "indicator": self.indicator,
            "operator": self.operator
        }
        if self.value is not None:
            result["value"] = self.value
        if self.period is not None:
            result["period"] = self.period
        if self.period2 is not None:
            result["period2"] = self.period2
        if self.secondary_indicator is not None:
            result["secondary_indicator"] = self.secondary_indicator
        if self.secondary_value is not None:
            result["secondary_value"] = self.secondary_value
        return result


@dataclass
class ConditionGroup:
    logic: str = "AND"
    conditions: List[ConditionRule] = field(default_factory=list)


@dataclass 
class RiskManagement:
    stop_loss_type: Optional[str] = None
    stop_loss_value: Optional[float] = None
    take_profit_type: Optional[str] = None
    take_profit_value: Optional[float] = None
    risk_reward_ratio: Optional[Union[float, str]] = None
    trailing_stop_loss: Optional[float] = None  # Trailing SL percentage
    trailing_stop_activation: Optional[float] = None  # Activate when profit reaches this %
    
    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.stop_loss_type and self.stop_loss_value is not None:
            if self.stop_loss_type == "percentage":
                result["stoploss"] = f"{self.stop_loss_value}%"
            else:
                result["stoploss"] = f"{self.stop_loss_value} points"
        if self.take_profit_type and self.take_profit_value is not None:
            if self.take_profit_type == "percentage":
                result["target"] = f"{self.take_profit_value}%"
            else:
                result["target"] = f"{self.take_profit_value} points"
        if self.risk_reward_ratio is not None:
            result["risk_reward"] = self.risk_reward_ratio
        if self.trailing_stop_loss is not None:
            result["trailing_stop_loss"] = self.trailing_stop_loss
            result["trailing_stop_activation"] = self.trailing_stop_activation
        return result


@dataclass
class StructuredStrategy:
    strategy_name: str
    timeframe: str = "1d"
    symbol: str = "UNKNOWN"
    exchange: str = "NSE"
    position: str = "BUY"
    
    # Options trading fields
    is_options: bool = False
    option_type: Optional[str] = None  # CE or PE
    strike_selection: Optional[str] = None  # ATM, ITM, OTM
    strike_distance: Optional[int] = None  # Distance from ATM (e.g., 100 points)
    expiry: Optional[str] = None  # Option expiry
    
    indicators: List[str] = field(default_factory=list)
    entry_conditions: List[ConditionGroup] = field(default_factory=list)
    exit_conditions: List[ConditionGroup] = field(default_factory=list)
    exit_details: Optional[Dict[str, Any]] = None
    risk_management: Optional[RiskManagement] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    warning: Optional[str] = None
    confidence: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        if self.error:
            result = {"error": self.error}
            if self.confidence is not None:
                result["confidence"] = self.confidence
            return result
        
        if self.warning:
            result = {"warning": self.warning}
            if self.confidence is not None:
                result["confidence"] = self.confidence
            return result
        
        result = {
            "strategy_name": self.strategy_name,
            "timeframe": self.timeframe,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "position": self.position,
        }
        
        # Add options trading info
        if self.is_options:
            result["is_options"] = True
            result["option_type"] = self.option_type
            result["strike_selection"] = self.strike_selection
            result["strike_distance"] = self.strike_distance
            result["expiry"] = self.expiry
        
        if self.indicators:
            result["indicators"] = self.indicators
        
        if self.entry_conditions:
            entry_list = []
            for group in self.entry_conditions:
                for cond in group.conditions:
                    entry_list.append(cond.to_human_readable())
            if len(entry_list) == 1:
                result["entry"] = entry_list[0]
            else:
                result["entry"] = entry_list
        
        if self.exit_conditions:
            exit_list = []
            for group in self.exit_conditions:
                for cond in group.conditions:
                    exit_list.append(cond.to_human_readable())
            if len(exit_list) == 1:
                result["exit"] = exit_list[0]
            else:
                result["exit"] = exit_list
        
        if self.exit_details:
            result["exit"] = self.exit_details
        
        if self.risk_management:
            risk_dict = self.risk_management.to_dict()
            if risk_dict:
                result["exit"] = risk_dict
        
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result


def _human_readable_condition(rule: ConditionRule) -> str:
    """Convert a condition rule to human readable format."""
    ind = rule.indicator
    op = rule.operator
    val = rule.value
    p1 = rule.period
    p2 = rule.period2
    
    if ind == "rsi":
        if op == "crosses_above":
            return f"RSI crosses above {val}"
        elif op == "crosses_below":
            return f"RSI crosses below {val}"
        elif op == "greater_than":
            return f"RSI > {val}"
        elif op == "less_than":
            return f"RSI < {val}"
        return f"RSI {op} {val}"
    
    elif ind == "ema_crossover" or ind == "ema":
        if p1 and p2:
            if op == "crosses_above":
                return f"EMA {p1} crosses above EMA {p2}"
            elif op == "crosses_below":
                return f"EMA {p1} crosses below EMA {p2}"
            elif op == "greater_than":
                return f"EMA {p1} > EMA {p2}"
            elif op == "less_than":
                return f"EMA {p1} < EMA {p2}"
        return f"EMA crossover"
    
    elif ind == "sma":
        if p1 and val:
            if op == "greater_than":
                return f"SMA {p1} > SMA {int(val)}"
            elif op == "less_than":
                return f"SMA {p1} < SMA {int(val)}"
        return f"SMA condition"
    
    elif ind == "vwap":
        if op == "crosses_above":
            return "Price crosses above VWAP"
        elif op == "crosses_below":
            return "Price crosses below VWAP"
        elif op == "greater_than":
            return "Price above VWAP"
        elif op == "less_than":
            return "Price below VWAP"
        return "VWAP condition"
    
    elif ind == "macd":
        if "bullish" in str(val).lower() or op == "crosses_above":
            return "MACD bullish crossover"
        elif "bearish" in str(val).lower() or op == "crosses_below":
            return "MACD bearish crossover"
        return "MACD condition"
    
    elif ind == "volume":
        return "Volume > previous candle"
    
    elif ind == "price":
        if op == "crosses_above":
            return "Price crosses above"
        elif op == "crosses_below":
            return "Price crosses below"
        elif op == "greater_than":
            return "Price above"
        elif op == "less_than":
            return "Price below"
        return "Price condition"
    
    return f"{ind} {op}"


ConditionRule.to_human_readable = _human_readable_condition


class ImprovedStrategyParser:
    """Improved parser with multi-condition support."""
    
    TIMEFRAME_MAP = {
        "1 minute": "5min", "1 min": "5min", "1m": "5min",
        "5 minute": "5min", "5 min": "5min", "5m": "5min", "5 mins": "5min",
        "5 min chart": "5min",
        "15 minute": "15min", "15 min": "15min", "15m": "15min",
        "15 min timeframe": "15min", "15 min chart": "15min",
        "30 minute": "30min", "30 min": "30min", "30m": "30min",
        "1 hour": "1hour", "1 hr": "1hour", "1h": "1hour",
        "4 hour": "4hour", "4 hr": "4hour", "4h": "4hour",
        "daily": "daily", "day": "daily", "1d": "daily",
        "daily chart": "daily",
        "weekly": "weekly", "week": "weekly", "1w": "weekly",
    }
    
    INDEX_SYMBOLS = {
        "nifty": "NIFTY", "nifty 50": "NIFTY", "nifty options": "NIFTY",
        "sensex": "SENSEX",
        "bank nifty": "BANKNIFTY", "banknifty": "BANKNIFTY",
        "fin nifty": "FINNIFTY", "finnifty": "FINNIFTY",
        "midcap": "MIDCAP",
    }
    
    AMBIGUOUS_PATTERNS = [
        r'rsi\s+is\s+(low|high|overbought|oversold|neutral)',
        r'price\s+is\s+(high|low|expensive|cheap)',
        r'stock\s+is\s+(good|bad|strong|weak)',
    ]
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def parse(self, text: str) -> StructuredStrategy:
        # Normalize input first
        original_text = text
        text = normalize_text(text)
        
        self.errors = []
        self.warnings = []
        
        if not text:
            return StructuredStrategy(
                strategy_name="Empty Strategy",
                error="Strategy text is empty",
                confidence=0
            )
        
        if self._is_ambiguous(text):
            return self._handle_ambiguous(text, original_text)
        
        if self._is_unclear(text):
            return self._handle_unclear(original_text, text)
        
        if self._is_subjective(text):
            return StructuredStrategy(
                strategy_name="Subjective Strategy",
                error="Subjective condition not measurable",
                confidence=10
            )
        
        options_info = self._extract_options_info(text)
        
        strategy = StructuredStrategy(
            strategy_name=self._generate_name(text),
            timeframe=self._extract_timeframe(text),
            symbol=self._extract_symbol(text),
            position=self._extract_position(text),
            indicators=self._extract_all_indicators(text),
            is_options=options_info["is_options"],
            option_type=options_info["option_type"],
            strike_selection=options_info["strike_selection"],
            strike_distance=options_info["strike_distance"],
            expiry=options_info["expiry"],
        )
        
        strategy.entry_conditions = self._parse_entry_conditions(text)
        strategy.exit_conditions = self._parse_exit_conditions(text)
        
        use_opposite = "vice versa" in text or "opposite signal" in text or "reverse" in text
        
        if use_opposite or not self._has_real_exit_conditions(strategy.exit_conditions):
            if strategy.entry_conditions and not use_opposite:
                pass
            elif strategy.entry_conditions:
                exit_group = ConditionGroup(logic="AND", conditions=[])
                for entry_group in strategy.entry_conditions:
                    for cond in entry_group.conditions:
                        opposite_cond = self._get_opposite_condition(cond)
                        if opposite_cond:
                            exit_group.conditions.append(opposite_cond)
                if exit_group.conditions:
                    strategy.exit_conditions = [exit_group]
                strategy.exit_details = {"type": "opposite_signal", "description": "Exit on opposite entry signal"}
        
        if "opposite signal" in text and not strategy.exit_details:
            strategy.exit_details = {"type": "opposite_signal", "description": "Exit on opposite entry signal"}
        
        strategy.risk_management = self._parse_risk_management(text)
        
        # If risk_management exists but no exit_conditions, add stoploss/target to exit
        if strategy.risk_management and not self._has_real_exit_conditions(strategy.exit_conditions):
            exit_conditions = []
            if strategy.risk_management.stop_loss_value:
                cond = ConditionRule(
                    indicator="stoploss",
                    operator="less_than",
                    value=strategy.risk_management.stop_loss_value,
                    period=strategy.risk_management.stop_loss_type == "points" and 0 or None
                )
                exit_conditions.append(cond)
            if strategy.risk_management.take_profit_value:
                cond = ConditionRule(
                    indicator="target",
                    operator="greater_than",
                    value=strategy.risk_management.take_profit_value,
                    period=strategy.risk_management.take_profit_type == "points" and 0 or None
                )
                exit_conditions.append(cond)
            if exit_conditions:
                strategy.exit_conditions = [ConditionGroup(logic="AND", conditions=exit_conditions)]
        
        strategy.metadata = {
            "original_text": original_text,
            "normalized_text": text,
        }
        
        return strategy
    
    def _is_ambiguous(self, text: str) -> bool:
        for pattern in self.AMBIGUOUS_PATTERNS:
            if re.search(pattern, text):
                return True
        return False
    
    def _is_unclear(self, text: str) -> bool:
        unclear_patterns = [
            r'above\s+\d+',
            r'below\s+\d+',
            r'higher\s+than\s+\d+',
            r'lower\s+than\s+\d+',
        ]
        for pattern in unclear_patterns:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                if match:
                    threshold = match.group(0).split()[-1]
                    if not any(ind in text for ind in ['ema', 'sma', 'rsi', 'price', 'vwap', 'macd']):
                        return True
        return False
    
    def _is_subjective(self, text: str) -> bool:
        subjective_patterns = [
            'market is strong',
            'market is weak', 
            'market is bullish',
            'market is bearish',
            'when market is strong',
            'when market is weak',
            'market is volatile',
        ]
        for pattern in subjective_patterns:
            if pattern in text:
                return True
        return False
    
    def _handle_ambiguous(self, text: str, original: str) -> StructuredStrategy:
        if 'rsi' in text and any(w in text for w in ['low', 'high', 'overbought', 'oversold']):
            return StructuredStrategy(
                strategy_name="Ambiguous RSI Strategy",
                error="RSI threshold not defined",
                confidence=40
            )
        return StructuredStrategy(
            strategy_name="Ambiguous Strategy",
            warning="Condition is ambiguous",
            confidence=40
        )
    
    def _handle_unclear(self, original: str, text: str) -> StructuredStrategy:
        match = re.search(r'above\s+(\d+)', text)
        if match and 'nifty' in text.lower():
            threshold = match.group(1)
            return StructuredStrategy(
                strategy_name="Unclear Strategy",
                warning=f"Condition unclear: 'above {threshold}'",
                confidence=30
            )
        match = re.search(r'below\s+(\d+)', text)
        if match:
            threshold = match.group(1)
            return StructuredStrategy(
                strategy_name="Unclear Strategy",
                warning=f"Condition unclear: 'below {threshold}'",
                confidence=30
            )
        return StructuredStrategy(
            strategy_name="Unclear Strategy",
            warning="Condition unclear",
            confidence=30
        )
    
    def _generate_name(self, text: str) -> str:
        indicators = self._extract_all_indicators(text)
        if indicators:
            indicator_str = " + ".join(indicators[:2])
            return f"Strategy: {indicator_str}"
        return "Custom Strategy"
    
    def _extract_timeframe(self, text: str) -> str:
        text_lower = text.lower()
        
        patterns_priority = [
            ("15 min timeframe", "15min"),
            ("15 min chart", "15min"),
            ("15 min", "15min"),
            ("15 minute", "15min"),
            ("15m", "15min"),
            ("5 min chart", "5min"),
            ("5 min", "5min"),
            ("5 mins", "5min"),
            ("5 minute", "5min"),
            ("5m", "5min"),
            ("1 min", "5min"),
            ("1 minute", "5min"),
            ("1m", "5min"),
            ("30 min", "30min"),
            ("30 minute", "30min"),
            ("30m", "30min"),
            ("1 hour", "1hour"),
            ("1 hr", "1hour"),
            ("1h", "1hour"),
            ("4 hour", "4hour"),
            ("4 hr", "4hour"),
            ("4h", "4hour"),
            ("daily chart", "daily"),
            ("daily", "daily"),
            ("day", "daily"),
            ("1d", "daily"),
            ("weekly", "weekly"),
            ("week", "weekly"),
            ("1w", "weekly"),
        ]
        
        for pattern, tf in patterns_priority:
            if pattern in text_lower:
                return tf
        return "daily"
    
    def _extract_symbol(self, text: str) -> str:
        text_lower = text.lower()
        
        index_patterns = [
            ("banknifty", "BANKNIFTY"),
            ("bank nifty", "BANKNIFTY"),
            ("nifty options", "NIFTY"),
            ("nifty 50", "NIFTY"),
            ("nifty", "NIFTY"),
            ("sensex", "SENSEX"),
            ("finnifty", "FINNIFTY"),
            ("fin nifty", "FINNIFTY"),
            ("midcap", "MIDCAP"),
        ]
        
        for pattern, symbol in index_patterns:
            if pattern in text_lower:
                return symbol
        
        return "UNKNOWN"
    
    def _extract_options_info(self, text: str) -> Dict[str, Any]:
        """Extract options trading information from strategy text."""
        text_lower = text.lower()
        result = {
            "is_options": False,
            "option_type": None,
            "strike_selection": None,
            "strike_distance": None,
            "expiry": None,
        }
        
        # Check if this is an options strategy
        options_keywords = [
            "options", "call", "put", "ce ", "pe ", "option",
            "nifty options", "banknifty options", "stock options"
        ]
        
        if any(kw in text_lower for kw in options_keywords):
            result["is_options"] = True
            
            # Extract CE or PE
            if re.search(r'\bce\b|\bcall\b', text_lower):
                result["option_type"] = "CE"
            elif re.search(r'\bpe\b|\bput\b', text_lower):
                result["option_type"] = "PE"
            
            # Extract strike selection (ATM, ITM, OTM)
            if re.search(r'\batm\b|\bat the money\b', text_lower):
                result["strike_selection"] = "ATM"
            elif re.search(r'\bitm\b|\bin the money\b', text_lower):
                result["strike_selection"] = "ITM"
            elif re.search(r'\botm\b|\bout of the money\b', text_lower):
                result["strike_selection"] = "OTM"
            
            # Extract specific strike distance (e.g., 100 points OTM)
            strike_dist_match = re.search(r'(\d+)\s*(?:points?)?\s*(?:otm|itm|atm)', text_lower)
            if strike_dist_match:
                result["strike_distance"] = int(strike_dist_match.group(1))
            
            # Extract strike price if directly specified
            strike_price_match = re.search(r'(?:strike|strike\s*price)\s*(\d+)', text_lower)
            if strike_price_match:
                result["strike_distance"] = int(strike_price_match.group(1))
                result["strike_selection"] = "FIXED"
            
            # Extract expiry
            expiry_patterns = [
                r'(\d{1,2})(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\d{2,4}',
                r'(?:weekly|monthly|current|next)\s*expiry',
            ]
            for pattern in expiry_patterns:
                if re.search(pattern, text_lower):
                    match = re.search(pattern, text_lower)
                    result["expiry"] = match.group(0)
                    break
        
        return result
        
        if re.search(r'long\s+on\s+([A-Z]{2,10})', text, re.IGNORECASE):
            match = re.search(r'long\s+on\s+([A-Z]{2,10})', text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        match = re.search(r'^([A-Z]{2,10}),?\s*BUY', text)
        if match:
            return match.group(1)
        
        match = re.search(r'\bBUY\s+([A-Z]{2,10})\b', text)
        if match:
            return match.group(1)
        
        match = re.search(r'\b(BUY|SELL|SHORT)\s+([A-Z]{2,10})\b', text)
        if match:
            return match.group(2)
        
        common_words = {'EMA', 'SMA', 'RSI', 'MACD', 'VWAP', 'ATR', 'STOP', 'LOSS', 'TARGET', 'BUY', 'SELL', 'AND', 'OR', 'EXIT', 'PROFIT', 'OPTIONS', 'CE', 'PE', 'STOCK'}
        matches = re.findall(r'\b([A-Z]{2,20})\b', text)
        for m in matches:
            if m not in common_words:
                return m
        
        return "UNKNOWN"
    
    def _extract_position(self, text: str) -> str:
        text_lower = text.lower()
        
        buy_at_start = text_lower.startswith('buy') or text_lower.startswith('enter long') or text_lower.startswith('long')
        sell_at_start = text_lower.startswith('sell') or text_lower.startswith('short')
        
        if buy_at_start and not sell_at_start:
            return "BUY"
        if sell_at_start:
            return "SELL"
        
        if 'buy' in text_lower and 'sell' not in text_lower:
            return "BUY"
        if 'sell' in text_lower and 'buy' not in text_lower:
            return "SELL"
        
        if any(w in text_lower for w in ['buy', 'enter long', 'long']):
            return "BUY"
        if any(w in text_lower for w in ['sell', 'short', 'exit long']):
            return "SELL"
        return "BUY"
    
    def _extract_all_indicators(self, text: str) -> List[str]:
        indicators = []
        text_lower = text.lower()
        
        if re.search(r'\bema\b', text_lower): indicators.append("EMA")
        if re.search(r'\bsma\b', text_lower): indicators.append("SMA")
        if re.search(r'\brsi\b', text_lower): indicators.append("RSI")
        if re.search(r'\bmacd\b', text_lower): indicators.append("MACD")
        if re.search(r'\bvwap\b', text_lower): indicators.append("VWAP")
        if re.search(r'\bbollinger\b', text_lower): indicators.append("Bollinger")
        if re.search(r'\batr\b', text_lower): indicators.append("ATR")
        if re.search(r'\bvolume\b', text_lower): indicators.append("Volume")
        
        ema_matches = re.findall(r'(\d+)\s*ema', text_lower)
        for match in set(ema_matches):
            if int(match) != 20:
                indicators.append(f"EMA_{match}")
        
        return list(dict.fromkeys(indicators))
    
    def _has_real_exit_conditions(self, conditions: List[ConditionGroup]) -> bool:
        if not conditions:
            return False
        for group in conditions:
            for cond in group.conditions:
                if cond.indicator in ["ema_crossover", "ema", "rsi", "macd", "sma", "vwap", "price"]:
                    return True
        return False
    
    def _parse_entry_conditions(self, text: str) -> List[ConditionGroup]:
        groups = []
        text_lower = text.lower()
        
        # Try to extract sections starting with buy keywords
        buy_section = self._extract_section(text, ["buy", "enter long", "long"])
        if not buy_section:
            buy_section = self._extract_section(text, ["enter"])
        
        all_conditions = []
        
        # Extract conditions from buy sections
        for section in buy_section:
            conditions = self._extract_conditions_from_text(section)
            all_conditions.extend(conditions)
        
        # If no buy sections found, try to extract indicators from the ENTIRE text
        # This handles flexible grammar like "13 ema cross above 34 ema" without "buy"
        if not all_conditions:
            conditions = self._extract_conditions_from_text(text)
            all_conditions.extend(conditions)
        
        if all_conditions:
            groups.append(ConditionGroup(logic="AND", conditions=all_conditions))
        
        return groups
    
    def _parse_exit_conditions(self, text: str) -> List[ConditionGroup]:
        groups = []
        text_lower = text.lower()
        
        sell_section = self._extract_section(text, ["sell", "exit", "square off"])
        
        all_conditions = []
        
        for section in sell_section:
            conditions = self._extract_conditions_from_text(section)
            all_conditions.extend(conditions)
        
        if all_conditions:
            groups.append(ConditionGroup(logic="AND", conditions=all_conditions))
        
        return groups
    
    def _extract_conditions_from_text(self, text: str) -> List[ConditionRule]:
        conditions = []
        text_lower = text.lower()
        seen = set()
        
        def add(cond: ConditionRule):
            key = (cond.indicator, cond.indicator, cond.operator, cond.period, cond.period2, cond.value)
            if key not in seen:
                seen.add(key)
                conditions.append(cond)
        
        # FLEXIBLE GRAMMAR: "13 ema cross above 34 ema" = EMA crossover
        ema_cross_patterns = [
            r'(\d+)\s*ema\s+cross(?:es)?\s+(?:above|over)\s+(\d+)\s*ema',
            r'(\d+)\s*ema\s+cross(?:es)?\s+(\d+)\s*ema',
            r'ema\s+(\d+)\s+cross(?:es)?\s+(?:above|over)\s+ema\s+(\d+)',
            r'cross(?:es)?\s+above\s+(\d+)\s*ema\s+(\d+)',
            r'(\d+)\s*ema\s+(?:goes\s+)?above\s+(\d+)\s*ema',
        ]
        for pattern in ema_cross_patterns:
            if re.search(pattern, text_lower):
                for m in re.finditer(pattern, text_lower):
                    # Find the numbers (could be in different order)
                    numbers = [int(x) for x in re.findall(r'\d+', m.group(0))]
                    if len(numbers) >= 2:
                        add(ConditionRule(indicator="ema_crossover", operator="crosses_above", period=numbers[0], period2=numbers[1]))
        
        # FLEXIBLE GRAMMAR: "close above 200 ema" = Close > EMA 200
        close_above_ema_patterns = [
            r'close\s+above\s+(\d+)\s*ema',
            r'close\s+goes\s+above\s+(\d+)\s*ema',
            r'price\s+above\s+(\d+)\s*ema',
            r'above\s+(\d+)\s*ema',  # Generic "above X ema"
        ]
        for pattern in close_above_ema_patterns:
            if re.search(pattern, text_lower):
                for m in re.finditer(pattern, text_lower):
                    val = int(m.group(1))
                    add(ConditionRule(indicator="price", operator="crosses_above", secondary_indicator=f"EMA_{val}"))
        
        # FLEXIBLE GRAMMAR: "close below 200 ema" = Close < EMA 200
        close_below_ema_patterns = [
            r'close\s+below\s+(\d+)\s*ema',
            r'close\s+goes\s+below\s+(\d+)\s*ema',
            r'price\s+below\s+(\d+)\s*ema',
            r'below\s+(\d+)\s*ema',
        ]
        for pattern in close_below_ema_patterns:
            if re.search(pattern, text_lower):
                for m in re.finditer(pattern, text_lower):
                    val = int(m.group(1))
                    add(ConditionRule(indicator="price", operator="crosses_below", secondary_indicator=f"EMA_{val}"))
        
        # Handle "SELL SL" as stoploss, NOT position change
        # Pattern: "SELL SL 2%" or "stoploss 2%" or "sl 2 points"
        sl_patterns = [
            r'stoploss\s+(\d+(?:\.\d+)?)\s*%',
            r'stop\s*loss\s+(\d+(?:\.\d+)?)\s*%',
            r'sl\s+(\d+(?:\.\d+)?)\s*%',
            r'stl\s+(\d+(?:\.\d+)?)\s*%',
            r'stoploss\s+(\d+(?:\.\d+)?)\s*(?:points?|rs)',
            r'sl\s+(\d+(?:\.\d+)?)\s*(?:points?|rs)',
        ]
        for pattern in sl_patterns:
            if re.search(pattern, text_lower):
                for m in re.finditer(pattern, text_lower):
                    val = float(m.group(1))
                    # This is risk management, not an exit condition
                    pass  # Handled in _parse_risk_management
        
        if re.search(r'(\d+)\s*ema\s+crosses?\s+(?:above|over)\s+(\d+)\s*ema', text_lower):
            for m in re.finditer(r'(\d+)\s*ema\s+crosses?\s+(?:above|over)\s+(\d+)\s*ema', text_lower):
                add(ConditionRule(indicator="ema_crossover", operator="crosses_above", period=int(m.group(1)), period2=int(m.group(2))))
        
        if re.search(r'(\d+)\s*ema\s+crosses?\s+(\d+)\s*ema', text_lower):
            for m in re.finditer(r'(\d+)\s*ema\s+crosses?\s+(\d+)\s*ema', text_lower):
                add(ConditionRule(indicator="ema_crossover", operator="crosses_above", period=int(m.group(1)), period2=int(m.group(2))))
        
        if re.search(r'crossover\s+(\d+)\s+(?:above|over)\s+(\d+)', text_lower):
            for m in re.finditer(r'crossover\s+(\d+)\s+(?:above|over)\s+(\d+)', text_lower):
                add(ConditionRule(indicator="ema_crossover", operator="crosses_above", period=int(m.group(1)), period2=int(m.group(2))))
        
        if re.search(r'(\d+)\s*ema\s+(?:above|over)\s+(\d+)\s*ema', text_lower):
            for m in re.finditer(r'(\d+)\s*ema\s+(?:above|over)\s+(\d+)\s*ema', text_lower):
                add(ConditionRule(indicator="ema", operator="greater_than", period=int(m.group(1)), period2=int(m.group(2))))
        
        if re.search(r'price\s+(?:goes\s+)?below\s+(\d+)\s*ema', text_lower):
            for m in re.finditer(r'price\s+(?:goes\s+)?below\s+(\d+)\s*ema', text_lower):
                add(ConditionRule(indicator="price", operator="crosses_below", period=int(m.group(1))))
        
        if re.search(r'price\s+(?:crosses\s+)?below\s+ema\s*(\d+)', text_lower):
            for m in re.finditer(r'price\s+(?:crosses\s+)?below\s+ema\s*(\d+)', text_lower):
                add(ConditionRule(indicator="price", operator="crosses_below", period=int(m.group(1))))
        
        if re.search(r'price\s+(?:crosses\s+)?above\s+vwap', text_lower):
            add(ConditionRule(indicator="price", operator="crosses_above", secondary_indicator="VWAP"))
        
        if re.search(r'(?:price\s+)?crosses?\s+(?:above|over)\s+vwap', text_lower):
            add(ConditionRule(indicator="price", operator="crosses_above", secondary_indicator="VWAP"))
        
        if re.search(r'price\s+(?:is\s+)?(above|below)\s+vwap', text_lower):
            m = re.search(r'price\s+(?:is\s+)?(above|below)\s+vwap', text_lower)
            op = "greater_than" if m.group(1) == "above" else "less_than"
            add(ConditionRule(indicator="vwap", operator=op))
        
        if re.search(r'above\s+vwap', text_lower):
            add(ConditionRule(indicator="vwap", operator="greater_than"))
        
        rsi_patterns = [
            r'rsi\s+crosses?\s+(?:above|over|below|under)\s+(\d+)',
            r'rsi\s+(?:crosses?\s+)?(\d+)\s+(?:above|below|over|under)',
            r'rsi\s+(?:crosses?\s+)?(\d+)\s*$',
        ]
        for pattern in rsi_patterns:
            if re.search(pattern, text_lower):
                for m in re.finditer(pattern, text_lower):
                    val = int(m.group(1))
                    if 'crosses' in m.group(0).lower() or 'above' in m.group(0).lower() or 'over' in m.group(0).lower():
                        if 'below' not in m.group(0).lower():
                            add(ConditionRule(indicator="rsi", operator="crosses_above", value=val))
                        else:
                            add(ConditionRule(indicator="rsi", operator="crosses_below", value=val))
                    elif 'below' in m.group(0).lower() or 'under' in m.group(0).lower():
                        add(ConditionRule(indicator="rsi", operator="crosses_below", value=val))
                    else:
                        add(ConditionRule(indicator="rsi", operator="crosses_above", value=val))
        
        if re.search(r'rsi\s+(?:is\s+)?(?:above|over)\s+(\d+)', text_lower):
            for m in re.finditer(r'rsi\s+(?:is\s+)?(?:above|over)\s+(\d+)', text_lower):
                add(ConditionRule(indicator="rsi", operator="greater_than", value=int(m.group(1))))
        
        if re.search(r'rsi\s+(?:is\s+)?(?:below|under)\s+(\d+)', text_lower):
            for m in re.finditer(r'rsi\s+(?:is\s+)?(?:below|under)\s+(\d+)', text_lower):
                add(ConditionRule(indicator="rsi", operator="less_than", value=int(m.group(1))))
        
        if re.search(r'(\d+)\s*sma\s+(?:is\s+)?(?:below|under)\s+(\d+)', text_lower):
            for m in re.finditer(r'(\d+)\s*sma\s+(?:is\s+)?(?:below|under)\s+(\d+)', text_lower):
                add(ConditionRule(indicator="sma", operator="less_than", period=int(m.group(1)), value=int(m.group(2))))
        
        if re.search(r'macd\s+(?:gives?\s+)?bullish\s+crossover', text_lower):
            add(ConditionRule(indicator="macd", operator="crosses_above", value="bullish"))
        
        if re.search(r'macd\s+(?:crosses?\s+(?:above|over|below|under))', text_lower):
            if 'above' in text_lower or 'over' in text_lower:
                add(ConditionRule(indicator="macd", operator="crosses_above"))
            else:
                add(ConditionRule(indicator="macd", operator="crosses_below"))
        
        if re.search(r'volume\s+higher\s+than\s+previous', text_lower):
            add(ConditionRule(indicator="volume", operator="greater_than", secondary_indicator="previous_candle"))
        
        if re.search(r'price\s+breaks?\s+previous', text_lower):
            add(ConditionRule(indicator="price", operator="breaks", secondary_indicator="previous_high"))
        
        return conditions
    
    def _extract_section(self, text: str, keywords: List[str]) -> List[str]:
        sections = []
        text_lower = text.lower()
        
        for keyword in keywords:
            pattern = rf'{keyword}\s+(?:when\s+)?(.+?)(?:\.|$|, exit|, and\s+exit)'
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                section = match.group(1).strip()
                if section and len(section) > 3:
                    sections.append(section)
            
            pattern2 = rf'{keyword}\s+(.+?)(?:,|\.|$)'
            for match in re.finditer(pattern2, text_lower, re.IGNORECASE):
                section = match.group(1).strip()
                if section and len(section) > 3 and section not in [s.lower() for s in sections]:
                    sections.append(section)
        
        return sections
    
    def _get_opposite_condition(self, cond: ConditionRule) -> Optional[ConditionRule]:
        op_map = {
            "crosses_above": "crosses_below",
            "crosses_below": "crosses_above",
            "greater_than": "less_than",
            "less_than": "greater_than",
        }
        
        new_op = op_map.get(cond.operator)
        if new_op:
            return ConditionRule(
                indicator=cond.indicator,
                operator=new_op,
                value=cond.value,
                period=cond.period,
                period2=cond.period2,
                secondary_indicator=cond.secondary_indicator,
                secondary_value=cond.secondary_value
            )
        return None
    
    def _parse_risk_management(self, text: str) -> Optional[RiskManagement]:
        risk = RiskManagement()
        text_lower = text.lower()
        
        sl_patterns = [
            (r'stop\s*loss\s*of\s*(\d+(?:\.\d+)?)\s*%', 'percentage'),
            (r'stop\s*loss\s*of\s*(\d+(?:\.\d+)?)\s*(?:points?|rs)', 'points'),
            (r'stop\s*loss\s*(\d+(?:\.\d+)?)\s*%', 'percentage'),
            (r'stop\s*loss\s*(\d+(?:\.\d+)?)\s*(?:points?|rs)', 'points'),
            (r'(\d+(?:\.\d+)?)\s*%\s*(?:loss|stoploss)', 'percentage'),
            (r'sl\s*(\d+(?:\.\d+)?)\s*%', 'percentage'),
            (r'sl\s*(\d+(?:\.\d+)?)\s*points?', 'points'),
            (r'stl\s*(\d+(?:\.\d+)?)\s*%', 'percentage'),
            (r'stl\s*(\d+(?:\.\d+)?)\s*points?', 'points'),
            # Handle "SELL SL 2%" - this is stoploss, NOT a sell order
            (r'sell\s+sl\s+(\d+(?:\.\d+)?)\s*%', 'percentage'),
            (r'sell\s+sl\s+(\d+(?:\.\d+)?)\s*points?', 'points'),
            # Handle standalone SL percentage
            (r'sl\s+(\d+(?:\.\d+)?)\s*%', 'percentage'),
            (r'stl\s+(\d+(?:\.\d+)?)\s*%', 'percentage'),
        ]
        
        for pattern, unit in sl_patterns:
            if re.search(pattern, text_lower):
                match = re.search(pattern, text_lower)
                if unit == 'percentage':
                    risk.stop_loss_type = "percentage"
                    risk.stop_loss_value = float(match.group(1))
                else:
                    risk.stop_loss_type = "points"
                    risk.stop_loss_value = float(match.group(1))
                break
        
        tp_patterns = [
            (r'target\s*(\d+(?:\.\d+)?)\s*%', 'percentage'),
            (r'take\s*profit\s*(\d+(?:\.\d+)?)\s*%', 'percentage'),
            (r'(\d+(?:\.\d+)?)\s*%\s*(?:profit|target)', 'percentage'),
            (r'profit\s*(\d+(?:\.\d+)?)\s*%', 'percentage'),
            (r'target\s*(\d+(?:\.\d+)?)\s*(?:points?|rs)', 'points'),
            (r'(\d+(?:\.\d+)?)\s*points?\s*(?:profit|target)', 'points'),
        ]
        
        for pattern, unit in tp_patterns:
            if re.search(pattern, text_lower):
                match = re.search(pattern, text_lower)
                if unit == 'percentage':
                    risk.take_profit_type = "percentage"
                    risk.take_profit_value = float(match.group(1))
                else:
                    risk.take_profit_type = "points"
                    risk.take_profit_value = float(match.group(1))
                break
        
        if re.search(r'risk\s*reward\s*(?:ratio\s*)?(\d+:\d+)', text_lower):
            match = re.search(r'risk\s*reward\s*(?:ratio\s*)?(\d+:\d+)', text_lower)
            risk.risk_reward_ratio = match.group(1)
        
        if re.search(r'(\d+):(\d+)\s*risk\s*reward', text_lower):
            match = re.search(r'(\d+):(\d+)\s*risk\s*reward', text_lower)
            risk.risk_reward_ratio = f"{match.group(1)}:{match.group(2)}"
        
        # Trailing stoploss patterns
        trailing_sl_patterns = [
            (r'trailing\s*stop\s*loss\s*(\d+(?:\.\d+)?)\s*%', 'activate_after'),
            (r'trailing\s*sl\s*(\d+(?:\.\d+)?)\s*%', 'activate_after'),
            (r'ts\s*(\d+(?:\.\d+)?)\s*%\s*activate\s*(\d+(?:\.\d+)?)\s*%', 'both'),
            (r'trailing\s*stop\s*(\d+(?:\.\d+)?)\s*%', 'sl_only'),
        ]
        
        for pattern, pattern_type in trailing_sl_patterns:
            if re.search(pattern, text_lower):
                match = re.search(pattern, text_lower)
                if pattern_type == 'both':
                    risk.trailing_stop_loss = float(match.group(1))
                    risk.trailing_stop_activation = float(match.group(2))
                else:
                    # Default activation at 1% profit
                    risk.trailing_stop_loss = float(match.group(1))
                    risk.trailing_stop_activation = 1.0
                break
        
        if risk.stop_loss_type or risk.take_profit_type or risk.risk_reward_ratio or risk.trailing_stop_loss:
            return risk
        return None


def parse_strategy(text: str) -> dict:
    parser = ImprovedStrategyParser()
    strategy = parser.parse(text)
    return strategy.to_dict()
