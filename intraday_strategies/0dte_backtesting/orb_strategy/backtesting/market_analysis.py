"""
Market Analysis Module for ORB Backtesting
Provides technical indicators and market regime analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """
    Analyze market conditions and technical indicators
    """
    
    def __init__(self, spy_data: pd.DataFrame):
        """
        Initialize with SPY data
        
        Args:
            spy_data: DataFrame with OHLCV data
        """
        self.spy_data = spy_data
        self.daily_data = self._prepare_daily_data()
        self._calculate_indicators()
        
    def _prepare_daily_data(self) -> pd.DataFrame:
        """Convert intraday to daily data"""
        daily = self.spy_data.resample('D').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        return daily
    
    def _calculate_indicators(self):
        """Calculate all technical indicators"""
        
        # Moving Averages
        self.daily_data['SMA_20'] = self.daily_data['close'].rolling(window=20).mean()
        self.daily_data['SMA_50'] = self.daily_data['close'].rolling(window=50).mean()
        self.daily_data['SMA_200'] = self.daily_data['close'].rolling(window=200).mean()
        
        # Exponential Moving Averages
        self.daily_data['EMA_20'] = self.daily_data['close'].ewm(span=20, adjust=False).mean()
        self.daily_data['EMA_50'] = self.daily_data['close'].ewm(span=50, adjust=False).mean()
        self.daily_data['EMA_200'] = self.daily_data['close'].ewm(span=200, adjust=False).mean()
        
        # ATR (Average True Range)
        high_low = self.daily_data['high'] - self.daily_data['low']
        high_close = np.abs(self.daily_data['high'] - self.daily_data['close'].shift())
        low_close = np.abs(self.daily_data['low'] - self.daily_data['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.daily_data['ATR_14'] = true_range.rolling(window=14).mean()
        self.daily_data['ATR_pct'] = (self.daily_data['ATR_14'] / self.daily_data['close']) * 100
        
        # Historical Volatility
        self.daily_data['returns'] = self.daily_data['close'].pct_change()
        self.daily_data['HV_10'] = self.daily_data['returns'].rolling(window=10).std() * np.sqrt(252) * 100
        self.daily_data['HV_20'] = self.daily_data['returns'].rolling(window=20).std() * np.sqrt(252) * 100
        self.daily_data['HV_30'] = self.daily_data['returns'].rolling(window=30).std() * np.sqrt(252) * 100
        
        # Market Position
        self.daily_data['above_EMA20'] = self.daily_data['close'] > self.daily_data['EMA_20']
        self.daily_data['above_EMA50'] = self.daily_data['close'] > self.daily_data['EMA_50']
        self.daily_data['above_EMA200'] = self.daily_data['close'] > self.daily_data['EMA_200']
        
        # Trend Strength (distance from EMAs)
        self.daily_data['dist_EMA20_pct'] = ((self.daily_data['close'] - self.daily_data['EMA_20']) / 
                                              self.daily_data['EMA_20']) * 100
        self.daily_data['dist_EMA50_pct'] = ((self.daily_data['close'] - self.daily_data['EMA_50']) / 
                                              self.daily_data['EMA_50']) * 100
        
        # Market Regime Classification
        self.daily_data['regime'] = self._classify_regime()
        
        # Volatility Regime
        self.daily_data['vol_regime'] = self._classify_volatility()
        
        logger.info(f"Calculated indicators for {len(self.daily_data)} days")
    
    def _classify_regime(self) -> pd.Series:
        """Classify market regime based on EMAs"""
        conditions = []
        
        # Strong Uptrend: Above all EMAs
        strong_up = (self.daily_data['above_EMA20'] & 
                    self.daily_data['above_EMA50'] & 
                    self.daily_data['above_EMA200'])
        
        # Uptrend: Above 20 and 50
        uptrend = (self.daily_data['above_EMA20'] & 
                  self.daily_data['above_EMA50'] & 
                  ~self.daily_data['above_EMA200'])
        
        # Neutral: Mixed signals
        neutral = (self.daily_data['above_EMA20'] & 
                  ~self.daily_data['above_EMA50'])
        
        # Downtrend: Below 20 and 50
        downtrend = (~self.daily_data['above_EMA20'] & 
                    ~self.daily_data['above_EMA50'] & 
                    self.daily_data['above_EMA200'])
        
        # Strong Downtrend: Below all EMAs
        strong_down = (~self.daily_data['above_EMA20'] & 
                      ~self.daily_data['above_EMA50'] & 
                      ~self.daily_data['above_EMA200'])
        
        regime = pd.Series('Neutral', index=self.daily_data.index)
        regime[strong_up] = 'Strong Uptrend'
        regime[uptrend] = 'Uptrend'
        regime[downtrend] = 'Downtrend'
        regime[strong_down] = 'Strong Downtrend'
        regime[neutral] = 'Neutral'
        
        return regime
    
    def _classify_volatility(self) -> pd.Series:
        """Classify volatility regime"""
        # Use percentiles for classification
        hv20 = self.daily_data['HV_20']
        
        # Calculate rolling percentiles
        low_threshold = hv20.rolling(window=60).quantile(0.25)
        high_threshold = hv20.rolling(window=60).quantile(0.75)
        
        vol_regime = pd.Series('Normal', index=self.daily_data.index)
        vol_regime[hv20 < low_threshold] = 'Low'
        vol_regime[hv20 > high_threshold] = 'High'
        
        return vol_regime
    
    def get_market_conditions(self, date: datetime) -> Dict:
        """
        Get market conditions for a specific date
        
        Args:
            date: Date to analyze
            
        Returns:
            Dict with market conditions
        """
        # Convert to date only for matching
        date_only = pd.Timestamp(date).date()
        
        # Find matching day
        mask = self.daily_data.index.date == date_only
        
        if not mask.any():
            return None
        
        day_data = self.daily_data[mask].iloc[0]
        
        return {
            'date': date,
            'close': day_data['close'],
            'EMA_20': day_data['EMA_20'],
            'EMA_50': day_data['EMA_50'],
            'EMA_200': day_data['EMA_200'],
            'above_EMA20': day_data['above_EMA20'],
            'above_EMA50': day_data['above_EMA50'],
            'above_EMA200': day_data['above_EMA200'],
            'ATR': day_data['ATR_14'],
            'ATR_pct': day_data['ATR_pct'],
            'HV_10': day_data['HV_10'],
            'HV_20': day_data['HV_20'],
            'HV_30': day_data['HV_30'],
            'regime': day_data['regime'],
            'vol_regime': day_data['vol_regime'],
            'dist_EMA20_pct': day_data['dist_EMA20_pct'],
            'dist_EMA50_pct': day_data['dist_EMA50_pct']
        }
    
    def analyze_trade_conditions(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """
        Add market conditions to trades DataFrame
        
        Args:
            trades_df: DataFrame with trade results (must have 'date' column)
            
        Returns:
            Enhanced DataFrame with market conditions
        """
        # Add market conditions for each trade
        conditions = []
        
        for idx, trade in trades_df.iterrows():
            trade_conditions = self.get_market_conditions(trade['date'])
            
            if trade_conditions:
                # Merge trade data with conditions
                combined = {**trade.to_dict(), **trade_conditions}
                conditions.append(combined)
            else:
                conditions.append(trade.to_dict())
        
        enhanced_df = pd.DataFrame(conditions)
        
        # Add trade outcome classification
        enhanced_df['outcome'] = enhanced_df['net_pnl'].apply(
            lambda x: 'Win' if x > 0 else 'Loss'
        )
        
        return enhanced_df
    
    def generate_statistics(self, enhanced_trades: pd.DataFrame) -> Dict:
        """
        Generate statistics about market conditions and trade outcomes
        
        Args:
            enhanced_trades: DataFrame with trades and market conditions
            
        Returns:
            Dict with statistics
        """
        stats = {}
        
        # Overall statistics
        wins = enhanced_trades[enhanced_trades['outcome'] == 'Win']
        losses = enhanced_trades[enhanced_trades['outcome'] == 'Loss']
        
        stats['overall'] = {
            'total_trades': len(enhanced_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(enhanced_trades) * 100 if len(enhanced_trades) > 0 else 0
        }
        
        # Statistics by market regime
        stats['by_regime'] = {}
        for regime in enhanced_trades['regime'].unique():
            if pd.notna(regime):
                regime_trades = enhanced_trades[enhanced_trades['regime'] == regime]
                regime_wins = regime_trades[regime_trades['outcome'] == 'Win']
                
                stats['by_regime'][regime] = {
                    'trades': len(regime_trades),
                    'wins': len(regime_wins),
                    'win_rate': len(regime_wins) / len(regime_trades) * 100 if len(regime_trades) > 0 else 0,
                    'avg_pnl': regime_trades['net_pnl'].mean()
                }
        
        # Statistics by volatility regime
        stats['by_vol_regime'] = {}
        for vol_regime in enhanced_trades['vol_regime'].unique():
            if pd.notna(vol_regime):
                vol_trades = enhanced_trades[enhanced_trades['vol_regime'] == vol_regime]
                vol_wins = vol_trades[vol_trades['outcome'] == 'Win']
                
                stats['by_vol_regime'][vol_regime] = {
                    'trades': len(vol_trades),
                    'wins': len(vol_wins),
                    'win_rate': len(vol_wins) / len(vol_trades) * 100 if len(vol_trades) > 0 else 0,
                    'avg_pnl': vol_trades['net_pnl'].mean()
                }
        
        # EMA position statistics
        stats['ema_position'] = {
            'losses_below_ema20': len(losses[losses['above_EMA20'] == False]) if 'above_EMA20' in losses.columns else 0,
            'losses_below_ema50': len(losses[losses['above_EMA50'] == False]) if 'above_EMA50' in losses.columns else 0,
            'wins_below_ema20': len(wins[wins['above_EMA20'] == False]) if 'above_EMA20' in wins.columns else 0,
            'wins_below_ema50': len(wins[wins['above_EMA50'] == False]) if 'above_EMA50' in wins.columns else 0
        }
        
        # Volatility statistics
        if 'HV_20' in enhanced_trades.columns:
            stats['volatility'] = {
                'avg_hv20_wins': wins['HV_20'].mean() if len(wins) > 0 else 0,
                'avg_hv20_losses': losses['HV_20'].mean() if len(losses) > 0 else 0,
                'avg_atr_pct_wins': wins['ATR_pct'].mean() if len(wins) > 0 else 0,
                'avg_atr_pct_losses': losses['ATR_pct'].mean() if len(losses) > 0 else 0
            }
        
        return stats
    
    def suggest_filters(self, enhanced_trades: pd.DataFrame) -> Dict:
        """
        Test various filters and suggest improvements
        
        Args:
            enhanced_trades: DataFrame with trades and market conditions
            
        Returns:
            Dict with filter test results
        """
        filters = {}
        
        # Original baseline
        original_stats = {
            'trades': len(enhanced_trades),
            'win_rate': (enhanced_trades['net_pnl'] > 0).mean() * 100,
            'total_pnl': enhanced_trades['net_pnl'].sum(),
            'avg_pnl': enhanced_trades['net_pnl'].mean()
        }
        filters['original'] = original_stats
        
        # Test: Trade only above EMA 20
        if 'above_EMA20' in enhanced_trades.columns:
            filtered = enhanced_trades[enhanced_trades['above_EMA20'] == True]
            filters['above_ema20'] = {
                'trades': len(filtered),
                'win_rate': (filtered['net_pnl'] > 0).mean() * 100 if len(filtered) > 0 else 0,
                'total_pnl': filtered['net_pnl'].sum() if len(filtered) > 0 else 0,
                'avg_pnl': filtered['net_pnl'].mean() if len(filtered) > 0 else 0
            }
        
        # Test: Trade only in uptrends
        if 'regime' in enhanced_trades.columns:
            filtered = enhanced_trades[enhanced_trades['regime'].isin(['Uptrend', 'Strong Uptrend'])]
            filters['uptrend_only'] = {
                'trades': len(filtered),
                'win_rate': (filtered['net_pnl'] > 0).mean() * 100 if len(filtered) > 0 else 0,
                'total_pnl': filtered['net_pnl'].sum() if len(filtered) > 0 else 0,
                'avg_pnl': filtered['net_pnl'].mean() if len(filtered) > 0 else 0
            }
        
        # Test: Avoid high volatility
        if 'vol_regime' in enhanced_trades.columns:
            filtered = enhanced_trades[enhanced_trades['vol_regime'] != 'High']
            filters['avoid_high_vol'] = {
                'trades': len(filtered),
                'win_rate': (filtered['net_pnl'] > 0).mean() * 100 if len(filtered) > 0 else 0,
                'total_pnl': filtered['net_pnl'].sum() if len(filtered) > 0 else 0,
                'avg_pnl': filtered['net_pnl'].mean() if len(filtered) > 0 else 0
            }
        
        # Test: Low volatility only
        if 'HV_20' in enhanced_trades.columns:
            threshold = enhanced_trades['HV_20'].quantile(0.5)
            filtered = enhanced_trades[enhanced_trades['HV_20'] < threshold]
            filters['low_vol_only'] = {
                'trades': len(filtered),
                'win_rate': (filtered['net_pnl'] > 0).mean() * 100 if len(filtered) > 0 else 0,
                'total_pnl': filtered['net_pnl'].sum() if len(filtered) > 0 else 0,
                'avg_pnl': filtered['net_pnl'].mean() if len(filtered) > 0 else 0
            }
        
        return filters
    
    def analyze_direction_by_regime(self, trades_df: pd.DataFrame) -> Dict:
        """
        Analyze how trade direction varies by market regime
        
        Args:
            trades_df: DataFrame with trades and market conditions
            
        Returns:
            Dict with direction analysis by regime
        """
        # Ensure we have enhanced trades with market data
        if 'regime' not in trades_df.columns:
            trades_df = self.analyze_trade_conditions(trades_df)
        
        direction_analysis = {
            'overall': {},
            'by_regime': {},
            'by_momentum': {},
            'correlation': {},
            'insights': []
        }
        
        # Overall direction split
        if 'direction' in trades_df.columns:
            bullish_count = len(trades_df[trades_df['direction'] == 'BULLISH'])
            bearish_count = len(trades_df[trades_df['direction'] == 'BEARISH'])
            total = len(trades_df)
            
            direction_analysis['overall'] = {
                'bullish_count': bullish_count,
                'bearish_count': bearish_count,
                'bullish_pct': bullish_count / total * 100 if total > 0 else 0,
                'bearish_pct': bearish_count / total * 100 if total > 0 else 0
            }
        
        # Direction by market regime
        if 'regime' in trades_df.columns:
            for regime in trades_df['regime'].unique():
                if pd.notna(regime):
                    regime_trades = trades_df[trades_df['regime'] == regime]
                    
                    if len(regime_trades) > 0:
                        bullish = len(regime_trades[regime_trades['direction'] == 'BULLISH'])
                        bearish = len(regime_trades[regime_trades['direction'] == 'BEARISH'])
                        total = len(regime_trades)
                        
                        # Calculate win rates
                        bullish_wins = len(regime_trades[(regime_trades['direction'] == 'BULLISH') & 
                                                        (regime_trades['net_pnl'] > 0)])
                        bearish_wins = len(regime_trades[(regime_trades['direction'] == 'BEARISH') & 
                                                        (regime_trades['net_pnl'] > 0)])
                        
                        direction_analysis['by_regime'][regime] = {
                            'total_trades': total,
                            'bullish_count': bullish,
                            'bearish_count': bearish,
                            'bullish_pct': bullish / total * 100 if total > 0 else 0,
                            'bearish_pct': bearish / total * 100 if total > 0 else 0,
                            'bullish_win_rate': bullish_wins / bullish * 100 if bullish > 0 else 0,
                            'bearish_win_rate': bearish_wins / bearish * 100 if bearish > 0 else 0,
                            'total_pnl': regime_trades['net_pnl'].sum(),
                            'avg_pnl': regime_trades['net_pnl'].mean()
                        }
        
        # Calculate correlation between trend and direction
        if 'dist_EMA20_pct' in trades_df.columns:
            trades_df['is_bullish'] = (trades_df['direction'] == 'BULLISH').astype(int)
            
            # Correlation with distance from EMAs
            corr_ema20 = trades_df[['dist_EMA20_pct', 'is_bullish']].corr().iloc[0, 1]
            corr_ema50 = trades_df[['dist_EMA50_pct', 'is_bullish']].corr().iloc[0, 1] if 'dist_EMA50_pct' in trades_df.columns else 0
            
            direction_analysis['correlation'] = {
                'ema20_correlation': corr_ema20,
                'ema50_correlation': corr_ema50,
                'interpretation': self._interpret_correlation(corr_ema20)
            }
        
        # Generate insights
        if direction_analysis['correlation'].get('ema20_correlation'):
            corr = abs(direction_analysis['correlation']['ema20_correlation'])
            if corr < 0.3:
                direction_analysis['insights'].append(
                    "✓ Direction is INDEPENDENT of trend (correlation < 0.3)"
                )
                direction_analysis['insights'].append(
                    "✓ ORB captures intraday momentum, not multi-day trends"
                )
            else:
                direction_analysis['insights'].append(
                    "⚠ Some correlation between trend and direction"
                )
        
        # Check if strategy works in all regimes
        if direction_analysis['by_regime']:
            all_profitable = all(
                data['avg_pnl'] > 0 
                for data in direction_analysis['by_regime'].values()
            )
            
            if all_profitable:
                direction_analysis['insights'].append(
                    "✓ Strategy is PROFITABLE in ALL market regimes"
                )
                direction_analysis['insights'].append(
                    "✓ No need to filter trades by market condition"
                )
        
        return direction_analysis
    
    def _interpret_correlation(self, correlation: float) -> str:
        """Interpret correlation value"""
        abs_corr = abs(correlation)
        
        if abs_corr < 0.1:
            return "No correlation - direction is random relative to trend"
        elif abs_corr < 0.3:
            return "Weak correlation - direction mostly independent of trend"
        elif abs_corr < 0.5:
            return "Moderate correlation - some trend influence on direction"
        elif abs_corr < 0.7:
            return "Strong correlation - trend influences direction"
        else:
            return "Very strong correlation - direction follows trend"