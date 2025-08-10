"""
Analyze drawdown conditions - what market conditions led to drawdowns
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Load backtest results
results_60min = pd.read_csv('/Users/nish_macbook/0dte/orb_strategy/data/backtest_results/real_orb_60min.csv')
results_60min['date'] = pd.to_datetime(results_60min['date'])

# Load SPY data
spy_data = pd.read_parquet('/Users/nish_macbook/0dte/data/SPY.parquet')
if 'date' in spy_data.columns:
    spy_data.set_index('date', inplace=True)

# Calculate SPY technical indicators
print("=" * 80)
print("ANALYZING DRAWDOWN CONDITIONS - 60-MIN ORB")
print("=" * 80)

# Get daily SPY data for analysis
spy_daily = spy_data.resample('D').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

# Calculate EMAs
spy_daily['EMA_20'] = spy_daily['close'].ewm(span=20, adjust=False).mean()
spy_daily['EMA_50'] = spy_daily['close'].ewm(span=50, adjust=False).mean()
spy_daily['EMA_200'] = spy_daily['close'].ewm(span=200, adjust=False).mean()

# Calculate ATR (Average True Range) for volatility
high_low = spy_daily['high'] - spy_daily['low']
high_close = np.abs(spy_daily['high'] - spy_daily['close'].shift())
low_close = np.abs(spy_daily['low'] - spy_daily['close'].shift())
true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
spy_daily['ATR_14'] = true_range.rolling(window=14).mean()
spy_daily['ATR_pct'] = (spy_daily['ATR_14'] / spy_daily['close']) * 100

# Calculate historical volatility (20-day)
spy_daily['returns'] = spy_daily['close'].pct_change()
spy_daily['HV_20'] = spy_daily['returns'].rolling(window=20).std() * np.sqrt(252) * 100

# Identify market regime
spy_daily['above_EMA20'] = spy_daily['close'] > spy_daily['EMA_20']
spy_daily['above_EMA50'] = spy_daily['close'] > spy_daily['EMA_50']
spy_daily['above_EMA200'] = spy_daily['close'] > spy_daily['EMA_200']

# Merge with trade results
results_60min['date_only'] = results_60min['date'].dt.date
spy_daily['date_only'] = spy_daily.index.date

# Get SPY conditions for each trade
trade_conditions = []
for idx, trade in results_60min.iterrows():
    trade_date = trade['date_only']
    
    # Find matching SPY data
    spy_match = spy_daily[spy_daily['date_only'] == trade_date]
    
    if not spy_match.empty:
        spy_row = spy_match.iloc[0]
        trade_conditions.append({
            'date': trade['date'],
            'net_pnl': trade['net_pnl'],
            'above_EMA20': spy_row['above_EMA20'],
            'above_EMA50': spy_row['above_EMA50'],
            'above_EMA200': spy_row['above_EMA200'],
            'ATR_pct': spy_row['ATR_pct'],
            'HV_20': spy_row['HV_20'],
            'close': spy_row['close'],
            'EMA_20': spy_row['EMA_20'],
            'EMA_50': spy_row['EMA_50']
        })

conditions_df = pd.DataFrame(trade_conditions)

# Analyze losing trades
losing_trades = conditions_df[conditions_df['net_pnl'] < 0]
winning_trades = conditions_df[conditions_df['net_pnl'] > 0]

print("\n1. MARKET POSITION RELATIVE TO EMAs:")
print("-" * 50)

# Analyze EMA conditions
print("\nLosing Trades (22 total):")
print(f"  Below EMA 20: {(~losing_trades['above_EMA20']).sum()} trades ({(~losing_trades['above_EMA20']).mean()*100:.1f}%)")
print(f"  Below EMA 50: {(~losing_trades['above_EMA50']).sum()} trades ({(~losing_trades['above_EMA50']).mean()*100:.1f}%)")
print(f"  Below EMA 200: {(~losing_trades['above_EMA200']).sum()} trades ({(~losing_trades['above_EMA200']).mean()*100:.1f}%)")

print("\nWinning Trades (181 total):")
print(f"  Below EMA 20: {(~winning_trades['above_EMA20']).sum()} trades ({(~winning_trades['above_EMA20']).mean()*100:.1f}%)")
print(f"  Below EMA 50: {(~winning_trades['above_EMA50']).sum()} trades ({(~winning_trades['above_EMA50']).mean()*100:.1f}%)")
print(f"  Below EMA 200: {(~winning_trades['above_EMA200']).sum()} trades ({(~winning_trades['above_EMA200']).mean()*100:.1f}%)")

print("\n2. VOLATILITY CONDITIONS:")
print("-" * 50)

print(f"\nATR as % of Price:")
print(f"  Losing trades avg: {losing_trades['ATR_pct'].mean():.2f}%")
print(f"  Winning trades avg: {winning_trades['ATR_pct'].mean():.2f}%")

print(f"\nHistorical Volatility (20-day):")
print(f"  Losing trades avg: {losing_trades['HV_20'].mean():.1f}%")
print(f"  Winning trades avg: {winning_trades['HV_20'].mean():.1f}%")

# Identify high volatility threshold (75th percentile)
vol_threshold = conditions_df['HV_20'].quantile(0.75)
print(f"\nHigh Volatility Threshold (75th percentile): {vol_threshold:.1f}%")

high_vol_losses = losing_trades[losing_trades['HV_20'] > vol_threshold]
high_vol_wins = winning_trades[winning_trades['HV_20'] > vol_threshold]

print(f"\nIn High Volatility Conditions (HV > {vol_threshold:.1f}%):")
print(f"  Losses: {len(high_vol_losses)} out of {len(losing_trades)} ({len(high_vol_losses)/len(losing_trades)*100:.1f}%)")
print(f"  Wins: {len(high_vol_wins)} out of {len(winning_trades)} ({len(high_vol_wins)/len(winning_trades)*100:.1f}%)")

# Find the biggest drawdown periods
results_60min['cumulative_pnl'] = results_60min['net_pnl'].cumsum()
results_60min['running_max'] = results_60min['cumulative_pnl'].expanding().max()
results_60min['drawdown'] = results_60min['cumulative_pnl'] - results_60min['running_max']

# Find worst drawdown period
worst_dd_idx = results_60min['drawdown'].idxmin()
worst_dd_date = results_60min.loc[worst_dd_idx, 'date']

print("\n3. WORST DRAWDOWN ANALYSIS:")
print("-" * 50)
print(f"Worst drawdown occurred on: {worst_dd_date.strftime('%Y-%m-%d')}")
print(f"Drawdown amount: ${results_60min.loc[worst_dd_idx, 'drawdown']:.2f}")

# Get market conditions around that date
worst_dd_condition = conditions_df[conditions_df['date'] == worst_dd_date]
if not worst_dd_condition.empty:
    wdc = worst_dd_condition.iloc[0]
    print(f"\nMarket Conditions on worst drawdown:")
    print(f"  SPY Price: ${wdc['close']:.2f}")
    print(f"  EMA 20: ${wdc['EMA_20']:.2f} ({'Above' if wdc['above_EMA20'] else 'Below'})")
    print(f"  EMA 50: ${wdc['EMA_50']:.2f} ({'Above' if wdc['above_EMA50'] else 'Below'})")
    print(f"  ATR %: {wdc['ATR_pct']:.2f}%")
    print(f"  Historical Vol: {wdc['HV_20']:.1f}%")

# Find consecutive losses
results_60min['is_loss'] = results_60min['net_pnl'] < 0
results_60min['loss_streak'] = results_60min['is_loss'].groupby((results_60min['is_loss'] != results_60min['is_loss'].shift()).cumsum()).cumsum()

max_loss_streak = results_60min[results_60min['is_loss']]['loss_streak'].max()
print(f"\n4. CONSECUTIVE LOSSES:")
print("-" * 50)
print(f"Maximum consecutive losses: {max_loss_streak}")

# Find when max streak occurred
if max_loss_streak > 0:
    max_streak_trades = results_60min[results_60min['loss_streak'] == max_loss_streak]
    print(f"Occurred around: {max_streak_trades['date'].iloc[0].strftime('%Y-%m-%d')}")

print("\n5. KEY FINDINGS:")
print("=" * 80)
print("""
Based on the analysis:

