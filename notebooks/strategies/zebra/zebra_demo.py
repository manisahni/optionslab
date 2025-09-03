#!/usr/bin/env python3
"""
ZEBRA Call Strategy Demo - Simplified version that works with existing data
"""

import sys
import os
sys.path.append('/Users/nish_macbook/trading/daily-optionslab')

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from pathlib import Path
import glob
import warnings
warnings.filterwarnings('ignore')

print("✅ ZEBRA Strategy Demo Starting...")
print("=" * 60)

# Load SPY options data
print("📂 Loading SPY options data...")

all_data = []

# Load consolidated files
files_to_load = [
    'data/spy_options/spy_options_2022_full_year.parquet',
    'data/spy_options/spy_options_2023_full_year.parquet',
]

for file_path in files_to_load:
    if Path(file_path).exists():
        df = pd.read_parquet(file_path)
        all_data.append(df)
        print(f"   ✅ Loaded {Path(file_path).name}: {len(df):,} records")

# Load some 2024 daily files
daily_2024 = sorted(glob.glob('data/spy_options/spy_options_eod_2024*.parquet'))[:50]
for file_path in daily_2024:
    df = pd.read_parquet(file_path)
    all_data.append(df)

if not all_data:
    print("❌ No data found!")
    sys.exit(1)

# Combine data
print(f"\n🔄 Combining {len(all_data)} data sources...")
data = pd.concat(all_data, ignore_index=True)

# Standardize
data['date'] = pd.to_datetime(data['date'])
data['expiration'] = pd.to_datetime(data['expiration'])
data['dte'] = (data['expiration'] - data['date']).dt.days

# Fix strike if needed
if data['strike'].max() > 10000:
    data['strike'] = data['strike'] / 1000

data['mid_price'] = (data['bid'] + data['ask']) / 2

# Filter valid data
data = data[(data['bid'] > 0) & (data['ask'] > 0) & (data['volume'] >= 0)]

print(f"📊 Total records: {len(data):,}")
print(f"📅 Date range: {data['date'].min().date()} to {data['date'].max().date()}")
print(f"💰 Strike range: ${data['strike'].min():.0f} - ${data['strike'].max():.0f}")

# Run simplified ZEBRA backtest
print("\n" + "=" * 60)
print("🎯 RUNNING ZEBRA STRATEGY BACKTEST")
print("=" * 60)

def find_zebra_strikes(day_data, spot_price):
    """Find ZEBRA strikes: 2 ITM calls + 1 OTM call"""
    
    # Filter calls with 35-60 DTE
    calls = day_data[
        (day_data['right'] == 'C') & 
        (day_data['dte'] >= 35) & 
        (day_data['dte'] <= 60) &
        (day_data['volume'] > 0)
    ].copy()
    
    if len(calls) == 0:
        return None
    
    # Find ITM call around 55 delta (simplified - using strike relative to spot)
    itm_target = spot_price * 0.95  # ~5% ITM
    calls['itm_diff'] = abs(calls['strike'] - itm_target)
    itm_call = calls.nsmallest(1, 'itm_diff').iloc[0]
    
    # Find OTM call around 30 delta
    otm_target = spot_price * 1.05  # ~5% OTM
    calls['otm_diff'] = abs(calls['strike'] - otm_target)
    otm_call = calls.nsmallest(1, 'otm_diff').iloc[0]
    
    return {
        'itm_strike': itm_call['strike'],
        'itm_price': itm_call['mid_price'],
        'otm_strike': otm_call['strike'],
        'otm_price': otm_call['mid_price'],
        'expiration': itm_call['expiration'],
        'dte': itm_call['dte']
    }

# Initialize backtest
initial_capital = 100000
cash = initial_capital
positions = []
trades = []
equity_curve = []

# Get unique dates
unique_dates = sorted(data['date'].unique())[:250]  # First 250 days for demo

print(f"📅 Backtesting {len(unique_dates)} trading days...")

