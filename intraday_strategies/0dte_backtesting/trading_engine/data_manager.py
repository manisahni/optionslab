import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Tuple, Optional, Any
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from configuration.performance_cache import cached_data_loader
except ImportError:
    # Cache manager not available, create dummy decorator
    def cached_data_loader(name):
        def decorator(func):
            return func
        return decorator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DTEAnalystAgent:
    """
    Interactive agent for 0DTE trading analysis with focus on ORB strategies
    """
    
    def __init__(self, data_path: str = "data/SPY.parquet"):
        """Initialize the agent with SPY data"""
        self.data_path = data_path
        self.df = None
        self.load_data()
        self.context = {}  # Store conversation context
        
    def load_data(self):
        """Load SPY data from parquet file"""
        try:
            self.df = pd.read_parquet(self.data_path)
            self.df = self.df.sort_values('date')
            logger.info(f"Loaded {len(self.df)} bars from {self.df['date'].min()} to {self.df['date'].max()}")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
            
    @cached_data_loader("last_n_days")
    def get_last_n_days(self, n_days: int = 30) -> pd.DataFrame:
        """Get last n days of trading data (cached for performance)"""
        # If n_days is 0 or negative, return all data
        if n_days <= 0:
            result_df = self.df.copy()
        else:
            end_date = self.df['date'].max()
            # Create timezone-aware start_date to match data timezone
            if self.df['date'].dt.tz is not None:
                start_date = end_date - pd.Timedelta(days=n_days * 1.5)  # Account for weekends
            else:
                start_date = end_date - timedelta(days=n_days * 1.5)  # Account for weekends
            mask = self.df['date'] >= start_date
            result_df = self.df[mask].copy()
        
        # Set the date column as the index for strategy compatibility
        result_df = result_df.set_index('date')
        
        return result_df
    
    def chat(self, message: str) -> Dict[str, Any]:
        """
        Process natural language queries and return analysis
        
        Returns dict with:
        - text: Natural language response
        - data: DataFrame if applicable
        - plot: Plotly figure if applicable
        - metrics: Dict of calculated metrics
        """
        message_lower = message.lower()
        
        # Route to appropriate analysis based on keywords
        if any(word in message_lower for word in ['orb', 'opening range', 'breakout']):
            return self._handle_orb_query(message)
        elif any(word in message_lower for word in ['volatility', 'vol', 'vix']):
            return self._handle_volatility_query(message)
        elif any(word in message_lower for word in ['pattern', 'setup', 'signal']):
            return self._handle_pattern_query(message)
        elif any(word in message_lower for word in ['stats', 'statistics', 'summary']):
            return self._handle_stats_query(message)
        else:
            return self._handle_general_query(message)
    
    def _handle_orb_query(self, message: str) -> Dict[str, Any]:
        """Handle ORB-related queries"""
        # Extract timeframe from message
        timeframe = 15  # default
        if '5' in message or '5min' in message or '5-min' in message:
            timeframe = 5
        elif '30' in message or '30min' in message or '30-min' in message:
            timeframe = 30
            
        # Extract days from message
        days = 30  # default
        for word in message.split():
            if word.isdigit():
                days = int(word)
                break
                
        response = {
            'text': f"Analyzing {timeframe}-minute ORB strategy for the last {days} days...",
            'data': None,
            'plot': None,
            'metrics': {
                'timeframe': timeframe,
                'days_analyzed': days,
                'strategy': 'ORB'
            }
        }
        
        return response
    
    def _handle_volatility_query(self, message: str) -> Dict[str, Any]:
        """Handle volatility-related queries"""
        df_recent = self.get_last_n_days(30)
        
        # Calculate basic volatility metrics
        returns = df_recent['close'].pct_change()
        volatility = returns.std() * np.sqrt(252 * 390)  # Annualized intraday vol
        
        response = {
            'text': f"Current 30-day volatility analysis:\n"
                   f"- Annualized volatility: {volatility:.2%}\n"
                   f"- Daily average range: ${(df_recent['high'] - df_recent['low']).mean():.2f}\n"
                   f"- Analyzing intraday patterns...",
            'data': None,
            'plot': None,
            'metrics': {
                'volatility': volatility,
                'avg_range': (df_recent['high'] - df_recent['low']).mean()
            }
        }
        
        return response
    
    def _handle_pattern_query(self, message: str) -> Dict[str, Any]:
        """Handle pattern detection queries"""
        return {
            'text': "Scanning for trading patterns in recent data...",
            'data': None,
            'plot': None,
            'metrics': {}
        }
    
    def _handle_stats_query(self, message: str) -> Dict[str, Any]:
        """Handle statistical summary queries"""
        df_recent = self.get_last_n_days(30)
        
        stats_text = f"""Market Statistics (Last 30 Days):
- Total bars: {len(df_recent):,}
- Price range: ${df_recent['low'].min():.2f} - ${df_recent['high'].max():.2f}
- Average daily volume: {df_recent.groupby(df_recent.index.date)['volume'].sum().mean():,.0f}
- Most volatile day: {df_recent.groupby(df_recent.index.date).apply(lambda x: (x['high'].max() - x['low'].min())).idxmax()}
"""
        
        return {
            'text': stats_text,
            'data': None,
            'plot': None,
            'metrics': {
                'total_bars': len(df_recent),
                'price_low': df_recent['low'].min(),
                'price_high': df_recent['high'].max()
            }
        }
    
    def _handle_general_query(self, message: str) -> Dict[str, Any]:
        """Handle general queries"""
        return {
            'text': "I can help you analyze:\n"
                   "- ORB strategies (e.g., 'test 15-minute ORB')\n"
                   "- Volatility patterns (e.g., 'show volatility analysis')\n"
                   "- Trading patterns (e.g., 'find reversal patterns')\n"
                   "- Market statistics (e.g., 'show market stats')\n\n"
                   "What would you like to analyze?",
            'data': None,
            'plot': None,
            'metrics': {}
        }
    
    def get_trading_days(self, df: pd.DataFrame) -> List[pd.Timestamp]:
        """Get unique trading days from dataframe"""
        if 'date' in df.columns:
            return df['date'].dt.date.unique()
        else:
            # Date is the index - convert numpy array to pandas Series for unique()
            return pd.Series(df.index.date).unique()
    
    def get_session_bars(self, date: pd.Timestamp, session: str = 'regular') -> pd.DataFrame:
        """Get bars for a specific trading session"""
        df_day = self.df[self.df['date'].dt.date == date]
        
        if session == 'regular':
            # Regular trading hours: 9:30 AM - 4:00 PM ET
            mask = (df_day['date'].dt.time >= pd.Timestamp('09:30').time()) & \
                   (df_day['date'].dt.time <= pd.Timestamp('16:00').time())
            return df_day[mask]
        elif session == 'premarket':
            # Pre-market: 4:00 AM - 9:30 AM ET
            mask = (df_day['date'].dt.time >= pd.Timestamp('04:00').time()) & \
                   (df_day['date'].dt.time < pd.Timestamp('09:30').time())
            return df_day[mask]
        elif session == 'afterhours':
            # After-hours: 4:00 PM - 8:00 PM ET
            mask = (df_day['date'].dt.time > pd.Timestamp('16:00').time()) & \
                   (df_day['date'].dt.time <= pd.Timestamp('20:00').time())
            return df_day[mask]
        else:
            return df_day