"""
Multi-leg option selector for complex spreads
Extends the basic option_selector to handle ZEBRA and other multi-leg strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class MultiLegSelector:
    """Handles selection of multiple option legs for complex strategies like ZEBRA"""
    
    def __init__(self, config: Dict):
        """Initialize with strategy configuration"""
        self.config = config
        self.strategy_type = config.get('strategy_type', 'custom_spread')
        self.legs = config.get('legs', [])
        self.option_selection = config.get('option_selection', {})
        
    def find_multi_leg_options(self, data: pd.DataFrame, current_price: float, 
                               current_date: str) -> Optional[Dict]:
        """
        Find suitable options for all legs of the strategy
        
        Args:
            data: DataFrame with options data for current date
            current_price: Current underlying price
            current_date: Current date string
            
        Returns:
            Dictionary with selected options for each leg or None if not found
        """
        print(f"🔍 MULTI-LEG: Selecting options for {len(self.legs)} legs")
        print(f"💰 MULTI-LEG: Underlying: ${current_price:.2f}")
        
        selected_legs = {}
        common_expiration = None
        
        # Process each leg
        for i, leg in enumerate(self.legs):
            leg_name = leg.get('name', f'leg_{i+1}')
            leg_type = leg['type']  # call or put
            leg_direction = leg['direction']  # long or short
            leg_quantity = leg.get('quantity', 1)
            
            print(f"\n📊 MULTI-LEG: Processing {leg_name}: {leg_quantity}x {leg_direction} {leg_type}")
            
            # Get selection criteria for this leg
            leg_config_key = f"leg_{i+1}_{leg_name.replace('-', '_')}"
            leg_criteria = self.option_selection.get(leg_config_key, {})
            
            # Select option for this leg
            if 'strike_offset_pct' in leg:
                # Handle percentage-based strike selection (for protective puts)
                selected_option = self._select_by_strike_offset(
                    data, current_price, leg_type, 
                    leg['strike_offset_pct'], common_expiration
                )
            else:
                # Handle delta-based selection (for calls)
                selected_option = self._select_by_delta(
                    data, current_price, leg_type,
                    leg.get('delta_target', 0.30),
                    leg_criteria, common_expiration
                )
            
            if selected_option is None:
                print(f"❌ MULTI-LEG: Could not find suitable option for {leg_name}")
                return None
                
            # Store selected option
            selected_legs[leg_name] = {
                'option': selected_option,
                'type': leg_type,
                'direction': leg_direction,
                'quantity': leg_quantity,
                'strike': selected_option['strike'],
                'expiration': selected_option['expiration'],
                'delta': selected_option.get('delta', 0),
                'mid_price': (selected_option['bid'] + selected_option['ask']) / 2
            }
            
            # Set common expiration from first leg
            if common_expiration is None:
                common_expiration = selected_option['expiration']
                print(f"✅ MULTI-LEG: Set common expiration: {common_expiration}")
        
        # Calculate net position metrics
        net_metrics = self._calculate_net_metrics(selected_legs, current_price)
        
        return {
            'legs': selected_legs,
            'net_metrics': net_metrics,
            'underlying_price': current_price,
            'selection_date': current_date
        }
    
    def _select_by_delta(self, data: pd.DataFrame, current_price: float, 
                        option_type: str, target_delta: float,
                        criteria: Dict, required_exp: Optional[str] = None) -> Optional[pd.Series]:
        """Select option by delta criteria"""
        
        # Filter for option type
        option_right = 'C' if option_type == 'call' else 'P'
        options = data[data['right'] == option_right].copy()
        
        if len(options) == 0:
            return None
            
        # Apply expiration filter if required
        if required_exp is not None:
            options = options[options['expiration'] == required_exp]
            
        # Extract criteria
        delta_criteria = criteria.get('delta_criteria', {})
        delta_tolerance = delta_criteria.get('tolerance', 0.05)
        
        dte_criteria = criteria.get('dte_criteria', {})
        min_dte = dte_criteria.get('minimum', 30)
        max_dte = dte_criteria.get('maximum', 60)
        
        liquidity_criteria = criteria.get('liquidity_criteria', {})
        min_volume = liquidity_criteria.get('min_volume', 100)
        max_spread_pct = liquidity_criteria.get('max_spread_pct', 0.15)
        
        # Calculate DTE
        options['dte'] = (pd.to_datetime(options['expiration']) - 
                         pd.to_datetime(data['date'].iloc[0])).dt.days
        
        # Apply filters
        options = options[
            (options['dte'] >= min_dte) &
            (options['dte'] <= max_dte) &
            (options['volume'] >= min_volume)
        ]
        
        if len(options) == 0:
            return None
            
        # Calculate spread percentage
        options['spread_pct'] = (options['ask'] - options['bid']) / options['ask']
        options = options[options['spread_pct'] <= max_spread_pct]
        
        if len(options) == 0:
            return None
            
        # Filter by delta
        options['delta_diff'] = abs(abs(options['delta']) - target_delta)
        options = options[options['delta_diff'] <= delta_tolerance]
        
        if len(options) == 0:
            return None
            
        # Select closest to target delta
        best_option = options.nsmallest(1, 'delta_diff').iloc[0]
        
        print(f"  ✅ Selected: Strike ${best_option['strike']:.0f}, "
              f"Delta {best_option['delta']:.3f}, DTE {best_option['dte']}")
        
        return best_option
    
    def _select_by_strike_offset(self, data: pd.DataFrame, current_price: float,
                                 option_type: str, offset_pct: float,
                                 required_exp: Optional[str] = None) -> Optional[pd.Series]:
        """Select option by strike offset from current price"""
        
        # Calculate target strike
        target_strike = current_price * (1 + offset_pct)
        
        # Filter for option type
        option_right = 'P' if option_type == 'put' else 'C'
        options = data[data['right'] == option_right].copy()
        
        if len(options) == 0:
            return None
            
        # Apply expiration filter if required
        if required_exp is not None:
            options = options[options['expiration'] == required_exp]
            
        # Calculate DTE
        options['dte'] = (pd.to_datetime(options['expiration']) - 
                         pd.to_datetime(data['date'].iloc[0])).dt.days
        
        # Basic filters
        options = options[
            (options['dte'] >= 30) &
            (options['dte'] <= 60) &
            (options['volume'] > 0)
        ]
        
        if len(options) == 0:
            return None
            
        # Find closest strike to target
        options['strike_diff'] = abs(options['strike'] - target_strike)
        best_option = options.nsmallest(1, 'strike_diff').iloc[0]
        
        print(f"  ✅ Selected: Strike ${best_option['strike']:.0f} "
              f"({offset_pct*100:.1f}% from spot), "
              f"Delta {best_option.get('delta', 0):.3f}")
        
        return best_option
    
    def _calculate_net_metrics(self, selected_legs: Dict, current_price: float) -> Dict:
        """Calculate net position metrics from selected legs"""
        
        net_delta = 0
        net_gamma = 0
        net_theta = 0
        net_vega = 0
        net_debit = 0
        
        for leg_name, leg_data in selected_legs.items():
            option = leg_data['option']
            direction_mult = 1 if leg_data['direction'] == 'long' else -1
            quantity = leg_data['quantity']
            
            # Calculate net Greeks
            net_delta += direction_mult * quantity * option.get('delta', 0) * 100
            net_gamma += direction_mult * quantity * option.get('gamma', 0) * 100
            net_theta += direction_mult * quantity * option.get('theta', 0) * 100
            net_vega += direction_mult * quantity * option.get('vega', 0) * 100
            
            # Calculate net cost
            mid_price = (option['bid'] + option['ask']) / 2
            net_debit += direction_mult * quantity * mid_price
        
        # Calculate breakeven and max profit/loss
        if self.strategy_type == 'custom_spread' and 'ZEBRA' in self.config.get('name', ''):
            # ZEBRA-specific calculations
            itm_strike = selected_legs.get('long_itm_calls', {}).get('strike', 0)
            otm_strike = selected_legs.get('short_otm_call', {}).get('strike', 0)
            
            max_profit = (otm_strike - itm_strike - net_debit) * 100
            max_loss = net_debit * 100
            breakeven = itm_strike + net_debit
        else:
            # Generic calculations
            max_profit = None
            max_loss = abs(net_debit) * 100
            breakeven = current_price
        
        metrics = {
            'net_delta': round(net_delta, 2),
            'net_gamma': round(net_gamma, 2),
            'net_theta': round(net_theta, 2),
            'net_vega': round(net_vega, 2),
            'net_debit': round(net_debit, 2),
            'max_profit': round(max_profit, 2) if max_profit else None,
            'max_loss': round(max_loss, 2),
            'breakeven': round(breakeven, 2),
            'risk_reward_ratio': round(max_profit / max_loss, 2) if max_profit and max_loss > 0 else None
        }
        
        print(f"\n📈 NET METRICS:")
        print(f"  Delta: {metrics['net_delta']:.1f}")
        print(f"  Debit: ${metrics['net_debit']:.2f}")
        print(f"  Max Loss: ${metrics['max_loss']:.0f}")
        if metrics['max_profit']:
            print(f"  Max Profit: ${metrics['max_profit']:.0f}")
            print(f"  Risk/Reward: 1:{metrics['risk_reward_ratio']:.1f}")
        
        return metrics


def find_zebra_options(data: pd.DataFrame, current_price: float, 
                       config: Dict, current_date: str) -> Optional[Dict]:
    """
    Wrapper function to find ZEBRA spread options
    Compatible with existing backtest engine
    """
    selector = MultiLegSelector(config)
    return selector.find_multi_leg_options(data, current_price, current_date)