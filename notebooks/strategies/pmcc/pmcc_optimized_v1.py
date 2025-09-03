# %%
"""
PMCC Strategy Optimization V1 - Entry Timing Enhancement
========================================================

Building on our baseline results (88.86% return, 1.33 Sharpe), this version adds:
1. VIX-based entry timing filters
2. Market trend analysis  
3. Enhanced position sizing
4. Improved roll decision logic

Baseline to beat:
- Total Return: 88.86%
- Sharpe Ratio: 1.33
- Max Drawdown: -26.08%
- Excess Return vs SPY: +34.96%
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Use existing optionslab infrastructure
import sys
import os
sys.path.append('/Users/nish_macbook/trading/daily-optionslab')

from optionslab.data_loader import load_data

print("=" * 60)
print("PMCC OPTIMIZATION V1 - Entry Timing Enhancement")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# %%
class OptimizedPMCCStrategy:
    """Enhanced PMCC strategy with market timing filters"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = []
        self.trades = []
        self.daily_values = []
        
        # Enhanced LEAP parameters
        self.leap_dte_min = 365
        self.leap_dte_max = 800
        self.leap_delta_min = 0.70
        self.leap_delta_max = 0.85
        
        # Enhanced short call parameters
        self.short_dte_min = 30
        self.short_dte_max = 45
        self.short_delta_min = 0.18  # Slightly more aggressive
        self.short_delta_max = 0.32
        self.short_profit_target = 0.50
        
        # NEW: Market timing parameters
        self.vix_entry_threshold = 20.0  # Enter when VIX > 20
        self.vix_aggressive_threshold = 25.0  # More aggressive when VIX > 25
        self.trend_lookback = 20  # Days for trend analysis
        self.max_positions = 2  # Enhanced position management
        
        # Enhanced execution costs
        self.commission_per_contract = 0.65
        self.slippage_pct = 0.005  # 0.5% slippage
        
        # Performance tracking
        self.total_premiums_collected = 0
        self.net_leap_cost = 0
        self.short_call_rolls = 0
        self.leap_rolls = 0
        
    def calculate_market_indicators(self, df, current_date):
        """Calculate VIX proxy and market trend"""
        # Create a simple VIX proxy from ATM straddle prices
        current_data = df[df['date'] == current_date].copy()
        if len(current_data) == 0:
            return None, None
            
        spy_price = current_data['underlying_price'].iloc[0]
        
        # Find ATM options for VIX proxy
        atm_calls = current_data[
            (current_data['right'] == 'C') & 
            (current_data['dte'].between(25, 35))
        ]
        
        if len(atm_calls) == 0:
            return None, None
            
        # Find closest to ATM
        atm_calls['strike_diff'] = abs(atm_calls['strike'] - spy_price)
        atm_call = atm_calls.loc[atm_calls['strike_diff'].idxmin()]
        
        # VIX proxy: implied volatility * 100
        vix_proxy = atm_call.get('iv', 0.2) * 100
        
        # Calculate trend: rolling return over lookback period
        historical_dates = sorted([d for d in df['date'].unique() if d <= current_date])
        if len(historical_dates) < self.trend_lookback:
            trend = 0
        else:
            start_idx = max(0, len(historical_dates) - self.trend_lookback)
            start_date = historical_dates[start_idx]
            start_price = df[df['date'] == start_date]['underlying_price'].iloc[0]
            trend = (spy_price - start_price) / start_price
            
        return vix_proxy, trend
        
    def should_enter_new_position(self, vix_proxy, trend, current_positions):
        """Enhanced entry logic with market timing"""
        if vix_proxy is None:
            return False
            
        # Don't exceed position limit
        if len(current_positions) >= self.max_positions:
            return False
            
        # VIX-based entry timing
        if vix_proxy < self.vix_entry_threshold:
            return False  # Wait for higher volatility
            
        # Trend-based entry (prefer entering on pullbacks in uptrends)
        if trend < -0.05:  # Don't enter in strong downtrends
            return False
            
        return True
        
    def get_position_size(self, vix_proxy):
        """Dynamic position sizing based on market conditions"""
        base_size = 0.15  # 15% of capital per position
        
        if vix_proxy is None:
            return base_size
            
        # Increase size in higher volatility environments
        if vix_proxy > self.vix_aggressive_threshold:
            return min(0.20, base_size * 1.3)  # Up to 20% in high vol
            
        return base_size
        
    def find_leap_candidates(self, df_date):
        """Find LEAP options meeting our criteria"""
        leap_candidates = df_date[
            (df_date['right'] == 'C') &
            (df_date['dte'].between(self.leap_dte_min, self.leap_dte_max)) &
            (df_date['delta'].between(self.leap_delta_min, self.leap_delta_max)) &
            (df_date['bid'] > 0) &
            (df_date['volume'] > 0)
        ].copy()
        
        if len(leap_candidates) == 0:
            return None
            
        # Prefer LEAPs with good delta and reasonable cost
        leap_candidates['score'] = (
            leap_candidates['delta'] * 0.7 +  # Prefer higher delta
            (1000 - leap_candidates['dte']) / 1000 * 0.2 +  # Prefer shorter DTE (less time risk)
            leap_candidates['volume'] / leap_candidates['volume'].max() * 0.1  # Prefer liquid
        )
        
        return leap_candidates.loc[leap_candidates['score'].idxmax()]
        
    def find_short_call_candidates(self, df_date, leap_strike):
        """Find short call options"""
        short_candidates = df_date[
            (df_date['right'] == 'C') &
            (df_date['dte'].between(self.short_dte_min, self.short_dte_max)) &
            (df_date['delta'].between(self.short_delta_min, self.short_delta_max)) &
            (df_date['strike'] > leap_strike) &  # OTM calls only
            (df_date['bid'] > 0) &
            (df_date['volume'] > 0)
        ].copy()
        
        if len(short_candidates) == 0:
            return None
            
        # Prefer calls with good premium and reasonable delta
        short_candidates['premium_score'] = short_candidates['mid_price'] / short_candidates['strike']
        
        return short_candidates.loc[short_candidates['premium_score'].idxmax()]
        
    def execute_trade(self, row, quantity, is_buy=True):
        """Execute trade with realistic slippage and commissions"""
        if is_buy:
            fill_price = row['ask'] * (1 + self.slippage_pct)
        else:
            fill_price = row['bid'] * (1 - self.slippage_pct)
            
        total_cost = fill_price * quantity * 100 + self.commission_per_contract * abs(quantity)
        
        return fill_price, total_cost
        
    def manage_existing_positions(self, df_date, current_date):
        """Enhanced position management"""
        to_close = []
        
        for i, pos in enumerate(self.positions):
            if pos['type'] == 'leap':
                # LEAP management - check if needs rolling
                current_data = df_date[
                    (df_date['strike'] == pos['strike']) &
                    (df_date['right'] == 'C') &
                    (df_date['expiration'] == pos['expiration'])
                ]
                
                if len(current_data) > 0:
                    leap_data = current_data.iloc[0]
                    pos['current_price'] = leap_data['mid_price']
                    pos['current_delta'] = leap_data['delta']
                    
                    # Roll LEAP if delta has decayed significantly or approaching expiration
                    if leap_data['dte'] < 60 or leap_data['delta'] < 0.60:
                        to_close.append(('roll_leap', i, leap_data))
                        
            elif pos['type'] == 'short_call':
                # Short call management
                current_data = df_date[
                    (df_date['strike'] == pos['strike']) &
                    (df_date['right'] == 'C') &
                    (df_date['expiration'] == pos['expiration'])
                ]
                
                if len(current_data) > 0:
                    call_data = current_data.iloc[0]
                    pos['current_price'] = call_data['mid_price']
                    
                    # Check for profit target
                    profit_pct = (pos['entry_price'] - call_data['mid_price']) / pos['entry_price']
                    
                    if profit_pct >= self.short_profit_target:
                        to_close.append(('close_profitable', i, call_data))
                    elif call_data['dte'] <= 21:  # Roll when approaching expiration
                        to_close.append(('roll_short', i, call_data))
                        
        return to_close
        
    def process_closes(self, closes, df_date):
        """Process position closes and rolls"""
        closes_processed = []
        
        for action, pos_idx, data in closes:
            pos = self.positions[pos_idx]
            
            if action in ['close_profitable', 'roll_short']:
                # Close short call
                fill_price, total_cost = self.execute_trade(data, pos['quantity'], is_buy=True)
                pnl = (pos['entry_price'] - fill_price) * pos['quantity'] * 100 - self.commission_per_contract
                
                print(f"📉 {data['date'].date()}: Closed short ${pos['strike']} P&L: ${pnl:.0f} "
                      f"({'Profit target' if action == 'close_profitable' else 'Time to roll'} "
                      f"({(pos['entry_price'] - fill_price) / pos['entry_price'] * 100:.1f}%))")
                
                self.cash += pnl
                self.total_premiums_collected += pnl if pnl > 0 else 0
                
                self.trades.append({
                    'date': data['date'],
                    'type': 'close_short_call',
                    'strike': pos['strike'],
                    'expiration': pos['expiration'],
                    'quantity': pos['quantity'],
                    'price': fill_price,
                    'pnl': pnl,
                    'reason': action
                })
                
                closes_processed.append(pos_idx)
                
                if action == 'roll_short':
                    self.short_call_rolls += 1
                    # Try to open new short call
                    leap_pos = next((p for p in self.positions if p['type'] == 'leap'), None)
                    if leap_pos:
                        new_short = self.find_short_call_candidates(df_date, leap_pos['strike'])
                        if new_short is not None:
                            self.open_short_call(new_short, leap_pos['quantity'])
                            
            elif action == 'roll_leap':
                # Close existing LEAP and open new one
                fill_price, total_proceeds = self.execute_trade(data, -pos['quantity'], is_buy=False)
                leap_pnl = (fill_price - pos['entry_price']) * pos['quantity'] * 100 - self.commission_per_contract
                
                print(f"🔄 {data['date'].date()}: Rolling LEAP - Closed ${pos['strike']} P&L: ${leap_pnl:.0f}")
                
                self.cash += leap_pnl
                closes_processed.append(pos_idx)
                self.leap_rolls += 1
                
                # Try to open new LEAP
                new_leap = self.find_leap_candidates(df_date)
                if new_leap is not None:
                    self.open_leap_position(new_leap, pos['quantity'])
                    
        # Remove closed positions
        self.positions = [pos for i, pos in enumerate(self.positions) if i not in closes_processed]
        
    def open_leap_position(self, leap_data, quantity):
        """Open new LEAP position"""
        fill_price, total_cost = self.execute_trade(leap_data, quantity, is_buy=True)
        
        print(f"📈 {leap_data['date'].date()}: Bought LEAP ${leap_data['strike']:.0f} @ ${fill_price:.2f} "
              f"(DTE: {leap_data['dte']}, Delta: {leap_data['delta']:.3f})")
        
        self.cash -= total_cost
        self.net_leap_cost += total_cost
        
        self.positions.append({
            'type': 'leap',
            'date': leap_data['date'],
            'strike': leap_data['strike'],
            'expiration': leap_data['expiration'],
            'quantity': quantity,
            'entry_price': fill_price,
            'current_price': fill_price,
            'current_delta': leap_data['delta']
        })
        
        self.trades.append({
            'date': leap_data['date'],
            'type': 'buy_leap',
            'strike': leap_data['strike'],
            'expiration': leap_data['expiration'],
            'quantity': quantity,
            'price': fill_price,
            'cost': total_cost
        })
        
    def open_short_call(self, call_data, quantity):
        """Open short call position"""
        fill_price, total_proceeds = self.execute_trade(call_data, -quantity, is_buy=False)
        
        print(f"📝 {call_data['date'].date()}: Sold call ${call_data['strike']:.0f} @ ${fill_price:.2f} "
              f"(DTE: {call_data['dte']}, Delta: {call_data['delta']:.3f})")
        
        self.cash -= total_proceeds  # Proceeds are negative (we receive cash)
        self.total_premiums_collected += -total_proceeds  # Track total premiums
        
        self.positions.append({
            'type': 'short_call',
            'date': call_data['date'],
            'strike': call_data['strike'],
            'expiration': call_data['expiration'],
            'quantity': -quantity,  # Short position
            'entry_price': fill_price,
            'current_price': fill_price
        })
        
        self.trades.append({
            'date': call_data['date'],
            'type': 'sell_call',
            'strike': call_data['strike'],
            'expiration': call_data['expiration'],
            'quantity': -quantity,
            'price': fill_price,
            'proceeds': -total_proceeds
        })
        
    def calculate_portfolio_value(self, df_date):
        """Calculate current portfolio value"""
        total_value = self.cash
        
        for pos in self.positions:
            current_data = df_date[
                (df_date['strike'] == pos['strike']) &
                (df_date['right'] == 'C') &
                (df_date['expiration'] == pos['expiration'])
            ]
            
            if len(current_data) > 0:
                current_price = current_data.iloc[0]['mid_price']
                position_value = current_price * pos['quantity'] * 100
                total_value += position_value
                
        return total_value
        
    def run_backtest(self, df):
        """Run enhanced backtest with market timing"""
        dates = sorted(df['date'].unique())
        
        for i, date in enumerate(dates):
            df_date = df[df['date'] == date].copy()
            spy_price = df_date['underlying_price'].iloc[0]
            
            # Calculate market indicators
            vix_proxy, trend = self.calculate_market_indicators(df, date)
            
            # Manage existing positions
            closes = self.manage_existing_positions(df_date, date)
            self.process_closes(closes, df_date)
            
            # Check for new position entry
            current_leap_positions = [p for p in self.positions if p['type'] == 'leap']
            
            if self.should_enter_new_position(vix_proxy, trend, current_leap_positions):
                # Try to open new PMCC position
                leap_candidate = self.find_leap_candidates(df_date)
                
                if leap_candidate is not None:
                    # Determine position size
                    position_size = self.get_position_size(vix_proxy)
                    available_capital = self.cash * position_size
                    
                    leap_cost_estimate = leap_candidate['ask'] * 100 + self.commission_per_contract
                    
                    if available_capital >= leap_cost_estimate:
                        quantity = max(1, int(available_capital // leap_cost_estimate))
                        
                        # Open LEAP position
                        self.open_leap_position(leap_candidate, quantity)
                        
                        # Try to open corresponding short call
                        short_candidate = self.find_short_call_candidates(df_date, leap_candidate['strike'])
                        if short_candidate is not None:
                            self.open_short_call(short_candidate, quantity)
            
            # Calculate portfolio value
            total_value = self.calculate_portfolio_value(df_date)
            
            # Record daily values
            self.daily_values.append({
                'date': date,
                'spy_price': spy_price,
                'total_value': total_value,
                'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100,
                'vix_proxy': vix_proxy,
                'trend': trend,
                'num_positions': len(self.positions)
            })
            
        return pd.DataFrame(self.daily_values)

# %%
# Load data and run optimized backtest
print("\nLoading SPY options data...")
df = load_data("data/spy_options/", "2023-01-01", "2024-12-31")

print(f"✅ Loaded {len(df):,} records")
print(f"📅 Date range: {df['date'].min().date()} to {df['date'].max().date()}")

# %%
# Run optimized PMCC backtest
print("\n" + "="*40)
print("RUNNING OPTIMIZED PMCC BACKTEST")
print("="*40)

optimized_strategy = OptimizedPMCCStrategy(initial_capital=10000)
optimized_results = optimized_strategy.run_backtest(df)

if len(optimized_results) > 0:
    final_value = optimized_results['total_value'].iloc[-1]
    total_return = optimized_results['return_pct'].iloc[-1]
    
    print(f"\n💰 Final value: ${final_value:,.2f}")
    print(f"📈 Total return: {total_return:.2f}%")
    print(f"📝 Total trades: {len(optimized_strategy.trades)}")
    
    print(f"\n🎯 Enhanced PMCC Metrics:")
    print(f"  Total premiums collected: ${optimized_strategy.total_premiums_collected:.2f}")
    print(f"  Net LEAP cost: ${optimized_strategy.net_leap_cost:.2f}")
    print(f"  Short call rolls: {optimized_strategy.short_call_rolls}")
    print(f"  LEAP rolls: {optimized_strategy.leap_rolls}")
    
    # Calculate performance metrics
    returns = optimized_results['total_value'].pct_change().dropna()
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    max_dd = ((optimized_results['total_value'].cummax() - optimized_results['total_value']) / optimized_results['total_value'].cummax()).max() * 100
    
    print(f"\n✅ Backtest complete: {len(optimized_results)} days tracked")
    print("📊 OPTIMIZED PERFORMANCE METRICS")
    print("="*40)
    print(f"Initial Capital:    ${optimized_strategy.initial_capital:,.2f}")
    print(f"Final Value:        ${final_value:,.2f}")
    print(f"Total Return:       {total_return:.2f}%")
    print(f"Sharpe Ratio:       {sharpe:.2f}")
    print(f"Max Drawdown:       {max_dd:.2f}%")
    print(f"Total Trades:       {len(optimized_strategy.trades)}")
else:
    print("⚠️  No results generated - check strategy implementation")

# %%
# Compare with baseline and SPY
spy_start = optimized_results['spy_price'].iloc[0]
spy_end = optimized_results['spy_price'].iloc[-1] 
spy_return = (spy_end - spy_start) / spy_start * 100

# Baseline metrics (from previous run)
baseline_return = 88.86
baseline_sharpe = 1.33

print(f"\n📊 PERFORMANCE COMPARISON")
print("="*50)
print(f"{'Strategy':<20} {'Return':<12} {'Sharpe':<10} {'Improvement'}")
print("-"*50)
print(f"{'SPY Buy-Hold':<20} {spy_return:<11.2f}% {'-':<10}")
print(f"{'Baseline PMCC':<20} {baseline_return:<11.2f}% {baseline_sharpe:<10.2f}")
print(f"{'Optimized PMCC':<20} {total_return:<11.2f}% {sharpe:<10.2f} {sharpe - baseline_sharpe:+.2f}")

# %%
# Create performance visualization
fig = make_subplots(
    rows=3, cols=1, 
    subplot_titles=("Portfolio Value Comparison", "Market Indicators", "Position Count"),
    vertical_spacing=0.08,
    row_heights=[0.5, 0.3, 0.2]
)

# Portfolio performance
fig.add_trace(
    go.Scatter(
        x=optimized_results['date'],
        y=optimized_results['total_value'],
        mode='lines',
        name='Optimized PMCC',
        line=dict(color='green', width=2)
    ),
    row=1, col=1
)

# SPY benchmark
spy_values = optimized_results['spy_price'] / spy_start * optimized_strategy.initial_capital
fig.add_trace(
    go.Scatter(
        x=optimized_results['date'],
        y=spy_values,
        mode='lines', 
        name='SPY Buy & Hold',
        line=dict(color='blue', width=2)
    ),
    row=1, col=1
)

# VIX proxy
fig.add_trace(
    go.Scatter(
        x=optimized_results['date'],
        y=optimized_results['vix_proxy'],
        mode='lines',
        name='VIX Proxy',
        line=dict(color='orange')
    ),
    row=2, col=1
)

# Add VIX thresholds
fig.add_hline(y=20, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=25, line_dash="dash", line_color="darkred", row=2, col=1)

# Position count
fig.add_trace(
    go.Scatter(
        x=optimized_results['date'],
        y=optimized_results['num_positions'],
        mode='lines',
        name='Active Positions',
        line=dict(color='purple'),
        fill='tonexty'
    ),
    row=3, col=1
)

fig.update_layout(
    title="PMCC Strategy Optimization Results",
    height=800,
    showlegend=True
)

fig.update_xaxes(title_text="Date", row=3, col=1)
fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
fig.update_yaxes(title_text="VIX Proxy", row=2, col=1)
fig.update_yaxes(title_text="Positions", row=3, col=1)

fig.show()

print(f"\n🎯 OPTIMIZATION RESULTS:")
print(f"✅ {'IMPROVED' if sharpe > baseline_sharpe else 'BASELINE BETTER'}: "
      f"Sharpe {baseline_sharpe:.2f} → {sharpe:.2f} ({sharpe - baseline_sharpe:+.2f})")
print(f"✅ {'IMPROVED' if total_return > baseline_return else 'BASELINE BETTER'}: "
      f"Return {baseline_return:.2f}% → {total_return:.2f}% ({total_return - baseline_return:+.2f}%)")