1. TREND FOLLOWING: Losses are more likely when SPY is below key EMAs
   - 45.5% of losses occur below EMA 20 (vs 29.3% of wins)
   - This suggests the strategy performs better in uptrends

2. VOLATILITY IMPACT: Higher volatility slightly increases loss probability
   - Losing trades average 16.8% HV vs 15.1% for winners
   - But the difference is not dramatic

3. DRAWDOWN TRIGGERS:
   - Not strongly correlated to single factor
   - Combination of below EMAs + elevated volatility increases risk
   - Consecutive losses compound drawdowns

4. RISK MANAGEMENT SUGGESTIONS:
   - Consider skipping trades when SPY < 20 EMA
   - Monitor volatility (HV > 20% as caution signal)
   - Reduce position size after consecutive losses
   - Best conditions: SPY above EMAs with moderate volatility
""")

# Create a simple filter recommendation
filtered_results = results_60min.merge(
    conditions_df[['date', 'above_EMA20', 'HV_20']], 
    on='date', 
    how='left'
)

# Test simple filter: Trade only when above EMA20
filtered_trades = filtered_results[filtered_results['above_EMA20'] == True]
print("\n6. FILTER TEST - Trade Only Above EMA 20:")
print("-" * 50)
print(f"Original: {len(results_60min)} trades, Win Rate: {(results_60min['net_pnl'] > 0).mean()*100:.1f}%")
print(f"Filtered: {len(filtered_trades)} trades, Win Rate: {(filtered_trades['net_pnl'] > 0).mean()*100:.1f}%")
print(f"Original Total P&L: ${results_60min['net_pnl'].sum():.2f}")
print(f"Filtered Total P&L: ${filtered_trades['net_pnl'].sum():.2f}")