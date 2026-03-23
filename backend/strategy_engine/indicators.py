"""Technical indicators for trading strategies."""
import math
from typing import Optional
import pandas as pd
import numpy as np


def sma(data: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return data.rolling(window=period).mean()


def ema(data: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return data.ewm(span=period, adjust=False).mean()


def rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def macd(
    data: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD (Moving Average Convergence Divergence).
    
    Returns:
        tuple: (macd_line, signal_line, histogram)
    """
    fast_ema = ema(data, fast_period)
    slow_ema = ema(data, slow_period)
    
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def bollinger_bands(
    data: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands.
    
    Returns:
        tuple: (upper_band, middle_band, lower_band)
    """
    middle_band = sma(data, period)
    std = data.rolling(window=period).std()
    
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    
    return upper_band, middle_band, lower_band


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Volume Weighted Average Price."""
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> tuple[pd.Series, pd.Series]:
    """Stochastic Oscillator.
    
    Returns:
        tuple: (%K, %D)
    """
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=3).mean()
    
    return k_percent, d_percent


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index."""
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = atr(high, low, close, period=1)
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    tp = (high + low + close) / 3
    sma_tp = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    
    cci = (tp - sma_tp) / (0.015 * mad)
    
    return cci


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Williams %R."""
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    
    williams = -100 * ((highest_high - close) / (highest_high - lowest_low))
    
    return williams


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    obv = pd.Series(index=close.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]
    
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif close.iloc[i] < close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    """Money Flow Index."""
    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume
    
    money_flow_sign = pd.Series(index=typical_price.index, dtype=float)
    for i in range(1, len(typical_price)):
        if typical_price.iloc[i] > typical_price.iloc[i-1]:
            money_flow_sign.iloc[i] = 1
        elif typical_price.iloc[i] < typical_price.iloc[i-1]:
            money_flow_sign.iloc[i] = -1
        else:
            money_flow_sign.iloc[i] = 0
    
    positive_flow = raw_money_flow * money_flow_sign.apply(lambda x: max(x, 0))
    negative_flow = raw_money_flow * money_flow_sign.apply(lambda x: max(-x, 0))
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + positive_mf / negative_mf))
    
    return mfi


def ichimoku(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series
) -> dict[str, pd.Series]:
    """Ichimoku Cloud.
    
    Returns:
        dict: {'tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b', 'chikou_span'}
    """
    nine_period = 9
    twenty_six_period = 26
    fifty_two_period = 52
    
    tenkan_sen = (high.rolling(window=nine_period).max() + low.rolling(window=nine_period).min()) / 2
    kijun_sen = (high.rolling(window=twenty_six_period).max() + low.rolling(window=twenty_six_period).min()) / 2
    
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(twenty_six_period)
    
    senkou_span_b = ((high.rolling(window=fifty_two_period).max() + low.rolling(window=fifty_two_period).min()) / 2).shift(twenty_six_period)
    
    chikou_span = close.shift(-twenty_six_period)
    
    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_span_a": senkou_span_a,
        "senkou_span_b": senkou_span_b,
        "chikou_span": chikou_span,
    }


def calculate_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate all common technical indicators.
    
    Args:
        data: DataFrame with 'high', 'low', 'close', 'volume' columns
    
    Returns:
        DataFrame with added indicator columns
    """
    result = data.copy()
    
    result["sma_20"] = sma(result["close"], 20)
    result["sma_50"] = sma(result["close"], 50)
    result["sma_200"] = sma(result["close"], 200)
    
    result["ema_12"] = ema(result["close"], 12)
    result["ema_26"] = ema(result["close"], 26)
    
    result["rsi"] = rsi(result["close"])
    
    macd_line, signal_line, histogram = macd(result["close"])
    result["macd"] = macd_line
    result["macd_signal"] = signal_line
    result["macd_histogram"] = histogram
    
    bb_upper, bb_middle, bb_lower = bollinger_bands(result["close"])
    result["bb_upper"] = bb_upper
    result["bb_middle"] = bb_middle
    result["bb_lower"] = bb_lower
    
    result["vwap"] = vwap(result["high"], result["low"], result["close"], result["volume"])
    
    result["atr"] = atr(result["high"], result["low"], result["close"])
    
    result["adx"] = adx(result["high"], result["low"], result["close"])
    
    return result