# Backtest loop
for i, current_date in enumerate(unique_dates):
    
    # Get current day data
    day_data = data[data['date'] == current_date]
    if day_data.empty:
        continue
    
    spot_price = day_data['underlying_price'].iloc[0]
    
    # Entry logic - monthly
    if i % 20 == 0 and len(positions) < 3:
        
        # Find ZEBRA strikes
        zebra = find_zebra_strikes(day_data, spot_price)
        
        if zebra:
            # Calculate net cost (2 long ITM - 1 short OTM)
            net_cost = (2 * zebra['itm_price'] - zebra['otm_price']) * 100
            
            if cash >= net_cost and net_cost > 0:
                # Open position
                positions.append({
                    'entry_date': current_date,
                    'entry_price': spot_price,
                    'itm_strike': zebra['itm_strike'],
                    'otm_strike': zebra['otm_strike'],
                    'net_cost': net_cost,
                    'expiration': zebra['expiration']
                })
                
                cash -= net_cost
                
                trades.append({
                    'date': current_date,
                    'action': 'OPEN',
                    'underlying': spot_price,
                    'itm_strike': zebra['itm_strike'],
                    'otm_strike': zebra['otm_strike'],
                    'cost': net_cost,
                    'dte': zebra['dte']
                })
                
                print(f"  📈 Opened ZEBRA: ITM ${zebra['itm_strike']:.0f} / OTM ${zebra['otm_strike']:.0f}, Cost: ${net_cost:.0f}")
    
    # Exit logic
    positions_to_close = []
    for pos in positions:
        days_held = (current_date - pos['entry_date']).days
        
        # Exit after 30 days or near expiration
        if days_held >= 30 or current_date >= pos['expiration']:
            
            # Calculate P&L (simplified)
            price_move = spot_price - pos['entry_price']
            
            # ZEBRA behaves like 100 shares of stock (2 ITM calls - 1 OTM call ≈ 100 delta)
            pnl = price_move * 100  # Simplified P&L
            
            # Limit loss to initial cost
            pnl = max(-pos['net_cost'], pnl)
            
            cash += pos['net_cost'] + pnl
            positions_to_close.append(pos)
            
            trades.append({
                'date': current_date,
                'action': 'CLOSE',
                'underlying': spot_price,
                'pnl': pnl,
                'days_held': days_held
            })
            
            result = "WIN" if pnl > 0 else "LOSS"
            print(f"  📊 Closed {result}: P&L ${pnl:.0f} after {days_held} days")
    
    # Remove closed positions
    for pos in positions_to_close:
        positions.remove(pos)
    
    # Track equity
    position_value = sum(p['net_cost'] for p in positions)
    total_equity = cash + position_value
    equity_curve.append({
        'date': current_date,
        'equity': total_equity,
        'cash': cash,
        'positions': len(positions)
    })

# Calculate final metrics
equity_df = pd.DataFrame(equity_curve)
trades_df = pd.DataFrame(trades)

# Calculate returns
final_equity = equity_df['equity'].iloc[-1]
total_return = (final_equity / initial_capital - 1) * 100

# Calculate win rate
closed_trades = trades_df[trades_df['action'] == 'CLOSE']
if len(closed_trades) > 0:
    wins = (closed_trades['pnl'] > 0).sum()
    win_rate = wins / len(closed_trades) * 100
else:
    win_rate = 0

# Calculate max drawdown
equity_df['cummax'] = equity_df['equity'].cummax()
equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax'] * 100
max_drawdown = equity_df['drawdown'].min()

# Print results
print("\n" + "=" * 60)
print("📊 BACKTEST RESULTS")
print("=" * 60)
print(f"Initial Capital: ${initial_capital:,.0f}")
print(f"Final Equity: ${final_equity:,.0f}")
print(f"Total Return: {total_return:.1f}%")
print(f"Total Trades: {len(closed_trades)}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Max Drawdown: {max_drawdown:.1f}%")

# Create visualization
print("\n📊 Creating visualization...")

fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('Equity Curve', 'Drawdown', 'Trade P&L', 'Monthly Returns'),
    specs=[[{'type': 'scatter'}, {'type': 'scatter'}],
           [{'type': 'bar'}, {'type': 'bar'}]]
)

# Equity curve
fig.add_trace(
    go.Scatter(x=equity_df['date'], y=equity_df['equity'],
               mode='lines', name='Portfolio Value',
               line=dict(color='blue', width=2)),
    row=1, col=1
)

# Drawdown
fig.add_trace(
    go.Scatter(x=equity_df['date'], y=equity_df['drawdown'],
               mode='lines', name='Drawdown %',
               line=dict(color='red', width=2)),
    row=1, col=2
)

# Trade P&L
if len(closed_trades) > 0:
    colors = ['green' if pnl > 0 else 'red' for pnl in closed_trades['pnl']]
    fig.add_trace(
        go.Bar(x=list(range(len(closed_trades))), y=closed_trades['pnl'],
               marker_color=colors, name='Trade P&L'),
        row=2, col=1
    )

# Monthly returns
equity_df['month'] = equity_df['date'].dt.to_period('M')
monthly_returns = equity_df.groupby('month')['equity'].last().pct_change() * 100
if len(monthly_returns) > 0:
    fig.add_trace(
        go.Bar(x=monthly_returns.index.astype(str), y=monthly_returns.values,
               name='Monthly Return %'),
        row=2, col=2
    )

fig.update_layout(
    title='ZEBRA Call Strategy - Backtest Results',
    height=800,
    showlegend=False
)

# Save chart
Path('results/charts').mkdir(parents=True, exist_ok=True)
chart_file = f'results/charts/zebra_demo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
fig.write_html(chart_file)
print(f"📊 Chart saved to: {chart_file}")

# Save results
Path('results/reports').mkdir(parents=True, exist_ok=True)
results_file = f'results/reports/zebra_demo_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
trades_df.to_csv(results_file, index=False)
print(f"📝 Results saved to: {results_file}")

print("\n✅ ZEBRA Demo Complete!")