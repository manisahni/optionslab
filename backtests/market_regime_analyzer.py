"""
Market Regime Analyzer
Identifies market conditions including volatility regimes, trends, and drawdown periods
Uses EMA analysis, GARCH models, and drawdown detection
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class MarketRegimeAnalyzer:
    """Analyzes market regimes for better strategy timing"""
    
    def __init__(self, spy_data: pd.DataFrame = None):
        """
        Initialize with SPY price data
        
        Args:
            spy_data: DataFrame with 'date' and 'underlying_price' columns
        """
        self.spy_data = spy_data
        self.regimes = None
        self.drawdown_periods = []
        self.volatility_regimes = None
        
    def load_spy_prices(self, start_date: str = "2020-07-15", end_date: str = "2025-07-11") -> pd.DataFrame:
        """Load SPY prices from options data"""
        from glob import glob
        import pandas as pd
        
        print(f"Loading SPY prices from {start_date} to {end_date}...")
        
        # Try yearly files first for efficiency
        yearly_files = sorted(glob("data/spy_options/SPY_OPTIONS_20*_COMPLETE.parquet"))
        
        all_prices = []
        for file in yearly_files:
            try:
                df = pd.read_parquet(file)
                if 'underlying_price' in df.columns and 'date' in df.columns:
                    daily = df.groupby('date')['underlying_price'].first().reset_index()
                    all_prices.append(daily)
            except:
                continue
        
        # Fallback to daily files if needed
        if not all_prices:
            daily_files = sorted(glob("data/spy_options/spy_options_eod_*.parquet"))
            for file in daily_files[:100]:  # Sample for speed
                try:
                    df = pd.read_parquet(file)
                    if 'underlying_price' in df.columns:
                        date_str = file.split('_')[-1].replace('.parquet', '')
                        date = pd.to_datetime(date_str, format='%Y%m%d')
                        all_prices.append({
                            'date': date,
                            'underlying_price': df['underlying_price'].iloc[0]
                        })
                except:
                    continue
            
            if all_prices:
                self.spy_data = pd.DataFrame(all_prices)
        else:
            self.spy_data = pd.concat(all_prices, ignore_index=True)
        
        # Sort and filter by date range
        self.spy_data = self.spy_data.sort_values('date')
        self.spy_data = self.spy_data[
            (self.spy_data['date'] >= start_date) & 
            (self.spy_data['date'] <= end_date)
        ]
        
        print(f"Loaded {len(self.spy_data)} days of SPY data")
        return self.spy_data
    
    def calculate_indicators(self) -> pd.DataFrame:
        """Calculate technical indicators and regime markers"""
        if self.spy_data is None or self.spy_data.empty:
            raise ValueError("No SPY data loaded")
        
        df = self.spy_data.copy()
        
        # Returns
        df['returns'] = df['underlying_price'].pct_change()
        df['log_returns'] = np.log(df['underlying_price'] / df['underlying_price'].shift(1))
        
        # Moving averages
        df['sma_20'] = df['underlying_price'].rolling(20).mean()
        df['sma_50'] = df['underlying_price'].rolling(50).mean()
        df['sma_200'] = df['underlying_price'].rolling(200).mean()
        
        # Exponential moving averages
        df['ema_20'] = df['underlying_price'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['underlying_price'].ewm(span=50, adjust=False).mean()
        
        # EMA signals
        df['ema_signal'] = np.where(df['ema_20'] > df['ema_50'], 1, -1)
        df['ema_cross'] = df['ema_signal'].diff()
        
        # Volatility measures
        df['realized_vol_20'] = df['returns'].rolling(20).std() * np.sqrt(252)
        df['realized_vol_60'] = df['returns'].rolling(60).std() * np.sqrt(252)
        
        # Drawdown calculation
        df['cum_max'] = df['underlying_price'].expanding().max()
        df['drawdown'] = (df['underlying_price'] / df['cum_max'] - 1) * 100
        
        # RSI
        df['rsi'] = self._calculate_rsi(df['underlying_price'])
        
        # Bollinger Bands
        df['bb_middle'] = df['sma_20']
        df['bb_std'] = df['underlying_price'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (2 * df['bb_std'])
        df['bb_lower'] = df['bb_middle'] - (2 * df['bb_std'])
        df['bb_position'] = (df['underlying_price'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        self.spy_data = df
        return df
    
    def identify_volatility_regimes(self) -> pd.DataFrame:
        """Classify market into volatility regimes"""
        if 'realized_vol_20' not in self.spy_data.columns:
            self.calculate_indicators()
        
        df = self.spy_data.copy()
        
        # Define volatility thresholds
        vol_thresholds = {
            'low': 0.15,      # < 15% annualized
            'normal': 0.25,   # 15-25% annualized
            'high': np.inf    # > 25% annualized
        }
        
        # Classify regimes
        df['vol_regime'] = 'unknown'
        df.loc[df['realized_vol_20'] < vol_thresholds['low'], 'vol_regime'] = 'low_vol'
        df.loc[
            (df['realized_vol_20'] >= vol_thresholds['low']) & 
            (df['realized_vol_20'] < vol_thresholds['normal']), 
            'vol_regime'
        ] = 'normal_vol'
        df.loc[df['realized_vol_20'] >= vol_thresholds['normal'], 'vol_regime'] = 'high_vol'
        
        # Market trend regime
        df['trend_regime'] = 'unknown'
        df.loc[df['underlying_price'] > df['sma_200'], 'trend_regime'] = 'bull'
        df.loc[df['underlying_price'] <= df['sma_200'], 'trend_regime'] = 'bear'
        
        # Combined regime
        df['market_regime'] = df['vol_regime'] + '_' + df['trend_regime']
        
        self.spy_data = df
        self.volatility_regimes = df
        return df
    
    def identify_drawdown_periods(self, threshold: float = -10.0) -> List[Dict]:
        """
        Identify significant drawdown periods
        
        Args:
            threshold: Drawdown threshold (e.g., -10 for 10% drawdown)
            
        Returns:
            List of drawdown period dictionaries
        """
        if 'drawdown' not in self.spy_data.columns:
            self.calculate_indicators()
        
        df = self.spy_data.copy()
        
        # Find periods below threshold
        df['in_drawdown'] = df['drawdown'] < threshold
        df['dd_group'] = (df['in_drawdown'] != df['in_drawdown'].shift()).cumsum()
        
        drawdown_periods = []
        
        for group_id in df[df['in_drawdown']]['dd_group'].unique():
            period_df = df[df['dd_group'] == group_id]
            
            if len(period_df) < 5:  # Skip very short drawdowns
                continue
            
            # Find the actual max drawdown in this period
            start_idx = max(0, period_df.index[0] - 5)
            end_idx = min(len(df) - 1, period_df.index[-1] + 5)
            extended_period = df.iloc[start_idx:end_idx]
            
            drawdown_info = {
                'start_date': period_df.iloc[0]['date'],
                'end_date': period_df.iloc[-1]['date'],
                'duration_days': len(period_df),
                'max_drawdown': period_df['drawdown'].min(),
                'start_price': period_df.iloc[0]['underlying_price'],
                'low_price': period_df['underlying_price'].min(),
                'end_price': period_df.iloc[-1]['underlying_price'],
                'avg_volatility': period_df['realized_vol_20'].mean() if 'realized_vol_20' in period_df else None,
                'recovery_date': None
            }
            
            # Find recovery date (when price recovers to pre-drawdown level)
            recovery_price = extended_period.iloc[0]['cum_max']
            recovery_df = df[
                (df['date'] > drawdown_info['end_date']) & 
                (df['underlying_price'] >= recovery_price)
            ]
            
            if not recovery_df.empty:
                drawdown_info['recovery_date'] = recovery_df.iloc[0]['date']
                drawdown_info['recovery_days'] = (
                    drawdown_info['recovery_date'] - drawdown_info['end_date']
                ).days
            
            drawdown_periods.append(drawdown_info)
        
        self.drawdown_periods = drawdown_periods
        return drawdown_periods
    
    def calculate_garch_volatility(self, lookback_days: int = 252) -> pd.DataFrame:
        """
        Calculate GARCH(1,1) volatility forecast
        Note: Simplified implementation - for production use arch package
        """
        if 'log_returns' not in self.spy_data.columns:
            self.calculate_indicators()
        
        df = self.spy_data.copy()
        
        # Simple GARCH(1,1) approximation using exponential weighting
        # For production, use: from arch import arch_model
        lambda_param = 0.94  # RiskMetrics parameter
        
        # Initialize
        df['garch_vol'] = df['realized_vol_20']  # Start with realized vol
        
        # Exponentially weighted moving average of squared returns
        df['ewma_var'] = df['returns'].pow(2).ewm(
            alpha=1-lambda_param, adjust=False
        ).mean()
        df['garch_vol'] = np.sqrt(df['ewma_var'] * 252)
        
        # Volatility forecast (1-day ahead)
        df['vol_forecast'] = df['garch_vol'].shift(1)
        
        # Volatility surprise
        df['vol_surprise'] = df['realized_vol_20'] - df['vol_forecast']
        
        self.spy_data = df
        return df
    
    def get_regime_summary(self) -> Dict:
        """Get summary statistics for each regime"""
        if self.volatility_regimes is None:
            self.identify_volatility_regimes()
        
        df = self.spy_data
        
        summary = {
            'date_range': {
                'start': df['date'].min(),
                'end': df['date'].max(),
                'total_days': len(df)
            },
            'volatility_regimes': {},
            'trend_regimes': {},
            'drawdown_periods': []
        }
        
        # Volatility regime statistics
        for regime in df['vol_regime'].unique():
            if regime == 'unknown':
                continue
            
            regime_df = df[df['vol_regime'] == regime]
            summary['volatility_regimes'][regime] = {
                'days': len(regime_df),
                'percentage': len(regime_df) / len(df) * 100,
                'avg_return': regime_df['returns'].mean() * 252 * 100,
                'avg_volatility': regime_df['realized_vol_20'].mean() * 100,
                'sharpe': regime_df['returns'].mean() / regime_df['returns'].std() * np.sqrt(252) if regime_df['returns'].std() > 0 else 0
            }
        
        # Trend regime statistics  
        for regime in df['trend_regime'].unique():
            if regime == 'unknown':
                continue
            
            regime_df = df[df['trend_regime'] == regime]
            summary['trend_regimes'][regime] = {
                'days': len(regime_df),
                'percentage': len(regime_df) / len(df) * 100,
                'avg_return': regime_df['returns'].mean() * 252 * 100,
                'avg_volatility': regime_df['realized_vol_20'].mean() * 100 if 'realized_vol_20' in regime_df else None
            }
        
        # Drawdown summary
        if not self.drawdown_periods:
            self.identify_drawdown_periods()
        
        for dd in self.drawdown_periods:
            summary['drawdown_periods'].append({
                'start': dd['start_date'],
                'end': dd['end_date'],
                'max_drawdown': f"{dd['max_drawdown']:.1f}%",
                'duration': dd['duration_days'],
                'recovery_days': dd.get('recovery_days', 'N/A')
            })
        
        return summary
    
    def get_regime_for_date(self, date) -> Dict:
        """Get regime information for a specific date"""
        if self.volatility_regimes is None:
            self.identify_volatility_regimes()
        
        date = pd.to_datetime(date)
        day_data = self.spy_data[self.spy_data['date'] == date]
        
        if day_data.empty:
            return {'error': 'Date not found in data'}
        
        row = day_data.iloc[0]
        
        return {
            'date': date,
            'price': row['underlying_price'],
            'volatility_regime': row.get('vol_regime', 'unknown'),
            'trend_regime': row.get('trend_regime', 'unknown'),
            'realized_vol': row.get('realized_vol_20', None),
            'drawdown': row.get('drawdown', None),
            'ema_signal': row.get('ema_signal', None),
            'rsi': row.get('rsi', None)
        }
    
    def export_regime_data(self, filepath: str = "backtests/results/market_regimes.csv"):
        """Export regime data for use in backtesting"""
        if self.volatility_regimes is None:
            self.identify_volatility_regimes()
        
        export_df = self.spy_data[['date', 'underlying_price', 'vol_regime', 
                                   'trend_regime', 'market_regime', 'drawdown',
                                   'realized_vol_20', 'ema_signal', 'rsi']].copy()
        
        export_df.to_csv(filepath, index=False)
        print(f"Regime data exported to {filepath}")
        
        return export_df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


# Example usage and testing
if __name__ == "__main__":
    # Initialize analyzer
    analyzer = MarketRegimeAnalyzer()
    
    # Load SPY data
    analyzer.load_spy_prices("2020-07-15", "2025-07-11")
    
    # Calculate all indicators
    analyzer.calculate_indicators()
    
    # Identify regimes
    analyzer.identify_volatility_regimes()
    
    # Find drawdown periods
    drawdowns = analyzer.identify_drawdown_periods(threshold=-10)
    
    print("\n" + "="*60)
    print("MARKET REGIME ANALYSIS COMPLETE")
    print("="*60)
    
    # Get summary
    summary = analyzer.get_regime_summary()
    
    print(f"\nDate Range: {summary['date_range']['start']} to {summary['date_range']['end']}")
    print(f"Total Trading Days: {summary['date_range']['total_days']}")
    
    print("\n--- Volatility Regimes ---")
    for regime, stats in summary['volatility_regimes'].items():
        print(f"{regime}:")
        print(f"  Days: {stats['days']} ({stats['percentage']:.1f}%)")
        print(f"  Avg Annual Return: {stats['avg_return']:.1f}%")
        print(f"  Avg Volatility: {stats['avg_volatility']:.1f}%")
        print(f"  Sharpe Ratio: {stats['sharpe']:.2f}")
    
    print("\n--- Major Drawdown Periods (>10%) ---")
    for dd in summary['drawdown_periods'][:5]:  # Show first 5
        print(f"{dd['start'].date()} to {dd['end'].date()}:")
        print(f"  Max Drawdown: {dd['max_drawdown']}")
        print(f"  Duration: {dd['duration']} days")
        print(f"  Recovery: {dd['recovery_days']} days")
    
    # Export for backtesting
    analyzer.export_regime_data()
    
    print("\n✅ Regime data exported for backtesting use")