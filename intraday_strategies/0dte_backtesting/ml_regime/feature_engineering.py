"""
Feature Engineering for Market Regime Classification

Extracts relevant features for regime detection including:
- Technical indicators (EMAs, RSI, etc.)
- Volume patterns
- Volatility measures (HAR-RV)
- Market microstructure
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Extract features for regime classification"""
    
    def __init__(self):
        self.features = []
        
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        features = pd.DataFrame(index=df.index)
        
        # Price-based features
        features['returns'] = df['close'].pct_change()
        features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # EMAs
        features['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        features['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        features['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # EMA slopes (rate of change)
        features['ema_20_slope'] = features['ema_20'].pct_change(5)  # 5-period slope
        features['ema_50_slope'] = features['ema_50'].pct_change(10)
        features['ema_200_slope'] = features['ema_200'].pct_change(20)
        
        # EMA ribbon alignment
        features['ema_bullish'] = (
            (features['ema_20'] > features['ema_50']) & 
            (features['ema_50'] > features['ema_200'])
        ).astype(int)
        
        features['ema_bearish'] = (
            (features['ema_20'] < features['ema_50']) & 
            (features['ema_50'] < features['ema_200'])
        ).astype(int)
        
        # Price relative to EMAs
        features['price_to_ema20'] = (df['close'] - features['ema_20']) / features['ema_20']
        features['price_to_ema50'] = (df['close'] - features['ema_50']) / features['ema_50']
        features['price_to_ema200'] = (df['close'] - features['ema_200']) / features['ema_200']
        
        # RSI
        features['rsi'] = self._calculate_rsi(df['close'], period=14)
        features['rsi_slope'] = features['rsi'].diff(5)  # 5-period RSI change
        
        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        sma = df['close'].rolling(window=bb_period).mean()
        std = df['close'].rolling(window=bb_period).std()
        features['bb_upper'] = sma + (bb_std * std)
        features['bb_lower'] = sma - (bb_std * std)
        features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / sma
        features['bb_position'] = (df['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        return features
    
    def calculate_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volume-based features"""
        features = pd.DataFrame(index=df.index)
        
        # Basic volume features
        features['volume'] = df['volume']
        features['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        features['volume_ratio'] = df['volume'] / features['volume_sma_20']
        
        # Volume-price features
        features['dollar_volume'] = df['volume'] * df['close']
        features['volume_price_trend'] = (
            (df['close'].diff() * df['volume']).cumsum()
        )
        
        # On-Balance Volume (OBV)
        obv = pd.Series(index=df.index, dtype=float)
        obv.iloc[0] = 0
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        features['obv'] = obv
        features['obv_sma'] = obv.rolling(window=20).mean()
        features['obv_divergence'] = (obv - features['obv_sma']) / features['obv_sma']
        
        # Volume at price levels
        features['volume_up'] = df.loc[df['close'] > df['open'], 'volume'].reindex(df.index).fillna(0)
        features['volume_down'] = df.loc[df['close'] <= df['open'], 'volume'].reindex(df.index).fillna(0)
        features['volume_delta'] = features['volume_up'] - features['volume_down']
        
        return features
    
    def calculate_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volatility features including HAR-RV"""
        features = pd.DataFrame(index=df.index)
        
        # Realized volatility
        returns = df['close'].pct_change()
        
        # Different time horizons for volatility
        features['rv_5min'] = returns.rolling(window=1).std() * np.sqrt(252 * 78)  # 78 5-min bars per day
        features['rv_hourly'] = returns.rolling(window=12).std() * np.sqrt(252 * 6.5)  # 6.5 hours per day
        features['rv_daily'] = returns.rolling(window=78).std() * np.sqrt(252)
        
        # HAR-RV components (Heterogeneous Autoregressive Realized Volatility)
        # Daily RV (using 5-minute returns)
        daily_rv = returns.rolling(window=78).std() * np.sqrt(252)
        
        # Weekly RV (5-day average of daily RV)
        weekly_rv = daily_rv.rolling(window=5*78).mean()
        
        # Monthly RV (22-day average of daily RV)
        monthly_rv = daily_rv.rolling(window=22*78).mean()
        
        features['har_daily'] = daily_rv
        features['har_weekly'] = weekly_rv
        features['har_monthly'] = monthly_rv
        
        # HAR-RV forecast (simple weighted average)
        features['har_forecast'] = (
            0.3 * features['har_daily'] + 
            0.4 * features['har_weekly'] + 
            0.3 * features['har_monthly']
        )
        
        # Volatility regime
        vol_median = features['rv_daily'].rolling(window=20*78).median()
        features['high_vol_regime'] = (features['rv_daily'] > vol_median * 1.5).astype(int)
        features['low_vol_regime'] = (features['rv_daily'] < vol_median * 0.7).astype(int)
        
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        features['atr'] = true_range.rolling(window=14).mean()
        features['atr_ratio'] = features['atr'] / df['close']
        
        return features
    
    def calculate_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate market microstructure features"""
        features = pd.DataFrame(index=df.index)
        
        # Spread-related features
        features['spread'] = df['high'] - df['low']
        features['spread_pct'] = features['spread'] / df['close']
        features['avg_spread'] = features['spread_pct'].rolling(window=20).mean()
        
        # Price efficiency
        features['efficiency_ratio'] = abs(
            df['close'].diff(20)
        ) / (
            abs(df['close'].diff()).rolling(window=20).sum()
        )
        
        # Tick direction
        features['tick_direction'] = np.sign(df['close'].diff())
        features['tick_momentum'] = features['tick_direction'].rolling(window=10).sum()
        
        # High-low position
        features['hl_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        features['hl_position_ma'] = features['hl_position'].rolling(window=20).mean()
        
        # Open interest proxy (using volume patterns)
        features['volume_momentum'] = df['volume'].pct_change(10)
        features['price_volume_corr'] = (
            df['close'].pct_change().rolling(window=20).corr(df['volume'].pct_change())
        )
        
        return features
    
    def calculate_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate time-based features"""
        features = pd.DataFrame(index=df.index)
        
        # Extract time components
        if isinstance(df.index, pd.DatetimeIndex):
            features['hour'] = df.index.hour
            features['minute'] = df.index.minute
            features['day_of_week'] = df.index.dayofweek
        else:
            # Assume 'date' column exists
            dt_index = pd.to_datetime(df['date'])
            features['hour'] = dt_index.dt.hour
            features['minute'] = dt_index.dt.minute
            features['day_of_week'] = dt_index.dt.dayofweek
        
        # Time of day features
        features['morning_session'] = ((features['hour'] >= 9) & (features['hour'] < 12)).astype(int)
        features['afternoon_session'] = ((features['hour'] >= 12) & (features['hour'] < 15)).astype(int)
        features['closing_hour'] = (features['hour'] >= 15).astype(int)
        
        # Opening range period
        features['opening_5min'] = ((features['hour'] == 9) & (features['minute'] < 35)).astype(int)
        features['opening_15min'] = ((features['hour'] == 9) & (features['minute'] < 45)).astype(int)
        features['opening_30min'] = ((features['hour'] == 9) | ((features['hour'] == 10) & (features['minute'] < 30))).astype(int)
        
        return features
    
    def extract_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract all features for regime classification"""
        logger.info("Extracting features for regime classification...")
        
        # Calculate all feature groups
        tech_features = self.calculate_technical_indicators(df)
        vol_features = self.calculate_volume_features(df)
        volatility_features = self.calculate_volatility_features(df)
        micro_features = self.calculate_microstructure_features(df)
        time_features = self.calculate_time_features(df)
        
        # Combine all features
        all_features = pd.concat([
            tech_features,
            vol_features,
            volatility_features,
            micro_features,
            time_features
        ], axis=1)
        
        # Add some interaction features
        all_features['rsi_volume_interaction'] = all_features['rsi'] * all_features['volume_ratio']
        all_features['volatility_volume'] = all_features['rv_daily'] * all_features['volume_ratio']
        all_features['trend_strength'] = all_features['ema_20_slope'] * all_features['volume_momentum']
        
        # Store feature names
        self.features = all_features.columns.tolist()
        
        # Handle any infinities or NaNs
        all_features = all_features.replace([np.inf, -np.inf], np.nan)
        
        logger.info(f"Extracted {len(self.features)} features")
        
        return all_features
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI (Relative Strength Index)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_feature_names(self) -> list:
        """Get list of feature names"""
        return self.features