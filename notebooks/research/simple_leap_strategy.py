# %%
"""
Simple LEAP Strategy - Foundation Fix
====================================
Fix the core LEAP buy-and-hold strategy before adding volatility protection.

Goal: Get basic LEAP leverage working properly in bull markets
Test Period: 2023-2024 (SPY +53.9% - should be excellent for LEAPs)

Strategy:
1. Buy 1-year LEAP call (0.75 delta) at start
2. Hold until expiration or roll at 60 DTE
3. No protection - just test basic mechanics
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

pd.set_option('display.float_format', '{:.2f}'.format)
print("=" * 60)
print("SIMPLE LEAP STRATEGY - FOUNDATION TEST")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# %% Load and prepare data
data_path = '/Users/nish_macbook/trading/daily-optionslab/data/spy_options/'

# Load data
df_2023 = pd.read_parquet(f'{data_path}SPY_OPTIONS_2023_COMPLETE.parquet')
df_2024 = pd.read_parquet(f'{data_path}SPY_OPTIONS_2024_COMPLETE.parquet')

# Combine and clean
df_all = pd.concat([df_2023, df_2024], ignore_index=True)
df_all['date'] = pd.to_datetime(df_all['date'])
df_all['expiration'] = pd.to_datetime(df_all['expiration'])
df_all['dte'] = (df_all['expiration'] - df_all['date']).dt.days
df_all['strike'] = df_all['strike'] / 1000  # Convert cents to dollars
df_all['mid_price'] = (df_all['bid'] + df_all['ask']) / 2

# Filter for valid data
df_clean = df_all[(df_all['bid'] > 0) & (df_all['volume'] > 0)].copy()

print(f"✓ Data loaded: {len(df_clean):,} records")
print(f"✓ Date range: {df_clean['date'].min().date()} to {df_clean['date'].max().date()}")

# Get SPY prices
spy_prices = df_clean.groupby('date')['underlying_price'].first().reset_index()
spy_prices.columns = ['date', 'spy_price']
spy_prices = spy_prices.sort_values('date').reset_index(drop=True)

spy_start = spy_prices['spy_price'].iloc[0]
spy_end = spy_prices['spy_price'].iloc[-1]
spy_return = (spy_end - spy_start) / spy_start * 100

print(f"✓ SPY: ${spy_start:.2f} → ${spy_end:.2f} (+{spy_return:.1f}%)")

# %%
class SimpleLEAPStrategy:
    """
    Dead simple LEAP strategy to test basic mechanics
    """
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = None  # Single LEAP position
        self.trades = []
        self.daily_values = []
        
        # Simple parameters
        self.target_delta = 0.75
        self.min_dte_buy = 300   # Buy LEAPs with 300+ days
        self.max_dte_buy = 400   # Buy LEAPs with <400 days  
        self.roll_dte = 60       # Roll when <60 days left
        
    def find_best_leap(self, df_date):
        """Find the best LEAP option for this date"""
        leap_candidates = df_date[
            (df_date['right'] == 'C') & 
            (df_date['dte'] >= self.min_dte_buy) &
            (df_date['dte'] <= self.max_dte_buy) &
            (df_date['delta'] >= self.target_delta - 0.15) &  # Wider range
            (df_date['delta'] <= self.target_delta + 0.15) &
            (df_date['bid'] > 0) &
            (df_date['ask'] > 0) &
            (df_date['volume'] > 0)
        ].copy()
        
        if len(leap_candidates) == 0:
            return None
            
        # Select LEAP closest to target delta
        leap_candidates['delta_diff'] = abs(leap_candidates['delta'] - self.target_delta)
        best_leap = leap_candidates.loc[leap_candidates['delta_diff'].idxmin()]
        
        return {
            'strike': best_leap['strike'],
            'expiration': best_leap['expiration'],
            'delta': best_leap['delta'],
            'price': best_leap['mid_price'],
            'dte': best_leap['dte']
        }
    
    def get_position_value(self, df_date):
        """Get current value of our LEAP position"""
        if self.position is None:
            return 0
            
        option_data = df_date[
            (df_date['strike'] == self.position['strike']) &
            (df_date['expiration'] == self.position['expiration']) &
            (df_date['right'] == 'C')
        ]
        
        if len(option_data) == 0:
            return 0  # Option expired or not found
            
        return option_data['mid_price'].iloc[0] * 100  # Contract multiplier
    
    def run_backtest(self, df):
        """Run simple LEAP backtest"""
        dates = sorted(df['date'].unique())
        
        print(f"\n🚀 Running Simple LEAP Backtest...")
        print(f"📅 {len(dates)} trading days")
        
        for i, date in enumerate(dates):
            df_date = df[df['date'] == date].copy()
            
            if len(df_date) == 0:
                continue
                
            # Check if we need to roll existing position
            if self.position is not None:
                current_dte = (self.position['expiration'] - date).days
                
                if current_dte <= self.roll_dte:
                    # Close existing position
                    current_value = self.get_position_value(df_date)
                    if current_value > 0:
                        self.capital += current_value
                        
                        # Calculate P&L
                        pnl = current_value - (self.position['entry_price'] * 100)
                        pnl_pct = pnl / (self.position['entry_price'] * 100) * 100
                        
                        self.trades.append({
                            'date': date,
                            'action': 'close_leap',
                            'strike': self.position['strike'],
                            'price': current_value / 100,
                            'entry_price': self.position['entry_price'],
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'dte': current_dte
                        })
                        
                        if i % 50 == 0:  # Progress update
                            print(f"📊 {date.date()}: Closed LEAP ${self.position['strike']:.0f} - "
                                  f"P&L: ${pnl:.0f} ({pnl_pct:.1f}%)")
                    
                    self.position = None
            
            # Look for new LEAP if we don't have one
            if self.position is None:
                new_leap = self.find_best_leap(df_date)
                
                if new_leap and self.capital >= new_leap['price'] * 100:
                    # Buy new LEAP
                    cost = new_leap['price'] * 100
                    self.capital -= cost
                    
                    self.position = {
                        'strike': new_leap['strike'],
                        'expiration': new_leap['expiration'],
                        'entry_price': new_leap['price'],
                        'entry_date': date,
                        'entry_delta': new_leap['delta'],
                        'entry_dte': new_leap['dte']
                    }
                    
                    self.trades.append({
                        'date': date,
                        'action': 'buy_leap',
                        'strike': new_leap['strike'],
                        'price': new_leap['price'],
                        'delta': new_leap['delta'],
                        'dte': new_leap['dte'],
                        'cost': cost
                    })
                    
                    print(f"🎯 {date.date()}: Bought LEAP ${new_leap['strike']:.0f} @ ${new_leap['price']:.2f} "
                          f"(Δ={new_leap['delta']:.2f}, DTE={new_leap['dte']})")
            
            # Calculate total portfolio value
            position_value = self.get_position_value(df_date)
            total_value = self.capital + position_value
            
            # Record daily values
            self.daily_values.append({
                'date': date,
                'total_value': total_value,
                'capital': self.capital,
                'position_value': position_value,
                'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100,
                'has_position': self.position is not None
            })
        
        return pd.DataFrame(self.daily_values)

# %% Run the backtest
print("\n" + "="*50)
print("RUNNING SIMPLE LEAP STRATEGY")
print("="*50)

strategy = SimpleLEAPStrategy(initial_capital=10000)
results = strategy.run_backtest(df_clean)

# %% Analyze results
print("\n" + "="*50)
print("RESULTS ANALYSIS")
print("="*50)

final_value = results['total_value'].iloc[-1]
total_return = results['return_pct'].iloc[-1]

print(f"📈 PERFORMANCE:")
print(f"   Initial Capital: $10,000")
print(f"   Final Value: ${final_value:,.0f}")
print(f"   Total Return: {total_return:.1f}%")

print(f"\n📊 COMPARISON:")
print(f"   SPY Return: {spy_return:.1f}%")
print(f"   LEAP Return: {total_return:.1f}%")
if spy_return > 0:
    leverage = total_return / spy_return
    print(f"   LEAP Leverage: {leverage:.1f}x")

print(f"\n🔧 TRADE SUMMARY:")
print(f"   Total Trades: {len(strategy.trades)}")

if len(strategy.trades) > 0:
    trades_df = pd.DataFrame(strategy.trades)
    
    leap_buys = trades_df[trades_df['action'] == 'buy_leap']
    leap_closes = trades_df[trades_df['action'] == 'close_leap']
    
    print(f"   LEAP Purchases: {len(leap_buys)}")
    print(f"   LEAP Closes: {len(leap_closes)}")
    
    if len(leap_closes) > 0:
        total_pnl = leap_closes['pnl'].sum()
        avg_pnl_pct = leap_closes['pnl_pct'].mean()
        print(f"   Total P&L from closed trades: ${total_pnl:.0f}")
        print(f"   Average P&L per trade: {avg_pnl_pct:.1f}%")
        
        print(f"\n📋 TRADE DETAILS:")
        for _, trade in leap_closes.iterrows():
            print(f"   ${trade['strike']:.0f} LEAP: "
                  f"${trade['entry_price']:.2f} → ${trade['price']:.2f} = "
                  f"${trade['pnl']:.0f} ({trade['pnl_pct']:.1f}%)")

# Check if we still have an open position
if strategy.position is not None:
    current_pos_value = results['position_value'].iloc[-1]
    entry_cost = strategy.position['entry_price'] * 100
    open_pnl = current_pos_value - entry_cost
    open_pnl_pct = open_pnl / entry_cost * 100
    
    print(f"\n🔓 OPEN POSITION:")
    print(f"   Strike: ${strategy.position['strike']:.0f}")
    print(f"   Entry: ${strategy.position['entry_price']:.2f}")
    print(f"   Current Value: ${current_pos_value:.0f}")
    print(f"   Unrealized P&L: ${open_pnl:.0f} ({open_pnl_pct:.1f}%)")

# %% Simple visualization
fig = go.Figure()

# Portfolio value
fig.add_trace(go.Scatter(
    x=results['date'],
    y=results['total_value'],
    mode='lines',
    name='Simple LEAP Strategy',
    line=dict(color='green', width=2)
))

# SPY benchmark
spy_benchmark = []
for date in results['date']:
    spy_price = spy_prices[spy_prices['date'] == date]['spy_price']
    if len(spy_price) > 0:
        spy_value = 10000 * (spy_price.iloc[0] / spy_start)
        spy_benchmark.append(spy_value)
    else:
        spy_benchmark.append(10000)

fig.add_trace(go.Scatter(
    x=results['date'],
    y=spy_benchmark,
    mode='lines',
    name='SPY Buy & Hold',
    line=dict(color='blue', width=2)
))

fig.add_hline(y=10000, line_dash="dash", line_color="gray")

fig.update_layout(
    title='Simple LEAP Strategy vs SPY Buy & Hold',
    xaxis_title='Date',
    yaxis_title='Portfolio Value ($)',
    hovermode='x unified',
    height=500
)

fig.show()

# %% Conclusion
print("\n" + "="*60)
print("FOUNDATION TEST RESULTS")
print("="*60)

if total_return > spy_return * 1.2:
    print("✅ SUCCESS: LEAP strategy shows proper leverage!")
    print("   → Ready to add volatility protection")
elif total_return > spy_return * 0.8:
    print("⚠️  PARTIAL: LEAP strategy works but needs optimization")
    print("   → Fix parameters before adding protection")
else:
    print("❌ FAILED: LEAP strategy fundamentally broken")
    print("   → Need to debug basic mechanics")

print(f"\n🎯 NEXT STEPS:")
if total_return > spy_return * 0.8:
    print("1. ✅ Foundation works - add volatility protection back")
    print("2. Test protection triggers and costs")
    print("3. Optimize combined strategy")
else:
    print("1. Debug LEAP selection logic")
    print("2. Fix rolling mechanics") 
    print("3. Test with different parameters")

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")