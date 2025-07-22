"""
Option selection and position sizing for backtesting
Handles delta/DTE/liquidity filtering and position size calculations
"""

import pandas as pd
from typing import Dict, Optional, Tuple


def find_suitable_options(data, current_price: float, config: Dict, current_date: str) -> Optional[pd.Series]:
    """Option selection with delta, DTE, and liquidity filters
    
    Args:
        data: DataFrame with options data for current date
        current_price: Current underlying price
        config: Strategy configuration dict
        current_date: Current date string
        
    Returns:
        Selected option as pandas Series or None if no suitable option found
    """
    print(f"🔍 AUDIT: Option selection started")
    print(f"💰 AUDIT: Underlying: ${current_price:.2f}")
    
    selection_process = {
        'total_options': 0,
        'after_dte_filter': 0,
        'after_delta_filter': 0,
        'after_liquidity_filter': 0
    }
    
    # Extract criteria
    selection_config = config.get('option_selection', {})
    delta_criteria = selection_config.get('delta_criteria', {})
    target_delta = delta_criteria.get('target', 0.30)
    delta_tolerance = delta_criteria.get('tolerance', 0.05)
    
    dte_criteria = selection_config.get('dte_criteria', {})
    target_dte = dte_criteria.get('target', 45)
    min_dte = dte_criteria.get('minimum', 30)
    max_dte = dte_criteria.get('maximum', 60)
    
    liquidity_criteria = selection_config.get('liquidity_criteria', {})
    min_volume = liquidity_criteria.get('min_volume', 100)
    max_spread_pct = liquidity_criteria.get('max_spread_pct', 0.15)
    
    # Determine option type based on strategy
    option_right = 'P' if config['strategy_type'] in ["long_put", "short_call", "protective_put"] else 'C'
    
    options = data[data['right'] == option_right].copy()
    selection_process['total_options'] = len(options)
    print(f"📊 AUDIT: {len(options)} {option_right} options")
    
    # Filter by DTE
    options['expiration_date'] = pd.to_datetime(options['expiration'])
    options['dte'] = (options['expiration_date'] - pd.to_datetime(current_date)).dt.days
    
    dte_filtered = options[(options['dte'] >= min_dte) & (options['dte'] <= max_dte)].copy()
    selection_process['after_dte_filter'] = len(dte_filtered)
    print(f"📅 AUDIT: After DTE filter: {len(dte_filtered)} options")
    
    if dte_filtered.empty:
        return None
    
    # Filter by delta
    if 'delta' in dte_filtered.columns:
        delta_filtered = dte_filtered[
            (dte_filtered['delta'] >= target_delta - delta_tolerance) &
            (dte_filtered['delta'] <= target_delta + delta_tolerance)
        ].copy()
        selection_process['after_delta_filter'] = len(delta_filtered)
        print(f"🎯 AUDIT: After delta filter: {len(delta_filtered)} options")
    else:
        # Fallback to strike-based selection
        print(f"⚠️ AUDIT: Using strike-based selection")
        target_strike = current_price * (0.98 if option_right == 'P' else 1.02)
        strike_tolerance = current_price * 0.05
        delta_filtered = dte_filtered[
            (dte_filtered['strike_dollars'] >= target_strike - strike_tolerance) &
            (dte_filtered['strike_dollars'] <= target_strike + strike_tolerance)
        ].copy()
    
    if delta_filtered.empty:
        return None
    
    # Calculate spreads and apply liquidity filter
    delta_filtered['spread'] = delta_filtered['ask'] - delta_filtered['bid']
    delta_filtered['mid_price'] = (delta_filtered['bid'] + delta_filtered['ask']) / 2
    delta_filtered['spread_pct'] = delta_filtered['spread'] / delta_filtered['mid_price']
    
    liquid_options = delta_filtered[
        (delta_filtered['volume'] >= min_volume) &
        (delta_filtered['bid'] > 0) &
        (delta_filtered['spread_pct'] <= max_spread_pct)
    ].copy()
    
    selection_process['after_liquidity_filter'] = len(liquid_options)
    print(f"💧 AUDIT: After liquidity filter: {len(liquid_options)} options")
    
    if liquid_options.empty:
        # Try relaxed criteria
        if selection_config.get('allow_relaxation', True):
            print(f"⚠️ AUDIT: Trying relaxed criteria")
            relaxed_volume = min_volume // 2
            liquid_options = delta_filtered[
                (delta_filtered['volume'] >= relaxed_volume) &
                (delta_filtered['bid'] > 0)
            ].copy()
            print(f"💧 AUDIT: With relaxed volume: {len(liquid_options)} options")
    
    if liquid_options.empty:
        return None
    
    # Score and select best option
    liquid_options['score'] = _score_option(liquid_options, target_delta, delta_tolerance, max_spread_pct)
    
    # Check current positions to avoid duplicates
    current_positions = config.get('_current_positions', [])
    
    for _, option in liquid_options.nlargest(len(liquid_options), 'score').iterrows():
        already_held = any(
            pos['strike'] == option['strike_dollars'] and pos['expiration'] == option['expiration']
            for pos in current_positions
        )
        
        if not already_held:
            best_option = option
            break
    else:
        print(f"⚠️ AUDIT: All suitable options already held")
        return None
    
    print(f"✅ AUDIT: Selected option:")
    print(f"   Strike: ${best_option['strike_dollars']:.2f}")
    print(f"   DTE: {best_option['dte']}")
    print(f"   Price: ${best_option['close']:.2f}")
    
    best_option['selection_process'] = selection_process
    return best_option


