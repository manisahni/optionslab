"""
Exit condition strategies for options backtesting
Handles profit targets, stop losses, technical exits, and time-based exits
"""

from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class Position:
    """Simplified position data for exit checking"""
    entry_date: str
    strike: float
    expiration: str
    option_type: str  # 'C' or 'P'
    option_price: float
    contracts: int
    days_held: int
    entry_delta: Optional[float] = None
    current_delta: Optional[float] = None
    entry_iv: Optional[float] = None
    current_iv: Optional[float] = None


class ExitConditions:
    """Manages all exit condition checks for positions"""
    
    def __init__(self, config: Dict, market_filters=None):
        self.config = config
        self.exit_rules = config.get('exit_rules', [])
        self.max_hold_days = config['parameters'].get('max_hold_days', 30)
        self.market_filters = market_filters
        
        # Pre-process exit rules by condition type for efficiency
        self.rules_by_type = {}
        for rule in self.exit_rules:
            condition = rule.get('condition')
            if condition:
                self.rules_by_type[condition] = rule
    
    def check_all_exits(self, position: Position, current_pnl: float, current_pnl_pct: float,
                       current_price: float, date_idx: int) -> Tuple[bool, Optional[str]]:
        """Check all exit conditions for a position
        
        Returns:
            Tuple of (should_exit: bool, exit_reason: str or None)
        """
        # Check profit target
        should_exit, reason = self.check_profit_target(current_pnl_pct)
        if should_exit:
            return True, reason
        
        # Check stop loss
        should_exit, reason = self.check_stop_loss(current_pnl_pct)
        if should_exit:
            return True, reason
        
        # Check delta stop
        should_exit, reason = self.check_delta_stop(position)
        if should_exit:
            return True, reason
        
        # Check technical exits (RSI, Bollinger Bands)
        should_exit, reason = self.check_technical_exits(position, current_price, date_idx)
        if should_exit:
            return True, reason
        
        # Check time stop
        should_exit, reason = self.check_time_stop(position)
        if should_exit:
            return True, reason
        
        return False, None
    
    def check_profit_target(self, current_pnl_pct: float) -> Tuple[bool, Optional[str]]:
        """Check if profit target is hit"""
        rule = self.rules_by_type.get('profit_target')
        if rule:
            target = rule.get('target_percent', 50)
            if current_pnl_pct >= target:
                return True, f"profit target ({current_pnl_pct:.1f}% >= {target}%)"
        return False, None
    
    def check_stop_loss(self, current_pnl_pct: float) -> Tuple[bool, Optional[str]]:
        """Check if stop loss is hit"""
        rule = self.rules_by_type.get('stop_loss')
        if rule:
            stop = rule.get('stop_percent', -30)
            if current_pnl_pct <= stop:
                return True, f"stop loss ({current_pnl_pct:.1f}% <= {stop}%)"
        return False, None
    
    def check_delta_stop(self, position: Position) -> Tuple[bool, Optional[str]]:
        """Check if delta stop is hit"""
        rule = self.rules_by_type.get('delta_stop')
        if not rule or position.current_delta is None:
            return False, None
        
        min_delta = rule.get('min_delta', 0.10)
        
        # IV adjustment if configured
        if rule.get('iv_adjusted', False) and position.current_iv and position.entry_iv:
            iv_ratio = position.current_iv / position.entry_iv
            # Higher IV means we can accept lower delta
            adjusted_min_delta = min_delta * (2 - iv_ratio)
            adjusted_min_delta = max(0.05, min(0.20, adjusted_min_delta))
        else:
            adjusted_min_delta = min_delta
        
        # Check based on option type
        if position.option_type == 'C':
            # Calls - check if delta dropped too low
            if position.current_delta < adjusted_min_delta:
                return True, f"delta stop (delta {position.current_delta:.3f} < {adjusted_min_delta:.3f})"
        else:
            # Puts - check if absolute delta dropped too low
            if abs(position.current_delta) < adjusted_min_delta:
                return True, f"delta stop (|delta| {abs(position.current_delta):.3f} < {adjusted_min_delta:.3f})"
        
        return False, None
    
    def check_time_stop(self, position: Position) -> Tuple[bool, Optional[str]]:
        """Check if time stop is hit"""
        if position.days_held >= self.max_hold_days:
            return True, f"time stop ({position.days_held} days)"
        return False, None
    
    def check_technical_exits(self, position: Position, current_price: float, 
                            date_idx: int) -> Tuple[bool, Optional[str]]:
        """Check RSI and Bollinger Band exit conditions"""
        # Check RSI exit
        rule = self.rules_by_type.get('rsi_exit')
        if rule and self.market_filters:
            rsi = self.market_filters.calculate_current_rsi(date_idx)
            if rsi is not None:
                exit_level = rule.get('exit_level', 50)
                
                if position.option_type == 'C':  # Calls
                    if rule.get('exit_on_overbought', True) and rsi >= exit_level:
                        return True, f"RSI exit (RSI {rsi:.1f} >= {exit_level})"
                else:  # Puts
                    if rule.get('exit_on_oversold', True) and rsi <= exit_level:
                        return True, f"RSI exit (RSI {rsi:.1f} <= {exit_level})"
        
        # Check Bollinger Band exit
        rule = self.rules_by_type.get('bollinger_exit')
        if rule and self.market_filters:
            bands = self.market_filters.calculate_current_bollinger_bands(date_idx)
            if bands:
                middle_band, upper_band, lower_band = bands
                if upper_band > lower_band:
                    band_position = (current_price - lower_band) / (upper_band - lower_band)
                    
                    if position.option_type == 'C':  # Calls
                        exit_threshold = rule.get('exit_at_band_pct', 0.9)
                        if band_position >= exit_threshold:
                            return True, f"BB exit (price at {band_position:.1%} >= {exit_threshold:.0%})"
                    else:  # Puts
                        exit_threshold = rule.get('exit_at_band_pct', 0.1)
                        if band_position <= exit_threshold:
                            return True, f"BB exit (price at {band_position:.1%} <= {exit_threshold:.0%})"
        
        return False, None
    
    def format_exit_log(self, exit_reason: str, exit_price: float, proceeds: float, 
                       pnl: float, pnl_pct: float) -> List[str]:
        """Format exit information for logging"""
        return [
            f"Exiting position - Reason: {exit_reason}",
            f"Exit price: ${exit_price:.2f}",
            f"Proceeds: ${proceeds:.2f}",
            f"P&L: ${pnl:.2f} ({pnl_pct:.1f}%)"
        ]