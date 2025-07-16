"""
Simple options strategies: long calls, long puts, covered calls, cash-secured puts
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional

import sys
sys.path.append('..')
from strategy_base import SimpleStrategy, Signal, OrderType


class LongCallStrategy(SimpleStrategy):
    """Simple long call strategy"""
    
    def __init__(self, params: Dict[str, Any]):
        super().__init__("Long Call", params)
        
        # Strategy-specific parameters
        self.entry_frequency = params.get('entry_frequency', 5)  # Enter every N days
        self.target_delta = params.get('target_delta', 0.30)
        self.days_since_last_entry = 0
    
    def generate_signals(self, current_data: pd.DataFrame, 
                        market_data: Dict[str, Any]) -> List[Signal]:
        """Generate entry signals for long calls"""
        signals = []
        
        # Only enter if we don't have max positions and enough time has passed
        self.days_since_last_entry += 1
        
        if (len(self.get_open_positions()) < 3 and 
            self.days_since_last_entry >= self.entry_frequency):
            
            # Look for call option with target delta
            calls = current_data[
                (current_data['right'] == 'C') &
                (current_data['dte'] >= self.min_dte) &
                (current_data['dte'] <= self.max_dte) &
                (current_data['delta'] > 0)
            ].copy()
            
            if not calls.empty:
                # Find option closest to target delta
                calls['delta_diff'] = abs(calls['delta'] - self.target_delta)
                
                # Add delta targeting diagnostics
                sorted_calls = calls.sort_values('delta_diff')
                top_candidates = sorted_calls.head(3)
                
                self.logger.info(f"Delta targeting analysis for {self.target_delta:.3f}:")
                self.logger.info(f"  Available calls count: {len(calls)}")
                self.logger.info(f"  Delta range: {calls['delta'].min():.3f} to {calls['delta'].max():.3f}")
                
                for i, (_, candidate) in enumerate(top_candidates.iterrows()):
                    self.logger.info(f"  Candidate {i+1}: Strike={candidate['strike']:.0f}, "
                                   f"Delta={candidate['delta']:.3f}, "
                                   f"DTE={candidate['dte']:.0f}, "
                                   f"Delta_diff={candidate['delta_diff']:.3f}")
                
                best_option = sorted_calls.iloc[0]
                delta_tolerance = self.delta_tolerance  # Use instance tolerance setting
                
                # Check if best option meets delta tolerance
                if best_option['delta_diff'] > delta_tolerance:
                    self.logger.warning(f"⚠️  DELTA TARGET MISS: Target={self.target_delta:.3f}, "
                                      f"Selected={best_option['delta']:.3f}, "
                                      f"Difference={best_option['delta_diff']:.3f} "
                                      f"(exceeds tolerance {delta_tolerance:.3f})")
                else:
                    self.logger.info(f"✅ Delta target achieved: Target={self.target_delta:.3f}, "
                                   f"Selected={best_option['delta']:.3f}, "
                                   f"Difference={best_option['delta_diff']:.3f}")
                
                # Calculate position size
                option_cost = best_option['ask'] * 100  # Cost per contract
                max_contracts = int(self.portfolio_value * self.max_position_size / option_cost)
                quantity = max(1, max_contracts)
                
                signals.append(Signal(
                    signal_type='entry',
                    action='buy',
                    option_criteria={
                        'strike': best_option['strike'],
                        'expiration': best_option['expiration'],
                        'option_type': 'C'
                    },
                    quantity=quantity,
                    reason=f"Long call entry - Target: {self.target_delta:.3f}, Selected: {best_option['delta']:.3f}"
                ))
                
                self.days_since_last_entry = 0
        
        return signals
    
    def should_exit_position(self, position, current_data: pd.DataFrame) -> bool:
        """Exit logic specific to long calls"""
        return super().should_exit_position(position, current_data)


class LongPutStrategy(SimpleStrategy):
    """Simple long put strategy"""
    
    def __init__(self, params: Dict[str, Any]):
        super().__init__("Long Put", params)
        
        # Strategy-specific parameters
        self.entry_frequency = params.get('entry_frequency', 5)
        self.target_delta = params.get('target_delta', -0.30)
        self.days_since_last_entry = 0
        
        # Delta band parameters
        self.use_delta_bands = params.get('use_delta_bands', False)
        if self.use_delta_bands:
            self.delta_min = params.get('delta_min', -0.40)
            self.delta_max = params.get('delta_max', -0.20)
            self.logger.info(f"Using explicit delta bands: {self.delta_min:.3f} to {self.delta_max:.3f}")
        else:
            self.delta_tolerance = params.get('delta_tolerance', 0.05)  # Use parameter or default tolerance
            self.logger.info(f"Using delta threshold: {self.target_delta:.3f} ± {self.delta_tolerance:.3f}")
        
        # Delta targeting statistics
        self.delta_targeting_stats = {
            'total_entries': 0,
            'target_hits': 0,
            'target_misses': 0,
            'rejected_no_match': 0,
            'delta_differences': [],
            'tolerance': self.delta_tolerance if hasattr(self, 'delta_tolerance') else 0.05,
            'use_bands': self.use_delta_bands
        }
    
    def generate_signals(self, current_data: pd.DataFrame, 
                        market_data: Dict[str, Any]) -> List[Signal]:
        """Generate entry signals for long puts"""
        signals = []
        
        self.days_since_last_entry += 1
        
        if (len(self.get_open_positions()) < 3 and 
            self.days_since_last_entry >= self.entry_frequency):
            
            # Look for put option with target delta
            puts = current_data[
                (current_data['right'] == 'P') &
                (current_data['dte'] >= self.min_dte) &
                (current_data['dte'] <= self.max_dte) &
                (current_data['delta'] < 0)
            ].copy()
            
            if not puts.empty:
                # Apply delta filtering based on mode (bands vs threshold)
                if self.use_delta_bands:
                    # Explicit delta bands - strict filtering
                    valid_puts = puts[
                        (puts['delta'] >= self.delta_min) & 
                        (puts['delta'] <= self.delta_max)
                    ].copy()
                    
                    self.logger.info(f"Delta band filtering [{self.delta_min:.3f}, {self.delta_max:.3f}]:")
                    self.logger.info(f"  Total puts available: {len(puts)}")
                    self.logger.info(f"  Puts within band: {len(valid_puts)}")
                    self.logger.info(f"  Available delta range: {puts['delta'].min():.3f} to {puts['delta'].max():.3f}")
                    
                    if valid_puts.empty:
                        self.delta_targeting_stats['rejected_no_match'] += 1
                        self.logger.warning(f"❌ NO ACCEPTABLE OPTIONS: No puts within delta band "
                                          f"[{self.delta_min:.3f}, {self.delta_max:.3f}] - TRADE REJECTED")
                        return signals
                    
                    # Select closest to center of band
                    band_center = (self.delta_min + self.delta_max) / 2
                    valid_puts['delta_diff'] = abs(valid_puts['delta'] - band_center)
                    best_option = valid_puts.loc[valid_puts['delta_diff'].idxmin()]
                    
                    self.delta_targeting_stats['total_entries'] += 1
                    self.delta_targeting_stats['target_hits'] += 1
                    self.delta_targeting_stats['delta_differences'].append(best_option['delta_diff'])
                    
                    self.logger.info(f"✅ DELTA BAND MATCH: Selected={best_option['delta']:.3f} "
                                   f"within band [{self.delta_min:.3f}, {self.delta_max:.3f}]")
                
                else:
                    # Traditional threshold mode with tolerance
                    puts['delta_diff'] = abs(puts['delta'] - self.target_delta)
                    sorted_puts = puts.sort_values('delta_diff')
                    best_option = sorted_puts.iloc[0]
                    
                    # Add delta targeting diagnostics
                    top_candidates = sorted_puts.head(3)
                    self.logger.info(f"Delta threshold targeting {self.target_delta:.3f}:")
                    self.logger.info(f"  Available puts count: {len(puts)}")
                    self.logger.info(f"  Delta range: {puts['delta'].min():.3f} to {puts['delta'].max():.3f}")
                    
                    for i, (_, candidate) in enumerate(top_candidates.iterrows()):
                        self.logger.info(f"  Candidate {i+1}: Strike={candidate['strike']:.0f}, "
                                       f"Delta={candidate['delta']:.3f}, "
                                       f"DTE={candidate['dte']:.0f}, "
                                       f"Delta_diff={candidate['delta_diff']:.3f}")
                    
                    # Update delta targeting statistics
                    self.delta_targeting_stats['total_entries'] += 1
                    self.delta_targeting_stats['delta_differences'].append(best_option['delta_diff'])
                    
                    # Check if best option meets delta tolerance
                    if best_option['delta_diff'] > self.delta_tolerance:
                        self.delta_targeting_stats['target_misses'] += 1
                        self.logger.warning(f"⚠️  DELTA TARGET MISS: Target={self.target_delta:.3f}, "
                                          f"Selected={best_option['delta']:.3f}, "
                                          f"Difference={best_option['delta_diff']:.3f} "
                                          f"(exceeds tolerance {self.delta_tolerance:.3f})")
                    else:
                        self.delta_targeting_stats['target_hits'] += 1
                        self.logger.info(f"✅ Delta target achieved: Target={self.target_delta:.3f}, "
                                       f"Selected={best_option['delta']:.3f}, "
                                       f"Difference={best_option['delta_diff']:.3f}")
                
                # Show selected option details
                self.logger.info(f"  Selected: Strike={best_option['strike']:.0f}, "
                               f"Delta={best_option['delta']:.3f}, "
                               f"DTE={best_option['dte']:.0f}, "
                               f"Bid/Ask={best_option['bid']:.2f}/{best_option['ask']:.2f}")
                
                # Calculate position size
                option_cost = best_option['ask'] * 100
                max_contracts = int(self.portfolio_value * self.max_position_size / option_cost)
                quantity = max(1, max_contracts)
                
                # Create appropriate reason text
                if self.use_delta_bands:
                    reason = f"Long put entry - Band: [{self.delta_min:.3f}, {self.delta_max:.3f}], Selected: {best_option['delta']:.3f}"
                else:
                    reason = f"Long put entry - Target: {self.target_delta:.3f}, Selected: {best_option['delta']:.3f}"
                
                # Prepare selection accuracy metadata
                candidates_list = []
                for i, (_, candidate) in enumerate(top_candidates.iterrows()):
                    candidates_list.append({
                        'rank': i + 1,
                        'strike': float(candidate['strike']),
                        'delta': float(candidate['delta']),
                        'dte': int(candidate['dte']),
                        'delta_diff': float(candidate['delta_diff']),
                        'bid': float(candidate['bid']),
                        'ask': float(candidate['ask'])
                    })
                
                selection_metadata = {
                    'target_delta': self.target_delta,
                    'actual_delta': float(best_option['delta']),
                    'delta_difference': float(best_option['delta_diff']),
                    'tolerance': self.delta_tolerance,
                    'available_options': len(puts),
                    'selection_method': 'delta_bands' if self.use_delta_bands else 'delta_targeting',
                    'best_candidates': candidates_list,
                    'is_compliant': best_option['delta_diff'] <= self.delta_tolerance,
                    'target_dte_min': self.min_dte,
                    'target_dte_max': self.max_dte,
                    'actual_dte': int(best_option['dte'])
                }
                
                signals.append(Signal(
                    signal_type='entry',
                    action='buy',
                    option_criteria={
                        'strike': best_option['strike'],
                        'expiration': best_option['expiration'],
                        'option_type': 'P'
                    },
                    quantity=quantity,
                    reason=reason,
                    selection_metadata=selection_metadata
                ))
                
                self.days_since_last_entry = 0
        
        return signals
    
    def should_exit_position(self, position, current_data: pd.DataFrame) -> bool:
        """Exit logic specific to long puts"""
        return super().should_exit_position(position, current_data)
    
    def get_delta_targeting_summary(self) -> str:
        """Generate delta targeting performance summary"""
        stats = self.delta_targeting_stats
        
        total_attempts = stats['total_entries'] + stats['rejected_no_match']
        
        if total_attempts == 0:
            return "No entry attempts made - no delta targeting data available"
        
        if stats['use_bands']:
            # Delta bands mode summary
            acceptance_rate = (stats['total_entries'] / total_attempts) * 100 if total_attempts > 0 else 0
            
            summary = f"""