def _score_option(options: pd.DataFrame, target_delta: float, delta_tolerance: float, 
                 max_spread_pct: float) -> pd.Series:
    """Score options for selection based on delta, liquidity, and spread
    
    Args:
        options: DataFrame of options to score
        target_delta: Target delta value
        delta_tolerance: Acceptable delta deviation
        max_spread_pct: Maximum acceptable spread percentage
        
    Returns:
        Series of scores for each option
    """
    # Normalize scores
    liquidity_score = options['volume'] / options['volume'].max()
    spread_score = 1 - (options['spread_pct'] / max_spread_pct)
    
    if 'delta' in options.columns:
        delta_score = 1 - abs(options['delta'] - target_delta) / delta_tolerance
    else:
        # Use moneyness for strike-based scoring
        underlying_price = options.iloc[0]['underlying_price']
        target_strike = underlying_price * 1.02  # Assuming OTM call
        delta_score = 1 - abs(options['strike_dollars'] - target_strike) / (underlying_price * 0.05)
    
    # Combined score with configurable weights
    weights = {'liquidity': 0.3, 'spread': 0.3, 'delta': 0.4}
    return (
        liquidity_score * weights['liquidity'] + 
        spread_score * weights['spread'] + 
        delta_score * weights['delta']
    )


def calculate_position_size(cash: float, option_price: float, position_size_pct: float, 
                          max_contracts: int = 100) -> Tuple[int, float]:
    """Calculate position size based on available cash and risk parameters
    
    Args:
        cash: Available cash
        option_price: Price per option contract
        position_size_pct: Percentage of capital to allocate
        max_contracts: Maximum contracts allowed
        
    Returns:
        Tuple of (contracts, actual_cost)
    """
    print(f"🔍 AUDIT: Position sizing")
    print(f"💰 AUDIT: Cash: ${cash:,.2f}")
    print(f"💵 AUDIT: Option: ${option_price:.2f}")
    
    # Calculate max loss per contract (options are 100 shares)
    max_loss_per_contract = option_price * 100
    
    # Calculate target position value
    target_position_value = cash * position_size_pct
    
    # Calculate number of contracts
    contracts = int(target_position_value / max_loss_per_contract)
    contracts = min(contracts, max_contracts)
    
    # Calculate actual cost
    actual_cost = contracts * option_price * 100
    
    print(f"📈 AUDIT: Contracts: {contracts}")
    print(f"💳 AUDIT: Cost: ${actual_cost:.2f}")
    
    return contracts, actual_cost