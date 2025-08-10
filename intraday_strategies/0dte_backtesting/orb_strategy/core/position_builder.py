"""
Position Builder for ORB Credit Spreads
Constructs optimal credit spreads based on breakout signals
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CreditSpreadBuilder:
    """
    Build credit spreads for ORB strategy
    Based on article's optimal $15 wide spreads
    """
    
    def __init__(self,
                 spread_width: float = 15,
                 strike_offset: float = 0.01,
                 position_size_pct: float = 0.02):
        """
        Initialize position builder
        
        Args:
            spread_width: Width of credit spread in dollars (default $15)
            strike_offset: Offset from OR level for short strike (default $0.01)
            position_size_pct: Position size as % of account (default 2%)
        """
        self.spread_width = spread_width
        self.strike_offset = strike_offset
        self.position_size_pct = position_size_pct
        
        logger.info(f"Position Builder initialized: ${spread_width} wide spreads")
    
    def build_put_spread(self, spy_price: float, or_low: float, 
                        account_value: float = 100000) -> Dict:
        """
        Build short put spread for bullish breakout
        
        Strategy: Sell put spread when price breaks above OR high
        Short put at OR low - $0.01
        Long put $15 below short put
        
        Args:
            spy_price: Current SPY price
            or_low: Opening range low
            account_value: Account value for position sizing
            
        Returns:
            Dict with spread details
        """
        # Calculate strikes
        short_strike = self.round_strike(or_low - self.strike_offset)
        long_strike = self.round_strike(short_strike - self.spread_width)
        
        # Estimate credit (simplified - would need real option prices)
        # Credit typically 30-40% of spread width for 30-delta spreads
        estimated_credit = self.spread_width * 0.35 * 100  # Per contract
        
        # Calculate position size
        num_contracts = self.calculate_position_size(
            account_value, 
            estimated_credit,
            self.spread_width * 100  # Max loss per contract
        )
        
        position = {
            'type': 'put_credit_spread',
            'direction': 'bullish',
            'short_strike': short_strike,
            'long_strike': long_strike,
            'spread_width': self.spread_width,
            'num_contracts': num_contracts,
            'estimated_credit': estimated_credit * num_contracts,
            'max_loss': self.spread_width * 100 * num_contracts,
            'max_profit': estimated_credit * num_contracts,
            'breakeven': short_strike - (estimated_credit / 100),
            'entry_time': datetime.now(),
            'underlying_price': spy_price,
            'or_low': or_low
        }
        
        logger.info(f"Built PUT spread: Short ${short_strike} / Long ${long_strike}")
        
        return position
    
    def build_call_spread(self, spy_price: float, or_high: float,
                         account_value: float = 100000) -> Dict:
        """
        Build short call spread for bearish breakout
        
        Strategy: Sell call spread when price breaks below OR low
        Short call at OR high + $0.01
        Long call $15 above short call
        
        Args:
            spy_price: Current SPY price
            or_high: Opening range high
            account_value: Account value for position sizing
            
        Returns:
            Dict with spread details
        """
        # Calculate strikes
        short_strike = self.round_strike(or_high + self.strike_offset)
        long_strike = self.round_strike(short_strike + self.spread_width)
        
        # Estimate credit
        estimated_credit = self.spread_width * 0.35 * 100  # Per contract
        
        # Calculate position size
        num_contracts = self.calculate_position_size(
            account_value,
            estimated_credit,
            self.spread_width * 100
        )
        
        position = {
            'type': 'call_credit_spread',
            'direction': 'bearish',
            'short_strike': short_strike,
            'long_strike': long_strike,
            'spread_width': self.spread_width,
            'num_contracts': num_contracts,
            'estimated_credit': estimated_credit * num_contracts,
            'max_loss': self.spread_width * 100 * num_contracts,
            'max_profit': estimated_credit * num_contracts,
            'breakeven': short_strike + (estimated_credit / 100),
            'entry_time': datetime.now(),
            'underlying_price': spy_price,
            'or_high': or_high
        }
        
        logger.info(f"Built CALL spread: Short ${short_strike} / Long ${long_strike}")
        
        return position
    
    def build_position(self, breakout_signal: Dict, or_levels: Dict,
                      account_value: float = 100000) -> Dict:
        """
        Build position based on breakout signal
        
        Args:
            breakout_signal: Breakout details from detector
            or_levels: Opening range levels
            account_value: Account value for sizing
            
        Returns:
            Position details
        """
        if not breakout_signal or not or_levels:
            return None
        
        spy_price = breakout_signal.get('entry_price')
        
        if breakout_signal['type'] == 'bullish':
            # Bullish breakout -> Short put spread
            position = self.build_put_spread(
                spy_price, 
                or_levels['low'],
                account_value
            )
        else:
            # Bearish breakout -> Short call spread
            position = self.build_call_spread(
                spy_price,
                or_levels['high'],
                account_value
            )
        
        # Add breakout details to position
        position['breakout_type'] = breakout_signal['type']
        position['breakout_strength'] = breakout_signal.get('strength', 0)
        position['entry_signal'] = breakout_signal
        
        return position
    
    def calculate_position_size(self, account_value: float, 
                               credit_per_contract: float,
                               max_loss_per_contract: float) -> int:
        """
        Calculate optimal position size using Kelly Criterion
        
        Args:
            account_value: Total account value
            credit_per_contract: Credit received per contract
            max_loss_per_contract: Maximum loss per contract
            
        Returns:
            Number of contracts to trade
        """
        # Risk per trade (2% default)
        risk_amount = account_value * self.position_size_pct
        
        # Basic position sizing
        contracts_by_risk = risk_amount / max_loss_per_contract
        
        # Kelly Criterion adjustment (simplified)
        # Based on article's 88.8% win rate for 60-min ORB
        win_rate = 0.888
        avg_win = credit_per_contract * 0.5  # Assume 50% profit target
        avg_loss = max_loss_per_contract * 0.5  # Assume stops at 50% loss
        
        if avg_loss > 0:
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_loss
            kelly_fraction = min(0.25, max(0, kelly_fraction))  # Cap at 25%
        else:
            kelly_fraction = 0.02
        
        # Combine basic and Kelly sizing
        optimal_contracts = min(
            contracts_by_risk,
            (account_value * kelly_fraction) / max_loss_per_contract
        )
        
        # Round down and apply limits
        num_contracts = int(optimal_contracts)
        num_contracts = min(10, max(1, num_contracts))  # Between 1-10 contracts
        
        return num_contracts
    
    def round_strike(self, price: float, interval: float = 1.0) -> float:
        """
        Round price to nearest strike interval
        
        Args:
            price: Raw price
            interval: Strike interval (default $1 for SPY)
            
        Returns:
            Rounded strike price
        """
        return round(price / interval) * interval
    
    def calculate_greeks_estimate(self, position: Dict, iv: float = 0.15) -> Dict:
        """
        Estimate Greeks for the position (simplified)
        
        Args:
            position: Position details
            iv: Implied volatility (default 15%)
            
        Returns:
            Dict with estimated Greeks
        """
        # Simplified Greeks estimation for credit spreads
        # In production, use py_vollib or real option data
        
        spread_width = position['spread_width']
        credit = position['estimated_credit'] / (position['num_contracts'] * 100)
        
        # Rough estimates based on typical 0DTE credit spreads
        greeks = {
            'delta': -0.15 if position['type'] == 'put_credit_spread' else 0.15,
            'gamma': -0.02,  # Negative gamma for short spreads
            'theta': credit * 0.5,  # Theta roughly half of credit
            'vega': -spread_width * 0.1,  # Negative vega for short
            'estimated': True
        }
        
        # Scale by number of contracts
        for greek in ['delta', 'gamma', 'theta', 'vega']:
            greeks[greek] *= position['num_contracts']
        
        return greeks
    
    def calculate_risk_metrics(self, position: Dict) -> Dict:
        """
        Calculate risk metrics for position
        
        Args:
            position: Position details
            
        Returns:
            Dict with risk metrics
        """
        credit = position['estimated_credit']
        max_loss = position['max_loss']
        
        metrics = {
            'risk_reward_ratio': credit / max_loss if max_loss > 0 else 0,
            'probability_profit': 0.65,  # Estimate based on delta
            'expected_value': credit * 0.888 - max_loss * 0.112,  # Based on win rate
            'margin_required': max_loss,  # For credit spreads
            'return_on_margin': (credit / max_loss) if max_loss > 0 else 0
        }
        
        return metrics


def main():
    """Test the position builder"""
    
    print("Testing Credit Spread Builder\n" + "="*50)
    
    # Initialize builder
    builder = CreditSpreadBuilder(spread_width=15)
    
    # Test bullish breakout scenario
    print("\n1. Bullish Breakout - Put Credit Spread:")
    print("-" * 40)
    
    spy_price = 450
    or_low = 448
    
    put_spread = builder.build_put_spread(spy_price, or_low, account_value=100000)
    
    print(f"Short Put: ${put_spread['short_strike']}")
    print(f"Long Put: ${put_spread['long_strike']}")
    print(f"Contracts: {put_spread['num_contracts']}")
    print(f"Credit: ${put_spread['estimated_credit']:.0f}")
    print(f"Max Loss: ${put_spread['max_loss']:.0f}")
    print(f"Breakeven: ${put_spread['breakeven']:.2f}")
    
    # Test bearish breakout scenario
    print("\n2. Bearish Breakout - Call Credit Spread:")
    print("-" * 40)
    
    or_high = 452
    
    call_spread = builder.build_call_spread(spy_price, or_high, account_value=100000)
    
    print(f"Short Call: ${call_spread['short_strike']}")
    print(f"Long Call: ${call_spread['long_strike']}")
    print(f"Contracts: {call_spread['num_contracts']}")
    print(f"Credit: ${call_spread['estimated_credit']:.0f}")
    print(f"Max Loss: ${call_spread['max_loss']:.0f}")
    print(f"Breakeven: ${call_spread['breakeven']:.2f}")
    
    # Calculate risk metrics
    print("\n3. Risk Metrics:")
    print("-" * 40)
    
    metrics = builder.calculate_risk_metrics(put_spread)
    
    print(f"Risk/Reward: {metrics['risk_reward_ratio']:.2f}")
    print(f"Expected Value: ${metrics['expected_value']:.0f}")
    print(f"Return on Margin: {metrics['return_on_margin']:.1%}")


if __name__ == "__main__":
    main()