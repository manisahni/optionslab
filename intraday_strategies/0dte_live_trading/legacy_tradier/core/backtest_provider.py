"""
Backtesting Data Provider using Tradier Cache
Provides historical data for backtesting strategies
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from typing import Optional, List, Dict, Tuple
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cache_manager import TradierCacheManager
from core.greeks_calculator import GreeksCalculator

logger = logging.getLogger(__name__)


class BacktestDataProvider:
    """Provides cached historical data for backtesting"""
    
    def __init__(self, cache_manager: Optional[TradierCacheManager] = None):
        """Initialize the backtest data provider
        
        Args:
            cache_manager: TradierCacheManager instance
        """
        self.cache = cache_manager or TradierCacheManager()
        self.greeks_calc = GreeksCalculator()
    
    def get_spy_prices(self, start_date: datetime, end_date: datetime,
                      interval: str = '1min') -> pd.DataFrame:
        """Get SPY price data for backtesting
        
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            interval: Time interval (currently only '1min' supported)
            
        Returns:
            DataFrame with OHLCV data
        """
        return self.cache.get_spy_data(start_date, end_date, session_type='regular')
    
    def get_trading_days(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Get list of trading days in date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of trading days
        """
        query = """
            SELECT DISTINCT date(timestamp) as trading_date
            FROM spy_prices
            WHERE timestamp >= ? AND timestamp <= ?
            AND session_type = 'regular'
            ORDER BY trading_date
        """
        
        results = self.cache.db.execute_query(query, (start_date, end_date))
        
        if results:
            return [datetime.strptime(row['trading_date'], '%Y-%m-%d') for row in results]
        return []
    
    def get_market_open_data(self, date: datetime) -> Optional[Dict]:
        """Get market open data for a specific date
        
        Args:
            date: Trading date
            
        Returns:
            Dictionary with open price and time
        """
        date_str = date.strftime('%Y-%m-%d')
        market_open = datetime.combine(date.date(), time(9, 30))
        
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM spy_prices
            WHERE date(timestamp) = ?
            AND time(timestamp) = '09:30:00'
            AND session_type = 'regular'
            LIMIT 1
        """
        
        result = self.cache.db.execute_query(query, (date_str,))
        
        if result:
            row = result[0]
            return {
                'timestamp': datetime.fromisoformat(row['timestamp']),
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            }
        return None
    
    def get_intraday_range(self, date: datetime) -> Optional[Dict]:
        """Get intraday price range for a date
        
        Args:
            date: Trading date
            
        Returns:
            Dictionary with daily high, low, range
        """
        stats = self.cache.get_intraday_stats(date)
        
        if stats and stats.get('daily_high'):
            return {
                'date': date,
                'high': stats['daily_high'],
                'low': stats['daily_low'],
                'open': stats.get('open'),
                'close': stats.get('last'),
                'range': stats['daily_high'] - stats['daily_low'],
                'volume': stats.get('total_volume', 0)
            }
        return None
    
    def find_strangle_strikes(self, spot_price: float, dte: int = 0,
                            delta_target: float = 0.15) -> Tuple[float, float]:
        """Find appropriate strangle strikes based on spot price
        
        Args:
            spot_price: Current SPY price
            dte: Days to expiration
            delta_target: Target delta for strikes
            
        Returns:
            Tuple of (call_strike, put_strike)
        """
        # For 0DTE, typical strike selection is 0.5-1% OTM
        if dte == 0:
            call_strike = np.ceil(spot_price * 1.005)  # 0.5% OTM call
            put_strike = np.floor(spot_price * 0.995)  # 0.5% OTM put
        else:
            # For longer DTE, use wider strikes
            call_strike = np.ceil(spot_price * (1 + 0.01 * np.sqrt(dte)))
            put_strike = np.floor(spot_price * (1 - 0.01 * np.sqrt(dte)))
        
        return call_strike, put_strike
    
    def simulate_option_prices(self, spot: float, strike: float, 
                              option_type: str, dte: float,
                              volatility: float = 0.15) -> Dict:
        """Simulate option prices using Black-Scholes
        
        Args:
            spot: Spot price
            strike: Strike price
            option_type: 'call' or 'put'
            dte: Days to expiration (can be fractional)
            volatility: Implied volatility
            
        Returns:
            Dictionary with option price and Greeks
        """
        # Calculate option price
        price = self.greeks_calc.calculate_option_price(
            spot=spot,
            strike=strike,
            time_to_expiry=dte / 365,  # Convert to years
            volatility=volatility,
            option_type=option_type
        )
        
        # Calculate Greeks
        greeks = self.greeks_calc.calculate_greeks(
            spot=spot,
            strike=strike,
            time_to_expiry=dte / 365,  # Convert to years
            volatility=volatility,
            option_type=option_type
        )
        
        # Estimate bid-ask spread (typically 0.01-0.05 for SPY options)
        spread = 0.02 if dte == 0 else 0.03
        
        return {
            'price': price,
            'bid': price - spread/2,
            'ask': price + spread/2,
            'delta': greeks['delta'],
            'gamma': greeks['gamma'],
            'theta': greeks['theta'],
            'vega': greeks['vega'],
            'iv': volatility
        }
    
    def backtest_strangle(self, date: datetime, entry_time: time = time(9, 45),
                         exit_time: time = time(15, 45)) -> Optional[Dict]:
        """Backtest a strangle trade for a specific date
        
        Args:
            date: Trading date
            entry_time: Time to enter position
            exit_time: Time to exit position
            
        Returns:
            Dictionary with backtest results
        """
        # Get SPY data for the day
        start = datetime.combine(date.date(), entry_time)
        end = datetime.combine(date.date(), exit_time)
        
        spy_data = self.cache.get_spy_data(start, end)
        
        if spy_data.empty:
            return None
        
        # Entry price
        entry_price = spy_data.iloc[0]['close']
        
        # Find strangle strikes
        call_strike, put_strike = self.find_strangle_strikes(entry_price, dte=0)
        
        # Simulate entry prices
        call_entry = self.simulate_option_prices(entry_price, call_strike, 'call', 0.3)
        put_entry = self.simulate_option_prices(entry_price, put_strike, 'put', 0.3)
        
        # Track position through the day
        max_loss = 0
        exit_price = spy_data.iloc[-1]['close']
        
        # Calculate time decay
        time_elapsed = (exit_time.hour - entry_time.hour) / 24
        
        # Simulate exit prices
        call_exit = self.simulate_option_prices(exit_price, call_strike, 'call', 0.3 - time_elapsed)
        put_exit = self.simulate_option_prices(exit_price, put_strike, 'put', 0.3 - time_elapsed)
        
        # Calculate P&L (short strangle)
        call_pnl = call_entry['price'] - call_exit['price']
        put_pnl = put_entry['price'] - put_exit['price']
        total_pnl = call_pnl + put_pnl
        
        return {
            'date': date,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'call_strike': call_strike,
            'put_strike': put_strike,
            'call_entry': call_entry['price'],
            'put_entry': put_entry['price'],
            'call_exit': call_exit['price'],
            'put_exit': put_exit['price'],
            'call_pnl': call_pnl,
            'put_pnl': put_pnl,
            'total_pnl': total_pnl,
            'return_pct': (total_pnl / (call_entry['price'] + put_entry['price'])) * 100
        }
    
    def run_backtest(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Run backtest over date range
        
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            DataFrame with backtest results
        """
        results = []
        trading_days = self.get_trading_days(start_date, end_date)
        
        logger.info(f"Running backtest for {len(trading_days)} trading days...")
        
        for date in trading_days:
            result = self.backtest_strangle(date)
            if result:
                results.append(result)
        
        if results:
            df = pd.DataFrame(results)
            
            # Calculate summary statistics
            df['cumulative_pnl'] = df['total_pnl'].cumsum()
            df['win'] = df['total_pnl'] > 0
            
            return df
        
        return pd.DataFrame()
    
    def get_backtest_summary(self, results: pd.DataFrame) -> Dict:
        """Generate backtest summary statistics
        
        Args:
            results: DataFrame with backtest results
            
        Returns:
            Dictionary with summary statistics
        """
        if results.empty:
            return {}
        
        return {
            'total_trades': len(results),
            'winning_trades': results['win'].sum(),
            'losing_trades': (~results['win']).sum(),
            'win_rate': results['win'].mean() * 100,
            'total_pnl': results['total_pnl'].sum(),
            'average_pnl': results['total_pnl'].mean(),
            'best_trade': results['total_pnl'].max(),
            'worst_trade': results['total_pnl'].min(),
            'sharpe_ratio': results['total_pnl'].mean() / results['total_pnl'].std() if results['total_pnl'].std() > 0 else 0,
            'max_drawdown': (results['cumulative_pnl'] - results['cumulative_pnl'].cummax()).min()
        }