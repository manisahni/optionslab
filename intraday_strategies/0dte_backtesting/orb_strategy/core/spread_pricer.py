"""
Credit Spread Pricer using Real Options Data
Finds optimal strikes and calculates actual credits
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpreadPricer:
    """
    Price credit spreads using real bid/ask data
    """
    
    def __init__(self, spread_width: float = 15, min_credit_ratio: float = 0.01):
        """
        Initialize spread pricer
        
        Args:
            spread_width: Target width of spread in dollars
            min_credit_ratio: Minimum credit as ratio of spread width (1% minimum for real markets)
        """
        self.spread_width = spread_width
        self.min_credit_ratio = min_credit_ratio
        
        logger.info(f"Spread Pricer initialized: ${spread_width} wide spreads")
    
    def find_put_spread_strikes(self, options_df: pd.DataFrame, 
                               or_low: float, timestamp: pd.Timestamp) -> Tuple[float, float]:
        """
        Find optimal put spread strikes for bullish breakout
        
        Strategy: Short put at OR low - $0.01, long put $15 below
        
        Args:
            options_df: Options data
            or_low: Opening range low
            timestamp: Time of breakout
            
        Returns:
            Tuple of (short_strike, long_strike)
        """
        # Get available strikes at this time
        time_data = options_df[options_df['timestamp'] == timestamp]
        put_data = time_data[time_data['right'] == 'PUT']
        
        if put_data.empty:
            return None, None
        
        available_strikes = sorted(put_data['strike'].unique())
        
        # Find short strike: nearest strike at or below OR low
        target_short = or_low - 0.01
        short_strike = None
        
        for strike in reversed(available_strikes):
            if strike <= target_short:
                short_strike = strike
                break
        
        if not short_strike:
            short_strike = available_strikes[-1]  # Use highest available
        
        # Find long strike: approximately spread_width below short
        target_long = short_strike - self.spread_width
        long_strike = None
        
        for strike in reversed(available_strikes):
            if strike <= target_long:
                long_strike = strike
                break
        
        if not long_strike:
            long_strike = available_strikes[0]  # Use lowest available
        
        return short_strike, long_strike
    
    def find_call_spread_strikes(self, options_df: pd.DataFrame,
                                or_high: float, timestamp: pd.Timestamp) -> Tuple[float, float]:
        """
        Find optimal call spread strikes for bearish breakout
        
        Strategy: Short call at OR high + $0.01, long call $15 above
        
        Args:
            options_df: Options data
            or_high: Opening range high
            timestamp: Time of breakout
            
        Returns:
            Tuple of (short_strike, long_strike)
        """
        # Get available strikes at this time
        time_data = options_df[options_df['timestamp'] == timestamp]
        call_data = time_data[time_data['right'] == 'CALL']
        
        if call_data.empty:
            return None, None
        
        available_strikes = sorted(call_data['strike'].unique())
        
        # Find short strike: nearest strike at or above OR high
        target_short = or_high + 0.01
        short_strike = None
        
        for strike in available_strikes:
            if strike >= target_short:
                short_strike = strike
                break
        
        if not short_strike:
            short_strike = available_strikes[0]  # Use lowest available
        
        # Find long strike: approximately spread_width above short
        target_long = short_strike + self.spread_width
        long_strike = None
        
        for strike in available_strikes:
            if strike >= target_long:
                long_strike = strike
                break
        
        if not long_strike:
            long_strike = available_strikes[-1]  # Use highest available
        
        return short_strike, long_strike
    
    def calculate_spread_credit(self, options_df: pd.DataFrame, timestamp: pd.Timestamp,
                               short_strike: float, long_strike: float, 
                               right: str) -> Dict:
        """
        Calculate actual credit for a spread using real bid/ask
        
        Args:
            options_df: Options data
            timestamp: Time for pricing
            short_strike: Short option strike
            long_strike: Long option strike
            right: 'CALL' or 'PUT'
            
        Returns:
            Dict with spread pricing details
        """
        # Get option quotes at this time
        time_data = options_df[options_df['timestamp'] == timestamp]
        
        # Get short option
        short_option = time_data[
            (time_data['strike'] == short_strike) & 
            (time_data['right'] == right)
        ]
        
        # Get long option
        long_option = time_data[
            (time_data['strike'] == long_strike) & 
            (time_data['right'] == right)
        ]
        
        if short_option.empty or long_option.empty:
            return None
        
        short_option = short_option.iloc[0]
        long_option = long_option.iloc[0]
        
        # Calculate credit
        # We receive bid on short, pay ask on long
        credit_per_contract = (short_option['bid'] - long_option['ask']) * 100
        
        # Skip if credit is too low
        actual_width = abs(short_strike - long_strike)
        credit_ratio = credit_per_contract / (actual_width * 100)
        
        if credit_ratio < self.min_credit_ratio:
            logger.debug(f"Credit too low: ${credit_per_contract:.2f} ({credit_ratio:.1%} of width)")
            return None
        
        # Calculate max loss
        max_loss = (actual_width * 100) - credit_per_contract
        
        # Calculate breakeven
        if right == 'PUT':
            breakeven = short_strike - (credit_per_contract / 100)
        else:
            breakeven = short_strike + (credit_per_contract / 100)
        
        return {
            'timestamp': timestamp,
            'right': right,
            'short_strike': short_strike,
            'long_strike': long_strike,
            'spread_width': actual_width,
            'short_bid': short_option['bid'],
            'short_ask': short_option['ask'],
            'long_bid': long_option['bid'],
            'long_ask': long_option['ask'],
            'credit': credit_per_contract,
            'credit_ratio': credit_ratio,
            'max_loss': max_loss,
            'breakeven': breakeven,
            'underlying_price': short_option['underlying_price_dollar'],
            # Greeks
            'net_delta': short_option['delta'] - long_option['delta'],
            'net_gamma': short_option['gamma'] - long_option['gamma'],
            'net_theta': short_option['theta'] - long_option['theta'],
            'net_vega': short_option['vega'] - long_option['vega']
        }
    
    def calculate_spread_value(self, options_df: pd.DataFrame, timestamp: pd.Timestamp,
                              short_strike: float, long_strike: float, 
                              right: str) -> float:
        """
        Calculate current value of spread (for exits)
        
        Args:
            options_df: Options data
            timestamp: Time for pricing
            short_strike: Short option strike
            long_strike: Long option strike
            right: 'CALL' or 'PUT'
            
        Returns:
            Cost to close spread (negative means profit)
        """
        # Get current quotes
        time_data = options_df[options_df['timestamp'] == timestamp]
        
        short_option = time_data[
            (time_data['strike'] == short_strike) & 
            (time_data['right'] == right)
        ]
        
        long_option = time_data[
            (time_data['strike'] == long_strike) & 
            (time_data['right'] == right)
        ]
        
        if short_option.empty or long_option.empty:
            # If options not found (maybe expired worthless), return 0
            return 0
        
        short_option = short_option.iloc[0]
        long_option = long_option.iloc[0]
        
        # Cost to close: pay ask on short, receive bid on long
        cost_to_close = (short_option['ask'] - long_option['bid']) * 100
        
        return cost_to_close
    
    def calculate_pnl(self, entry_credit: float, exit_cost: float, 
                     num_contracts: int = 1) -> Dict:
        """
        Calculate P&L for a spread trade
        
        Args:
            entry_credit: Credit received at entry
            exit_cost: Cost to close (0 if expired worthless)
            num_contracts: Number of contracts
            
        Returns:
            Dict with P&L details
        """
        # Gross P&L
        gross_pnl = (entry_credit - exit_cost) * num_contracts
        
        # Commission (simplified)
        commission = 0.65 * 2 * 2 * num_contracts  # $0.65 per contract, 2 legs, 2 trades
        
        # Net P&L
        net_pnl = gross_pnl - commission
        
        return {
            'gross_pnl': gross_pnl,
            'commission': commission,
            'net_pnl': net_pnl,
            'return_pct': (net_pnl / (entry_credit * num_contracts)) if entry_credit > 0 else 0
        }


def main():
    """Test the spread pricer"""
    
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    
    from backtesting.options_data_loader import OptionsDataLoader
    
    # Load sample data
    loader = OptionsDataLoader()
    dates = loader.get_available_dates()
    
    if dates:
        test_date = dates[0]
        df = loader.load_day_data(test_date)
        
        if df is not None:
            # Initialize pricer
            pricer = SpreadPricer(spread_width=15)
            
            # Test at 10:30 AM
            test_time = pd.Timestamp(f'{test_date} 10:30:00')
            
            # Get SPY price
            sample = df[df['timestamp'] == test_time].iloc[0]
            spy_price = sample['underlying_price_dollar']
            
            print(f"Testing spread pricing at {test_time}")
            print(f"SPY Price: ${spy_price:.2f}")
            
            # Simulate OR levels
            or_high = spy_price + 2
            or_low = spy_price - 2
            
            print(f"\nSimulated OR: ${or_low:.2f} - ${or_high:.2f}")
            
            # Find put spread strikes
            put_short, put_long = pricer.find_put_spread_strikes(df, or_low, test_time)
            
            if put_short and put_long:
                print(f"\nPut Spread Strikes: ${put_short}/{put_long}")
                
                # Calculate credit
                spread_details = pricer.calculate_spread_credit(
                    df, test_time, put_short, put_long, 'PUT'
                )
                
                if spread_details:
                    print(f"  Credit: ${spread_details['credit']:.2f}")
                    print(f"  Credit Ratio: {spread_details['credit_ratio']:.1%}")
                    print(f"  Max Loss: ${spread_details['max_loss']:.2f}")
                    print(f"  Breakeven: ${spread_details['breakeven']:.2f}")
                    print(f"  Net Delta: {spread_details['net_delta']:.3f}")
                    print(f"  Net Vega: {spread_details['net_vega']:.3f}")


if __name__ == "__main__":
    main()