📊 DELTA BANDS PERFORMANCE SUMMARY:
  Delta Band: [{self.delta_min:.3f}, {self.delta_max:.3f}]
  Band Width: {abs(self.delta_max - self.delta_min):.3f}
  
  Total Entry Attempts: {total_attempts}
  Successful Entries: {stats['total_entries']} ({acceptance_rate:.1f}%)
  Rejected (No Match): {stats['rejected_no_match']} ({100-acceptance_rate:.1f}%)
  
  🎯 Recommendation: {self._get_delta_bands_recommendation(acceptance_rate)}
            """
        else:
            # Traditional threshold mode summary
            if stats['total_entries'] == 0:
                return "No entries made - no delta targeting data available"
            
            hit_rate = (stats['target_hits'] / stats['total_entries']) * 100
            avg_diff = sum(stats['delta_differences']) / len(stats['delta_differences'])
            max_diff = max(stats['delta_differences'])
            min_diff = min(stats['delta_differences'])
            
            summary = f"""
📊 DELTA THRESHOLD PERFORMANCE SUMMARY:
  Target Delta: {self.target_delta:.3f}
  Tolerance: ±{self.delta_tolerance:.3f}
  
  Total Entries: {stats['total_entries']}
  Target Hits: {stats['target_hits']} ({hit_rate:.1f}%)
  Target Misses: {stats['target_misses']} ({100-hit_rate:.1f}%)
  
  Delta Difference Statistics:
    Average: {avg_diff:.3f}
    Minimum: {min_diff:.3f}
    Maximum: {max_diff:.3f}
  
  🎯 Recommendation: {self._get_delta_targeting_recommendation(hit_rate, avg_diff)}
            """
        
        return summary.strip()
    
    def _get_delta_targeting_recommendation(self, hit_rate: float, avg_diff: float) -> str:
        """Generate recommendations based on delta targeting performance"""
        if hit_rate >= 80:
            return "✅ Excellent delta targeting - strategy is working well"
        elif hit_rate >= 60:
            return "⚠️  Moderate delta targeting - consider tightening selection criteria"
        elif avg_diff > 0.1:
            return "❌ Poor delta targeting - significant adjustment needed to selection logic"
        else:
            return "❌ Poor delta targeting - review available options or adjust target delta"
    
    def _get_delta_bands_recommendation(self, acceptance_rate: float) -> str:
        """Generate recommendations based on delta bands performance"""
        if acceptance_rate >= 80:
            return "✅ Excellent band acceptance - good balance of precision and opportunity"
        elif acceptance_rate >= 60:
            return "⚠️  Moderate acceptance rate - consider widening bands for more trades"
        elif acceptance_rate >= 40:
            return "⚠️  Low acceptance rate - bands may be too narrow for available options"
        else:
            return "❌ Very low acceptance - bands too restrictive, consider widening or different targets"


class StraddleStrategy(SimpleStrategy):
    """Long straddle strategy (buy call + put at same strike)"""
    
    def __init__(self, params: Dict[str, Any]):
        super().__init__("Long Straddle", params)
        
        # Strategy-specific parameters  
        self.entry_frequency = params.get('entry_frequency', 10)
        self.target_delta = params.get('target_delta', 0.50)  # ATM target
        self.max_straddles = params.get('max_straddles', 2)
        self.days_since_last_entry = 0
    
    def generate_signals(self, current_data: pd.DataFrame, 
                        market_data: Dict[str, Any]) -> List[Signal]:
        """Generate entry signals for straddles"""
        signals = []
        
        self.days_since_last_entry += 1
        
        # Count current straddles (positions with both calls and puts)
        current_straddles = self._count_straddles()
        
        if (current_straddles < self.max_straddles and 
            self.days_since_last_entry >= self.entry_frequency):
            
            # Find ATM strike
            underlying_price = current_data['underlying_price'].iloc[0]
            
            # Get calls and puts with similar DTE
            options = current_data[
                (current_data['dte'] >= self.min_dte) &
                (current_data['dte'] <= self.max_dte)
            ].copy()
            
            if not options.empty:
                # Find strike closest to ATM
                options['strike_diff'] = abs(options['strike'] - underlying_price)
                atm_strike = options.loc[options['strike_diff'].idxmin(), 'strike']
                
                # Get call and put at this strike
                atm_options = options[options['strike'] == atm_strike]
                
                call_option = atm_options[atm_options['right'] == 'C']
                put_option = atm_options[atm_options['right'] == 'P']
                
                if not call_option.empty and not put_option.empty:
                    call_data = call_option.iloc[0]
                    put_data = put_option.iloc[0]
                    
                    # Use same expiration
                    if call_data['expiration'] == put_data['expiration']:
                        # Calculate position size based on total straddle cost
                        total_cost = (call_data['ask'] + put_data['ask']) * 100
                        max_contracts = int(self.portfolio_value * self.max_position_size / total_cost)
                        quantity = max(1, max_contracts)
                        
                        # Create signals for both legs
                        signals.append(Signal(
                            signal_type='entry',
                            action='buy',
                            option_criteria={
                                'strike': call_data['strike'],
                                'expiration': call_data['expiration'],
                                'option_type': 'C'
                            },
                            quantity=quantity,
                            reason=f"Long straddle call leg - ${atm_strike:.0f} strike"
                        ))
                        
                        signals.append(Signal(
                            signal_type='entry',
                            action='buy',
                            option_criteria={
                                'strike': put_data['strike'],
                                'expiration': put_data['expiration'],
                                'option_type': 'P'
                            },
                            quantity=quantity,
                            reason=f"Long straddle put leg - ${atm_strike:.0f} strike"
                        ))
                        
                        self.days_since_last_entry = 0
        
        return signals
    
    def _count_straddles(self) -> int:
        """Count number of complete straddles (matching call/put pairs)"""
        positions = self.get_open_positions()
        
        # Group by strike and expiration
        straddle_count = 0
        strike_exp_combinations = {}
        
        for position in positions:
            last_trade = position.trades[-1]
            key = (last_trade.strike, last_trade.expiration)
            
            if key not in strike_exp_combinations:
                strike_exp_combinations[key] = {'C': 0, 'P': 0}
            
            strike_exp_combinations[key][last_trade.option_type] += position.net_quantity
        
        # Count complete straddles (where both C and P > 0)
        for combo in strike_exp_combinations.values():
            if combo['C'] > 0 and combo['P'] > 0:
                straddle_count += min(combo['C'], combo['P'])
        
        return straddle_count
    
    def should_exit_position(self, position, current_data: pd.DataFrame) -> bool:
        """Exit straddle legs together when possible"""
        return super().should_exit_position(position, current_data)


class CoveredCallStrategy(SimpleStrategy):
    """Covered call strategy (assumes we own SPY shares)"""
    
    def __init__(self, params: Dict[str, Any]):
        super().__init__("Covered Call", params)
        
        # Strategy-specific parameters
        self.shares_owned = params.get('shares_owned', 100)  # Assume 100 shares
        self.target_delta = params.get('target_delta', 0.30)  # OTM calls
        self.roll_dte = params.get('roll_dte', 21)  # Roll at 21 DTE
        self.entry_frequency = params.get('entry_frequency', 1)
        self.days_since_last_entry = 0
    
    def generate_signals(self, current_data: pd.DataFrame, 
                        market_data: Dict[str, Any]) -> List[Signal]:
        """Generate covered call signals"""
        signals = []
        
        self.days_since_last_entry += 1
        
        # Only write calls if we don't have short call positions
        current_short_calls = len([p for p in self.get_open_positions() 
                                 if p.net_quantity < 0 and 
                                 p.trades[-1].option_type == 'C'])
        
        if (current_short_calls == 0 and 
            self.days_since_last_entry >= self.entry_frequency):
            
            # Look for OTM call to sell
            underlying_price = current_data['underlying_price'].iloc[0]
            
            calls = current_data[
                (current_data['right'] == 'C') &
                (current_data['dte'] >= self.min_dte) &
                (current_data['dte'] <= self.max_dte) &
                (current_data['strike'] > underlying_price) &  # OTM
                (current_data['delta'] > 0) &
                (current_data['delta'] <= self.target_delta)
            ].copy()
            
            if not calls.empty:
                # Find call closest to target delta
                calls['delta_diff'] = abs(calls['delta'] - self.target_delta)
                best_call = calls.loc[calls['delta_diff'].idxmin()]
                
                # Sell calls equivalent to shares owned
                contracts_to_sell = self.shares_owned // 100
                
                signals.append(Signal(
                    signal_type='entry',
                    action='sell',
                    option_criteria={
                        'strike': best_call['strike'],
                        'expiration': best_call['expiration'],
                        'option_type': 'C'
                    },
                    quantity=contracts_to_sell,
                    reason=f"Covered call - {self.target_delta:.2f} delta OTM call"
                ))
                
                self.days_since_last_entry = 0
        
        return signals
    
    def should_exit_position(self, position, current_data: pd.DataFrame) -> bool:
        """Exit covered calls at target profit or roll"""
        last_trade = position.trades[-1]
        
        # Find current option price
        option_data = self._find_option_in_data(
            current_data, last_trade.strike, 
            last_trade.option_type, last_trade.expiration
        )
        
        if option_data is None:
            return True
        
        # Roll at specific DTE
        if option_data['dte'] <= self.roll_dte:
            return True
        
        # Check profit target (for short calls, profit when price decreases)
        current_price = option_data['mid_price']
        entry_price = position.average_entry_price
        
        if position.net_quantity < 0:  # Short position
            pnl_pct = (entry_price - current_price) / entry_price
            
            # Close if 50% profit target hit
            if pnl_pct >= 0.50:
                return True
        
        return False