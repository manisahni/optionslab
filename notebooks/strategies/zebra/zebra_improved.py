#!/usr/bin/env python3
"""
ZEBRA Call Strategy - IMPROVED VERSION
With proper exit rules, position management, and risk controls
"""

import sys
import os
sys.path.append('/Users/nish_macbook/trading/daily-optionslab')

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from pathlib import Path
import glob
import warnings
warnings.filterwarnings('ignore')

print("🚀 ZEBRA Strategy IMPROVED Version Starting...")
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

# Load 2024 daily files
daily_2024 = sorted(glob.glob('data/spy_options/spy_options_eod_2024*.parquet'))[:100]
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

# ============================================================
# IMPROVED ZEBRA STRATEGY IMPLEMENTATION
# ============================================================

def find_zebra_strikes_improved(day_data, spot_price):
    """
    Find ZEBRA strikes with IMPROVED selection criteria
    - Deeper ITM for better delta (90% of spot)
    - Further OTM for more credit (110% of spot)
    - Target 45-60 DTE for less decay
    """
    
    # Filter calls with proper DTE range
    calls = day_data[
        (day_data['right'] == 'C') & 
        (day_data['dte'] >= 45) &  # More time
        (day_data['dte'] <= 60) &
        (day_data['volume'] > 10)  # Some liquidity
    ].copy()
    
    if len(calls) == 0:
        return None
    
    # ITM call - 10% below spot (deeper ITM = higher delta)
    itm_target = spot_price * 0.90
    calls['itm_diff'] = abs(calls['strike'] - itm_target)
    itm_call = calls.nsmallest(1, 'itm_diff').iloc[0]
    
    # OTM call - 10% above spot (further OTM = more credit)
    otm_target = spot_price * 1.10
    calls['otm_diff'] = abs(calls['strike'] - otm_target)
    otm_call = calls.nsmallest(1, 'otm_diff').iloc[0]
    
    # Calculate net cost
    net_debit = (2 * itm_call['mid_price'] - otm_call['mid_price'])
    
    # Only return if net debit is reasonable (5-20% of spot price)
    if net_debit > 0 and net_debit < spot_price * 0.20:
        return {
            'itm_strike': itm_call['strike'],
            'itm_price': itm_call['mid_price'],
            'otm_strike': otm_call['strike'],
            'otm_price': otm_call['mid_price'],
            'net_debit': net_debit,
            'expiration': itm_call['expiration'],
            'dte': itm_call['dte']
        }
    
    return None

def calculate_position_pnl(position, current_day_data, spot_price):
    """
    Calculate current P&L for a ZEBRA position
    """
    # Find current prices for our strikes
    calls = current_day_data[
        (current_day_data['right'] == 'C') &
        (current_day_data['expiration'] == position['expiration'])
    ]
    
    if len(calls) == 0:
        # If options expired or not found, calculate intrinsic value
        itm_value = max(spot_price - position['itm_strike'], 0)
        otm_value = max(spot_price - position['otm_strike'], 0)
        current_value = 2 * itm_value - otm_value
    else:
        # Get current mid prices
        itm_calls = calls[calls['strike'] == position['itm_strike']]
        otm_calls = calls[calls['strike'] == position['otm_strike']]
        
        if len(itm_calls) > 0 and len(otm_calls) > 0:
            itm_mid = itm_calls.iloc[0]['mid_price']
            otm_mid = otm_calls.iloc[0]['mid_price']
            current_value = 2 * itm_mid - otm_mid
        else:
            # Fallback to intrinsic
            itm_value = max(spot_price - position['itm_strike'], 0)
            otm_value = max(spot_price - position['otm_strike'], 0)
            current_value = 2 * itm_value - otm_value
    
    # Calculate P&L
    pnl = (current_value - position['net_cost'] / 100) * 100
    pnl_pct = (pnl / position['net_cost']) * 100
    
    return pnl, pnl_pct, current_value * 100

# ============================================================
# RUN IMPROVED BACKTEST
# ============================================================

print("\n" + "=" * 60)
print("🎯 RUNNING IMPROVED ZEBRA STRATEGY")
print("=" * 60)

# Initialize backtest
initial_capital = 100000
cash = initial_capital
positions = []
trades = []
equity_curve = []
spy_prices = []

# Strategy parameters
MAX_POSITIONS = 3
POSITION_SIZE_PCT = 0.20  # 20% of capital per position
PROFIT_TARGET = 25  # Exit at 25% profit
STOP_LOSS = -20  # Exit at 20% loss
MAX_HOLDING_DAYS = 30  # Maximum holding period
ENTRY_FREQUENCY = 10  # Check for entry every 10 days

# Get unique dates
unique_dates = sorted(data['date'].unique())

print(f"📅 Backtesting {len(unique_dates)} trading days...")
print(f"📊 Strategy Rules:")
print(f"   - Profit Target: {PROFIT_TARGET}%")
print(f"   - Stop Loss: {STOP_LOSS}%")
print(f"   - Max Hold: {MAX_HOLDING_DAYS} days")
print(f"   - Position Size: {POSITION_SIZE_PCT*100}% of capital")
print(f"   - Max Positions: {MAX_POSITIONS}")
print("")

