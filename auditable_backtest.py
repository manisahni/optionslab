#!/usr/bin/env python3
"""
Simple, Auditable Backtest Script
This script runs a basic long call strategy with full data flow tracing.
Every step is logged so we can audit the entire process.
"""

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec

def load_and_audit_data(file_path):
    """Load parquet data and audit its contents"""
    print(f"🔍 AUDIT: Loading data from {file_path}")
    
    try:
        df = pd.read_parquet(file_path)
        print(f"✅ AUDIT: Successfully loaded {len(df)} records")
    except Exception as e:
        # Try fastparquet if default fails
        try:
            print(f"⚠️ AUDIT: Default parser failed ({e}), trying fastparquet...")
            df = pd.read_parquet(file_path, engine='fastparquet')
            print(f"✅ AUDIT: Successfully loaded {len(df)} records with fastparquet")
        except Exception as e2:
            print(f"❌ AUDIT: Failed to load data: {e}")
            print(f"❌ AUDIT: Fastparquet also failed: {e2}")
            return None
    
    # Audit the loaded data
    print(f"📊 AUDIT: Columns: {list(df.columns)}")
    print(f"📅 AUDIT: Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"💰 AUDIT: Underlying price range: ${df['underlying_price'].min():.2f} to ${df['underlying_price'].max():.2f}")
    print(f"📈 AUDIT: Strike price range: ${df['strike'].min()/1000:.2f} to ${df['strike'].max()/1000:.2f}")
    
    # Sample data for verification
    print(f"🔍 AUDIT: Sample call options:")
    calls = df[df['right'] == 'C'].head(3)
    for _, row in calls.iterrows():
        print(f"   Strike: ${row['strike']/1000:.2f}, Price: ${row['close']:.2f}, IV: {row['implied_vol']:.3f}")
    
    return df


def load_multi_day_data(data_dir, start_date, end_date):
    """Load multiple days of parquet data for date range"""
    print(f"🔍 AUDIT: Loading multi-day data from {start_date} to {end_date}")
    
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"❌ AUDIT: Data directory not found: {data_dir}")
        return None
    
    # Convert dates to datetime objects
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # Find all parquet files in the date range
    all_data = []
    files_loaded = 0
    
    # Try both main and repaired directories
    for subdir in ['', 'repaired']:
        search_path = data_path / subdir if subdir else data_path
        if not search_path.exists():
            continue
            
        for file in sorted(search_path.glob("spy_options_eod_*.parquet")):
            # Extract date from filename
            date_str = file.stem.split('_')[-1]
            try:
                file_date = pd.to_datetime(date_str, format='%Y%m%d')
                
                # Check if file is within date range
                if start_dt <= file_date <= end_dt:
                    print(f"\n📁 AUDIT: Loading file for {file_date.strftime('%Y-%m-%d')}")
                    
                    # Load the file
                    try:
                        df = pd.read_parquet(file)
                        print(f"✅ AUDIT: Loaded {len(df)} records")
                    except Exception as e:
                        # Try fastparquet if default fails
                        try:
                            print(f"⚠️ AUDIT: Default parser failed, trying fastparquet...")
                            df = pd.read_parquet(file, engine='fastparquet')
                            print(f"✅ AUDIT: Loaded {len(df)} records with fastparquet")
                        except Exception as e2:
                            print(f"❌ AUDIT: Failed to load {file.name}: {e2}")
                            continue
                    
                    all_data.append(df)
                    files_loaded += 1
                    
            except Exception as e:
                print(f"⚠️ AUDIT: Skipping {file.name} - couldn't parse date: {e}")
    
    if not all_data:
        print(f"❌ AUDIT: No data files found for date range {start_date} to {end_date}")
        return None
    
    # Combine all dataframes
    print(f"\n🔄 AUDIT: Combining {files_loaded} files...")
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Sort by date
    combined_df = combined_df.sort_values('date').reset_index(drop=True)
    
    # Audit combined data
    print(f"✅ AUDIT: Combined dataset: {len(combined_df)} total records")
    print(f"📅 AUDIT: Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    print(f"📊 AUDIT: Unique dates: {combined_df['date'].nunique()}")
    
    return combined_df

def audit_strategy_config(config_path):
    """Load and audit strategy configuration"""
    print(f"🔍 AUDIT: Loading strategy config from {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"✅ AUDIT: Strategy: {config['name']}")
        print(f"📝 AUDIT: Description: {config['description']}")
        print(f"🎯 AUDIT: Type: {config['strategy_type']}")
        print(f"💰 AUDIT: Initial Capital: ${config['parameters']['initial_capital']:,.2f}")
        print(f"📊 AUDIT: Position Size: {config['parameters']['position_size']*100}%")
        
        return config
    except Exception as e:
        print(f"❌ AUDIT: Failed to load config: {e}")
        return None

def find_suitable_options(data, current_price, strategy_type="long_call", target_strike_offset=0.02):
    """Find suitable options and audit the selection process"""
    print(f"🔍 AUDIT: Finding suitable options for {strategy_type}")
    print(f"💰 AUDIT: Current underlying price: ${current_price:.2f}")
    
    # Determine option type based on strategy
    if strategy_type in ["long_put", "short_call", "protective_put"]:
        option_right = 'P'
        option_type_name = "put"
        # For puts, target strike is below current price
        if strategy_type == "long_put":
            target_strike_offset = -abs(target_strike_offset)
    else:
        option_right = 'C'
        option_type_name = "call"
    
    # Filter for appropriate option type
    options = data[data['right'] == option_right]
    print(f"📊 AUDIT: Found {len(options)} {option_type_name} options")
    
    # Calculate target strike
    target_strike = current_price * (1 + target_strike_offset)
    print(f"🎯 AUDIT: Target strike: ${target_strike:.2f}")
    
    # Find options within reasonable range
    strike_range = 0.05  # 5% range
    suitable = options[
        (options['strike_dollars'] >= current_price * (1 - strike_range)) &
        (options['strike_dollars'] <= current_price * (1 + strike_range)) &
        (options['close'] > 0) &
        (options['implied_vol'] > 0)
    ]
    
    print(f"✅ AUDIT: Found {len(suitable)} suitable options")
    
    if not suitable.empty:
        # Select closest to target strike
        suitable = suitable.copy()  # Create a copy to avoid SettingWithCopyWarning
        suitable['strike_diff'] = abs(suitable['strike_dollars'] - target_strike)
        selected = suitable.loc[suitable['strike_diff'].idxmin()]
        
        print(f"🎯 AUDIT: Selected option:")
        print(f"   Type: {option_type_name.upper()}")
        print(f"   Strike: ${selected['strike_dollars']:.2f}")
        print(f"   Price: ${selected['close']:.2f}")
        print(f"   IV: {selected['implied_vol']:.3f}")
        print(f"   Expiration: {selected['expiration']}")
        
        return selected
    else:
        print(f"❌ AUDIT: No suitable options found")
        return None

def find_suitable_options_advanced(data, current_price, config, current_date):
    """Advanced option selection with delta, DTE, and liquidity filters"""
    print(f"🔍 AUDIT: Advanced option selection started")
    print(f"💰 AUDIT: Current underlying price: ${current_price:.2f}")
    print(f"📅 AUDIT: Current date: {current_date}")
    
    # Extract selection criteria from config
    selection_config = config.get('option_selection', {})
    method = selection_config.get('method', 'delta')
    
    # Get criteria with defaults
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
    strategy_type = config.get('strategy_type', 'long_call')
    if strategy_type in ["long_put", "short_call", "protective_put"]:
        option_right = 'P'
        option_type_name = "put"
        # For puts, adjust delta target (puts have negative delta)
        if method == 'delta':
            target_delta = -abs(target_delta)  # Make negative for puts
    else:
        option_right = 'C'
        option_type_name = "call"
    
    options = data[data['right'] == option_right].copy()
    print(f"📊 AUDIT: Starting with {len(options)} {option_type_name} options")
    
    # Step 1: Calculate DTE and filter
    options['expiration_date'] = pd.to_datetime(options['expiration'])
    options['dte'] = (options['expiration_date'] - pd.to_datetime(current_date)).dt.days
    
    dte_filtered = options[(options['dte'] >= min_dte) & (options['dte'] <= max_dte)].copy()
    print(f"📅 AUDIT: After DTE filter ({min_dte}-{max_dte} days): {len(dte_filtered)} options")
    
    if dte_filtered.empty:
        print(f"❌ AUDIT: No options found in DTE range")
        return None
    
    # Step 2: Apply delta filter if using delta method
    if method == 'delta' and 'delta' in dte_filtered.columns:
        delta_filtered = dte_filtered[
            (dte_filtered['delta'] >= target_delta - delta_tolerance) &
            (dte_filtered['delta'] <= target_delta + delta_tolerance)
        ].copy()
        print(f"🎯 AUDIT: After delta filter ({target_delta}±{delta_tolerance}): {len(delta_filtered)} options")
    else:
        # Fallback to strike-based selection
        print(f"⚠️ AUDIT: Using strike-based selection (delta not available or not requested)")
        # For puts, target strike is below current price
        if option_right == 'P':
            target_strike = current_price * 0.98  # 2% OTM put
        else:
            target_strike = current_price * 1.02  # 2% OTM call
        strike_tolerance = current_price * 0.05  # 5% range
        delta_filtered = dte_filtered[
            (dte_filtered['strike_dollars'] >= target_strike - strike_tolerance) &
            (dte_filtered['strike_dollars'] <= target_strike + strike_tolerance)
        ].copy()
        print(f"🎯 AUDIT: After strike filter: {len(delta_filtered)} options")
    
    if delta_filtered.empty:
        print(f"❌ AUDIT: No options found in delta/strike range")
        return None
    
    # Step 3: Calculate bid-ask spread and apply liquidity filters
    delta_filtered['spread'] = delta_filtered['ask'] - delta_filtered['bid']
    delta_filtered['mid_price'] = (delta_filtered['bid'] + delta_filtered['ask']) / 2
    delta_filtered['spread_pct'] = delta_filtered['spread'] / delta_filtered['mid_price']
    
    # Apply liquidity filters
    liquid_options = delta_filtered[
        (delta_filtered['volume'] >= min_volume) &
        (delta_filtered['bid'] > 0) &  # Has a bid
        (delta_filtered['spread_pct'] <= max_spread_pct)
    ].copy()
    
    print(f"💧 AUDIT: After liquidity filter (vol>={min_volume}, spread<={max_spread_pct*100}%): {len(liquid_options)} options")
    
    # Step 4: If no options pass all filters, try relaxation
    if liquid_options.empty and selection_config.get('allow_relaxation', True):
        print(f"⚠️ AUDIT: No options meet all criteria, trying relaxed filters")
        
        # Relax volume requirement
        relaxed_volume = min_volume // 2
        liquid_options = delta_filtered[
            (delta_filtered['volume'] >= relaxed_volume) &
            (delta_filtered['bid'] > 0)
        ].copy()
        print(f"💧 AUDIT: With relaxed volume (>={relaxed_volume}): {len(liquid_options)} options")
    
    if liquid_options.empty:
        print(f"❌ AUDIT: No liquid options found even with relaxed criteria")
        return None
    
    # Step 5: Score and select best option
    # Score based on multiple factors
    liquid_options['liquidity_score'] = liquid_options['volume'] / liquid_options['volume'].max()
    liquid_options['spread_score'] = 1 - (liquid_options['spread_pct'] / max_spread_pct)
    
    # If using delta method, score by how close to target
    if method == 'delta' and 'delta' in liquid_options.columns:
        liquid_options['delta_score'] = 1 - abs(liquid_options['delta'] - target_delta) / delta_tolerance
    else:
        # Score by moneyness for strike-based
        liquid_options['delta_score'] = 1 - abs(liquid_options['strike_dollars'] - current_price * 1.02) / (current_price * 0.05)
    
    # Combined score (weights can be configured)
    liquid_options['total_score'] = (
        liquid_options['liquidity_score'] * 0.3 +
        liquid_options['spread_score'] * 0.3 +
        liquid_options['delta_score'] * 0.4
    )
    
    # Select highest scoring option not already in positions
    # First, get list of current position strikes and expirations
    current_positions = config.get('_current_positions', [])
    
    for _, option in liquid_options.nlargest(len(liquid_options), 'total_score').iterrows():
        # Check if this option is already held
        already_held = False
        for pos in current_positions:
            if (pos['strike'] == option['strike_dollars'] and 
                pos['expiration'] == option['expiration']):
                already_held = True
                break
        
        if not already_held:
            best_option = option
            break
    else:
        # All options are already held
        print(f"⚠️ AUDIT: All suitable options are already in positions")
        return None
    
    print(f"✅ AUDIT: Selected best option:")
    print(f"   Strike: ${best_option['strike_dollars']:.2f}")
    print(f"   Expiration: {best_option['expiration']} (DTE: {best_option['dte']})")
    print(f"   Delta: {best_option.get('delta', 'N/A')}")
    print(f"   Price: ${best_option['close']:.2f} (Bid: ${best_option['bid']:.2f}, Ask: ${best_option['ask']:.2f})")
    print(f"   Volume: {best_option['volume']}")
    print(f"   Spread: ${best_option['spread']:.2f} ({best_option['spread_pct']*100:.1f}%)")
    print(f"   Score: {best_option['total_score']:.3f}")
    
    return best_option


def calculate_position_size(cash, option_price, position_size_pct, max_contracts=100):
    """Calculate position size and audit the calculation"""
    print(f"🔍 AUDIT: Calculating position size")
    print(f"💰 AUDIT: Available cash: ${cash:,.2f}")
    print(f"📊 AUDIT: Position size %: {position_size_pct*100}%")
    print(f"💵 AUDIT: Option price: ${option_price:.2f}")
    
    # Calculate max loss per contract
    max_loss_per_contract = option_price * 100
    print(f"💸 AUDIT: Max loss per contract: ${max_loss_per_contract:.2f}")
    
    # Calculate target position value
    target_position_value = cash * position_size_pct
    print(f"🎯 AUDIT: Target position value: ${target_position_value:.2f}")
    
    # Calculate number of contracts
    contracts = int(target_position_value / max_loss_per_contract)
    contracts = min(contracts, max_contracts)  # Cap at max contracts
    
    print(f"📈 AUDIT: Contracts to buy: {contracts}")
    
    # Calculate actual cost
    actual_cost = contracts * option_price * 100
    print(f"💳 AUDIT: Actual cost: ${actual_cost:.2f}")
    
    return contracts, actual_cost

def run_auditable_backtest(data_file, config_file, start_date, end_date):
    """Run a fully auditable backtest"""
    print("🚀 AUDIT: Starting auditable backtest")
    print("=" * 60)
    
    # Step 1: Load and audit data
    # Check if data_file is a directory (multi-day) or single file
    data_path = Path(data_file)
    
    if data_path.is_dir():
        # Multi-day backtest
        print(f"📅 AUDIT: Multi-day backtest mode - loading data from {start_date} to {end_date}")
        data = load_multi_day_data(data_file, start_date, end_date)
    else:
        # Single file backtest (legacy mode)
        print(f"📄 AUDIT: Single-file backtest mode")
        data = load_and_audit_data(data_file)
        
    if data is None:
        return None
    
    # Add strike_dollars column consistently
    data = data.copy()
    data['strike_dollars'] = data['strike'] / 1000.0
    
    # Step 2: Load and audit strategy config
    config = audit_strategy_config(config_file)
    if config is None:
        return None
    
    print("=" * 60)
    print("📊 AUDIT: Initializing backtest")
    
    # Initialize portfolio
    initial_capital = config['parameters']['initial_capital']
    cash = initial_capital
    positions = []
    trades = []
    equity_curve = []
    last_entry_date = None  # Track last entry for calendar-based frequency
    
    print(f"💰 AUDIT: Initial capital: ${initial_capital:,.2f}")
    print(f"💳 AUDIT: Starting cash: ${cash:,.2f}")
    
    # Get unique dates
    unique_dates = sorted(data['date'].unique())
    print(f"📅 AUDIT: Trading on {len(unique_dates)} unique dates")
    
    # Run backtest
    for i, current_date in enumerate(unique_dates):
        print(f"\n📅 AUDIT: Processing date {current_date}")
        
        # Get data for current date
        date_data = data[data['date'] == current_date]
        if date_data.empty:
            print(f"⚠️ AUDIT: No data for {current_date}")
            continue
        
        current_price = date_data['underlying_price'].iloc[0]
        print(f"💰 AUDIT: Current underlying price: ${current_price:.2f}")
        
        # Entry logic - check based on calendar days
        entry_frequency = config['parameters'].get('entry_frequency', 3)  # Default 3 days
        
        # Calculate days since last entry
        if last_entry_date is None:
            days_since_entry = float('inf')  # First entry allowed
        else:
            days_since_entry = (pd.to_datetime(current_date) - pd.to_datetime(last_entry_date)).days
        
        # Check if we should consider entry
        max_positions = config['parameters'].get('max_positions', 1)  # Default to 1 for backward compatibility
        
        # Check IV-based market regime filter
        iv_filter_passed = True
        if 'market_filters' in config and 'iv_regime' in config['market_filters']:
            iv_filter = config['market_filters']['iv_regime']
            # Calculate average IV for at-the-money options
            atm_options = date_data[
                (abs(date_data['strike_dollars'] - current_price) <= current_price * 0.02) &  # Within 2% of ATM
                (date_data['implied_vol'] > 0)
            ]
            
            if not atm_options.empty:
                avg_iv = atm_options['implied_vol'].mean()
                min_iv = iv_filter.get('min_iv', 0.10)
                max_iv = iv_filter.get('max_iv', 0.50)
                
                if avg_iv < min_iv or avg_iv > max_iv:
                    iv_filter_passed = False
                    print(f"⚠️ AUDIT: IV regime filter blocked entry - Avg IV: {avg_iv:.3f} (allowed: {min_iv:.3f}-{max_iv:.3f})")
                else:
                    print(f"✅ AUDIT: IV regime filter passed - Avg IV: {avg_iv:.3f}")
        
        # Check MA-based trend filter
        ma_filter_passed = True
        if 'market_filters' in config and 'trend_filter' in config['market_filters']:
            trend_filter = config['market_filters']['trend_filter']
            ma_period = trend_filter.get('ma_period', 20)
            require_above_ma = trend_filter.get('require_above_ma', True)
            
            # Calculate MA if we have enough history
            if i >= ma_period - 1:
                # Get historical prices
                ma_prices = []
                for j in range(ma_period):
                    hist_idx = i - j
                    if hist_idx >= 0:
                        hist_date = unique_dates[hist_idx]
                        hist_data = data[data['date'] == hist_date]
                        if not hist_data.empty:
                            ma_prices.append(hist_data['underlying_price'].iloc[0])
                
                if len(ma_prices) == ma_period:
                    ma_value = sum(ma_prices) / len(ma_prices)
                    
                    if require_above_ma and current_price < ma_value:
                        ma_filter_passed = False
                        print(f"⚠️ AUDIT: MA trend filter blocked entry - Price ${current_price:.2f} < MA({ma_period}) ${ma_value:.2f}")
                    elif not require_above_ma and current_price > ma_value:
                        ma_filter_passed = False
                        print(f"⚠️ AUDIT: MA trend filter blocked entry - Price ${current_price:.2f} > MA({ma_period}) ${ma_value:.2f}")
                    else:
                        print(f"✅ AUDIT: MA trend filter passed - Price ${current_price:.2f} vs MA({ma_period}) ${ma_value:.2f}")
                else:
                    print(f"⚠️ AUDIT: Not enough data for MA({ma_period}) calculation")
        
        # Check RSI filter
        rsi_filter_passed = True
        if 'market_filters' in config and 'rsi_filter' in config['market_filters']:
            rsi_filter = config['market_filters']['rsi_filter']
            rsi_period = rsi_filter.get('period', 14)
            rsi_oversold = rsi_filter.get('oversold', 30)
            rsi_overbought = rsi_filter.get('overbought', 70)
            
            # Calculate RSI if we have enough history
            if i >= rsi_period:
                # Get price changes
                price_changes = []
                for j in range(rsi_period + 1):
                    hist_idx = i - j
                    if hist_idx >= 0 and hist_idx > 0:
                        curr_date = unique_dates[hist_idx]
                        prev_date = unique_dates[hist_idx - 1]
                        curr_data = data[data['date'] == curr_date]
                        prev_data = data[data['date'] == prev_date]
                        if not curr_data.empty and not prev_data.empty:
                            change = curr_data['underlying_price'].iloc[0] - prev_data['underlying_price'].iloc[0]
                            price_changes.append(change)
                
                if len(price_changes) >= rsi_period:
                    # Calculate average gains and losses
                    gains = [c for c in price_changes[:rsi_period] if c > 0]
                    losses = [-c for c in price_changes[:rsi_period] if c < 0]
                    
                    avg_gain = sum(gains) / rsi_period if gains else 0
                    avg_loss = sum(losses) / rsi_period if losses else 0
                    
                    if avg_loss > 0:
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))
                    else:
                        rsi = 100 if avg_gain > 0 else 50
                    
                    # Apply RSI entry rules
                    if config['strategy_type'] in ['long_call', 'short_put']:
                        # Bullish strategies - enter on oversold
                        if rsi > rsi_oversold:
                            rsi_filter_passed = False
                            print(f"⚠️ AUDIT: RSI filter blocked entry - RSI {rsi:.1f} > {rsi_oversold} (not oversold)")
                        else:
                            print(f"✅ AUDIT: RSI filter passed - RSI {rsi:.1f} <= {rsi_oversold} (oversold)")
                    else:
                        # Bearish strategies - enter on overbought
                        if rsi < rsi_overbought:
                            rsi_filter_passed = False
                            print(f"⚠️ AUDIT: RSI filter blocked entry - RSI {rsi:.1f} < {rsi_overbought} (not overbought)")
                        else:
                            print(f"✅ AUDIT: RSI filter passed - RSI {rsi:.1f} >= {rsi_overbought} (overbought)")
        
        # Check Bollinger Bands filter
        bb_filter_passed = True
        if 'market_filters' in config and 'bollinger_bands' in config['market_filters']:
            bb_filter = config['market_filters']['bollinger_bands']
            bb_period = bb_filter.get('period', 20)
            bb_std_dev = bb_filter.get('std_dev', 2.0)
            
            # Calculate Bollinger Bands if we have enough history
            if i >= bb_period - 1:
                # Get historical prices
                bb_prices = []
                for j in range(bb_period):
                    hist_idx = i - j
                    if hist_idx >= 0:
                        hist_date = unique_dates[hist_idx]
                        hist_data = data[data['date'] == hist_date]
                        if not hist_data.empty:
                            bb_prices.append(hist_data['underlying_price'].iloc[0])
                
                if len(bb_prices) == bb_period:
                    # Calculate middle band (SMA)
                    middle_band = sum(bb_prices) / len(bb_prices)
                    
                    # Calculate standard deviation
                    variance = sum((p - middle_band) ** 2 for p in bb_prices) / len(bb_prices)
                    std_dev = variance ** 0.5
                    
                    # Calculate bands
                    upper_band = middle_band + (bb_std_dev * std_dev)
                    lower_band = middle_band - (bb_std_dev * std_dev)
                    
                    # Calculate band position (0 = lower band, 1 = upper band)
                    band_position = (current_price - lower_band) / (upper_band - lower_band) if upper_band > lower_band else 0.5
                    
                    # Apply Bollinger Bands entry rules
                    if bb_filter.get('entry_at_bands', True):
                        if config['strategy_type'] in ['long_call', 'short_put']:
                            # Bullish strategies - enter near lower band
                            lower_threshold = bb_filter.get('lower_band_threshold', 0.2)  # Within 20% of lower band
                            if band_position > lower_threshold:
                                bb_filter_passed = False
                                print(f"⚠️ AUDIT: BB filter blocked entry - Price at {band_position:.1%} of bands (need < {lower_threshold:.0%})")
                            else:
                                print(f"✅ AUDIT: BB filter passed - Price near lower band ({band_position:.1%})")
                                print(f"   Lower: ${lower_band:.2f}, Price: ${current_price:.2f}, Upper: ${upper_band:.2f}")
                        else:
                            # Bearish strategies - enter near upper band
                            upper_threshold = bb_filter.get('upper_band_threshold', 0.8)  # Within 20% of upper band
                            if band_position < upper_threshold:
                                bb_filter_passed = False
                                print(f"⚠️ AUDIT: BB filter blocked entry - Price at {band_position:.1%} of bands (need > {upper_threshold:.0%})")
                            else:
                                print(f"✅ AUDIT: BB filter passed - Price near upper band ({band_position:.1%})")
                                print(f"   Lower: ${lower_band:.2f}, Price: ${current_price:.2f}, Upper: ${upper_band:.2f}")
        
        if iv_filter_passed and ma_filter_passed and rsi_filter_passed and bb_filter_passed and days_since_entry >= entry_frequency and len(positions) < max_positions:
            print(f"🔍 AUDIT: Checking for entry opportunity (days since last entry: {days_since_entry})")
            print(f"📊 AUDIT: Current positions: {len(positions)}/{max_positions}")
            
            # Find suitable option
            if config.get('use_advanced_selection', False):
                # Pass current positions to avoid duplicates
                config['_current_positions'] = positions
                selected_option = find_suitable_options_advanced(
                    date_data,
                    current_price,
                    config,
                    current_date
                )
            else:
                selected_option = find_suitable_options(
                    date_data, 
                    current_price, 
                    config['strategy_type'],
                    0.02  # 2% above current price
                )
            
            if selected_option is not None:
                # Calculate position size
                contracts, cost = calculate_position_size(
                    cash, 
                    selected_option['close'], 
                    config['parameters']['position_size']
                )
                
                if contracts > 0 and cost <= cash:
                    print(f"✅ AUDIT: Executing trade")
                    
                    # Log Greeks at entry
                    if selected_option.get('delta') is not None:
                        print(f"📊 AUDIT: Entry Greeks:")
                        print(f"   Delta: {selected_option['delta']:.3f}")
                        print(f"   Gamma: {selected_option.get('gamma', 'N/A'):.3f}" if selected_option.get('gamma') else "   Gamma: N/A")
                        print(f"   Theta: {selected_option.get('theta', 'N/A'):.3f}" if selected_option.get('theta') else "   Theta: N/A")
                        print(f"   Vega: {selected_option.get('vega', 'N/A'):.3f}" if selected_option.get('vega') else "   Vega: N/A")
                        print(f"   IV: {selected_option.get('implied_vol', 'N/A'):.3f}" if selected_option.get('implied_vol') else "   IV: N/A")
                    
                    # Record the trade
                    trade = {
                        'entry_date': current_date,
                        'strike': selected_option['strike_dollars'],
                        'option_price': selected_option['close'],
                        'contracts': contracts,
                        'cost': cost,
                        'cash_before': cash,
                        'cash_after': cash - cost,
                        # Store entry Greeks in trade record
                        'entry_delta': selected_option.get('delta', None),
                        'entry_gamma': selected_option.get('gamma', None),
                        'entry_theta': selected_option.get('theta', None),
                        'entry_vega': selected_option.get('vega', None),
                        'entry_iv': selected_option.get('implied_vol', None)
                    }
                    trades.append(trade)
                    
                    # Update portfolio with Greeks and IV tracking
                    positions.append({
                        'entry_date': current_date,
                        'strike': selected_option['strike_dollars'],
                        'expiration': selected_option['expiration'],
                        'option_type': selected_option['right'],  # 'C' or 'P'
                        'option_price': selected_option['close'],
                        'contracts': contracts,
                        'days_held': 0,
                        # Greeks at entry
                        'entry_delta': selected_option.get('delta', None),
                        'entry_gamma': selected_option.get('gamma', None),
                        'entry_theta': selected_option.get('theta', None),
                        'entry_vega': selected_option.get('vega', None),
                        'entry_iv': selected_option.get('implied_vol', None),
                        # Current Greeks (will be updated daily)
                        'current_delta': selected_option.get('delta', None),
                        'current_gamma': selected_option.get('gamma', None),
                        'current_theta': selected_option.get('theta', None),
                        'current_vega': selected_option.get('vega', None),
                        'current_iv': selected_option.get('implied_vol', None),
                        # Greeks history
                        'greeks_history': [{
                            'date': current_date,
                            'delta': selected_option.get('delta', None),
                            'gamma': selected_option.get('gamma', None),
                            'theta': selected_option.get('theta', None),
                            'vega': selected_option.get('vega', None),
                            'iv': selected_option.get('implied_vol', None)
                        }]
                    })
                    
                    cash -= cost
                    last_entry_date = current_date  # Update last entry date
                    print(f"💳 AUDIT: Cash after trade: ${cash:.2f}")
                else:
                    print(f"❌ AUDIT: Trade not executed (insufficient funds or no contracts)")
        
        # Exit logic
        for pos in positions[:]:  # Copy to avoid modification during iteration
            pos['days_held'] += 1
            
            # Find current option price for P&L calculation
            exit_data = date_data[
                (date_data['strike_dollars'] == pos['strike']) &
                (date_data['expiration'] == pos['expiration']) &
                (date_data['right'] == pos.get('option_type', 'C'))  # Support legacy positions
            ]
            
            if not exit_data.empty:
                exit_option = exit_data.iloc[0]
                exit_price = exit_option['close']
                proceeds = pos['contracts'] * exit_price * 100
                entry_cost = pos['contracts'] * pos['option_price'] * 100
                current_pnl = proceeds - entry_cost
                current_pnl_pct = (current_pnl / entry_cost) * 100
                
                # Update current Greeks
                pos['current_delta'] = exit_option.get('delta', None)
                pos['current_gamma'] = exit_option.get('gamma', None)
                pos['current_theta'] = exit_option.get('theta', None)
                pos['current_vega'] = exit_option.get('vega', None)
                pos['current_iv'] = exit_option.get('implied_vol', None)
                
                # Add to Greeks history
                pos['greeks_history'].append({
                    'date': current_date,
                    'delta': exit_option.get('delta', None),
                    'gamma': exit_option.get('gamma', None),
                    'theta': exit_option.get('theta', None),
                    'vega': exit_option.get('vega', None),
                    'iv': exit_option.get('implied_vol', None)
                })
                
                exit_reason = None
                
                # Check profit target
                profit_target = None
                if 'exit_rules' in config:
                    for rule in config['exit_rules']:
                        if rule.get('condition') == 'profit_target':
                            profit_target = rule.get('target_percent', 50)
                            break
                
                if profit_target and current_pnl_pct >= profit_target:
                    exit_reason = f"profit target ({current_pnl_pct:.1f}% >= {profit_target}%)"
                    print(f"🎯 AUDIT: Profit target hit! Current P&L: {current_pnl_pct:.1f}%")
                
                # Check stop loss
                stop_loss = None
                if 'exit_rules' in config:
                    for rule in config['exit_rules']:
                        if rule.get('condition') == 'stop_loss':
                            stop_loss = rule.get('stop_percent', -30)
                            break
                
                if not exit_reason and stop_loss and current_pnl_pct <= stop_loss:
                    exit_reason = f"stop loss ({current_pnl_pct:.1f}% <= {stop_loss}%)"
                    print(f"🛑 AUDIT: Stop loss hit! Current P&L: {current_pnl_pct:.1f}%")
                
                # Check delta stop exit (with IV adjustment)
                delta_stop = None
                if not exit_reason and 'exit_rules' in config:
                    for rule in config['exit_rules']:
                        if rule.get('condition') == 'delta_stop':
                            min_delta = rule.get('min_delta', 0.10)
                            # Adjust delta threshold based on IV if specified
                            if rule.get('iv_adjusted', False) and pos['current_iv'] and pos['entry_iv']:
                                iv_ratio = pos['current_iv'] / pos['entry_iv']
                                # Higher IV means we can accept lower delta
                                adjusted_min_delta = min_delta * (2 - iv_ratio)  # If IV doubled, halve the min delta
                                adjusted_min_delta = max(0.05, min(0.20, adjusted_min_delta))  # Keep within bounds
                            else:
                                adjusted_min_delta = min_delta
                            
                            # For calls, check if delta dropped too low
                            # For puts, check if absolute delta dropped too low
                            if pos['option_type'] == 'C' and pos['current_delta'] and pos['current_delta'] < adjusted_min_delta:
                                delta_stop = adjusted_min_delta
                                exit_reason = f"delta stop (delta {pos['current_delta']:.3f} < {adjusted_min_delta:.3f})"
                                print(f"📉 AUDIT: Delta stop triggered! Current delta: {pos['current_delta']:.3f}")
                            elif pos['option_type'] == 'P' and pos['current_delta'] and abs(pos['current_delta']) < adjusted_min_delta:
                                delta_stop = adjusted_min_delta
                                exit_reason = f"delta stop (|delta| {abs(pos['current_delta']):.3f} < {adjusted_min_delta:.3f})"
                                print(f"📉 AUDIT: Delta stop triggered! Current |delta|: {abs(pos['current_delta']):.3f}")
                            break
                
                # Check RSI exit condition
                if not exit_reason and 'exit_rules' in config:
                    for rule in config['exit_rules']:
                        if rule.get('condition') == 'rsi_exit':
                            rsi_exit_level = rule.get('exit_level', 50)
                            
                            # Calculate current RSI
                            if i >= 14:  # Need at least 14 periods for RSI
                                price_changes = []
                                for j in range(15):  # 14 changes need 15 prices
                                    hist_idx = i - j
                                    if hist_idx >= 0 and hist_idx > 0:
                                        curr_date = unique_dates[hist_idx]
                                        prev_date = unique_dates[hist_idx - 1]
                                        curr_data = data[data['date'] == curr_date]
                                        prev_data = data[data['date'] == prev_date]
                                        if not curr_data.empty and not prev_data.empty:
                                            change = curr_data['underlying_price'].iloc[0] - prev_data['underlying_price'].iloc[0]
                                            price_changes.append(change)
                                
                                if len(price_changes) >= 14:
                                    gains = [c for c in price_changes[:14] if c > 0]
                                    losses = [-c for c in price_changes[:14] if c < 0]
                                    
                                    avg_gain = sum(gains) / 14 if gains else 0
                                    avg_loss = sum(losses) / 14 if losses else 0
                                    
                                    if avg_loss > 0:
                                        rs = avg_gain / avg_loss
                                        rsi = 100 - (100 / (1 + rs))
                                    else:
                                        rsi = 100 if avg_gain > 0 else 50
                                    
                                    # Exit logic based on strategy type
                                    if pos['option_type'] == 'C':  # Calls
                                        if rule.get('exit_on_overbought', True) and rsi >= rsi_exit_level:
                                            exit_reason = f"RSI exit (RSI {rsi:.1f} >= {rsi_exit_level})"
                                            print(f"📊 AUDIT: RSI exit triggered! RSI: {rsi:.1f}")
                                    else:  # Puts
                                        if rule.get('exit_on_oversold', True) and rsi <= rsi_exit_level:
                                            exit_reason = f"RSI exit (RSI {rsi:.1f} <= {rsi_exit_level})"
                                            print(f"📊 AUDIT: RSI exit triggered! RSI: {rsi:.1f}")
                            break
                
                # Check Bollinger Bands exit condition
                if not exit_reason and 'exit_rules' in config:
                    for rule in config['exit_rules']:
                        if rule.get('condition') == 'bollinger_exit':
                            bb_period = rule.get('period', 20)
                            bb_std_dev = rule.get('std_dev', 2.0)
                            
                            # Calculate current Bollinger Bands
                            if i >= bb_period - 1:
                                bb_prices = []
                                for j in range(bb_period):
                                    hist_idx = i - j
                                    if hist_idx >= 0:
                                        hist_date = unique_dates[hist_idx]
                                        hist_data = data[data['date'] == hist_date]
                                        if not hist_data.empty:
                                            bb_prices.append(hist_data['underlying_price'].iloc[0])
                                
                                if len(bb_prices) == bb_period:
                                    # Calculate bands
                                    middle_band = sum(bb_prices) / len(bb_prices)
                                    variance = sum((p - middle_band) ** 2 for p in bb_prices) / len(bb_prices)
                                    std_dev = variance ** 0.5
                                    upper_band = middle_band + (bb_std_dev * std_dev)
                                    lower_band = middle_band - (bb_std_dev * std_dev)
                                    
                                    band_position = (current_price - lower_band) / (upper_band - lower_band) if upper_band > lower_band else 0.5
                                    
                                    # Exit logic based on option type
                                    if pos['option_type'] == 'C':  # Calls
                                        # Exit calls when price reaches upper band
                                        exit_threshold = rule.get('exit_at_band_pct', 0.9)  # Exit at 90% of bands
                                        if band_position >= exit_threshold:
                                            exit_reason = f"BB exit (price at {band_position:.1%} >= {exit_threshold:.0%})"
                                            print(f"📊 AUDIT: Bollinger Band exit triggered!")
                                            print(f"   Price ${current_price:.2f} near upper band ${upper_band:.2f}")
                                    else:  # Puts
                                        # Exit puts when price reaches lower band
                                        exit_threshold = rule.get('exit_at_band_pct', 0.1)  # Exit at 10% of bands
                                        if band_position <= exit_threshold:
                                            exit_reason = f"BB exit (price at {band_position:.1%} <= {exit_threshold:.0%})"
                                            print(f"📊 AUDIT: Bollinger Band exit triggered!")
                                            print(f"   Price ${current_price:.2f} near lower band ${lower_band:.2f}")
                            break
                
                # Check time-based exit
                if not exit_reason and pos['days_held'] >= config['parameters']['max_hold_days']:
                    exit_reason = f"time stop ({pos['days_held']} days)"
                    print(f"⏰ AUDIT: Time-based exit after {pos['days_held']} days")
                
                # Execute exit if any condition is met
                if exit_reason:
                    print(f"🔍 AUDIT: Exiting position - Reason: {exit_reason}")
                    print(f"💰 AUDIT: Exit price: ${exit_price:.2f}")
                    print(f"💵 AUDIT: Proceeds: ${proceeds:.2f}")
                    print(f"📈 AUDIT: P&L: ${current_pnl:.2f} ({current_pnl_pct:.1f}%)")
                    
                    # Log Greeks at exit
                    if pos['current_delta'] is not None:
                        print(f"📊 AUDIT: Exit Greeks:")
                        print(f"   Delta: {pos['current_delta']:.3f} (entry: {pos['entry_delta']:.3f})")
                        if pos['current_gamma'] is not None:
                            print(f"   Gamma: {pos['current_gamma']:.3f} (entry: {pos['entry_gamma']:.3f})")
                        if pos['current_theta'] is not None:
                            print(f"   Theta: {pos['current_theta']:.3f} (entry: {pos['entry_theta']:.3f})")
                        if pos['current_vega'] is not None:
                            print(f"   Vega: {pos['current_vega']:.3f} (entry: {pos['entry_vega']:.3f})")
                        if pos['current_iv'] is not None:
                            print(f"   IV: {pos['current_iv']:.3f} (entry: {pos['entry_iv']:.3f})")
                    
                    # Update cash
                    cash += proceeds
                    print(f"💳 AUDIT: Cash after exit: ${cash:.2f}")
                    
                    # Update trade log
                    for trade in trades:
                        if (trade['entry_date'] == pos['entry_date'] and 
                            'exit_date' not in trade):
                            trade['exit_date'] = current_date
                            trade['exit_price'] = exit_price
                            trade['proceeds'] = proceeds
                            trade['pnl'] = current_pnl
                            trade['exit_reason'] = exit_reason
                            # Store exit Greeks
                            trade['exit_delta'] = pos['current_delta']
                            trade['exit_gamma'] = pos['current_gamma']
                            trade['exit_theta'] = pos['current_theta']
                            trade['exit_vega'] = pos['current_vega']
                            trade['exit_iv'] = pos['current_iv']
                            # Store Greeks history
                            trade['greeks_history'] = pos['greeks_history']
                            break
                    
                    positions.remove(pos)
        
        # Record equity curve
        position_value = 0
        for pos in positions:
            # Find current option price
            current_option_data = date_data[
                (date_data['strike_dollars'] == pos['strike']) &
                (date_data['expiration'] == pos['expiration']) &
                (date_data['right'] == pos.get('option_type', 'C'))  # Support legacy positions
            ]
            if not current_option_data.empty:
                current_price = current_option_data.iloc[0]['close']
                position_value += pos['contracts'] * current_price * 100
        
        total_value = cash + position_value
        equity_curve.append({
            'date': current_date,
            'cash': cash,
            'position_value': position_value,
            'total_value': total_value,
            'positions': len(positions)
        })
    
    # Close any remaining positions at the end
    if positions:
        print(f"\n🔍 AUDIT: Closing remaining positions at end of period")
        final_data = data[data['date'] == unique_dates[-1]]
        
        for pos in positions:
            exit_data = final_data[
                (final_data['strike_dollars'] == pos['strike']) &
                (final_data['expiration'] == pos['expiration']) &
                (final_data['right'] == pos.get('option_type', 'C'))  # Support legacy positions
            ]
            
            if not exit_data.empty:
                exit_option = exit_data.iloc[0]
                exit_price = exit_option['close']
                proceeds = pos['contracts'] * exit_price * 100
                cash += proceeds
                
                entry_cost = pos['contracts'] * pos['option_price'] * 100
                pnl = proceeds - entry_cost
                
                print(f"💰 AUDIT: Final exit - Strike: ${pos['strike']:.2f}, P&L: ${pnl:.2f}")
                
                # Update trade log
                for trade in trades:
                    if 'exit_date' not in trade:
                        trade['exit_date'] = unique_dates[-1]
                        trade['exit_price'] = exit_price
                        trade['proceeds'] = proceeds
                        trade['pnl'] = pnl
                        break
    
    # Calculate final results
    final_value = cash
    total_return = (final_value - initial_capital) / initial_capital
    
    print("\n" + "=" * 60)
    print("📊 AUDIT: Final Results")
    print("=" * 60)
    print(f"💰 Final Value: ${final_value:,.2f}")
    print(f"📈 Total Return: {total_return:.2%}")
    print(f"💳 Initial Capital: ${initial_capital:,.2f}")
    print(f"📊 Total Trades: {len([t for t in trades if 'exit_date' in t])}")
    
    # Calculate additional metrics
    if len(equity_curve) > 1:
        equity_values = [point['total_value'] for point in equity_curve]
        returns = np.diff(equity_values) / equity_values[:-1]
        
        if len(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            
            # Max drawdown
            peak = equity_values[0]
            max_drawdown = 0
            for value in equity_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
            
            print(f"📊 Sharpe Ratio: {sharpe_ratio:.2f}")
            print(f"📉 Max Drawdown: {max_drawdown:.2%}")
    
    # Win rate
    completed_trades = [t for t in trades if 'exit_date' in t]
    if completed_trades:
        winning_trades = [t for t in completed_trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(completed_trades)
        print(f"🎯 Win Rate: {win_rate:.2%}")
    
    print("\n📋 AUDIT: Trade Log")
    print("-" * 80)
    for i, trade in enumerate(trades, 1):
        if 'exit_date' in trade:
            exit_reason = trade.get('exit_reason', 'unknown')
            pnl_pct = (trade['pnl'] / trade['cost']) * 100
            print(f"Trade {i}: Entry ${trade['option_price']:.2f} → Exit ${trade['exit_price']:.2f} → P&L ${trade['pnl']:.2f} ({pnl_pct:+.1f}%) | {exit_reason}")
    
    # Prepare results dictionary
    results = {
        'final_value': final_value,
        'total_return': total_return,
        'trades': trades,
        'equity_curve': equity_curve,
        'config': config,
        'initial_capital': initial_capital,
        'win_rate': win_rate if 'win_rate' in locals() else None,
        'sharpe_ratio': sharpe_ratio if 'sharpe_ratio' in locals() else None,
        'max_drawdown': max_drawdown if 'max_drawdown' in locals() else None,
        'start_date': start_date,
        'end_date': end_date
    }
    
    # Export results if requested
    if config.get('export_results', False):
        export_format = config.get('export_format', ['csv', 'json'])
        export_dir = config.get('export_dir', 'backtest_results')
        
        # Create export directory if it doesn't exist
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        strategy_name = config['name'].replace(' ', '_').lower()
        
        # Export to CSV
        if 'csv' in export_format:
            print(f"\n📁 AUDIT: Exporting results to CSV...")
            
            # Export trades
            trades_df = pd.DataFrame(trades)
            trades_file = Path(export_dir) / f"{strategy_name}_trades_{timestamp}.csv"
            trades_df.to_csv(trades_file, index=False)
            print(f"✅ AUDIT: Trades exported to {trades_file}")
            
            # Export equity curve
            equity_df = pd.DataFrame(equity_curve)
            equity_file = Path(export_dir) / f"{strategy_name}_equity_{timestamp}.csv"
            equity_df.to_csv(equity_file, index=False)
            print(f"✅ AUDIT: Equity curve exported to {equity_file}")
            
            # Export summary metrics
            summary_data = {
                'Metric': ['Initial Capital', 'Final Value', 'Total Return', 'Sharpe Ratio', 
                          'Max Drawdown', 'Win Rate', 'Total Trades', 'Start Date', 'End Date'],
                'Value': [initial_capital, final_value, f"{total_return:.2%}", 
                         f"{sharpe_ratio:.2f}" if sharpe_ratio else 'N/A',
                         f"{max_drawdown:.2%}" if max_drawdown else 'N/A',
                         f"{win_rate:.2%}" if win_rate else 'N/A',
                         len(completed_trades) if 'completed_trades' in locals() else len(trades),
                         start_date, end_date]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_file = Path(export_dir) / f"{strategy_name}_summary_{timestamp}.csv"
            summary_df.to_csv(summary_file, index=False)
            print(f"✅ AUDIT: Summary exported to {summary_file}")
        
        # Export to JSON
        if 'json' in export_format:
            print(f"\n📁 AUDIT: Exporting results to JSON...")
            
            # Prepare JSON-serializable data
            json_data = {
                'metadata': {
                    'strategy_name': config['name'],
                    'backtest_timestamp': timestamp,
                    'start_date': start_date,
                    'end_date': end_date
                },
                'config': config,
                'results': {
                    'initial_capital': initial_capital,
                    'final_value': final_value,
                    'total_return': total_return,
                    'sharpe_ratio': sharpe_ratio if sharpe_ratio else None,
                    'max_drawdown': max_drawdown if max_drawdown else None,
                    'win_rate': win_rate if win_rate else None
                },
                'trades': trades,
                'equity_curve': equity_curve
            }
            
            json_file = Path(export_dir) / f"{strategy_name}_full_results_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(json_data, f, indent=2, default=str)
            print(f"✅ AUDIT: Full results exported to {json_file}")
    
    # Create visualizations if requested
    if config.get('create_charts', False):
        print(f"\n📊 AUDIT: Creating visualization charts...")
        create_backtest_charts(results, config.get('export_dir', 'backtest_results'))
    
    return results


def create_backtest_charts(results, export_dir='backtest_results'):
    """Create visualization charts for backtest results"""
    try:
        # Create export directory if it doesn't exist
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        strategy_name = results['config']['name'].replace(' ', '_').lower()
        
        # Convert equity curve to DataFrame
        equity_df = pd.DataFrame(results['equity_curve'])
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        
        # Create figure with subplots
        fig = plt.figure(figsize=(15, 12))
        gs = GridSpec(4, 2, figure=fig, hspace=0.3, wspace=0.3)
        
        # 1. Equity Curve
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(equity_df['date'], equity_df['total_value'], 'b-', linewidth=2, label='Total Value')
        ax1.plot(equity_df['date'], equity_df['cash'], 'g--', linewidth=1, label='Cash')
        ax1.axhline(y=results['initial_capital'], color='r', linestyle=':', label='Initial Capital')
        ax1.set_title(f"{results['config']['name']} - Equity Curve", fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # 2. Drawdown
        ax2 = fig.add_subplot(gs[1, :])
        # Calculate drawdown
        rolling_max = equity_df['total_value'].expanding().max()
        drawdown = (equity_df['total_value'] - rolling_max) / rolling_max * 100
        ax2.fill_between(equity_df['date'], drawdown, 0, color='red', alpha=0.3)
        ax2.plot(equity_df['date'], drawdown, 'r-', linewidth=1)
        ax2.set_title('Drawdown (%)', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Drawdown %')
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # 3. Trade P&L Distribution
        ax3 = fig.add_subplot(gs[2, 0])
        completed_trades = [t for t in results['trades'] if 'pnl' in t]
        if completed_trades:
            pnls = [t['pnl'] for t in completed_trades]
            colors = ['green' if pnl > 0 else 'red' for pnl in pnls]
            bars = ax3.bar(range(len(pnls)), pnls, color=colors, alpha=0.7)
            ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax3.set_title('Trade P&L', fontsize=12, fontweight='bold')
            ax3.set_xlabel('Trade Number')
            ax3.set_ylabel('P&L ($)')
            ax3.grid(True, alpha=0.3)
            
            # Add average line
            avg_pnl = np.mean(pnls)
            ax3.axhline(y=avg_pnl, color='blue', linestyle='--', label=f'Avg: ${avg_pnl:.2f}')
            ax3.legend()
        
        # 4. Win/Loss Statistics
        ax4 = fig.add_subplot(gs[2, 1])
        if completed_trades:
            wins = sum(1 for t in completed_trades if t['pnl'] > 0)
            losses = sum(1 for t in completed_trades if t['pnl'] <= 0)
            
            # Pie chart
            sizes = [wins, losses]
            labels = [f'Wins ({wins})', f'Losses ({losses})']
            colors = ['green', 'red']
            explode = (0.1, 0)  # explode wins slice
            
            ax4.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                    shadow=True, startangle=90)
            ax4.set_title('Win/Loss Distribution', fontsize=12, fontweight='bold')
        
        # 5. Position Count Over Time
        ax5 = fig.add_subplot(gs[3, 0])
        ax5.plot(equity_df['date'], equity_df['positions'], 'b-', linewidth=2, marker='o', markersize=4)
        ax5.set_title('Active Positions Over Time', fontsize=12, fontweight='bold')
        ax5.set_xlabel('Date')
        ax5.set_ylabel('Number of Positions')
        ax5.grid(True, alpha=0.3)
        ax5.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45)
        
        # 6. Exit Reasons
        ax6 = fig.add_subplot(gs[3, 1])
        if completed_trades:
            exit_reasons = {}
            for trade in completed_trades:
                reason = trade.get('exit_reason', 'unknown')
                # Simplify exit reason
                if 'profit target' in reason:
                    reason = 'Profit Target'
                elif 'stop loss' in reason:
                    reason = 'Stop Loss'
                elif 'time stop' in reason:
                    reason = 'Time Stop'
                elif 'delta stop' in reason:
                    reason = 'Delta Stop'
                elif 'RSI exit' in reason:
                    reason = 'RSI Exit'
                elif 'BB exit' in reason:
                    reason = 'BB Exit'
                else:
                    reason = 'Other'
                
                exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
            
            # Bar chart
            reasons = list(exit_reasons.keys())
            counts = list(exit_reasons.values())
            bars = ax6.bar(reasons, counts, color='skyblue', alpha=0.7)
            ax6.set_title('Exit Reasons', fontsize=12, fontweight='bold')
            ax6.set_xlabel('Exit Type')
            ax6.set_ylabel('Count')
            ax6.grid(True, alpha=0.3, axis='y')
            plt.setp(ax6.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Add count labels on bars
            for bar, count in zip(bars, counts):
                ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        str(count), ha='center', va='bottom')
        
        # Add overall title and metrics
        fig.suptitle(f"Backtest Results: {results['config']['name']}\n" +
                    f"Period: {results['start_date']} to {results['end_date']} | " +
                    f"Return: {results['total_return']:.2%} | " +
                    f"Sharpe: {results.get('sharpe_ratio', 0):.2f} | " +
                    f"Max DD: {results.get('max_drawdown', 0):.2%}",
                    fontsize=16, fontweight='bold')
        
        # Save the figure
        chart_file = Path(export_dir) / f"{strategy_name}_charts_{timestamp}.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        print(f"✅ AUDIT: Charts saved to {chart_file}")
        
        # Close the figure to free memory
        plt.close()
        
    except Exception as e:
        print(f"⚠️ AUDIT: Error creating charts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    # Check command line arguments for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--multi-day":
        # Test multi-day backtest
        print("🧪 AUDIT: Running multi-day test backtest")
        data_dir = "spy_options_downloader/spy_options_parquet"
        config_file = "advanced_test_strategy.yaml"
        start_date = "2022-08-01"
        end_date = "2022-08-10"
        
        print(f"📅 Using date range: {start_date} to {end_date}")
        print(f"📁 Using data directory: {data_dir}")
        print(f"📝 Using strategy: {config_file}")
        
        results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    else:
        # Test with a single file (legacy mode)
        data_file = "spy_options_downloader/spy_options_parquet/repaired/spy_options_eod_20230809.parquet"
        config_file = "simple_test_strategy.yaml"
        
        print("🧪 AUDIT: Running simple test backtest (single-day mode)")
        print(f"📁 Using data file: {data_file}")
        
        # Check if file exists
        if not Path(data_file).exists():
            print(f"❌ AUDIT: Data file not found: {data_file}")
            print("🔍 AUDIT: Available repaired files:")
            repaired_dir = Path("spy_options_downloader/spy_options_parquet/repaired")
            if repaired_dir.exists():
                for file in repaired_dir.glob("*.parquet"):
                    print(f"   - {file.name}")
            else:
                print("   No repaired directory found")
            exit(1)
        
        results = run_auditable_backtest(data_file, config_file, "2023-08-09", "2023-08-09")
    
    if results:
        print("\n✅ AUDIT: Backtest completed successfully!")
        print(f"📊 Final Value: ${results['final_value']:,.2f}")
        print(f"📈 Total Return: {results['total_return']:.2%}")
    else:
        print("\n❌ AUDIT: Backtest failed!") 