#!/usr/bin/env python3
"""
SPY Options Backtester - Enhanced CLI Interface with YAML Support
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
import yaml
import json

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "optionslab-ui"))

from data_loader import SPYDataLoader
from portfolio_manager import PortfolioManager
from strategy_base import OrderType
from strategies.simple_strategies import (
    LongCallStrategy, LongPutStrategy, 
    StraddleStrategy, CoveredCallStrategy
)
from config import DEFAULT_PARAMS
from cli_utils import (
    Colors, print_banner, print_strategy_descriptions, print_examples,
    print_error, print_warning, print_success, print_info,
    print_progress_bar, format_currency, format_percentage,
    suggest_similar_command, is_interactive
)
from interactive_mode import run_interactive_mode

# Import YAML configuration manager
try:
    from core.strategy_config_manager import StrategyConfigManager
    YAML_SUPPORT = True
except ImportError:
    print_warning("YAML strategy configuration support not available")
    YAML_SUPPORT = False


class EnhancedBacktestEngine:
    """Enhanced backtesting engine with better user feedback"""
    
    def __init__(self, strategy, start_date: str, end_date: str, 
                 initial_capital: float = 100000):
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date
        self.data_loader = SPYDataLoader()
        self.portfolio = PortfolioManager(initial_capital)
        self.results = []
        
    def run_backtest(self) -> Dict[str, Any]:
        """Execute the backtest with enhanced feedback"""
        print(f"\n{Colors.bold('🚀 STARTING BACKTEST')}")
        print("=" * 60)
        print(f"{Colors.cyan('Strategy:')} {self.strategy.name}")
        print(f"{Colors.cyan('Period:')} {self.start_date} to {self.end_date}")
        print(f"{Colors.cyan('Initial Capital:')} {format_currency(self.portfolio.initial_capital)}")
        print("-" * 60)
        
        # Validate data availability
        print_info("Validating data availability...")
        try:
            available_dates = self.data_loader.get_available_dates()
            backtest_dates = [d for d in available_dates 
                             if self.start_date <= d <= self.end_date]
            
            if not backtest_dates:
                raise ValueError(f"No data available for period {self.start_date} to {self.end_date}")
            
            missing_days = self._check_missing_dates(backtest_dates)
            if missing_days:
                print_warning(f"Missing {len(missing_days)} days (likely holidays)")
            
            print_success(f"Found {len(backtest_dates)} trading days")
            
        except Exception as e:
            print_error(f"Data validation failed: {e}")
            raise
        
        # Run backtest with progress tracking
        print(f"\n{Colors.bold('📊 EXECUTING BACKTEST')}")
        total_days = len(backtest_dates)
        
        for i, date in enumerate(backtest_dates):
            try:
                self._process_date(date)
                
                # Update progress bar
                if total_days > 50:  # Only show progress bar for longer backtests
                    if (i + 1) % max(1, total_days // 20) == 0 or i == total_days - 1:
                        portfolio_value = self.portfolio.snapshots[-1].total_value if self.portfolio.snapshots else self.portfolio.initial_capital
                        suffix = f"${portfolio_value:,.0f}"
                        print_progress_bar(i + 1, total_days, "Progress:", suffix)
                elif (i + 1) % 10 == 0 or i == total_days - 1:
                    # For shorter backtests, show periodic updates
                    portfolio_value = self.portfolio.snapshots[-1].total_value if self.portfolio.snapshots else self.portfolio.initial_capital
                    progress = (i + 1) / total_days * 100
                    print(f"  {progress:.0f}% - {date} - Portfolio: {format_currency(portfolio_value)}")
                    
            except Exception as e:
                # Check if this is a data loading error - these are critical and should stop execution
                if "Error loading data for" in str(e) or "Repetition level histogram size mismatch" in str(e):
                    print_error(f"CRITICAL DATA ERROR on {date}: {e}")
                    print_error("Data loading failures prevent reliable backtesting. Stopping execution.")
                    raise RuntimeError(f"Backtest halted due to data loading failure on {date}: {e}")
                else:
                    print_warning(f"Error processing {date}: {e}")
                    continue
        
        # Close all remaining open positions at end of backtest
        self._close_remaining_positions(backtest_dates[-1])
        
        # Generate results
        results = self._generate_results()
        return results
    
    def _process_date(self, date: str):
        """Process a single trading date"""
        current_data = self.data_loader.load_date(date)
        current_date = datetime.strptime(date, '%Y%m%d')
        
        self.strategy.current_date = current_date
        
        # Update Greeks tracking for all open positions
        self.portfolio.update_position_greeks(current_data, current_date)
        
        # Check exit conditions for existing positions
        positions_to_close = []
        for position in self.portfolio.get_open_positions():
            should_exit, exit_reason = self.strategy.should_exit_position(position, current_data)
            if should_exit:
                positions_to_close.append((position, exit_reason))
        
        # Close positions
        for position, exit_reason in positions_to_close:
            self._close_position(position, current_data, current_date, exit_reason)
        
        # Generate new entry signals
        market_data = {
            'underlying_price': current_data['underlying_price'].iloc[0],
            'date': current_date
        }
        
        signals = self.strategy.generate_signals(current_data, market_data)
        
        # Execute signals
        for signal in signals:
            self._execute_signal(signal, current_data, current_date)
        
        # Update strategy state
        self.strategy.trades = self.portfolio.trades.copy()
        self.strategy.positions = self.portfolio.positions.copy()
        self.strategy.portfolio_value = self.portfolio.calculate_portfolio_value(current_data)
        
        # Take portfolio snapshot
        self.portfolio.take_snapshot(current_date, current_data)
    
    def _execute_signal(self, signal, current_data: pd.DataFrame, current_date: datetime):
        """Execute a trading signal with enhanced logging"""
        option_data = self._find_option(current_data, signal.option_criteria)
        
        if option_data is None:
            if len(self.portfolio.trades) < 5:  # Only show warnings for first few trades
                print_warning(f"Could not find option for: {signal.reason}")
            return
        
        order_type = OrderType.BUY_TO_OPEN if signal.action == 'buy' else OrderType.SELL_TO_OPEN
        
        trade = self.portfolio.execute_trade(
            option_data, signal.quantity, order_type, current_date, 
            selection_metadata=signal.selection_metadata
        )
        
        if trade:
            action_color = Colors.green if signal.action == 'buy' else Colors.red
            print(f"  {current_date.strftime('%Y-%m-%d')}: {signal.reason} - "
                  f"{action_color(signal.action.upper())} {signal.quantity} {trade.option_type} "
                  f"${trade.strike:.0f} @ {format_currency(trade.price)}")
    
    def _close_position(self, position, current_data: pd.DataFrame, current_date: datetime, exit_reason: str = "time_decay"):
        """Close an open position with enhanced logging"""
        last_trade = position.trades[-1]
        
        option_data = self._find_option(current_data, {
            'strike': last_trade.strike,
            'expiration': last_trade.expiration,
            'option_type': last_trade.option_type
        })
        
        if option_data is None:
            # Option expired - close the position at $0.01 (worthless)
            print(f"  {current_date.strftime('%Y-%m-%d')}: Position expired - "
                  f"{last_trade.option_type} ${last_trade.strike:.0f}")
            
            # Create synthetic option data for expired option (worthless)
            expired_option_data = pd.Series({
                'strike': last_trade.strike,
                'right': last_trade.option_type,
                'expiration': last_trade.expiration,
                'bid': 0.01,
                'ask': 0.01,
                'mid_price': 0.01,
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0,
                'implied_volatility': 0.0,
                'dte': 0,
                'underlying_price': current_data['underlying_price'].iloc[0] if not current_data.empty else 0.0
            })
            
            order_type = OrderType.SELL_TO_CLOSE if position.net_quantity > 0 else OrderType.BUY_TO_CLOSE
            
            # Close the expired position properly with exit accuracy tracking
            trade = self.portfolio.close_trade_with_exit_data(
                last_trade, expired_option_data, abs(position.net_quantity), order_type, current_date, "expiration",
                strategy_params=self.strategy.params
            )
            
            if trade:
                print(f"  {current_date.strftime('%Y-%m-%d')}: {Colors.yellow('CLOSE')} {trade.option_type} "
                      f"${trade.strike:.0f} @ $0.01 (expired) - Exit: expiration")
            return
        
        order_type = OrderType.SELL_TO_CLOSE if position.net_quantity > 0 else OrderType.BUY_TO_CLOSE
        
        # Use the enhanced close method with exit reason
        trade = self.portfolio.close_trade_with_exit_data(
            last_trade, option_data, abs(position.net_quantity), order_type, current_date, exit_reason,
            strategy_params=self.strategy.params
        )
        
        if trade:
            # Calculate P&L for position
            total_cost = sum(t.total_cost for t in position.trades)
            pnl = total_cost + trade.total_cost
            
            print(f"  {current_date.strftime('%Y-%m-%d')}: {Colors.yellow('CLOSE')} {trade.option_type} "
                  f"${trade.strike:.0f} @ {format_currency(trade.price)} - "
                  f"P&L: {format_currency(pnl)}")
    
    def _close_remaining_positions(self, final_date: str):
        """Close all remaining open positions at the end of the backtest"""
        final_date_obj = datetime.strptime(final_date, '%Y%m%d')
        current_data = self.data_loader.load_date(final_date)
        
        if current_data is None or current_data.empty:
            print_warning(f"No data available for final date {final_date} to close remaining positions")
            return
        
        open_positions = self.portfolio.get_open_positions()
        if open_positions:
            print(f"\n📋 Closing {len(open_positions)} remaining positions at end of backtest ({final_date}):")
            
            for position in open_positions:
                self._close_position(position, current_data, final_date_obj, "backtest_end")
    
    def _find_option(self, current_data: pd.DataFrame, criteria: Dict[str, Any]) -> pd.Series:
        """Find option matching criteria"""
        matches = current_data[
            (current_data['strike'] == criteria['strike']) &
            (current_data['right'] == criteria['option_type']) &
            (current_data['expiration'] == pd.to_datetime(criteria['expiration']))
        ]
        
        return matches.iloc[0] if not matches.empty else None
    
    def _check_missing_dates(self, backtest_dates) -> list:
        """Check for missing trading days"""
        if len(backtest_dates) < 2:
            return []
        
        start_date = datetime.strptime(backtest_dates[0], '%Y%m%d')
        end_date = datetime.strptime(backtest_dates[-1], '%Y%m%d')
        
        # Generate expected trading days (weekdays)
        expected_days = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                expected_days.append(current.strftime('%Y%m%d'))
            current += timedelta(days=1)
        
        return [day for day in expected_days if day not in backtest_dates]
    
    def _generate_results(self) -> Dict[str, Any]:
        """Generate final backtest results with Greeks data"""
        performance = self.portfolio.get_performance_summary()
        
        results = {
            'strategy': self.strategy.name,
            'period': f"{self.start_date} to {self.end_date}",
            'performance': performance,
            'trades_df': self.portfolio.get_trades_df(),
            'snapshots_df': self.portfolio.get_snapshots_df()
        }
        
        # Add Greeks history if tracking is enabled
        if self.portfolio.track_greeks:
            results['portfolio_greeks_df'] = self.portfolio.get_greeks_history_df()
            
            # Add position-level Greeks summaries
            greeks_summaries = {}
            for position_key in self.portfolio.greeks_tracker.position_histories.keys():
                history = self.portfolio.greeks_tracker.position_histories[position_key]
                greeks_summaries[position_key] = history.get_greeks_summary()
            
            results['position_greeks_summaries'] = greeks_summaries
            
            # Add Greeks-based insights
            results['greeks_insights'] = self._generate_greeks_insights()
        
        return results
    
    def _generate_greeks_insights(self) -> Dict[str, Any]:
        """Generate insights from Greeks tracking data"""
        insights = {
            'total_positions_tracked': len(self.portfolio.greeks_tracker.position_histories),
            'active_positions': sum(1 for h in self.portfolio.greeks_tracker.position_histories.values() 
                                  if h.exit_snapshot is None),
            'closed_positions': sum(1 for h in self.portfolio.greeks_tracker.position_histories.values() 
                                  if h.exit_snapshot is not None)
        }
        
        # Analyze exit patterns
        exit_patterns = {'delta_decay': 0, 'theta_acceleration': 0, 'iv_crush': 0, 'gamma_risk': 0}
        
        for position_key, history in self.portfolio.greeks_tracker.position_histories.items():
            if history.exit_snapshot:
                patterns = self.portfolio.greeks_tracker.analyze_greeks_patterns(position_key)
                if patterns:
                    if patterns.get('delta_decay', {}).get('change_percent', 0) > 50:
                        exit_patterns['delta_decay'] += 1
                    if patterns.get('theta_acceleration', {}).get('change_ratio', 0) > 2.0:
                        exit_patterns['theta_acceleration'] += 1
                    if patterns.get('iv_crush', {}).get('is_crushing', False):
                        exit_patterns['iv_crush'] += 1
                    if patterns.get('gamma_risk', {}).get('is_high_gamma', False):
                        exit_patterns['gamma_risk'] += 1
        
        insights['exit_patterns'] = exit_patterns
        
        # Portfolio Greeks extremes
        if self.portfolio.greeks_tracker.portfolio_snapshots:
            portfolio_df = pd.DataFrame(self.portfolio.greeks_tracker.portfolio_snapshots)
            insights['portfolio_greeks_extremes'] = {
                'max_delta_exposure': portfolio_df['total_delta'].max() if 'total_delta' in portfolio_df else 0,
                'min_delta_exposure': portfolio_df['total_delta'].min() if 'total_delta' in portfolio_df else 0,
                'max_gamma_exposure': portfolio_df['total_gamma'].max() if 'total_gamma' in portfolio_df else 0,
                'max_theta_exposure': portfolio_df['total_theta'].min() if 'total_theta' in portfolio_df else 0,  # Most negative
                'max_vega_exposure': portfolio_df['total_vega'].max() if 'total_vega' in portfolio_df else 0
            }
        
        return insights


def create_strategy(strategy_name: str, params: Dict[str, Any]):
    """Enhanced strategy factory with better error handling"""
    strategies = {
        'long_call': LongCallStrategy,
        'long_put': LongPutStrategy,
        'straddle': StraddleStrategy,
        'covered_call': CoveredCallStrategy
    }
    
    if strategy_name not in strategies:
        suggestion = suggest_similar_command(strategy_name, list(strategies.keys()))
        error_msg = f"Unknown strategy: {strategy_name}"
        if suggestion:
            error_msg += f". Did you mean '{suggestion}'?"
        else:
            error_msg += f". Available strategies: {', '.join(strategies.keys())}"
        
        raise ValueError(error_msg)
    
    return strategies[strategy_name](params)


def create_strategy_from_yaml(yaml_config: Dict[str, Any], override_params: Optional[Dict[str, Any]] = None) -> Any:
    """Create strategy instance from YAML configuration"""
    # Extract strategy type from YAML config
    if 'legs' not in yaml_config or len(yaml_config['legs']) == 0:
        raise ValueError("YAML config must have at least one leg defined")
    
    # Determine strategy type from leg configuration
    legs = yaml_config['legs']
    first_leg = legs[0]
    
    # Map YAML leg configuration to strategy type
    strategy_mapping = {
        ('call', 'long', 1): 'long_call',
        ('put', 'long', 1): 'long_put',
        ('call', 'long', 2): 'straddle',  # Assumes call+put straddle
        ('call', 'short', 1): 'covered_call'  # Simplified mapping
    }
    
    # Determine strategy key
    leg_type = first_leg.get('type', '').lower()
    direction = first_leg.get('direction', '').lower()
    num_legs = len(legs)
    
    strategy_key = strategy_mapping.get((leg_type, direction, num_legs))
    
    if not strategy_key:
        # For straddle, check if it's call + put
        if num_legs == 2 and any(leg['type'].lower() == 'put' for leg in legs):
            strategy_key = 'straddle'
        else:
            raise ValueError(f"Cannot determine strategy type from YAML configuration")
    
    # Build parameters from YAML config
    params = DEFAULT_PARAMS.copy()
    
    # Extract entry rules
    if 'entry_rules' in yaml_config:
        entry_rules = yaml_config['entry_rules']
        
        # DTE parameters
        if 'dte' in entry_rules:
            params['target_dte'] = int(entry_rules['dte'])
        if 'dte_range' in entry_rules:
            params['min_dte'] = int(entry_rules['dte_range'][0])
            params['max_dte'] = int(entry_rules['dte_range'][1])
        
        # Delta parameters
        if 'target_delta' in entry_rules:
            params['delta_threshold'] = abs(float(entry_rules['target_delta']))
            params['target_delta'] = float(entry_rules['target_delta'])
        if 'delta_tolerance' in entry_rules:
            params['delta_tolerance'] = float(entry_rules['delta_tolerance'])
        if 'delta_range' in entry_rules:
            params['use_delta_bands'] = True
            params['delta_min'] = float(entry_rules['delta_range'][0])
            params['delta_max'] = float(entry_rules['delta_range'][1])
    
    # Extract exit rules
    if 'exit_rules' in yaml_config:
        exit_rules = yaml_config['exit_rules']
        
        if 'profit_target_pct' in exit_rules:
            params['profit_target_pct'] = float(exit_rules['profit_target_pct'])
        if 'stop_loss_pct' in exit_rules:
            params['stop_loss_pct'] = float(exit_rules['stop_loss_pct'])
        if 'exit_on_dte' in exit_rules:
            params['exit_dte'] = int(exit_rules['exit_on_dte'])
        if 'max_hold_days' in exit_rules:
            params['max_hold_days'] = int(exit_rules['max_hold_days'])
    
    # Extract risk management parameters
    if 'risk_management' in yaml_config:
        risk_mgmt = yaml_config['risk_management']
        
        if 'max_positions' in risk_mgmt:
            params['max_positions'] = int(risk_mgmt['max_positions'])
        
        if 'position_sizing' in risk_mgmt:
            sizing = risk_mgmt['position_sizing']
            if 'max_position_size_pct' in sizing:
                params['max_position_size'] = float(sizing['max_position_size_pct'])
    
    # Parse advanced exit configurations
    if 'dynamic_stops' in yaml_config and yaml_config['dynamic_stops'].get('enabled'):
        params['use_advanced_exits'] = True
        params['enable_dynamic_stops'] = True
        
        # Parse ATR settings
        atr_settings = yaml_config['dynamic_stops'].get('atr_settings', {})
        params['atr_period'] = int(atr_settings.get('period', 14))
        params['volatility_lookback'] = int(atr_settings.get('volatility_lookback', 30))
        
        # Parse component weights
        weights = yaml_config['dynamic_stops'].get('component_weights', {})
        params['atr_weight'] = float(weights.get('atr_weight', 0.4))
        params['vega_weight'] = float(weights.get('vega_weight', 0.35))
        params['theta_weight'] = float(weights.get('theta_weight', 0.25))
        
        params['confidence_threshold'] = float(yaml_config['dynamic_stops'].get('confidence_threshold', 0.7))
    
    if 'greeks_exits' in yaml_config and yaml_config['greeks_exits'].get('enabled'):
        params['use_advanced_exits'] = True
        params['enable_greeks_exits'] = True
        
        # Parse Greeks exit thresholds
        if 'delta_threshold_exit' in yaml_config['greeks_exits']:
            delta_exit = yaml_config['greeks_exits']['delta_threshold_exit']
            if delta_exit.get('enabled') and 'threshold' in delta_exit:
                params['delta_exit_threshold'] = float(delta_exit['threshold'])
        
        if 'theta_acceleration_exit' in yaml_config['greeks_exits']:
            theta_exit = yaml_config['greeks_exits']['theta_acceleration_exit']
            if theta_exit.get('enabled') and 'threshold' in theta_exit:
                params['theta_acceleration_threshold'] = float(theta_exit['threshold'])
        
        if 'vega_crush_exit' in yaml_config['greeks_exits']:
            vega_exit = yaml_config['greeks_exits']['vega_crush_exit']
            if vega_exit.get('enabled') and 'threshold' in vega_exit:
                params['vega_crush_threshold'] = float(vega_exit['threshold'])
    
    if 'iv_exits' in yaml_config and yaml_config['iv_exits'].get('enabled'):
        params['use_advanced_exits'] = True
        params['enable_iv_exits'] = True
        
        # Parse IV exit thresholds
        if 'iv_rank_exit' in yaml_config['iv_exits']:
            iv_rank_exit = yaml_config['iv_exits']['iv_rank_exit']
            if iv_rank_exit.get('enabled') and 'threshold' in iv_rank_exit:
                params['iv_rank_exit_threshold'] = float(iv_rank_exit['threshold'])
    
    # Apply any parameter overrides
    if override_params:
        params.update(override_params)
    
    # Create strategy instance
    return create_strategy(strategy_key, params)


def reconstruct_cli_command(args) -> str:
    """Reconstruct the CLI command from parsed arguments"""
    cmd_parts = ['python backtester_enhanced.py']
    
    # Check if YAML config was used
    if hasattr(args, 'yaml_config') and args.yaml_config:
        cmd_parts.append(f"--yaml-config {args.yaml_config}")
        cmd_parts.append(f"--start-date {args.start_date}")
        cmd_parts.append(f"--end-date {args.end_date}")
        
        # Add any YAML overrides
        if hasattr(args, 'yaml_overrides') and args.yaml_overrides:
            for key, value in args.yaml_overrides.items():
                cmd_parts.append(f"--override {key}={value}")
    else:
        # Traditional CLI arguments
        cmd_parts.append(f"--strategy {args.strategy}")
        cmd_parts.append(f"--start-date {args.start_date}")
        cmd_parts.append(f"--end-date {args.end_date}")
        
        # Optional arguments (only add if different from defaults)
        if args.initial_capital != 100000:
            cmd_parts.append(f"--initial-capital {args.initial_capital}")
        
        # Delta parameters - show the approach being used
        if args.delta_min is not None and args.delta_max is not None:
            cmd_parts.append(f"--delta-min {args.delta_min}")
            cmd_parts.append(f"--delta-max {args.delta_max}")
        else:
            if args.delta_threshold != 0.30:
                cmd_parts.append(f"--delta-threshold {args.delta_threshold}")
        
        # DTE parameters
        if args.min_dte != 10:
            cmd_parts.append(f"--min-dte {args.min_dte}")
        if args.max_dte != 60:
            cmd_parts.append(f"--max-dte {args.max_dte}")
        
        # Risk management parameters
        if args.stop_loss != 0.50:
            cmd_parts.append(f"--stop-loss {args.stop_loss}")
        if args.profit_target != 1.00:
            cmd_parts.append(f"--profit-target {args.profit_target}")
        if args.position_size != 0.05:
            cmd_parts.append(f"--position-size {args.position_size}")
    
    # Output parameter
    if args.output:
        cmd_parts.append(f"--output {args.output}")
    
    return ' '.join(cmd_parts)


def print_enhanced_results(results: Dict[str, Any]):
    """Print enhanced backtest results with colors and formatting"""
    print(f"\n{Colors.bold('📊 BACKTEST RESULTS')}")
    print("=" * 70)
    
    perf = results['performance']
    
    print(f"{Colors.cyan('Strategy:')} {results['strategy']}")
    print(f"{Colors.cyan('Period:')} {results['period']}")
    
    # Show CLI command if available
    if 'cli_command' in results:
        print(f"\n{Colors.bold('📋 REPRODUCIBLE COMMAND')}")
        print("-" * 40)
        # Break long command into multiple lines for readability
        cmd = results['cli_command']
        if len(cmd) > 80:
            # Split at logical points and indent continuation lines
            parts = cmd.split(' --')
            print(f"  {parts[0]} \\")
            for part in parts[1:]:
                print(f"    --{part} \\")
            print()  # Remove trailing backslash visually
        else:
            print(f"  {cmd}")
        print()
    
    print(f"\n{Colors.bold('💰 PERFORMANCE SUMMARY')}")
    print("-" * 40)
    print(f"  Initial Capital:     {format_currency(perf['initial_capital']):>15}")
    print(f"  Final Value:         {format_currency(perf['final_value']):>15}")
    print(f"  Total Return:        {format_percentage(perf['total_return']):>15}")
    print(f"  Total P&L:           {format_currency(perf['total_pnl']):>15}")
    print(f"  Max Drawdown:        {format_percentage(perf['max_drawdown']):>15}")
    print(f"  Sharpe Ratio:        {Colors.cyan(f'{perf['sharpe_ratio']:.2f}'):>15}")
    print(f"  Number of Trades:    {Colors.cyan(str(perf['num_trades'])):>15}")
    
    # Print trade summary if trades exist
    trades_df = results['trades_df']
    if not trades_df.empty:
        print(f"\n{Colors.bold('📈 TRADE SUMMARY')}")
        print("-" * 40)
        
        # Calculate some trade stats
        opening_trades = trades_df[trades_df['order_type'].str.contains('open')]
        if not opening_trades.empty:
            avg_trade_size = opening_trades['total_cost'].mean()
            print(f"  Average Trade Size:  {format_currency(abs(avg_trade_size)):>15}")
        
        # Show trade distribution by option type
        trade_counts = trades_df['option_type'].value_counts()
        for option_type, count in trade_counts.items():
            print(f"  {option_type} Trades:           {Colors.cyan(str(count)):>15}")
        
        print(f"\n{Colors.bold('📋 RECENT TRADES (Last 5)')}")
        recent_trades = trades_df.tail(5)[['date', 'option_type', 'strike', 'order_type', 'quantity', 'price']]
        print(recent_trades.to_string(index=False))
    
    # Performance insights
    print(f"\n{Colors.bold('🎯 INSIGHTS')}")
    print("-" * 40)
    
    return_pct = perf['total_return']
    sharpe = perf['sharpe_ratio']
    max_dd = perf['max_drawdown']
    
    if return_pct > 0.1:
        print(f"  {Colors.green('✅')} Strong positive returns ({return_pct:.1%})")
    elif return_pct > 0:
        print(f"  {Colors.yellow('⚡')} Modest positive returns ({return_pct:.1%})")
    else:
        print(f"  {Colors.red('❌')} Negative returns ({return_pct:.1%})")
    
    if sharpe > 1.0:
        print(f"  {Colors.green('✅')} Excellent risk-adjusted returns (Sharpe: {sharpe:.2f})")
    elif sharpe > 0.5:
        print(f"  {Colors.yellow('⚡')} Good risk-adjusted returns (Sharpe: {sharpe:.2f})")
    else:
        print(f"  {Colors.red('❌')} Poor risk-adjusted returns (Sharpe: {sharpe:.2f})")
    
    if max_dd < 0.1:
        print(f"  {Colors.green('✅')} Low drawdown ({max_dd:.1%})")
    elif max_dd < 0.2:
        print(f"  {Colors.yellow('⚡')} Moderate drawdown ({max_dd:.1%})")
    else:
        print(f"  {Colors.red('❌')} High drawdown ({max_dd:.1%})")
    
    # Greeks insights if available
    if 'greeks_insights' in results:
        print(f"\n{Colors.bold('📊 GREEKS ANALYSIS')}")
        print("-" * 40)
        
        greeks = results['greeks_insights']
        print(f"  Positions tracked: {greeks['total_positions_tracked']}")
        
        if 'exit_patterns' in greeks:
            patterns = greeks['exit_patterns']
            if any(patterns.values()):
                print(f"\n  {Colors.cyan('Exit Patterns Detected:')}")
                if patterns['delta_decay'] > 0:
                    print(f"    • Delta decay exits: {patterns['delta_decay']}")
                if patterns['theta_acceleration'] > 0:
                    print(f"    • Theta acceleration exits: {patterns['theta_acceleration']}")
                if patterns['iv_crush'] > 0:
                    print(f"    • IV crush exits: {patterns['iv_crush']}")
                if patterns['gamma_risk'] > 0:
                    print(f"    • High gamma risk exits: {patterns['gamma_risk']}")
        
        if 'portfolio_greeks_extremes' in greeks:
            extremes = greeks['portfolio_greeks_extremes']
            print(f"\n  {Colors.cyan('Portfolio Greeks Extremes:')}")
            print(f"    • Max Delta exposure: {extremes['max_delta_exposure']:.2f}")
            print(f"    • Max Gamma exposure: {extremes['max_gamma_exposure']:.3f}")
            print(f"    • Max Theta exposure: {extremes['max_theta_exposure']:.2f}")
            print(f"    • Max Vega exposure: {extremes['max_vega_exposure']:.2f}")


def validate_inputs(args) -> bool:
    """Validate user inputs and provide helpful feedback"""
    # Validate dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y%m%d')
        end_date = datetime.strptime(args.end_date, '%Y%m%d')
        
        if start_date >= end_date:
            print_error("Start date must be before end date")
            return False
        
        # Check if date range is reasonable
        days_diff = (end_date - start_date).days
        if days_diff < 30:
            print_warning(f"Short backtest period ({days_diff} days). Consider longer periods for meaningful results.")
        elif days_diff > 1000:
            print_warning(f"Very long backtest period ({days_diff} days). This may take a while.")
        
    except ValueError:
        print_error("Invalid date format. Please use YYYYMMDD (e.g., 20220101)")
        return False
    
    # If using YAML config, validate it exists
    if hasattr(args, 'yaml_config') and args.yaml_config:
        yaml_path = Path(args.yaml_config)
        if not yaml_path.exists():
            # Try looking in standard directories
            search_paths = [
                Path("config/strategies") / args.yaml_config,
                Path("strategy_templates") / args.yaml_config,
                Path("../optionslab-ui/config/strategies") / args.yaml_config,
                Path("../optionslab-ui/strategy_templates") / args.yaml_config
            ]
            
            found = False
            for path in search_paths:
                if path.exists():
                    args.yaml_config = str(path)
                    found = True
                    break
            
            if not found:
                print_error(f"YAML config file not found: {args.yaml_config}")
                print_info("Available locations searched:")
                for path in search_paths:
                    print_info(f"  - {path}")
                return False
        
        print_info(f"Using YAML configuration: {args.yaml_config}")
        return True  # Skip other validations for YAML mode
    
    # Traditional parameter validation
    if args.initial_capital <= 0:
        print_error("Initial capital must be positive")
        return False
    
    # Validate delta parameters
    if args.delta_min is not None and args.delta_max is not None:
        # Using explicit delta bands
        if args.delta_min >= args.delta_max:
            print_error("Delta min must be less than delta max")
            return False
        if not (-1 <= args.delta_min <= 1 and -1 <= args.delta_max <= 1):
            print_error("Delta bands must be between -1 and 1")
            return False
        print_info(f"Using explicit delta bands: {args.delta_min:.3f} to {args.delta_max:.3f}")
    else:
        # Using traditional delta threshold
        if not (0 < args.delta_threshold < 1):
            print_error("Delta threshold must be between 0 and 1")
            return False
    
    if args.min_dte >= args.max_dte:
        print_error("Minimum DTE must be less than maximum DTE")
        return False
    
    if not (0 < args.position_size <= 1):
        print_error("Position size must be between 0 and 1 (0 to 100%)")
        return False
    
    return True


def parse_override(override_str: str) -> Tuple[str, Any]:
    """Parse override string in format key=value"""
    if '=' not in override_str:
        raise ValueError(f"Invalid override format: {override_str}. Expected key=value")
    
    key, value = override_str.split('=', 1)
    key = key.strip()
    value = value.strip()
    
    # Try to parse value as different types
    # Boolean
    if value.lower() in ['true', 'false']:
        return key, value.lower() == 'true'
    
    # Number
    try:
        if '.' in value:
            return key, float(value)
        else:
            return key, int(value)
    except ValueError:
        pass
    
    # String (default)
    return key, value


def list_yaml_configs():
    """List available YAML configuration files"""
    print(f"\n{Colors.bold('📋 AVAILABLE YAML CONFIGURATIONS')}")
    print("=" * 60)
    
    config_dirs = [
        ("Strategy Configs", Path("config/strategies")),
        ("Strategy Templates", Path("strategy_templates")),
        ("Streamlit Configs", Path("../optionslab-ui/config/strategies")),
        ("Streamlit Templates", Path("../optionslab-ui/strategy_templates"))
    ]
    
    found_any = False
    for dir_name, dir_path in config_dirs:
        if dir_path.exists():
            yaml_files = list(dir_path.glob("*.yaml"))
            if yaml_files:
                found_any = True
                print(f"\n{Colors.cyan(dir_name)}:")
                for yaml_file in sorted(yaml_files):
                    # Try to load and show description
                    try:
                        with open(yaml_file, 'r') as f:
                            config = yaml.safe_load(f)
                            name = config.get('name', yaml_file.stem)
                            desc = config.get('description', 'No description')
                            print(f"  {Colors.green(yaml_file.name):30} - {name}")
                            if desc != 'No description':
                                print(f"    {desc[:60]}...")
                    except:
                        print(f"  {Colors.green(yaml_file.name)}")
    
    if not found_any:
        print_warning("No YAML configuration files found!")
        print_info("Create YAML files in config/strategies/ or strategy_templates/")
    
    print("\n" + "=" * 60)
    print(f"{Colors.yellow('Usage:')} python backtester_enhanced.py --yaml-config <filename.yaml> --start-date YYYYMMDD --end-date YYYYMMDD")


def main():
    """Enhanced main CLI function with YAML support"""
    # Create parser with better description and help
    parser = argparse.ArgumentParser(
        description='🚀 SPY Options Backtester - Professional options strategy testing with YAML support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Colors.bold('EXAMPLES:')}
  # Quick test with traditional CLI
  python backtester_enhanced.py --strategy long_call --start-date 20220601 --end-date 20220630
  
  # Using YAML configuration
  python backtester_enhanced.py --yaml-config long_put_template.yaml --start-date 20220101 --end-date 20221231
  
  # YAML with parameter overrides
  python backtester_enhanced.py --yaml-config enhanced_exit_template.yaml --start-date 20230101 --end-date 20231231 --override profit_target_pct=0.75

{Colors.bold('INTERACTIVE MODE:')}
  python backtester_enhanced.py --interactive

{Colors.bold('MORE INFO:')}
  python backtester_enhanced.py --strategies    # View strategy descriptions
  python backtester_enhanced.py --examples      # View detailed examples
  python backtester_enhanced.py --list-yaml     # List available YAML configs
        """
    )
    
    # Special flags that don't require strategy
    parser.add_argument('-i', '--interactive', action='store_true',
                       help='Run in interactive mode (guided setup)')
    parser.add_argument('--strategies', action='store_true',
                       help='Show detailed strategy descriptions')
    parser.add_argument('--examples', action='store_true',
                       help='Show usage examples')
    parser.add_argument('--list-yaml', action='store_true',
                       help='List available YAML configuration files')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    
    # YAML configuration support
    parser.add_argument('--yaml-config', type=str,
                       help='Path to YAML strategy configuration file')
    parser.add_argument('--override', action='append',
                       help='Override YAML parameters (format: key=value, can be used multiple times)')
    
    # Strategy and date arguments (required unless using special flags or YAML)
    parser.add_argument('--strategy', 
                       choices=['long_call', 'long_put', 'straddle', 'covered_call'],
                       help='Strategy to backtest (not needed with --yaml-config)')
    parser.add_argument('--start-date', 
                       help='Start date (YYYYMMDD)')
    parser.add_argument('--end-date',
                       help='End date (YYYYMMDD)')
    
    # Optional parameters with better descriptions
    parser.add_argument('--initial-capital', type=float, default=100000,
                       help='Initial capital in dollars (default: 100000)')
    # Delta selection - either threshold OR explicit bands
    parser.add_argument('--delta-threshold', type=float, default=0.30,
                       help='Delta threshold for option selection (default: 0.30)')
    parser.add_argument('--delta-tolerance', type=float, default=0.05,
                       help='Acceptable deviation from delta threshold (default: 0.05)')
    parser.add_argument('--delta-min', type=float, 
                       help='Minimum acceptable delta (explicit band approach)')
    parser.add_argument('--delta-max', type=float,
                       help='Maximum acceptable delta (explicit band approach)')
    parser.add_argument('--min-dte', type=int, default=10,
                       help='Minimum days to expiration (default: 10)')
    parser.add_argument('--max-dte', type=int, default=60,
                       help='Maximum days to expiration (default: 60)')
    parser.add_argument('--stop-loss', type=float, default=0.50,
                       help='Stop loss as decimal (0.50 = 50%%, default: 0.50)')
    parser.add_argument('--profit-target', type=float, default=1.00,
                       help='Profit target as decimal (1.00 = 100%%, default: 1.00)')
    parser.add_argument('--position-size', type=float, default=0.05,
                       help='Max position size as decimal (0.05 = 5%%, default: 0.05)')
    parser.add_argument('--output', type=str, 
                       help='Output directory for saving results')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle special flags first
    if args.no_color:
        # Disable colors globally (would need to modify Colors class)
        pass
    
    if args.strategies:
        print_strategy_descriptions()
        return
    
    if args.examples:
        print_examples()
        return
    
    if args.list_yaml:
        list_yaml_configs()
        return
    
    if args.interactive:
        if not is_interactive():
            print_error("Interactive mode requires a terminal")
            sys.exit(1)
        
        # Run interactive mode
        config = run_interactive_mode()
        
        # Convert interactive config to args format
        args.strategy = config['strategy']
        args.start_date = config['start_date']
        args.end_date = config['end_date']
        args.initial_capital = config['initial_capital']
        args.delta_threshold = config['delta_threshold']
        args.min_dte = config['min_dte']
        args.max_dte = config['max_dte']
        args.stop_loss = config['stop_loss']
        args.profit_target = config['profit_target']
        args.position_size = config['position_size']
        args.output = config.get('output')
    
    # Check if using YAML configuration
    if args.yaml_config:
        if not YAML_SUPPORT:
            print_error("YAML configuration support not available. Please ensure strategy_config_manager is accessible.")
            sys.exit(1)
        
        # Validate date arguments are provided
        if not args.start_date or not args.end_date:
            print_error("Start date and end date are required when using YAML config")
            print_info("Usage: python backtester_enhanced.py --yaml-config <file.yaml> --start-date YYYYMMDD --end-date YYYYMMDD")
            sys.exit(1)
        
        # Validate inputs (including YAML path validation)
        if not validate_inputs(args):
            sys.exit(1)
        
        try:
            # Load YAML configuration
            config_manager = StrategyConfigManager()
            yaml_config = config_manager.load_strategy_config(args.yaml_config)
            
            # Process overrides if provided
            override_params = {}
            if args.override:
                args.yaml_overrides = {}
                for override in args.override:
                    try:
                        key, value = parse_override(override)
                        override_params[key] = value
                        args.yaml_overrides[key] = value
                    except Exception as e:
                        print_error(f"Invalid override: {override}")
                        print_info(f"Error: {e}")
                        sys.exit(1)
            
            # Apply overrides to YAML config
            if override_params:
                yaml_config = config_manager.apply_overrides(yaml_config, override_params)
            
            # Create strategy from YAML
            print_info(f"Loading strategy: {yaml_config.get('name', 'Unknown')}")
            print_info(f"Description: {yaml_config.get('description', 'No description')[:80]}...")
            
            # Add initial capital override if specified
            if args.initial_capital != 100000:
                override_params['initial_capital'] = args.initial_capital
            
            strategy = create_strategy_from_yaml(yaml_config, override_params)
            
            # Run enhanced backtest
            engine = EnhancedBacktestEngine(strategy, args.start_date, args.end_date, 
                                          args.initial_capital)
            results = engine.run_backtest()
            
            # Add CLI command and config info to results
            results['cli_command'] = reconstruct_cli_command(args)
            results['yaml_config'] = args.yaml_config
            results['config_name'] = yaml_config.get('name', 'Unknown')
            
            # Print enhanced results
            print_enhanced_results(results)
            
            # Print configuration summary
            if yaml_config.get('dynamic_stops', {}).get('enabled') or yaml_config.get('greeks_exits', {}).get('enabled'):
                print(f"\n{Colors.bold('🔧 ADVANCED FEATURES USED:')}")
                print("-" * 40)
                if yaml_config.get('dynamic_stops', {}).get('enabled'):
                    print(f"  {Colors.green('✓')} Dynamic Volatility Stops")
                if yaml_config.get('greeks_exits', {}).get('enabled'):
                    print(f"  {Colors.green('✓')} Greeks-Based Exits")
                if yaml_config.get('iv_exits', {}).get('enabled'):
                    print(f"  {Colors.green('✓')} IV-Based Exits")
            
            # Save results if requested
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                trades_df = results['trades_df']
                if not trades_df.empty:
                    trades_file = output_path.with_suffix('.csv')
                    trades_df.to_csv(trades_file, index=False)
                    print_success(f"Trades saved to: {trades_file}")
                
                snapshots_df = results['snapshots_df']
                if not snapshots_df.empty:
                    snapshots_file = output_path.with_name(f"{output_path.stem}_portfolio.csv")
                    snapshots_df.to_csv(snapshots_file, index=False)
                    print_success(f"Portfolio history saved to: {snapshots_file}")
                
                # Save configuration used
                config_file = output_path.with_name(f"{output_path.stem}_config.yaml")
                with open(config_file, 'w') as f:
                    yaml.dump(yaml_config, f, default_flow_style=False, indent=2)
                print_success(f"Configuration saved to: {config_file}")
            
            print(f"\n{Colors.bold('🎉 YAML BACKTEST COMPLETE!')}")
            
        except Exception as e:
            print_error(f"YAML backtest failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    else:
        # Traditional CLI mode
        # Validate required arguments
        if not args.strategy:
            print_banner()
            print_error("Strategy is required (or use --yaml-config)")
            print_info("Try: python backtester_enhanced.py --interactive")
            print_info("Or:  python backtester_enhanced.py --list-yaml")
            print_info("Or:  python backtester_enhanced.py --help")
            sys.exit(1)
        
        if not args.start_date or not args.end_date:
            print_error("Start date and end date are required")
            print_info("Try: python backtester_enhanced.py --interactive")
            sys.exit(1)
        
        # Validate inputs
        if not validate_inputs(args):
            sys.exit(1)
        
        # Build strategy parameters
        params = DEFAULT_PARAMS.copy()
        
        # Handle delta parameters - explicit bands vs threshold
        if args.delta_min is not None and args.delta_max is not None:
            # Using explicit delta bands
            params.update({
                'use_delta_bands': True,
                'delta_min': args.delta_min,
                'delta_max': args.delta_max,
                'delta_threshold': (abs(args.delta_min) + abs(args.delta_max)) / 2,  # For backward compatibility
                'target_delta': (args.delta_min + args.delta_max) / 2  # Center of band
            })
        else:
            # Using traditional delta threshold
            params.update({
                'use_delta_bands': False,
                'delta_threshold': args.delta_threshold,
                'delta_tolerance': args.delta_tolerance,
                'target_delta': args.delta_threshold if args.strategy != 'long_put' else -args.delta_threshold,
            })
        
        params.update({
            'initial_capital': args.initial_capital,
            'min_dte': args.min_dte,
            'max_dte': args.max_dte,
            'stop_loss_pct': args.stop_loss,
            'profit_target_pct': args.profit_target,
            'max_position_size': args.position_size
        })
        
        try:
            # Create strategy
            strategy = create_strategy(args.strategy, params)
            
            # Run enhanced backtest
            engine = EnhancedBacktestEngine(strategy, args.start_date, args.end_date, 
                                          args.initial_capital)
            results = engine.run_backtest()
            
            # Add CLI command to results for reproducibility
            results['cli_command'] = reconstruct_cli_command(args)
            
            # Print enhanced results
            print_enhanced_results(results)
            
            # Print delta targeting summary if available
            if hasattr(strategy, 'get_delta_targeting_summary'):
                print(f"\n{Colors.bold('=' * 60)}")
                print(strategy.get_delta_targeting_summary())
                print(f"{Colors.bold('=' * 60)}")
            
            # Save results if requested
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                trades_df = results['trades_df']
                if not trades_df.empty:
                    trades_file = output_path.with_suffix('.csv')
                    trades_df.to_csv(trades_file, index=False)
                    print_success(f"Trades saved to: {trades_file}")
                
                snapshots_df = results['snapshots_df']
                if not snapshots_df.empty:
                    snapshots_file = output_path.with_name(f"{output_path.stem}_portfolio.csv")
                    snapshots_df.to_csv(snapshots_file, index=False)
                    print_success(f"Portfolio history saved to: {snapshots_file}")
            
            print(f"\n{Colors.bold('🎉 BACKTEST COMPLETE!')}")
            
        except KeyboardInterrupt:
            print(f"\n{Colors.yellow('⚠️  Backtest cancelled by user')}")
            sys.exit(0)
        except Exception as e:
            print_error(f"Backtest failed: {e}")
            print_info("Try running with --interactive for guided setup")
            sys.exit(1)


if __name__ == "__main__":
    main()