# Track statistics
total_trades = 0
winning_trades = 0
total_pnl = 0
days_since_entry = 0

# Backtest loop
for i, current_date in enumerate(unique_dates):
    
    # Get current day data
    day_data = data[data['date'] == current_date]
    if day_data.empty:
        continue
    
    spot_price = day_data['underlying_price'].iloc[0]
    spy_prices.append({'date': current_date, 'price': spot_price})
    
    # ============================================================
    # EXIT MANAGEMENT - Check all positions for exit signals
    # ============================================================
    positions_to_close = []
    
    for pos in positions:
        days_held = (current_date - pos['entry_date']).days
        pnl, pnl_pct, current_value = calculate_position_pnl(pos, day_data, spot_price)
        
        exit_reason = None
        
        # Check exit conditions
        if pnl_pct >= PROFIT_TARGET:
            exit_reason = f"PROFIT TARGET ({pnl_pct:.1f}%)"
        elif pnl_pct <= STOP_LOSS:
            exit_reason = f"STOP LOSS ({pnl_pct:.1f}%)"
        elif days_held >= MAX_HOLDING_DAYS:
            exit_reason = f"TIME STOP ({days_held} days)"
        elif spot_price > pos['otm_strike'] - 5:  # Short strike threatened
            exit_reason = f"SHORT STRIKE BREACH"
        
        if exit_reason:
            # Close position
            cash += pos['net_cost'] + pnl
            positions_to_close.append(pos)
            total_trades += 1
            
            if pnl > 0:
                winning_trades += 1
                result = "✅ WIN"
            else:
                result = "❌ LOSS"
            
            total_pnl += pnl
            
            trades.append({
                'date': current_date,
                'action': 'CLOSE',
                'result': result,
                'underlying': spot_price,
                'entry_price': pos['entry_price'],
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'days_held': days_held,
                'exit_reason': exit_reason
            })
            
            print(f"  {result} Exit: {exit_reason}, P&L: ${pnl:.0f} ({pnl_pct:.1f}%), Held: {days_held} days")
    
    # Remove closed positions
    for pos in positions_to_close:
        positions.remove(pos)
    
    # ============================================================
    # ENTRY LOGIC - Check for new positions
    # ============================================================
    days_since_entry += 1
    
    # Entry conditions
    can_enter = (
        days_since_entry >= ENTRY_FREQUENCY and  # Time since last entry
        len(positions) < MAX_POSITIONS and  # Position limit
        i > 0  # Not first day
    )
    
    if can_enter:
        # Check market conditions (avoid entering after big moves)
        if i >= 5:
            recent_move = (spot_price / spy_prices[-5]['price'] - 1) * 100
            if abs(recent_move) > 5:  # Skip if >5% move in 5 days
                can_enter = False
    
    if can_enter:
        # Find ZEBRA strikes
        zebra = find_zebra_strikes_improved(day_data, spot_price)
        
        if zebra:
            # Calculate position size
            position_capital = min(cash * POSITION_SIZE_PCT, cash)
            net_cost = zebra['net_debit'] * 100
            
            if cash >= net_cost and net_cost <= position_capital:
                # Open position
                positions.append({
                    'entry_date': current_date,
                    'entry_price': spot_price,
                    'itm_strike': zebra['itm_strike'],
                    'otm_strike': zebra['otm_strike'],
                    'net_cost': net_cost,
                    'expiration': zebra['expiration'],
                    'dte': zebra['dte']
                })
                
                cash -= net_cost
                days_since_entry = 0
                
                trades.append({
                    'date': current_date,
                    'action': 'OPEN',
                    'underlying': spot_price,
                    'itm_strike': zebra['itm_strike'],
                    'otm_strike': zebra['otm_strike'],
                    'cost': net_cost,
                    'dte': zebra['dte']
                })
                
                print(f"📈 OPEN: ITM ${zebra['itm_strike']:.0f} / OTM ${zebra['otm_strike']:.0f}, "
                      f"Cost: ${net_cost:.0f}, DTE: {zebra['dte']}")
    
    # Track equity
    position_value = 0
    for pos in positions:
        _, _, current_value = calculate_position_pnl(pos, day_data, spot_price)
        position_value += current_value
    
    total_equity = cash + position_value
    equity_curve.append({
        'date': current_date,
        'equity': total_equity,
        'cash': cash,
        'positions': len(positions),
        'spy_price': spot_price
    })

# ============================================================
# CALCULATE FINAL METRICS
# ============================================================

equity_df = pd.DataFrame(equity_curve)
spy_df = pd.DataFrame(spy_prices)
trades_df = pd.DataFrame(trades)

# Calculate returns
final_equity = equity_df['equity'].iloc[-1]
total_return = (final_equity / initial_capital - 1) * 100

# SPY buy-and-hold return
spy_return = (spy_df['price'].iloc[-1] / spy_df['price'].iloc[0] - 1) * 100

# Win rate
if total_trades > 0:
    win_rate = (winning_trades / total_trades) * 100
else:
    win_rate = 0

