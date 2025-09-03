# %%
"""
Enhanced PMCC (Poor Man's Covered Call) Strategy - v1
====================================================
Uses improved optionslab core infrastructure:
- Robust data loading with automatic DTE calculation
- VIX-based entry timing filters  
- Dynamic position sizing based on volatility and Greeks
- Enhanced exit rules with adaptive profit targets
- Portfolio Greeks monitoring for risk management

Strategy Overview:
- LEAP: Buy deep ITM call with 365-800 DTE, delta 0.70-0.85
- Short Call: Sell OTM call with 30-45 DTE, delta 0.20-0.30  
- Roll short call at 18 DTE if not profitable
- Manage based on Greeks and volatility environment

Key Improvements from v2:
- VIX timing for optimal entries
- Dynamic position sizing reduces risk in high vol
- Portfolio Greeks monitoring prevents overexposure
- Enhanced profit targets based on market regime
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import enhanced optionslab infrastructure
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))

from optionslab.data_loader import load_data
from optionslab.market_filters import MarketFilters
from optionslab.option_selector import (
    find_suitable_options, calculate_dynamic_position_size, 
    calculate_portfolio_greeks, calculate_volatility_context
)

# Display settings
pd.set_option('display.float_format', '{:.2f}'.format)
pd.set_option('display.max_columns', None)

print("=" * 60)
print("ENHANCED PMCC STRATEGY WITH OPTIMIZATION FRAMEWORK")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# %% [markdown]
# ## 1. Strategy Configuration

# %%
# Enhanced strategy configuration with optimization parameters
STRATEGY_CONFIG = {
    'name': 'Enhanced PMCC v1',
    'strategy_type': 'pmcc',
    
    # Capital management
    'parameters': {
        'initial_capital': 50000,
        'commission_per_contract': 0.65,
        'slippage_pct': 0.005,  # 0.5% slippage
    },
    
    # LEAP leg configuration
    'leap_selection': {
        'delta_criteria': {
            'target': 0.80,
            'minimum': 0.70,
            'maximum': 0.90
        },
        'dte_criteria': {
            'minimum': 365,
            'maximum': 800,
            'target': 500
        },
        'liquidity_criteria': {
            'min_volume': 50,
            'max_spread_pct': 0.10,
            'min_open_interest': 100
        }
    },
    
    # Short call leg configuration  
    'short_call_selection': {
        'delta_criteria': {
            'target': 0.25,
            'minimum': 0.20,
            'maximum': 0.35
        },
        'dte_criteria': {
            'minimum': 30,
            'maximum': 45, 
            'target': 35
        },
        'liquidity_criteria': {
            'min_volume': 100,
            'max_spread_pct': 0.15,
            'min_open_interest': 50
        }
    },
    
    # Enhanced market timing filters
    'market_filters': {
        'vix_timing': {
            'lookback_days': 20,
            'percentile_threshold': 30,  # Enter in lower 30% of VIX (favorable for long premium)
            'absolute_threshold': 25.0   # Don't enter if VIX > 25
        },
        'trend_filter': {
            'ma_period': 20,
            'require_above_ma': True    # Only enter when SPY above 20-day MA
        }
    },
    
    # Dynamic position sizing
    'dynamic_sizing': {
        'base_position_size_pct': 0.20,      # 20% per position (PMCC needs larger allocation)
        'max_position_size_pct': 0.35,       # 35% max
        'max_concurrent_positions': 3,        # Max 3 PMCC positions (higher capital per position)
        'max_portfolio_delta': 200,           # Max 200 delta exposure
        'max_portfolio_vega': 500            # Max 500 vega exposure
    },
    
    # Enhanced exit rules
    'exit_rules': {
        'profit_targets': {
            'short_call_base': 0.40,          # 40% of credit received
            'short_call_high_vol': 0.50,      # 50% in high vol environment  
            'leap_stop_loss': 0.30,           # 30% loss on LEAP
            'total_position_profit': 0.25     # 25% profit on total position
        },
        'time_rules': {
            'short_call_roll_dte': 18,        # Roll at 18 DTE
            'leap_min_hold_days': 30,         # Hold LEAP minimum 30 days
            'max_position_days': 120          # Close position after 120 days
        },
        'greeks_management': {
            'delta_stop': 0.80,               # Close if position delta > 80
            'vega_stop': 100                  # Close if position vega > 100
        }
    }
}

print("✅ Strategy configuration loaded")
print(f"📊 Base position size: {STRATEGY_CONFIG['dynamic_sizing']['base_position_size_pct']:.1%}")
print(f"🎯 Target short call delta: {STRATEGY_CONFIG['short_call_selection']['delta_criteria']['target']:.2f}")
print(f"🎯 Target LEAP delta: {STRATEGY_CONFIG['leap_selection']['delta_criteria']['target']:.2f}")

# %% [markdown] 
# ## 2. Data Loading and Validation

# %%
# Load SPY options data using enhanced data_loader
print("\n" + "=" * 40)
print("LOADING DATA WITH ENHANCED INFRASTRUCTURE")
print("=" * 40)

# Data parameters
START_DATE = "2023-01-01" 
END_DATE = "2024-12-31"
DATA_PATH = "/Users/nish_macbook/trading/daily-optionslab/data/spy_options/SPY_OPTIONS_2024_COMPLETE.parquet"

# Load data - now automatically handles DTE calculation and date conversion
data = load_data(DATA_PATH, START_DATE, END_DATE)

if data is None or len(data) == 0:
    raise ValueError("Failed to load options data!")

print(f"\n✅ Data loaded successfully: {len(data):,} records")
print(f"📅 Date range: {data['date'].min().date()} to {data['date'].max().date()}")
print(f"📊 Strike range: ${data['strike'].min():.0f} - ${data['strike'].max():.0f}")
print(f"⏰ DTE range: {data['dte'].min()} - {data['dte'].max()} days")

# Filter for valid options data
data_clean = data[
    (data['bid'] > 0) & 
    (data['ask'] > data['bid']) &
    (data['volume'] > 0) &
    (data['implied_vol'] > 0) &
    (data['implied_vol'] < 2.0)  # Remove extreme IV outliers
].copy()

print(f"📊 After cleaning: {len(data_clean):,} records ({len(data_clean)/len(data)*100:.1f}% retained)")

# Get unique trading dates
trading_dates = sorted(data_clean['date'].unique())
print(f"📅 Trading days: {len(trading_dates)}")

# %% [markdown]
# ## 3. Enhanced PMCC Strategy Implementation

# %%
class EnhancedPMCCStrategy:
    """Enhanced PMCC strategy with optimization framework"""
    
    def __init__(self, config, data):
        self.config = config
        self.data = data
        self.initial_capital = config['parameters']['initial_capital']
        self.cash = self.initial_capital
        
        # Position tracking
        self.positions = []  # List of PMCC positions
        self.trade_history = []
        self.daily_values = []
        
        # Greeks tracking
        self.portfolio_greeks_history = []
        
        # Performance metrics
        self.metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'total_pnl': 0,
            'max_drawdown': 0,
            'max_positions': 0
        }
    
    def run_backtest(self):
        """Run enhanced PMCC backtest with all optimizations"""
        print(f"\n🚀 Starting enhanced PMCC backtest...")
        
        trading_dates = sorted(self.data['date'].unique())
        
        for i, date in enumerate(trading_dates):
            date_data = self.data[self.data['date'] == date].copy()
            if date_data.empty:
                continue
                
            current_price = date_data['underlying_price'].iloc[0]
            
            print(f"\n📅 {date.date()} | SPY: ${current_price:.2f} | Positions: {len(self.positions)} | Cash: ${self.cash:,.0f}")
            
            # 1. Manage existing positions
            self._manage_existing_positions(date_data, date)
            
            # 2. Calculate current portfolio Greeks and volatility context
            portfolio_context = calculate_portfolio_greeks(self.positions)
            volatility_context = calculate_volatility_context(
                self.data[self.data['date'] <= date], current_price
            )
            
            # 3. Check market filters for new entries
            market_filters = MarketFilters(self.config, self.data, trading_dates)
            filters_passed, filter_messages = market_filters.check_all_filters(
                date, current_price, i
            )
            
            # 4. Look for new PMCC entry if filters pass and we have capacity
            if filters_passed and len(self.positions) < self.config['dynamic_sizing']['max_concurrent_positions']:
                if self._should_enter_new_position(portfolio_context, volatility_context):
                    self._enter_new_pmcc_position(date_data, date, portfolio_context, volatility_context)
            
            # 5. Record daily portfolio value and Greeks
            total_value = self._calculate_portfolio_value(date_data, date)
            self.daily_values.append({
                'date': date,
                'spy_price': current_price,
                'total_value': total_value,
                'cash': self.cash,
                'positions_count': len(self.positions),
                'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100,
                **portfolio_context,
                **volatility_context
            })
            
            # Update metrics
            self.metrics['max_positions'] = max(self.metrics['max_positions'], len(self.positions))
        
        print(f"\n✅ Backtest completed!")
        print(f"📊 Total trades: {len(self.trade_history)}")
        print(f"📈 Final value: ${total_value:,.2f}")
        print(f"💰 Total return: {(total_value - self.initial_capital) / self.initial_capital * 100:.2f}%")
        
        return pd.DataFrame(self.daily_values)
    
    def _should_enter_new_position(self, portfolio_context, volatility_context):
        """Enhanced entry logic with portfolio and volatility considerations"""
        
        # Check portfolio delta exposure
        max_delta = self.config['dynamic_sizing']['max_portfolio_delta']
        if abs(portfolio_context.get('total_delta', 0)) > max_delta * 0.8:
            print(f"⛔ Entry blocked - High portfolio delta: {portfolio_context.get('total_delta', 0):.1f}")
            return False
            
        # Check volatility regime for PMCC entry
        regime = volatility_context.get('regime', 'normal')
        current_iv = volatility_context.get('current_iv', 0.20)
        
        # PMCC works best in normal to low volatility environments
        if regime == 'high_vol' and current_iv > 0.35:
            print(f"⛔ Entry blocked - High volatility regime (IV: {current_iv:.1%})")
            return False
            
        return True
    
    def _enter_new_pmcc_position(self, date_data, date, portfolio_context, volatility_context):
        """Enter new PMCC position with enhanced infrastructure"""
        
        current_price = date_data['underlying_price'].iloc[0]
        
        # 1. Find LEAP (long call)
        leap_config = self.config['leap_selection'].copy()
        leap_config['strategy_type'] = 'long_call'
        leap_config['option_selection'] = leap_config  # Rename for compatibility
        
        leap_candidates = date_data[
            (date_data['right'] == 'C') &
            (date_data['dte'] >= leap_config['dte_criteria']['minimum']) &
            (date_data['dte'] <= leap_config['dte_criteria']['maximum']) &
            (date_data['delta'] >= leap_config['delta_criteria']['minimum']) &
            (date_data['delta'] <= leap_config['delta_criteria']['maximum']) &
            (date_data['strike'] <= current_price)  # ITM calls only
        ].copy()
        
        if leap_candidates.empty:
            print(f"❌ No suitable LEAP candidates found")
            return
            
        # Select best LEAP (highest delta, closest to target)
        target_delta = leap_config['delta_criteria']['target']
        leap_candidates['delta_score'] = 1 - abs(leap_candidates['delta'] - target_delta)
        leap = leap_candidates.loc[leap_candidates['delta_score'].idxmax()]
        
        # 2. Find short call
        short_config = self.config['short_call_selection'].copy()
        short_config['strategy_type'] = 'short_call'
        short_config['option_selection'] = short_config
        
        short_candidates = date_data[
            (date_data['right'] == 'C') &
            (date_data['dte'] >= short_config['dte_criteria']['minimum']) &
            (date_data['dte'] <= short_config['dte_criteria']['maximum']) &
            (date_data['delta'] >= short_config['delta_criteria']['minimum']) &
            (date_data['delta'] <= short_config['delta_criteria']['maximum']) &
            (date_data['strike'] > current_price)  # OTM calls only
        ].copy()
        
        if short_candidates.empty:
            print(f"❌ No suitable short call candidates found")
            return
            
        # Select best short call
        target_delta = short_config['delta_criteria']['target']
        short_candidates['delta_score'] = 1 - abs(short_candidates['delta'] - target_delta)
        short_call = short_candidates.loc[short_candidates['delta_score'].idxmax()]
        
        # 3. Calculate position size using dynamic sizing
        net_debit = leap['close'] - short_call['close']  # Net debit for PMCC
        
        # Create a mock option series for the PMCC position
        pmcc_option = pd.Series({
            'close': net_debit,
            'mid_price': net_debit,
            'implied_vol': leap['implied_vol'],
            'delta': leap['delta'] - short_call['delta'],
            'vega': leap['vega'] - short_call['vega'],
            'theta': leap['theta'] - short_call['theta']
        })
        
        contracts, position_cost = calculate_dynamic_position_size(
            self.cash, 
            pmcc_option,
            self.config,
            volatility_context,
            portfolio_context
        )
        
        if contracts == 0 or position_cost > self.cash:
            print(f"❌ Insufficient capital for position")
            return
        
        # 4. Enter the position
        position = {
            'entry_date': date,
            'contracts': contracts,
            'leap': {
                'strike': leap['strike'],
                'expiration': leap['expiration'],
                'entry_price': leap['close'],
                'delta': leap['delta'],
                'vega': leap['vega'],
                'theta': leap['theta'],
                'side': 'long'
            },
            'short_call': {
                'strike': short_call['strike'],
                'expiration': short_call['expiration'], 
                'entry_price': short_call['close'],
                'delta': short_call['delta'],
                'vega': short_call['vega'],
                'theta': short_call['theta'],
                'side': 'short'
            },
            'net_debit': net_debit,
            'total_cost': position_cost,
            'status': 'open'
        }
        
        self.positions.append(position)
        self.cash -= position_cost
        
        print(f"✅ New PMCC position entered:")
        print(f"   LEAP: ${leap['strike']:.0f}C {leap['expiration'].date()} @ ${leap['close']:.2f} (Δ={leap['delta']:.2f})")
        print(f"   Short: ${short_call['strike']:.0f}C {short_call['expiration'].date()} @ ${short_call['close']:.2f} (Δ={short_call['delta']:.2f})")
        print(f"   Net debit: ${net_debit:.2f} x {contracts} = ${position_cost:.2f}")
        
        self.metrics['total_trades'] += 1
    
    def _manage_existing_positions(self, date_data, date):
        """Enhanced position management with adaptive exit rules"""
        
        positions_to_close = []
        
        for i, position in enumerate(self.positions):
            if position['status'] != 'open':
                continue
                
            # Get current option prices
            leap_current = self._get_current_option_price(date_data, position['leap'])
            short_current = self._get_current_option_price(date_data, position['short_call'])
            
            if leap_current is None or short_current is None:
                continue
            
            # Calculate current P&L
            leap_pnl = (leap_current['close'] - position['leap']['entry_price']) * position['contracts'] * 100
            short_pnl = (position['short_call']['entry_price'] - short_current['close']) * position['contracts'] * 100
            total_pnl = leap_pnl + short_pnl
            
            # Check exit conditions
            should_close, reason = self._check_exit_conditions(position, date, leap_current, short_current, total_pnl)
            
            if should_close:
                self._close_position(position, i, date, leap_current, short_current, total_pnl, reason)
                positions_to_close.append(i)
            else:
                # Check if we should roll the short call
                short_dte = (pd.to_datetime(position['short_call']['expiration']) - date).days
                if short_dte <= self.config['exit_rules']['time_rules']['short_call_roll_dte']:
                    self._roll_short_call(position, date_data, date)
        
        # Remove closed positions (in reverse order to maintain indices)
        for i in sorted(positions_to_close, reverse=True):
            del self.positions[i]
    
    def _check_exit_conditions(self, position, date, leap_current, short_current, total_pnl):
        """Enhanced exit conditions with adaptive rules"""
        
        # 1. Profit target - adaptive based on volatility
        current_iv = leap_current.get('implied_vol', 0.20)
        if current_iv > 0.30:  # High volatility environment
            profit_target = self.config['exit_rules']['profit_targets']['short_call_high_vol']
        else:
            profit_target = self.config['exit_rules']['profit_targets']['short_call_base']
            
        short_profit_pct = (position['short_call']['entry_price'] - short_current['close']) / position['short_call']['entry_price']
        if short_profit_pct >= profit_target:
            return True, f"Short call profit target reached: {short_profit_pct:.1%}"
        
        # 2. Total position profit target
        total_profit_pct = total_pnl / position['total_cost']
        if total_profit_pct >= self.config['exit_rules']['profit_targets']['total_position_profit']:
            return True, f"Total position profit target: {total_profit_pct:.1%}"
        
        # 3. LEAP stop loss
        leap_loss_pct = (position['leap']['entry_price'] - leap_current['close']) / position['leap']['entry_price']
        if leap_loss_pct >= self.config['exit_rules']['profit_targets']['leap_stop_loss']:
            return True, f"LEAP stop loss: -{leap_loss_pct:.1%}"
        
        # 4. Time-based exit
        days_held = (date - position['entry_date']).days
        if days_held >= self.config['exit_rules']['time_rules']['max_position_days']:
            return True, f"Maximum holding period reached: {days_held} days"
        
        # 5. Greeks-based exit
        position_delta = abs(leap_current.get('delta', 0) - short_current.get('delta', 0)) * position['contracts'] * 100
        if position_delta > self.config['exit_rules']['greeks_management']['delta_stop']:
            return True, f"Delta stop triggered: {position_delta:.1f}"
        
        return False, None
    
    def _get_current_option_price(self, date_data, option_leg):
        """Get current option price from market data"""
        option_data = date_data[
            (date_data['strike'] == option_leg['strike']) &
            (date_data['expiration'] == option_leg['expiration']) &
            (date_data['right'] == 'C')
        ]
        
        if option_data.empty:
            return None
            
        return option_data.iloc[0]
    
    def _roll_short_call(self, position, date_data, date):
        """Roll short call to next expiration"""
        # Implementation for rolling short call
        # This is a simplified version - full implementation would be more sophisticated
        print(f"🔄 Rolling short call for position (simplified)")
        pass
    
    def _close_position(self, position, position_idx, date, leap_current, short_current, total_pnl, reason):
        """Close PMCC position and record trade"""
        
        # Calculate exit value
        exit_value = (leap_current['close'] - short_current['close']) * position['contracts'] * 100
        commission = position['contracts'] * 2 * self.config['parameters']['commission_per_contract']  # 2 legs
        net_pnl = total_pnl - commission
        
        # Add cash back
        self.cash += exit_value
        
        # Record trade
        trade = {
            'entry_date': position['entry_date'],
            'exit_date': date,
            'contracts': position['contracts'],
            'entry_cost': position['total_cost'],
            'exit_value': exit_value,
            'gross_pnl': total_pnl,
            'net_pnl': net_pnl,
            'return_pct': net_pnl / position['total_cost'],
            'days_held': (date - position['entry_date']).days,
            'exit_reason': reason,
            'leap_entry': position['leap']['entry_price'],
            'leap_exit': leap_current['close'],
            'short_entry': position['short_call']['entry_price'],
            'short_exit': short_current['close']
        }
        
        self.trade_history.append(trade)
        
        # Update metrics
        if net_pnl > 0:
            self.metrics['winning_trades'] += 1
        self.metrics['total_pnl'] += net_pnl
        
        print(f"🔚 Position closed: {reason}")
        print(f"   P&L: ${net_pnl:.2f} ({trade['return_pct']:.1%}) in {trade['days_held']} days")
        
        position['status'] = 'closed'
    
    def _calculate_portfolio_value(self, date_data, date):
        """Calculate total portfolio value"""
        total_value = self.cash
        
        for position in self.positions:
            if position['status'] != 'open':
                continue
                
            leap_current = self._get_current_option_price(date_data, position['leap'])
            short_current = self._get_current_option_price(date_data, position['short_call'])
            
            if leap_current is not None and short_current is not None:
                position_value = (leap_current['close'] - short_current['close']) * position['contracts'] * 100
                total_value += position_value
        
        return total_value

# %% [markdown]
# ## 4. Run Enhanced Backtest

# %%
# Initialize and run enhanced PMCC strategy
strategy = EnhancedPMCCStrategy(STRATEGY_CONFIG, data_clean)
results = strategy.run_backtest()

print(f"\n📊 Backtest Results Summary:")
print(f"Total trades: {len(strategy.trade_history)}")
if len(strategy.trade_history) > 0:
    trades_df = pd.DataFrame(strategy.trade_history)
    print(f"Win rate: {(trades_df['net_pnl'] > 0).mean():.1%}")
    print(f"Average trade: ${trades_df['net_pnl'].mean():.2f}")
    print(f"Average return per trade: {trades_df['return_pct'].mean():.1%}")
    print(f"Average hold time: {trades_df['days_held'].mean():.1f} days")

# %% [markdown]
# ## 5. Performance Analysis and Visualization

# %%
# Performance comparison with SPY buy & hold
spy_benchmark = data_clean.groupby('date')['underlying_price'].first().reset_index()
spy_benchmark.columns = ['date', 'spy_price']

initial_capital = STRATEGY_CONFIG['parameters']['initial_capital']
spy_start = spy_benchmark['spy_price'].iloc[0]
spy_shares = initial_capital / spy_start
spy_benchmark['spy_value'] = spy_benchmark['spy_price'] * spy_shares
spy_benchmark['spy_return'] = (spy_benchmark['spy_value'] - initial_capital) / initial_capital * 100

# Merge results with SPY benchmark
results_merged = pd.merge(results, spy_benchmark[['date', 'spy_value', 'spy_return']], on='date', how='left')

print(f"\n📈 PERFORMANCE COMPARISON:")
if len(results) > 0:
    final_strategy_return = results['return_pct'].iloc[-1]
    final_spy_return = results_merged['spy_return'].iloc[-1] 
    print(f"Strategy return: {final_strategy_return:.2f}%")
    print(f"SPY return: {final_spy_return:.2f}%")
    print(f"Outperformance: {final_strategy_return - final_spy_return:.2f}%")

# %% [markdown]
# ## 6. Advanced Visualizations

# %%
# Create comprehensive performance visualization
if len(results) > 0:
    fig = make_subplots(
        rows=4, cols=2,
        subplot_titles=[
            'Strategy vs SPY Performance', 'Portfolio Value Breakdown',
            'Position Count Over Time', 'Portfolio Greeks Evolution', 
            'Volatility Environment', 'Trade Analysis',
            'Risk Metrics', 'Monthly Returns'
        ],
        specs=[[{"colspan": 2}, None],
               [{"colspan": 2}, None],
               [{}, {}],
               [{}, {}]],
        vertical_spacing=0.08
    )
    
    # Performance comparison
    fig.add_trace(
        go.Scatter(x=results['date'], y=results['total_value'], 
                  name='Enhanced PMCC', line=dict(color='green', width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=results_merged['date'], y=results_merged['spy_value'],
                  name='SPY Buy & Hold', line=dict(color='blue', width=2)),
        row=1, col=1
    )
    
    # Portfolio breakdown
    fig.add_trace(
        go.Scatter(x=results['date'], y=results['cash'],
                  name='Cash', stackgroup='one', fillcolor='lightblue'),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=results['date'], y=results['total_value'] - results['cash'],
                  name='Positions Value', stackgroup='one', fillcolor='lightgreen'),
        row=2, col=1
    )
    
    # Position count
    fig.add_trace(
        go.Scatter(x=results['date'], y=results['positions_count'],
                  name='Active Positions', line=dict(color='orange')),
        row=3, col=1
    )
    
    # Portfolio Greeks (if available)
    if 'total_delta' in results.columns:
        fig.add_trace(
            go.Scatter(x=results['date'], y=results['total_delta'],
                      name='Portfolio Delta', line=dict(color='red')),
            row=3, col=2
        )
    
    # Volatility regime (if available)
    if 'current_iv' in results.columns:
        fig.add_trace(
            go.Scatter(x=results['date'], y=results['current_iv'] * 100,
                      name='Implied Volatility', line=dict(color='purple')),
            row=4, col=1
        )
    
    # Trade histogram (if trades available)
    if len(strategy.trade_history) > 0:
        trade_returns = [t['return_pct'] * 100 for t in strategy.trade_history]
        fig.add_trace(
            go.Histogram(x=trade_returns, name='Trade Returns (%)', 
                        marker_color='lightcoral'),
            row=4, col=2
        )
    
    fig.update_layout(height=1200, title_text="Enhanced PMCC Strategy Analysis", showlegend=True)
    fig.show()

# %% [markdown]
# ## 7. Strategy Optimization Insights

# %%
print(f"\n📊 OPTIMIZATION INSIGHTS:")
print(f"=" * 40)

# Volatility analysis
if 'current_iv' in results.columns:
    avg_iv = results['current_iv'].mean()
    print(f"Average IV environment: {avg_iv:.1%}")
    
    high_vol_days = (results['current_iv'] > 0.25).sum()
    print(f"High volatility days (>25% IV): {high_vol_days} ({high_vol_days/len(results)*100:.1f}%)")

# Position sizing effectiveness
if len(results) > 0:
    max_positions = results['positions_count'].max()
    avg_positions = results['positions_count'].mean()
    print(f"Max concurrent positions: {max_positions}")
    print(f"Average positions: {avg_positions:.1f}")

# Risk metrics
if len(strategy.trade_history) > 0:
    trades_df = pd.DataFrame(strategy.trade_history)
    max_loss = trades_df['net_pnl'].min()
    max_win = trades_df['net_pnl'].max()
    print(f"Largest win: ${max_win:.2f}")
    print(f"Largest loss: ${max_loss:.2f}")
    print(f"Win/Loss ratio: {abs(max_win/max_loss):.1f}x")

# Capital efficiency
if len(results) > 0:
    capital_usage = 1 - (results['cash'] / results['total_value']).mean()
    print(f"Average capital deployed: {capital_usage:.1%}")

print(f"\n✅ Enhanced PMCC analysis complete!")
print(f"🎯 Ready for parameter optimization and systematic testing")