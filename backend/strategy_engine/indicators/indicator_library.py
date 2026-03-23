"""Technical Indicator Library.

Indicators implemented:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- VWAP (Volume Weighted Average Price)
- CCI (Commodity Channel Index)
"""
import math
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class IndicatorResult:
    """Result container for indicator values."""
    value: float
    signal: Optional[float] = None  # For MACD
    histogram: Optional[float] = None  # For MACD
    upper: Optional[float] = None  # For Bollinger
    lower: Optional[float] = None  # For Bollinger


class Indicator:
    """Base class for technical indicators."""

    @staticmethod
    def _validate_data(data: list) -> np.ndarray:
        """Validate and convert input data to numpy array."""
        if not data or len(data) < 2:
            raise ValueError("Insufficient data for calculation")
        return np.array(data, dtype=float)

    @staticmethod
    def sma(data: list, period: int) -> Optional[float]:
        """Calculate Simple Moving Average.

        SMA = (P1 + P2 + ... + Pn) / n

        Args:
            data: List of closing prices
            period: Number of periods for SMA

        Returns:
            SMA value or None if insufficient data
        """
        data = Indicator._validate_data(data)
        if len(data) < period:
            return None

        return float(np.mean(data[-period:]))

    @staticmethod
    def ema(data: list, period: int) -> Optional[float]:
        """Calculate Exponential Moving Average.

        EMA = (Close * k) + (Previous EMA * (1 - k))
        where k = 2 / (period + 1)

        Args:
            data: List of closing prices
            period: Number of periods for EMA

        Returns:
            EMA value or None if insufficient data
        """
        data = Indicator._validate_data(data)
        if len(data) < period:
            return None

        k = 2 / (period + 1)

        # Start with SMA for first value
        ema = float(np.mean(data[:period]))

        # Calculate EMA for remaining values
        for price in data[period:]:
            ema = (price * k) + (ema * (1 - k))

        return ema

    @staticmethod
    def rsi(data: list, period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index.

        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss

        Args:
            data: List of closing prices
            period: Number of periods (typically 14)

        Returns:
            RSI value (0-100) or None if insufficient data
        """
        data = Indicator._validate_data(data)
        if len(data) < period + 1:
            return None

        # Calculate price changes
        deltas = np.diff(data)

        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # Calculate initial average gain and loss
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        # Use Wilder's smoothing method for subsequent values
        for gain, loss in zip(gains[period:], losses[period:]):
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi)

    @staticmethod
    def macd(
        data: list,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Optional[IndicatorResult]:
        """Calculate Moving Average Convergence Divergence.

        MACD Line = Fast EMA - Slow EMA
        Signal Line = EMA of MACD Line
        Histogram = MACD Line - Signal Line

        Args:
            data: List of closing prices
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)

        Returns:
            IndicatorResult with MACD, signal, and histogram values
        """
        data = Indicator._validate_data(data)
        if len(data) < slow_period + signal_period:
            return None

        # Calculate MACD line
        ema_fast = Indicator.ema(data, fast_period)
        ema_slow = Indicator.ema(data, slow_period)

        if ema_fast is None or ema_slow is None:
            return None

        macd_line = ema_fast - ema_slow

        # Calculate signal line (EMA of MACD)
        # We need the MACD values to calculate signal
        macd_values = []
        for i in range(slow_period - 1, len(data)):
            fast = Indicator.ema(data[:i+1], fast_period)
            slow = Indicator.ema(data[:i+1], slow_period)
            if fast and slow:
                macd_values.append(fast - slow)

        if len(macd_values) < signal_period:
            return None

        signal_line = Indicator.ema(macd_values, signal_period)
        histogram = macd_line - signal_line if signal_line else None

        return IndicatorResult(
            value=macd_line,
            signal=signal_line,
            histogram=histogram
        )

    @staticmethod
    def vwap(
        high: list,
        low: list,
        close: list,
        volume: list
    ) -> Optional[float]:
        """Calculate Volume Weighted Average Price.

        VWAP = Sum(Price * Volume) / Sum(Volume)

        For intraday: Use rolling calculation
        VWAP = Cumulative(Price * Volume) / Cumulative(Volume)

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            volume: List of volumes

        Returns:
            VWAP value or None if insufficient data
        """
        if not (len(high) == len(low) == len(close) == len(volume)):
            raise ValueError("All input lists must have the same length")

        if len(high) < 2:
            return None

        high = np.array(high, dtype=float)
        low = np.array(low, dtype=float)
        close = np.array(close, dtype=float)
        volume = np.array(volume, dtype=float)

        # Typical Price = (High + Low + Close) / 3
        typical_price = (high + low + close) / 3

        # VWAP = Sum(Typical Price * Volume) / Sum(Volume)
        cumulative_tpv = np.cumsum(typical_price * volume)
        cumulative_vol = np.cumsum(volume)

        vwap = cumulative_tpv[-1] / cumulative_vol[-1]

        return float(vwap)

    @staticmethod
    def vwap_rolling(
        high: list,
        low: list,
        close: list,
        volume: list,
        window: int = 14
    ) -> list:
        """Calculate rolling VWAP.

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            volume: List of volumes
            window: Rolling window size

        Returns:
            List of VWAP values
        """
        if not (len(high) == len(low) == len(close) == len(volume)):
            raise ValueError("All input lists must have the same length")

        high = np.array(high, dtype=float)
        low = np.array(low, dtype=float)
        close = np.array(close, dtype=float)
        volume = np.array(volume, dtype=float)

        typical_price = (high + low + close) / 3

        vwap_values = []
        for i in range(len(typical_price)):
            if i < window - 1:
                vwap_values.append(None)
            else:
                window_tpv = typical_price[i - window + 1:i + 1]
                window_vol = volume[i - window + 1:i + 1]
                vwap = np.sum(window_tpv * window_vol) / np.sum(window_vol)
                vwap_values.append(float(vwap))

        return vwap_values

    @staticmethod
    def cci(
        high: list,
        low: list,
        close: list,
        period: int = 20
    ) -> Optional[float]:
        """Calculate Commodity Channel Index.

        CCI = (Typical Price - SMA of TP) / (0.015 * Mean Deviation)

        Typical Price (TP) = (High + Low + Close) / 3
        Mean Deviation = Sum(|TP - SMA(TP)|) / n

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            period: Number of periods (typically 20)

        Returns:
            CCI value or None if insufficient data
        """
        if not (len(high) == len(low) == len(close)):
            raise ValueError("All input lists must have the same length")

        if len(high) < period:
            return None

        high = np.array(high, dtype=float)
        low = np.array(low, dtype=float)
        close = np.array(close, dtype=float)

        # Calculate Typical Price
        tp = (high + low + close) / 3

        # Calculate SMA of Typical Price
        tp_sma = Indicator.sma(tp.tolist(), period)
        if tp_sma is None:
            return None

        # Calculate Mean Deviation
        recent_tp = tp[-period:]
        mean_deviation = np.mean(np.abs(recent_tp - tp_sma))

        if mean_deviation == 0:
            return 0.0

        # Calculate CCI
        cci = (tp[-1] - tp_sma) / (0.015 * mean_deviation)

        return float(cci)

    @staticmethod
    def bollinger_bands(
        data: list,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Optional[IndicatorResult]:
        """Calculate Bollinger Bands.

        Middle Band = SMA
        Upper Band = SMA + (std_dev * StdDev)
        Lower Band = SMA - (std_dev * StdDev)

        Args:
            data: List of closing prices
            period: Number of periods (typically 20)
            std_dev: Standard deviation multiplier (typically 2.0)

        Returns:
            IndicatorResult with middle, upper, and lower band values
        """
        data = Indicator._validate_data(data)
        if len(data) < period:
            return None

        # Calculate SMA (middle band)
        middle = Indicator.sma(data, period)
        if middle is None:
            return None

        # Calculate standard deviation
        recent_data = data[-period:]
        std = float(np.std(recent_data))

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return IndicatorResult(
            value=middle,
            upper=upper,
            lower=lower
        )

    @staticmethod
    def atr(
        high: list,
        low: list,
        close: list,
        period: int = 14
    ) -> Optional[float]:
        """Calculate Average True Range.

        TR = Max(High - Low, |High - Previous Close|, |Low - Previous Close|)
        ATR = SMA of TR

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            period: Number of periods (typically 14)

        Returns:
            ATR value or None if insufficient data
        """
        if not (len(high) == len(low) == len(close)):
            raise ValueError("All input lists must have the same length")

        if len(high) < period + 1:
            return None

        high = np.array(high, dtype=float)
        low = np.array(low, dtype=float)
        close = np.array(close, dtype=float)

        # Calculate True Range
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])

        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        # Calculate ATR using Wilder's smoothing
        atr = np.mean(tr[:period])
        for value in tr[period:]:
            atr = (atr * (period - 1) + value) / period

        return float(atr)

    @staticmethod
    def stochastic(
        high: list,
        low: list,
        close: list,
        k_period: int = 14,
        d_period: int = 3
    ) -> Optional[IndicatorResult]:
        """Calculate Stochastic Oscillator.

        %K = 100 * (Close - Lowest Low) / (Highest High - Lowest Low)
        %D = SMA of %K

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            k_period: %K period (typically 14)
            d_period: %D period (typically 3)

        Returns:
            IndicatorResult with %K and %D values
        """
        if not (len(high) == len(low) == len(close)):
            raise ValueError("All input lists must have the same length")

        if len(high) < k_period:
            return None

        high = np.array(high, dtype=float)
        low = np.array(low, dtype=float)
        close = np.array(close, dtype=float)

        # Calculate %K
        lowest_low = np.min(low[-k_period:])
        highest_high = np.max(high[-k_period:])

        if highest_high == lowest_low:
            k = 50.0
        else:
            k = 100 * (close[-1] - lowest_low) / (highest_high - lowest_low)

        # Calculate %D (SMA of %K)
        k_values = []
        for i in range(k_period - 1, len(close)):
            ll = np.min(low[i - k_period + 1:i + 1])
            hh = np.max(high[i - k_period + 1:i + 1])
            if hh != ll:
                k_val = 100 * (close[i] - ll) / (hh - ll)
            else:
                k_val = 50.0
            k_values.append(k_val)

        if len(k_values) < d_period:
            return IndicatorResult(value=k, signal=50.0)

        d = np.mean(k_values[-d_period:])

        return IndicatorResult(
            value=float(k),
            signal=float(d)
        )


class IndicatorCache:
    """Cache for storing indicator values to avoid recalculation."""

    def __init__(self):
        self._cache: dict = {}

    def get(self, key: str) -> Optional[float]:
        """Get cached value."""
        return self._cache.get(key)

    def set(self, key: str, value: float):
        """Set cached value."""
        self._cache[key] = value

    def clear(self):
        """Clear cache."""
        self._cache.clear()

    def calculate_indicators(
        self,
        data: dict,
        indicators: list[str]
    ) -> dict:
        """Calculate multiple indicators from price data.

        Args:
            data: Dictionary with 'high', 'low', 'close', 'volume' lists
            indicators: List of indicator names to calculate

        Returns:
            Dictionary of calculated indicator values
        """
        results = {}
        close = data.get('close', [])
        high = data.get('high', [])
        low = data.get('low', [])
        volume = data.get('volume', [])

        for indicator in indicators:
            indicator_lower = indicator.lower()

            if indicator_lower == 'sma':
                period = data.get('sma_period', 20)
                results['sma'] = Indicator.sma(close, period)

            elif indicator_lower == 'ema':
                period = data.get('ema_period', 20)
                results['ema'] = Indicator.ema(close, period)

            elif indicator_lower == 'rsi':
                period = data.get('rsi_period', 14)
                results['rsi'] = Indicator.rsi(close, period)

            elif indicator_lower == 'macd':
                result = Indicator.macd(close)
                if result:
                    results['macd'] = result.value
                    results['macd_signal'] = result.signal
                    results['macd_histogram'] = result.histogram

            elif indicator_lower == 'vwap':
                if high and low and volume:
                    results['vwap'] = Indicator.vwap(high, low, close, volume)

            elif indicator_lower == 'cci':
                period = data.get('cci_period', 20)
                results['cci'] = Indicator.cci(high, low, close, period)

            elif indicator_lower == 'bb' or indicator_lower == 'bollinger':
                result = Indicator.bollinger_bands(close)
                if result:
                    results['bb_middle'] = result.value
                    results['bb_upper'] = result.upper
                    results['bb_lower'] = result.lower

            elif indicator_lower == 'atr':
                period = data.get('atr_period', 14)
                results['atr'] = Indicator.atr(high, low, close, period)

        return results


# Example usage
if __name__ == "__main__":
    # Sample data
    sample_close = [
        100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
        110, 108, 111, 113, 112, 114, 116, 115, 117, 119,
        120, 118, 121, 123, 122, 124, 126, 125, 127, 129
    ]

    sample_high = [x + 2 for x in sample_close]
    sample_low = [x - 2 for x in sample_close]
    sample_volume = [1000] * len(sample_close)

    print("=== Technical Indicator Library Demo ===\n")

    # SMA
    sma_20 = Indicator.sma(sample_close, 20)
    print(f"SMA(20): {sma_20:.2f}")

    # EMA
    ema_20 = Indicator.ema(sample_close, 20)
    print(f"EMA(20): {ema_20:.2f}")

    # RSI
    rsi = Indicator.rsi(sample_close, 14)
    print(f"RSI(14): {rsi:.2f}")

    # MACD
    macd = Indicator.macd(sample_close)
    if macd:
        print(f"MACD: {macd.value:.2f}, Signal: {macd.signal:.2f}, Histogram: {macd.histogram:.2f}")

    # VWAP
    vwap = Indicator.vwap(sample_high, sample_low, sample_close, sample_volume)
    print(f"VWAP: {vwap:.2f}")

    # CCI
    cci = Indicator.cci(sample_high, sample_low, sample_close, 20)
    print(f"CCI(20): {cci:.2f}")

    # Bollinger Bands
    bb = Indicator.bollinger_bands(sample_close, 20, 2.0)
    if bb:
        print(f"Bollinger Bands: Upper={bb.upper:.2f}, Middle={bb.value:.2f}, Lower={bb.lower:.2f}")

    # ATR
    atr = Indicator.atr(sample_high, sample_low, sample_close, 14)
    print(f"ATR(14): {atr:.2f}")