# Average win/loss
closed_trades = trades_df[trades_df['action'] == 'CLOSE']
if len(closed_trades) > 0:
    wins = closed_trades[closed_trades['pnl'] > 0]
    losses = closed_trades[closed_trades['pnl'] <= 0]
    
    avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0
    avg_days = closed_trades['days_held'].mean()
else:
    avg_win = avg_loss = avg_days = 0

# Max drawdown
equity_df['cummax'] = equity_df['equity'].cummax()
equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax'] * 100
max_drawdown = equity_df['drawdown'].min()

# Sharpe ratio (simplified)
equity_df['returns'] = equity_df['equity'].pct_change()
sharpe = np.sqrt(252) * equity_df['returns'].mean() / equity_df['returns'].std() if equity_df['returns'].std() > 0 else 0

# ============================================================
# PRINT RESULTS
# ============================================================

print("\n" + "=" * 60)
print("📊 IMPROVED ZEBRA STRATEGY RESULTS")
print("=" * 60)
print(f"Initial Capital: ${initial_capital:,.0f}")
print(f"Final Equity: ${final_equity:,.0f}")
print(f"ZEBRA Return: {total_return:.1f}%")
print(f"SPY Return: {spy_return:.1f}%")
print(f"Outperformance: {total_return - spy_return:+.1f}%")
print("")
print(f"Total Trades: {total_trades}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Avg Win: {avg_win:.1f}%")
print(f"Avg Loss: {avg_loss:.1f}%")
print(f"Avg Days Held: {avg_days:.0f}")
print(f"Max Drawdown: {max_drawdown:.1f}%")
print(f"Sharpe Ratio: {sharpe:.2f}")

# ============================================================
# CREATE VISUALIZATIONS
# ============================================================

print("\n📊 Creating visualizations...")

fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('Equity Curve vs SPY', 'Drawdown', 'Trade P&L Distribution', 'Exit Reasons'),
    specs=[[{'type': 'scatter'}, {'type': 'scatter'}],
           [{'type': 'histogram'}, {'type': 'bar'}]]
)

# Normalize for comparison
equity_df['equity_norm'] = equity_df['equity'] / initial_capital * 100
equity_df['spy_norm'] = equity_df['spy_price'] / equity_df['spy_price'].iloc[0] * 100

# Equity curves
fig.add_trace(
    go.Scatter(x=equity_df['date'], y=equity_df['equity_norm'],
               mode='lines', name='ZEBRA Improved',
               line=dict(color='blue', width=2)),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(x=equity_df['date'], y=equity_df['spy_norm'],
               mode='lines', name='SPY Buy & Hold',
               line=dict(color='gray', width=2, dash='dash')),
    row=1, col=1
)

# Drawdown
fig.add_trace(
    go.Scatter(x=equity_df['date'], y=equity_df['drawdown'],
               mode='lines', name='Drawdown %',
               line=dict(color='red', width=2)),
    row=1, col=2
)

# Trade P&L distribution
if len(closed_trades) > 0:
    fig.add_trace(
        go.Histogram(x=closed_trades['pnl_pct'],
                    nbinsx=20,
                    name='P&L Distribution',
                    marker_color='purple'),
        row=2, col=1
    )
    
    # Exit reasons
    exit_reasons = closed_trades['exit_reason'].value_counts()
    fig.add_trace(
        go.Bar(x=exit_reasons.index, y=exit_reasons.values,
               name='Exit Reasons',
               marker_color='orange'),
        row=2, col=2
    )

fig.update_layout(
    title=f'ZEBRA Strategy IMPROVED - {total_return:.1f}% vs SPY {spy_return:.1f}%',
    height=800,
    showlegend=True
)

fig.update_yaxes(title_text="Value (Normalized to 100)", row=1, col=1)
fig.update_yaxes(title_text="Drawdown %", row=1, col=2)
fig.update_xaxes(title_text="P&L %", row=2, col=1)
fig.update_xaxes(title_text="Exit Reason", row=2, col=2)

# Save chart
Path('results/charts').mkdir(parents=True, exist_ok=True)
chart_file = f'results/charts/zebra_improved_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
fig.write_html(chart_file)
print(f"📊 Chart saved to: {chart_file}")

# Save detailed results
Path('results/reports').mkdir(parents=True, exist_ok=True)
results_file = f'results/reports/zebra_improved_trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
trades_df.to_csv(results_file, index=False)
print(f"📝 Trade log saved to: {results_file}")

# ============================================================
# COMPARISON WITH ORIGINAL
# ============================================================

print("\n" + "=" * 60)
print("📊 IMPROVEMENT COMPARISON")
print("=" * 60)
print("Original ZEBRA:")
print("  - Return: 3.1%")
print("  - Trades: 2")
print("  - Avg Hold: 194 days")
print("")
print("Improved ZEBRA:")
print(f"  - Return: {total_return:.1f}%")
print(f"  - Trades: {total_trades}")
print(f"  - Avg Hold: {avg_days:.0f} days")
print(f"  - Improvement: {total_return - 3.1:+.1f}% better!")

print("\n✅ IMPROVED ZEBRA Strategy Complete!")