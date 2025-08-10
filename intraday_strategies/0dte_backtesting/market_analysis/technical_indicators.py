import pandas as pd
import numpy as np
from typing import Tuple, Optional
try:
    from configuration.performance_cache import cached_indicator
except ImportError:
    # Cache manager not available, create dummy decorator
    def cached_indicator(name):
        def decorator(func):
            return func
        return decorator


@cached_indicator("sma")
def sma(data: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average (cached)"""
    return data.rolling(window=period).mean()


@cached_indicator("ema")
def ema(data: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average (cached)"""
    return data.ewm(span=period, adjust=False).mean()


@cached_indicator("rsi")
def rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (cached)
    Returns values between 0-100
    Oversold < 30, Overbought > 70
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence)
    Returns: (macd_line, signal_line, histogram)
    """
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands
    Returns: (upper_band, middle_band, lower_band)
    """
    middle_band = sma(data, period)
    std = data.rolling(window=period).std()
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    return upper_band, middle_band, lower_band


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average True Range - Volatility indicator
    """
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator
    Returns: (k_line, d_line)
    Oversold < 20, Overbought > 80
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k_line = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_line = k_line.rolling(window=d_period).mean()
    return k_line, d_line


def vwap(price: pd.Series, volume: pd.Series, reset_daily: bool = True) -> pd.Series:
    """
    Volume Weighted Average Price
    """
    if reset_daily and hasattr(price.index, 'date'):
        # Group by date for daily VWAP reset
        df = pd.DataFrame({'price': price, 'volume': volume})
        df['date'] = price.index.date
        df['pv'] = df['price'] * df['volume']
        df['cumvol'] = df.groupby('date')['volume'].cumsum()
        df['cumpv'] = df.groupby('date')['pv'].cumsum()
        return df['cumpv'] / df['cumvol']
    else:
        # Continuous VWAP
        return (price * volume).cumsum() / volume.cumsum()


def pivot_points(high: pd.Series, low: pd.Series, close: pd.Series) -> dict:
    """
    Calculate Pivot Points (support/resistance levels)
    Returns dict with: pivot, r1, r2, r3, s1, s2, s3
    """
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)
    
    return {
        'pivot': pivot,
        'r1': r1, 'r2': r2, 'r3': r3,
        's1': s1, 's2': s2, 's3': s3
    }


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    On Balance Volume - Volume indicator
    """
    obv = volume.copy()
    obv[close < close.shift()] *= -1
    obv[close == close.shift()] = 0
    return obv.cumsum()


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Williams %R - Momentum indicator
    Returns values between -100 and 0
    Oversold < -80, Overbought > -20
    """
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    wr = -100 * ((highest_high - close) / (highest_high - lowest_low))
    return wr


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """
    Commodity Channel Index
    Overbought > 100, Oversold < -100
    """
    typical_price = (high + low + close) / 3
    sma_tp = typical_price.rolling(window=period).mean()
    mean_dev = typical_price.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    cci = (typical_price - sma_tp) / (0.015 * mean_dev)
    return cci


def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    """
    Money Flow Index - Volume-weighted RSI
    Returns values between 0-100
    """
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(), 0)
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + positive_mf / negative_mf))
    return mfi


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average Directional Index - Trend strength indicator
    Values > 25 indicate strong trend
    """
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = atr(high, low, close, 1)
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())
    minus_di = 100 * (abs(minus_dm).rolling(window=period).mean() / tr.rolling(window=period).mean())
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx


# Backtesting helper functions
def calculate_returns(entry_prices: pd.Series, exit_prices: pd.Series, 
                     position_type: str = 'long') -> pd.Series:
    """Calculate returns for trades"""
    if position_type == 'long':
        returns = (exit_prices - entry_prices) / entry_prices
    else:  # short
        returns = (entry_prices - exit_prices) / entry_prices
    return returns


def calculate_sharpe_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Calculate Sharpe ratio"""
    if len(returns) == 0:
        return 0
    mean_return = returns.mean()
    std_return = returns.std()
    if std_return == 0:
        return 0
    return np.sqrt(periods_per_year) * mean_return / std_return


def calculate_max_drawdown(cumulative_returns: pd.Series) -> float:
    """Calculate maximum drawdown"""
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    return drawdown.min()


def calculate_win_rate(returns: pd.Series) -> float:
    """Calculate win rate"""
    if len(returns) == 0:
        return 0
    return (returns > 0).sum() / len(returns)


def calculate_profit_factor(returns: pd.Series) -> float:
    """Calculate profit factor"""
    gains = returns[returns > 0].sum()
    losses = abs(returns[returns < 0].sum())
    if losses == 0:
        return float('inf') if gains > 0 else 0
    return gains / losses


def calculate_daily_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate ADX on daily timeframe from minute data
    
    Args:
        df: DataFrame with minute OHLC data (must have 'high', 'low', 'close' columns)
        period: ADX period (default 14 days)
    
    Returns:
        DataFrame with daily ADX values mapped back to minute data
    """
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # Store whether we had date as column originally
    had_date_column = 'date' in df.columns
    
    # Ensure we have a datetime index
    if 'date' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index('date')
    elif not isinstance(df.index, pd.DatetimeIndex) and 'date' not in df.columns:
        # No date column and no datetime index - can't proceed
        raise ValueError("DataFrame must have either a 'date' column or a DatetimeIndex")
    
    # Aggregate to daily OHLC
    daily_df = df.resample('D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # Calculate ADX on daily data
    daily_df['ADX'] = adx(daily_df['high'], daily_df['low'], daily_df['close'], period=period)
    
    # Map daily ADX back to minute data
    # Create a date column for merging
    df['date_only'] = df.index.date
    daily_df['date_only'] = daily_df.index.date
    
    # Merge daily ADX with minute data
    df = df.merge(
        daily_df[['date_only', 'ADX']].rename(columns={'ADX': 'daily_ADX'}),
        on='date_only',
        how='left'
    )
    
    # Forward fill ADX values (same ADX for entire day)
    df['daily_ADX'] = df['daily_ADX'].fillna(method='ffill')
    
    # Drop helper column
    df = df.drop('date_only', axis=1)
    
    # If we originally had date as a column, reset index to restore it
    if had_date_column:
        df = df.reset_index()
    
    return df