"""
Backtest Results Management System
Handles saving, loading, and analyzing backtest results
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BacktestResults:
    """Manages backtest results storage and retrieval"""
    
    def __init__(self, strategy: str, params: Dict, trades_df: pd.DataFrame, 
                 market_df: pd.DataFrame, base_dir: str = "backtest_results"):
        self.strategy = strategy
        self.params = params
        self.trades_df = trades_df
        self.market_df = market_df
        self.base_dir = base_dir
        
        # Create unique ID for this backtest
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_clean = strategy.replace(" ", "_").lower()
        self.backtest_id = f"{timestamp}_{strategy_clean}"
        self.save_path = os.path.join(base_dir, self.backtest_id)
        
        # Ensure directory exists
        os.makedirs(self.save_path, exist_ok=True)
        
        # Results containers
        self.daily_df = None
        self.summary_stats = {}
        
    def save_all(self) -> str:
        """Save all backtest data and return the save path"""
        try:
            # Save configuration
            logger.info(f"Saving config to {self.save_path}")
            self._save_config()
            
            # Save enhanced trades data (already created in UI)
            try:
                trades_path = os.path.join(self.save_path, "trades_enhanced.csv")
                logger.info(f"Saving {len(self.trades_df)} trades to {trades_path}")
                self.trades_df.to_csv(trades_path, index=False)
            except Exception as e:
                logger.error(f"Error saving trades data: {e}")
                raise
            
            # Create and save daily time series
            try:
                logger.info("Creating daily timeseries...")
                self.daily_df = self._create_daily_timeseries()
                daily_path = os.path.join(self.save_path, "daily_timeseries.csv")
                logger.info(f"Saving {len(self.daily_df)} days to {daily_path}")
                self.daily_df.to_csv(daily_path, index=False)
            except Exception as e:
                logger.error(f"Error creating/saving daily timeseries: {e}")
                # Save empty DataFrame to prevent load errors
                self.daily_df = pd.DataFrame()
                daily_path = os.path.join(self.save_path, "daily_timeseries.csv")
                self.daily_df.to_csv(daily_path, index=False)
            
            # Calculate and save summary statistics
            try:
                logger.info("Calculating summary statistics...")
                self.summary_stats = self._calculate_summary_stats()
                summary_path = os.path.join(self.save_path, "summary_stats.json")
                with open(summary_path, 'w') as f:
                    json.dump(self.summary_stats, f, indent=2, default=str)
            except Exception as e:
                logger.error(f"Error calculating/saving summary stats: {e}")
                self.summary_stats = {"error": str(e)}
                summary_path = os.path.join(self.save_path, "summary_stats.json")
                with open(summary_path, 'w') as f:
                    json.dump(self.summary_stats, f, indent=2, default=str)
            
            logger.info(f"Backtest results saved to: {self.save_path}")
            return self.save_path
            
        except Exception as e:
            logger.error(f"Error saving backtest results: {e}", exc_info=True)
            raise
    
    def _save_config(self):
        """Save backtest configuration"""
        config = {
            "strategy": self.strategy,
            "parameters": self.params,
            "backtest_id": self.backtest_id,
            "timestamp": datetime.now().isoformat(),
            "data_range": {
                "start": str(self.trades_df['date'].min()) if not self.trades_df.empty and 'date' in self.trades_df.columns else None,
                "end": str(self.trades_df['date'].max()) if not self.trades_df.empty and 'date' in self.trades_df.columns else None,
                "trading_days": len(pd.to_datetime(self.trades_df['date']).dt.date.unique()) if not self.trades_df.empty and 'date' in self.trades_df.columns else 0
            }
        }
        
        config_path = os.path.join(self.save_path, "config.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _create_daily_timeseries(self) -> pd.DataFrame:
        """Create continuous daily time series dataset"""
        if self.trades_df.empty:
            logger.warning("No trades to create daily timeseries")
            return pd.DataFrame()
        
        # Get date range - handle different date column names
        date_col = None
        for col in ['date', 'entry_time', 'breakout_time']:
            if col in self.trades_df.columns:
                date_col = col
                break
        
        if date_col is None:
            logger.error("No date column found in trades_df")
            return pd.DataFrame()
        
        start_date = pd.to_datetime(self.trades_df[date_col]).min()
        end_date = pd.to_datetime(self.trades_df[date_col]).max()
        
        # Filter market data to backtest period
        market_dates = pd.to_datetime(self.market_df['date'])
        
        # Handle timezone mismatches
        if market_dates.dt.tz is not None and start_date.tz is None:
            start_date = start_date.tz_localize(market_dates.dt.tz)
            end_date = end_date.tz_localize(market_dates.dt.tz)
        elif market_dates.dt.tz is None and start_date.tz is not None:
            start_date = start_date.tz_localize(None)
            end_date = end_date.tz_localize(None)
        
        mask = (market_dates >= start_date) & (market_dates <= end_date)
        period_data = self.market_df[mask].copy()
        
        # Create daily aggregates
        daily_data = []
        
        # Group by trading day
        period_data['trading_day'] = pd.to_datetime(period_data['date']).dt.date
        
        for day, day_group in period_data.groupby('trading_day'):
            # Market data aggregates
            daily_row = {
                'date': day,
                'day_of_week': pd.Timestamp(day).dayofweek,
                'day_of_month': pd.Timestamp(day).day,
                'day_of_year': pd.Timestamp(day).dayofyear,
                
                # OHLCV
                'open': day_group['open'].iloc[0],
                'high': day_group['high'].max(),
                'low': day_group['low'].min(),
                'close': day_group['close'].iloc[-1],
                'volume': day_group['volume'].sum(),
                
                # Derived metrics
                'range': day_group['high'].max() - day_group['low'].min(),
                'range_pct': (day_group['high'].max() - day_group['low'].min()) / day_group['close'].iloc[-1] * 100,
            }
            
            # Opening gap (if not first day)
            if len(daily_data) > 0:
                prev_close = daily_data[-1]['close']
                daily_row['opening_gap'] = (daily_row['open'] - prev_close) / prev_close * 100
            else:
                daily_row['opening_gap'] = 0
            
            # Intraday volatility
            returns = day_group['close'].pct_change().dropna()
            daily_row['intraday_volatility'] = returns.std() * np.sqrt(390) * 100  # Annualized
            
            # Volume metrics
            if 'volume' in day_group.columns and day_group['volume'].sum() > 0:
                daily_row['volume_mean'] = day_group['volume'].mean()
                daily_row['volume_std'] = day_group['volume'].std()
            else:
                daily_row['volume_mean'] = 0
                daily_row['volume_std'] = 0
            
            # Technical indicators (end of day values)
            last_bar = day_group.iloc[-1]
            
            # Add technical indicators if available in market data
            for indicator in ['ema_20', 'ema_50', 'ema_200', 'rsi', 'atr']:
                if indicator in day_group.columns:
                    daily_row[indicator] = last_bar[indicator]
            
            daily_data.append(daily_row)
        
        # Create DataFrame
        daily_df = pd.DataFrame(daily_data)
        
        # Add trading activity from trades_df
        if not self.trades_df.empty:
            # Ensure we have a date column for grouping
            if 'entry_time' in self.trades_df.columns:
                self.trades_df['trade_date'] = pd.to_datetime(self.trades_df['entry_time']).dt.date
            elif 'breakout_time' in self.trades_df.columns:
                self.trades_df['trade_date'] = pd.to_datetime(self.trades_df['breakout_time']).dt.date
            else:
                self.trades_df['trade_date'] = pd.to_datetime(self.trades_df['date']).dt.date
            
            # Calculate daily trading metrics
            daily_trades = self.trades_df.groupby('trade_date').agg({
                'pnl': ['count', 'sum', 'mean', 'std'],
                'outcome': lambda x: (x == 'target').sum() if 'outcome' in self.trades_df.columns else 0,
            })
            
            daily_trades.columns = ['trades_taken', 'daily_pnl', 'avg_pnl_per_trade', 'pnl_std', 'winning_trades']
            daily_trades.reset_index(inplace=True)
            
            # Add losing trades count
            daily_trades['losing_trades'] = daily_trades['trades_taken'] - daily_trades['winning_trades']
            
            # Merge with daily data
            daily_df = daily_df.merge(daily_trades, left_on='date', right_on='trade_date', how='left')
            daily_df.drop('trade_date', axis=1, inplace=True)
            
            # Fill NaN values for days with no trades
            trade_cols = ['trades_taken', 'daily_pnl', 'winning_trades', 'losing_trades']
            daily_df[trade_cols] = daily_df[trade_cols].fillna(0)
        
        # Calculate cumulative metrics
        daily_df['cumulative_pnl'] = daily_df['daily_pnl'].cumsum()
        daily_df['peak_pnl'] = daily_df['cumulative_pnl'].expanding().max()
        daily_df['drawdown'] = daily_df['cumulative_pnl'] - daily_df['peak_pnl']
        daily_df['drawdown_pct'] = (daily_df['drawdown'] / daily_df['peak_pnl'].replace(0, np.nan)) * 100
        
        # Rolling metrics
        daily_df['win_rate_20d'] = daily_df['winning_trades'].rolling(20).sum() / daily_df['trades_taken'].rolling(20).sum()
        daily_df['sharpe_20d'] = (daily_df['daily_pnl'].rolling(20).mean() / 
                                  daily_df['daily_pnl'].rolling(20).std().replace(0, np.nan)) * np.sqrt(252)
        
        # Volatility regime classification
        if 'intraday_volatility' in daily_df.columns:
            vol_percentiles = daily_df['intraday_volatility'].rank(pct=True)
            daily_df['volatility_regime'] = pd.cut(vol_percentiles, 
                                                  bins=[0, 0.33, 0.67, 1.0],
                                                  labels=['low_vol', 'normal_vol', 'high_vol'])
        
        # Trend regime classification
        if all(col in daily_df.columns for col in ['close', 'ema_20', 'ema_50']):
            conditions = [
                (daily_df['close'] > daily_df['ema_20']) & (daily_df['ema_20'] > daily_df['ema_50']),
                (daily_df['close'] < daily_df['ema_20']) & (daily_df['ema_20'] < daily_df['ema_50']),
            ]
            choices = ['uptrend', 'downtrend']
            daily_df['trend_regime'] = np.select(conditions, choices, default='ranging')
        
        return daily_df
    
    def _calculate_summary_stats(self) -> Dict:
        """Calculate comprehensive summary statistics"""
        stats = {}
        
        # Basic metrics
        if not self.trades_df.empty:
            stats['total_trades'] = len(self.trades_df)
            stats['winning_trades'] = (self.trades_df['pnl'] > 0).sum()
            stats['losing_trades'] = (self.trades_df['pnl'] <= 0).sum()
            stats['win_rate'] = stats['winning_trades'] / stats['total_trades'] if stats['total_trades'] > 0 else 0
            
            stats['total_pnl'] = self.trades_df['pnl'].sum()
            stats['avg_pnl'] = self.trades_df['pnl'].mean()
            stats['avg_win'] = self.trades_df[self.trades_df['pnl'] > 0]['pnl'].mean() if stats['winning_trades'] > 0 else 0
            stats['avg_loss'] = self.trades_df[self.trades_df['pnl'] <= 0]['pnl'].mean() if stats['losing_trades'] > 0 else 0
            
            stats['largest_win'] = self.trades_df['pnl'].max()
            stats['largest_loss'] = self.trades_df['pnl'].min()
        
        # Daily metrics
        if self.daily_df is not None and not self.daily_df.empty:
            stats['trading_days'] = len(self.daily_df)
            stats['days_with_trades'] = (self.daily_df['trades_taken'] > 0).sum()
            stats['max_drawdown'] = self.daily_df['drawdown'].min()
            stats['max_drawdown_pct'] = self.daily_df['drawdown_pct'].min()
            
            # Sharpe ratio
            daily_returns = self.daily_df['daily_pnl'] / self.params.get('starting_capital', 10000)
            if daily_returns.std() > 0:
                stats['sharpe_ratio'] = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
            else:
                stats['sharpe_ratio'] = 0
            
            # Calmar ratio
            annual_return = stats['total_pnl'] / stats['trading_days'] * 252
            stats['calmar_ratio'] = annual_return / abs(stats['max_drawdown']) if stats['max_drawdown'] != 0 else 0
        
        return stats
    
    @classmethod
    def load(cls, backtest_id: str, base_dir: str = "backtest_results") -> 'BacktestResults':
        """Load a saved backtest result"""
        save_path = os.path.join(base_dir, backtest_id)
        
        # Load config
        with open(os.path.join(save_path, "config.json"), 'r') as f:
            config = json.load(f)
        
        # Load data - try enhanced full first, fallback to basic
        enhanced_full_path = os.path.join(save_path, "trades_enhanced_full.csv")
        basic_path = os.path.join(save_path, "trades_enhanced.csv")
        
        if os.path.exists(enhanced_full_path):
            trades_df = pd.read_csv(enhanced_full_path)
        else:
            trades_df = pd.read_csv(basic_path)
            
        daily_df = pd.read_csv(os.path.join(save_path, "daily_timeseries.csv"))
        
        # Load summary stats
        with open(os.path.join(save_path, "summary_stats.json"), 'r') as f:
            summary_stats = json.load(f)
        
        # Create instance
        instance = cls.__new__(cls)
        instance.strategy = config['strategy']
        instance.params = config['parameters']
        instance.trades_df = trades_df
        instance.daily_df = daily_df
        instance.summary_stats = summary_stats
        instance.backtest_id = backtest_id
        instance.save_path = save_path
        
        return instance
    
    @staticmethod
    def list_saved_backtests(base_dir: str = "backtest_results") -> List[Dict]:
        """List all saved backtests with their metadata"""
        backtests = []
        
        if not os.path.exists(base_dir):
            return backtests
        
        for folder in os.listdir(base_dir):
            folder_path = os.path.join(base_dir, folder)
            if os.path.isdir(folder_path):
                config_path = os.path.join(folder_path, "config.json")
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    # Add folder name for loading
                    config['folder_name'] = folder
                    backtests.append(config)
        
        # Sort by timestamp (newest first)
        backtests.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return backtests