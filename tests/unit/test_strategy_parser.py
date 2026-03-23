"""
Unit tests for Strategy Builder Parser
"""
import pytest
from strategy_engine.improved_parser import ImprovedStrategyParser, parse_strategy


class TestTimeframeExtraction:
    """Test timeframe extraction."""
    
    def test_minute_1(self):
        parser = ImprovedStrategyParser()
        assert parser._extract_timeframe("1 minute") == "1m"
        assert parser._extract_timeframe("1 min") == "1m"
        assert parser._extract_timeframe("1m") == "1m"
    
    def test_minute_5(self):
        parser = ImprovedStrategyParser()
        assert parser._extract_timeframe("5 minute") == "5m"
        assert parser._extract_timeframe("5 min") == "5m"
        assert parser._extract_timeframe("5m") == "5m"
        assert parser._extract_timeframe("5 mins") == "5m"
    
    def test_hour_1(self):
        parser = ImprovedStrategyParser()
        assert parser._extract_timeframe("1 hour") == "1h"
        assert parser._extract_timeframe("1 hr") == "1h"
        assert parser._extract_timeframe("1h") == "1h"
    
    def test_daily(self):
        parser = ImprovedStrategyParser()
        assert parser._extract_timeframe("daily") == "1d"
        assert parser._extract_timeframe("day") == "1d"
        assert parser._extract_timeframe("1d") == "1d"
    
    def test_default(self):
        parser = ImprovedStrategyParser()
        assert parser._extract_timeframe("random text") == "1d"


class TestSymbolExtraction:
    """Test symbol extraction."""
    
    def test_index_symbols(self):
        parser = ImprovedStrategyParser()
        assert parser._extract_symbol("Buy NIFTY") == "NIFTY"
        assert parser._extract_symbol("Trade BANKNIFTY") == "BANKNIFTY"
        assert parser._extract_symbol("On SENSEX") == "SENSEX"
        assert parser._extract_symbol("Buy FINNIFTY") == "FINNIFTY"
    
    def test_stock_symbol(self):
        parser = ImprovedStrategyParser()
        assert parser._extract_symbol("Buy RELIANCE") == "RELIANCE"
        assert parser._extract_symbol("Trade TCS") == "TCS"
    
    def test_unknown(self):
        parser = ImprovedStrategyParser()
        assert parser._extract_symbol("random text") == "UNKNOWN"


class TestIndicatorExtraction:
    """Test indicator extraction."""
    
    def test_single_indicator(self):
        parser = ImprovedStrategyParser()
        indicators = parser._extract_all_indicators("Buy when RSI crosses above 30")
        assert "RSI" in indicators
    
    def test_multiple_indicators(self):
        parser = ImprovedStrategyParser()
        indicators = parser._extract_all_indicators("Buy when EMA and RSI")
        assert "EMA" in indicators
        assert "RSI" in indicators


class TestStrategyParsing:
    """Test complete strategy parsing."""
    
    def test_rsi_strategy(self):
        result = parse_strategy("Buy NIFTY when RSI crosses above 30 and sell when RSI crosses below 70")
        
        assert result["symbol"] == "NIFTY"
        assert result["timeframe"] == "1d"
        assert len(result["entry_conditions"]) > 0
        assert len(result["exit_conditions"]) > 0
    
    def test_ema_crossover_strategy(self):
        result = parse_strategy("Buy NIFTY when EMA 13 crosses EMA 34")
        
        assert result["symbol"] == "NIFTY"
        assert len(result["entry_conditions"]) > 0
    
    def test_multi_condition_strategy(self):
        result = parse_strategy("Buy NIFTY when EMA 13 and EMA 34 above EMA 200 and EMA 13 crosses EMA 34")
        
        assert result["symbol"] == "NIFTY"
        # Should have multiple conditions
        entry = result["entry_conditions"][0]
        assert len(entry["conditions"]) >= 2
    
    def test_risk_management(self):
        result = parse_strategy("Buy NIFTY when RSI above 30, stop loss 2%, target 4%")
        
        assert "risk_management" in result["parameters"]
        assert result["parameters"]["risk_management"]["stop_loss"]["value"] == 2.0
        assert result["parameters"]["risk_management"]["take_profit"]["value"] == 4.0
    
    def test_vice_versa_exit(self):
        result = parse_strategy("Buy NIFTY when RSI above 30, vice versa for SELL")
        
        assert len(result["entry_conditions"]) > 0
        assert len(result["exit_conditions"]) > 0


class TestConditionFormat:
    """Test condition output format."""
    
    def test_ema_crossover_format(self):
        result = parse_strategy("Buy NIFTY when crossover 13 above 34")
        
        entry = result["entry_conditions"][0]["conditions"][0]
        assert entry["indicator"] == "ema_crossover"
        assert entry["period"] == 13
        assert entry["period2"] == 34
    
    def test_ema_above_format(self):
        result = parse_strategy("Buy NIFTY when EMA 13 above EMA 200")
        
        entry = result["entry_conditions"][0]["conditions"][0]
        assert entry["indicator"] == "ema_above_ema"
        assert entry["period"] == 13
        assert entry["period2"] == 200
    
    def test_rsi_format(self):
        result = parse_strategy("Buy NIFTY when RSI above 30")
        
        entry = result["entry_conditions"][0]["conditions"][0]
        assert entry["indicator"] == "rsi"
        assert entry["value"] == 30


class TestValidation:
    """Test validation."""
    
    def test_missing_symbol(self):
        parser = ImprovedStrategyParser()
        strategy = parser.parse("Buy when RSI above 30")
        
        assert strategy.symbol == "UNKNOWN"
        assert "Could not identify" in parser.warnings[0] if parser.warnings else True
    
    def test_empty_input(self):
        result = parse_strategy("")
        
        assert result["symbol"] == "UNKNOWN"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
