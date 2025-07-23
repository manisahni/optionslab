#!/usr/bin/env python3
"""
Backtest Engine - Core execution engine for options backtesting
Orchestrates data loading, option selection, trade execution, and results
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Import our modular components
from .data_loader import load_data, load_strategy_config
from .option_selector import find_suitable_options, calculate_position_size
from .market_filters import MarketFilters
from .greek_tracker import GreekTracker
from .trade_recorder import TradeRecorder
from .exit_conditions import ExitConditions, Position
from .visualization import create_backtest_charts
from .backtest_metrics import (
    create_implementation_metrics, 
    calculate_compliance_scorecard,
    calculate_performance_metrics
)


def run_auditable_backtest(data_file, config_file, start_date, end_date):
    """Run a fully auditable backtest with modular components
    
    This is the main orchestration function that coordinates all the
    specialized modules to execute a complete backtest.
    
    Args:
        data_file: Path to data file or directory
        config_file: Path to strategy YAML configuration
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Dictionary containing backtest results or None if failed
    """
    import uuid
    
    # Generate unique backtest ID at the very start
    backtest_id = str(uuid.uuid4())
    
    print("🚀 AUDIT: Starting auditable backtest")
    print(f"🔑 AUDIT: Backtest ID: {backtest_id}")
    print("=" * 60)
    
    # Load data using data_loader module
    data = load_data(data_file, start_date, end_date)
    if data is None or len(data) == 0:
        print(f"❌ AUDIT: No data available")
        return None
    
    # Add strike_dollars column for consistency
    data = data.copy()
    data['strike_dollars'] = data['strike'] / 1000.0
    
    # Load strategy configuration
    config = load_strategy_config(config_file)
    if config is None:
        return None
    
    print("=" * 60)
    print("📊 AUDIT: Initializing backtest")
    
    # Initialize portfolio state
    initial_capital = config['parameters']['initial_capital']
    cash = initial_capital
    positions = []  # Active positions with GreekTracker
    equity_curve = []
    last_entry_date = None
    
    # Initialize specialized modules
    unique_dates = sorted(data['date'].unique())
    market_filters = MarketFilters(config, data, unique_dates)
    trade_recorder = TradeRecorder(config)
    exit_conditions = ExitConditions(config, market_filters)
    
    print(f"💰 AUDIT: Initial capital: ${initial_capital:,.2f}")
    print(f"📅 AUDIT: Trading on {len(unique_dates)} dates")
    
    # Main backtest loop - orchestrating all modules
    for i, current_date in enumerate(unique_dates):
        print(f"\n📅 AUDIT: Processing {current_date}")
        
        # Get current day's data
        date_data = data[data['date'] == current_date]
        if date_data.empty:
            continue
            
        current_price = date_data['underlying_price'].iloc[0]
        print(f"💰 AUDIT: Underlying: ${current_price:.2f}")
        
        # Entry logic - check if we should enter new positions
        entry_frequency = config['parameters'].get('entry_frequency', 3)
        max_positions = config['parameters'].get('max_positions', 1)
        
        days_since_entry = (
            float('inf') if last_entry_date is None 
            else (pd.to_datetime(current_date) - pd.to_datetime(last_entry_date)).days
        )
        
        # Check market filters
        filters_passed, filter_messages = market_filters.check_all_filters(
            current_date, current_price, i
        )
        for msg in filter_messages:
            if msg:
                print(f"✅ AUDIT: {msg}" if "passed" in msg else f"⚠️ AUDIT: {msg}")
        
        # Attempt entry if conditions are met
        if (filters_passed and 
            days_since_entry >= entry_frequency and 
            len(positions) < max_positions):
            
            print(f"🔍 AUDIT: Entry check (days since last: {days_since_entry})")
            print(f"📊 AUDIT: Positions: {len(positions)}/{max_positions}")
            
            # Find suitable option using option_selector module
            config['_current_positions'] = [
                {'strike': p['strike'], 'expiration': p['expiration']} 
                for p in positions
            ]
            selected_option = find_suitable_options(
                date_data, current_price, config, current_date
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
                    
                    # Create Greek tracker for the position
                    greek_tracker = GreekTracker.from_option_data(
                        selected_option, current_date
                    )
                    
                    # Log entry Greeks
                    entry_log = greek_tracker.log_entry_greeks()
                    if entry_log:
                        print(f"📊 AUDIT: {entry_log}")
                    
                    # Record trade using trade_recorder module
                    trade = trade_recorder.record_entry(
                        selected_option, current_date, current_price,
                        contracts, cash, cost
                    )
                    
                    # Track position
                    positions.append({
                        'entry_date': current_date,
                        'strike': selected_option['strike_dollars'],
                        'expiration': selected_option['expiration'],
                        'option_type': selected_option['right'],
                        'option_price': selected_option['close'],
                        'contracts': contracts,
                        'days_held': 0,
                        'greek_tracker': greek_tracker,
                        'trade': trade
                    })
                    
                    cash -= cost
                    last_entry_date = current_date
                    print(f"💳 AUDIT: Cash after: ${cash:.2f}")
        
        # Exit logic - check all positions for exit conditions
        for pos in positions[:]:  # Copy to allow removal during iteration
            pos['days_held'] += 1
            
            # Find current option data
            exit_data = date_data[
                (date_data['strike_dollars'] == pos['strike']) &
                (date_data['expiration'] == pos['expiration']) &
                (date_data['right'] == pos['option_type'])
            ]
            
            if not exit_data.empty:
                exit_option = exit_data.iloc[0]
                exit_price = exit_option['close']
                proceeds = pos['contracts'] * exit_price * 100
                entry_cost = pos['contracts'] * pos['option_price'] * 100
                current_pnl = proceeds - entry_cost
                current_pnl_pct = (current_pnl / entry_cost) * 100
                
                # Update Greeks
                pos['greek_tracker'].update_current(exit_option, current_date)
                
                # Create position object for exit checking
                position = Position(
                    entry_date=pos['entry_date'],
                    strike=pos['strike'],
                    expiration=pos['expiration'],
                    option_type=pos['option_type'],
                    option_price=pos['option_price'],
                    contracts=pos['contracts'],
                    days_held=pos['days_held'],
                    entry_delta=pos['greek_tracker'].entry_greeks.delta,
                    current_delta=pos['greek_tracker'].current_greeks.delta,
                    entry_iv=pos['greek_tracker'].entry_greeks.iv,
                    current_iv=pos['greek_tracker'].current_greeks.iv
                )
                
                # Check exit conditions using exit_conditions module
                should_exit, exit_reason = exit_conditions.check_all_exits(
                    position, current_pnl, current_pnl_pct, current_price, i
                )
                
                if should_exit:
                    # Log exit details
                    for line in exit_conditions.format_exit_log(
                        exit_reason, exit_price, proceeds, current_pnl, current_pnl_pct
                    ):
                        print(f"🔍 AUDIT: {line}")
                    
                    # Log exit Greeks
                    exit_log = pos['greek_tracker'].log_exit_greeks()
                    if exit_log:
                        print(f"📊 AUDIT: {exit_log}")
                    
                    # Update portfolio
                    cash += proceeds
                    print(f"💳 AUDIT: Cash after exit: ${cash:.2f}")
                    
                    # Record exit using trade_recorder module
                    pos['greek_tracker'].set_exit_greeks(exit_option, current_date)
                    trade_recorder.record_exit(
                        pos['trade'], exit_option, current_date, current_price,
                        exit_reason, pos['days_held'], proceeds
                    )
                    
                    # Update trade with complete Greeks history
                    trade_recorder.update_trade_greeks(
                        pos['trade'],
                        pos['greek_tracker'].get_history_list()
                    )
                    
                    # Add Greek data to trade record
                    pos['trade'].__dict__.update(pos['greek_tracker'].get_entry_dict())
                    pos['trade'].__dict__.update(pos['greek_tracker'].get_exit_dict())
                    
                    positions.remove(pos)
        
        # Record equity curve snapshot
        position_value = _calculate_position_value(positions, date_data)
        total_value = cash + position_value
        
        equity_curve.append({
            'date': current_date,
            'cash': cash,
            'position_value': position_value,
            'total_value': total_value,
            'positions': len(positions)
        })
    
    # Close any remaining positions at end of backtest
    if positions:
        _close_final_positions(
            positions, data, unique_dates[-1], trade_recorder, cash
        )
    
    # Calculate final results using backtest_metrics module
    final_value = cash
    total_return = (final_value - initial_capital) / initial_capital
    
    print("\n" + "=" * 60)
    print("📊 AUDIT: Final Results")
    print("=" * 60)
    print(f"💰 Final Value: ${final_value:,.2f}")
    print(f"📈 Total Return: {total_return:.2%}")
    print(f"📊 Total Trades: {len(trade_recorder.get_completed_trades())}")
    
    # Calculate comprehensive metrics
    trades_dict = trade_recorder.get_trades_as_dicts()
    performance_metrics = calculate_performance_metrics(
        equity_curve, trades_dict, initial_capital
    )
    
    print(f"📊 Sharpe Ratio: {performance_metrics['sharpe_ratio']:.2f}")
    print(f"📉 Max Drawdown: {performance_metrics['max_drawdown']:.2%}")
    print(f"🎯 Win Rate: {performance_metrics['win_rate']:.2%}")
    
    # Prepare complete results package
    results = {
        'backtest_id': backtest_id,  # Include the unique ID
        'final_value': final_value,
        'total_return': total_return,
        'trades': trades_dict,
        'equity_curve': equity_curve,
        'config': config,
        'initial_capital': initial_capital,
        'win_rate': performance_metrics['win_rate'],
        'sharpe_ratio': performance_metrics['sharpe_ratio'],
        'max_drawdown': performance_metrics['max_drawdown'],
        'start_date': start_date,
        'end_date': end_date,
        'compliance_scorecard': calculate_compliance_scorecard(trades_dict),
        'implementation_metrics': create_implementation_metrics(trades_dict, config),
        'performance_metrics': performance_metrics
    }
    
    # Export results if requested
    if config.get('export_results', False):
        _export_results(results)
    
    # Create visualization charts if requested
    if config.get('create_charts', False):
        print(f"\n📊 AUDIT: Creating visualization charts...")
        create_backtest_charts(
            results, 
            config.get('export_dir', 'backtest_results')
        )
    
    return results


def _calculate_position_value(positions: List[Dict], date_data: pd.DataFrame) -> float:
    """Calculate total value of open positions
    
    Args:
        positions: List of open positions
        date_data: Current date's market data
        
    Returns:
        Total position value in dollars
    """
    total_value = 0
    
    for pos in positions:
        option_data = date_data[
            (date_data['strike_dollars'] == pos['strike']) &
            (date_data['expiration'] == pos['expiration']) &
            (date_data['right'] == pos['option_type'])
        ]
        
        if not option_data.empty:
            current_price = option_data.iloc[0]['close']
            total_value += pos['contracts'] * current_price * 100
    
    return total_value


def _close_final_positions(positions: List[Dict], data: pd.DataFrame, 
                          final_date: str, trade_recorder: TradeRecorder,
                          cash: float) -> float:
    """Close all remaining positions at end of backtest
    
    Args:
        positions: List of open positions
        data: Complete dataset
        final_date: Last date of backtest
        trade_recorder: Trade recorder instance
        cash: Current cash balance
        
    Returns:
        Updated cash balance
    """
    print(f"\n🔍 AUDIT: Closing {len(positions)} positions at end")
    final_data = data[data['date'] == final_date]
    
    for pos in positions:
        exit_data = final_data[
            (final_data['strike_dollars'] == pos['strike']) &
            (final_data['expiration'] == pos['expiration']) &
            (final_data['right'] == pos['option_type'])
        ]
        
        if not exit_data.empty:
            exit_option = exit_data.iloc[0]
            exit_price = exit_option['close']
            proceeds = pos['contracts'] * exit_price * 100
            cash += proceeds
            
            entry_cost = pos['contracts'] * pos['option_price'] * 100
            pnl = proceeds - entry_cost
            
            print(f"💰 AUDIT: Final exit - Strike: ${pos['strike']:.2f}, P&L: ${pnl:.2f}")
            
            # Record final exit
            pos['greek_tracker'].set_exit_greeks(exit_option, final_date)
            trade_recorder.record_exit(
                pos['trade'], exit_option, final_date, 
                exit_option['underlying_price'],
                'end_of_period', pos['days_held'], proceeds
            )
            
            # Update with final Greeks
            trade_recorder.update_trade_greeks(
                pos['trade'],
                pos['greek_tracker'].get_history_list()
            )
            pos['trade'].__dict__.update(pos['greek_tracker'].get_entry_dict())
            pos['trade'].__dict__.update(pos['greek_tracker'].get_exit_dict())
    
    return cash


def _export_results(results: Dict):
    """Export backtest results to CSV format only
    
    Args:
        results: Complete backtest results dictionary
    """
    export_dir = results['config'].get('export_dir', 'backtest_results')
    
    Path(export_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    strategy_name = results['config']['name'].replace(' ', '_').lower()
    
    print(f"\n📁 AUDIT: Exporting to CSV...")
    
    # Export trades
    trades_df = pd.DataFrame(results['trades'])
    trades_file = Path(export_dir) / f"{strategy_name}_trades_{timestamp}.csv"
    trades_df.to_csv(trades_file, index=False)
    print(f"✅ AUDIT: Trades exported to {trades_file}")
    
    # Export equity curve
    equity_df = pd.DataFrame(results['equity_curve'])
    equity_file = Path(export_dir) / f"{strategy_name}_equity_{timestamp}.csv"
    equity_df.to_csv(equity_file, index=False)
    print(f"✅ AUDIT: Equity curve exported to {equity_file}")


if __name__ == "__main__":
    import sys
    
    # Test mode for development
    if len(sys.argv) > 1 and sys.argv[1] == "--multi-day":
        print("🧪 AUDIT: Running multi-day test")
        data_dir = "../spy_options_downloader/spy_options_parquet"
        config_file = "../simple_test_strategy.yaml"
        start_date = "2022-08-01"
        end_date = "2022-08-10"
        
        results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    else:
        # Single file test
        data_file = "optionslab/data/SPY_OPTIONS_2022_COMPLETE.parquet"
        config_file = "simple_test_strategy.yaml"
        
        print("🧪 AUDIT: Running single-day test")
        
        if not Path(data_file).exists():
            print(f"❌ AUDIT: Data file not found: {data_file}")
            exit(1)
        
        results = run_auditable_backtest(data_file, config_file, "2022-08-09", "2022-08-09")
    
    if results:
        print("\n✅ AUDIT: Backtest completed successfully!")
        print(f"📊 Final Value: ${results['final_value']:,.2f}")
        print(f"📈 Total Return: {results['total_return']:.2%}")
    else:
        print("\n❌ AUDIT: Backtest failed!")