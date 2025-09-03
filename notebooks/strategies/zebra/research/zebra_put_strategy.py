# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Zebra Put Strategy Backtest
# 
# ## Strategy Overview
# **ZEBRA = Zero Extrinsic Back Ratio**
# 
# The Zebra Put is a bearish strategy that:
# - Buys 2 ITM (In-The-Money) puts @ ~70-75 delta each
# - Sells 1 ATM (At-The-Money) put @ ~50 delta
# - Creates a synthetic short stock position with limited risk
# - Net delta: ~-100 (like being short 100 shares)
# 
# ### Advantages over Short Stock:
# - Limited risk (max loss = debit paid)
# - No margin requirements like short stock
# - No borrowing costs
# - Embedded stop loss
# 
# ### Profit Profile:
# - Profits from stock decline (like short stock)
# - Breakeven ≈ entry stock price (zero extrinsic value)
# - Max loss = initial debit
# - Max profit = (Short strike - Net debit) × 100

# %%
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

pd.set_option('display.float_format', '{:.2f}'.format)
print("Libraries loaded - Zebra Put Strategy")

# %% [markdown]
# ## 1. Load SPY Options Data

# %%
# Load data
data_path = '/Users/nish_macbook/trading/daily-optionslab/data/spy_options/'

# Load 2023-2024 data for backtesting
df_2023 = pd.read_parquet(f'{data_path}SPY_OPTIONS_2023_COMPLETE.parquet')
df_2024 = pd.read_parquet(f'{data_path}SPY_OPTIONS_2024_COMPLETE.parquet')

# Combine datasets
df = pd.concat([df_2023, df_2024], ignore_index=True)

# Convert and prepare
df['date'] = pd.to_datetime(df['date'])
df['expiration'] = pd.to_datetime(df['expiration'])
df['dte'] = (df['expiration'] - df['date']).dt.days
df['strike'] = df['strike'] / 1000  # Convert cents to dollars
df['mid_price'] = (df['bid'] + df['ask']) / 2
df['option_type'] = df['right'].map({'C': 'call', 'P': 'put'})  # Map right to option_type
df['underlying_last'] = df['underlying_price']  # Create consistent column name

# Filter for valid data
df = df[(df['bid'] > 0) & (df['volume'] > 0)]

print(f"Loaded {len(df):,} option records")
print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
print(f"Strike range: ${df['strike'].min():.0f} - ${df['strike'].max():.0f}")

# %% [markdown]
# ## 2. Zebra Put Setup Functions

# %%
def find_zebra_put_strikes(spy_price, options_df, target_dte=45):
    """
    Find optimal strikes for Zebra Put
    - Buy 2 ITM puts around 70-75 delta
    - Sell 1 ATM put around 50 delta
    """
    # Filter for target expiration
    dte_tolerance = 7
    exp_options = options_df[
        (options_df['dte'] >= target_dte - dte_tolerance) &
        (options_df['dte'] <= target_dte + dte_tolerance) &
        (options_df['option_type'] == 'put')
    ].copy()
    
    
    if len(exp_options) == 0:
        return None
    
    # Use most common expiration
    exp_date = exp_options['expiration'].mode()[0]
    exp_options = exp_options[exp_options['expiration'] == exp_date]
    
    # Find ATM strike (closest to current price)
    exp_options['distance'] = abs(exp_options['strike'] - spy_price)
    atm_strike = exp_options.nsmallest(1, 'distance')['strike'].iloc[0]
    
    # Find ITM strike (5-7% ITM for ~70-75 delta)
    itm_target = spy_price * 1.06  # 6% ITM
    exp_options['itm_distance'] = abs(exp_options['strike'] - itm_target)
    itm_strike = exp_options[exp_options['strike'] > spy_price].nsmallest(1, 'itm_distance')['strike'].iloc[0]
    
    return {
        'itm_strike': itm_strike,
        'atm_strike': atm_strike,
        'expiration': exp_date,
        'dte': exp_options['dte'].iloc[0]
    }

def calculate_zebra_put_cost(strikes_info, options_df, current_date):
    """
    Calculate the net debit for opening a Zebra Put
    """
    if strikes_info is None:
        return None
    
    # Get prices for each leg
    exp_opts = options_df[
        (options_df['date'] == current_date) &
        (options_df['expiration'] == strikes_info['expiration']) &
        (options_df['option_type'] == 'put')
    ]
    
    # Buy 2 ITM puts
    itm_put = exp_opts[exp_opts['strike'] == strikes_info['itm_strike']]
    if len(itm_put) == 0:
        return None
    itm_cost = itm_put['ask'].iloc[0] * 2  # Buy 2 contracts
    
    # Sell 1 ATM put
    atm_put = exp_opts[exp_opts['strike'] == strikes_info['atm_strike']]
    if len(atm_put) == 0:
        return None
    atm_credit = atm_put['bid'].iloc[0]  # Sell 1 contract
    
    # Net debit
    net_debit = itm_cost - atm_credit
    
    # Calculate approximate delta (simplified)
    itm_delta = -0.70  # Approximate for 6% ITM put
    atm_delta = -0.50  # Approximate for ATM put
    net_delta = (2 * itm_delta) - atm_delta  # Should be around -0.90 to -1.00
    
    return {
        'net_debit': net_debit,
        'itm_cost': itm_cost,
        'atm_credit': atm_credit,
        'net_delta': net_delta,
        'max_profit': strikes_info['atm_strike'] - net_debit,
        'max_loss': net_debit,
        'breakeven': strikes_info['atm_strike']  # Zero extrinsic means BE ≈ current price
    }

# %% [markdown]
# ## 3. Backtest Zebra Put Strategy

# %%
def backtest_zebra_put(df, start_date, end_date, initial_capital=10000):
    """
    Backtest the Zebra Put strategy
    """
    # Get SPY prices
    spy_prices = df[df['option_type'] == 'call'].groupby('date')['underlying_last'].first()
    
    # Filter date range
    mask = (spy_prices.index >= start_date) & (spy_prices.index <= end_date)
    spy_prices = spy_prices[mask]
    
    results = []
    trades = []
    capital = initial_capital
    position = None
    
    # Monthly trading (enter on first trading day of month)
    for date in spy_prices.index:
        if date.day <= 5 and position is None:  # Enter in first week of month
            # Find Zebra Put strikes
            spy_price = spy_prices[date]
            date_options = df[df['date'] == date]
            
            strikes = find_zebra_put_strikes(spy_price, date_options, target_dte=45)
            if strikes is None:
                continue
            
            cost_info = calculate_zebra_put_cost(strikes, date_options, date)
            if cost_info is None:
                continue
            
            # Open position
            # Calculate number of contracts
            contract_cost = cost_info['net_debit'] * 100
            
            # Skip if insufficient capital for even 1 contract
            if capital < contract_cost:
                continue
                
            max_investment = capital * 0.25  # Max 25% of capital per trade
            num_contracts = max(1, min(int(max_investment / contract_cost), 5))  # At least 1, max 5 contracts
            
            position = {
                'entry_date': date,
                'entry_price': spy_price,
                'strikes': strikes,
                'cost': cost_info,
                'contracts': num_contracts
            }
            
            position_cost = position['contracts'] * cost_info['net_debit'] * 100
            capital -= position_cost
            
            
            trades.append({
                'entry_date': date,
                'entry_price': spy_price,
                'itm_strike': strikes['itm_strike'],
                'atm_strike': strikes['atm_strike'],
                'net_debit': cost_info['net_debit'],
                'contracts': position['contracts'],
                'position_cost': position_cost,
                'net_delta': cost_info['net_delta'] * position['contracts'] * 100
            })
        
        # Check for exit (at expiration or stop loss)
        if position is not None:
            exp_date = position['strikes']['expiration']
            
            # Exit at expiration or if 21 DTE
            days_to_exp = (exp_date - date).days
            if days_to_exp <= 21:
                # Calculate P&L at exit
                exit_price = spy_prices[date]
                
                # Get option prices at exit
                exit_options = df[
                    (df['date'] == date) &
                    (df['expiration'] == exp_date) &
                    (df['option_type'] == 'put')
                ]
                
                if len(exit_options) > 0:
                    # Calculate intrinsic values
                    itm_value = max(position['strikes']['itm_strike'] - exit_price, 0)
                    atm_value = max(position['strikes']['atm_strike'] - exit_price, 0)
                    
                    # P&L = 2 * ITM value - ATM value - initial debit
                    spread_value = 2 * itm_value - atm_value
                    pnl_per_contract = spread_value - position['cost']['net_debit']
                    total_pnl = pnl_per_contract * position['contracts'] * 100
                    
                    capital += (position['contracts'] * position['cost']['net_debit'] * 100) + total_pnl
                    
                    
                    trades[-1].update({
                        'exit_date': date,
                        'exit_price': exit_price,
                        'days_held': (date - position['entry_date']).days,
                        'pnl': total_pnl,
                        'pnl_pct': (total_pnl / (position['contracts'] * position['cost']['net_debit'] * 100)) * 100
                    })
                    
                    position = None
        
        results.append({
            'date': date,
            'spy_price': spy_prices[date],
            'capital': capital,
            'in_position': position is not None
        })
    
    return pd.DataFrame(results), pd.DataFrame(trades)

# %% [markdown]
# ## 4. Run Backtest for 2023-2024

# %%
# Run backtest
results, trades = backtest_zebra_put(
    df,
    start_date='2023-01-01',
    end_date='2024-12-31',
    initial_capital=10000
)

# Calculate performance metrics
total_return = (results['capital'].iloc[-1] / 10000 - 1) * 100
completed_trades = trades.dropna(subset=['pnl'])
win_rate = (completed_trades['pnl'] > 0).mean() * 100
avg_win = completed_trades[completed_trades['pnl'] > 0]['pnl_pct'].mean() if len(completed_trades[completed_trades['pnl'] > 0]) > 0 else 0
avg_loss = completed_trades[completed_trades['pnl'] < 0]['pnl_pct'].mean() if len(completed_trades[completed_trades['pnl'] < 0]) > 0 else 0

print("=" * 60)
print("ZEBRA PUT STRATEGY BACKTEST RESULTS (2023-2024)")
print("=" * 60)
print(f"Initial Capital: $10,000")
print(f"Final Capital: ${results['capital'].iloc[-1]:,.2f}")
print(f"Total Return: {total_return:.1f}%")
print(f"Total Trades: {len(completed_trades)}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Avg Win: {avg_win:.1f}%")
print(f"Avg Loss: {avg_loss:.1f}%")
print(f"Max Drawdown: {((results['capital'].min() / 10000 - 1) * 100):.1f}%")

# %% [markdown]
# ## 5. Visualize Results

# %%
# Create visualization
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('Equity Curve', 'Trade P&L Distribution', 
                    'Monthly Returns', 'Win/Loss by Trade'),
    specs=[[{'type': 'scatter'}, {'type': 'histogram'}],
           [{'type': 'bar'}, {'type': 'bar'}]]
)

# Equity curve
fig.add_trace(
    go.Scatter(x=results['date'], y=results['capital'], 
               mode='lines', name='Portfolio Value',
               line=dict(color='purple', width=2)),
    row=1, col=1
)

# P&L distribution
if len(completed_trades) > 0:
    fig.add_trace(
        go.Histogram(x=completed_trades['pnl'], 
                     name='P&L Distribution',
                     marker_color='purple'),
        row=1, col=2
    )
    
    # Monthly returns
    completed_trades['month'] = pd.to_datetime(completed_trades['entry_date']).dt.to_period('M')
    monthly_pnl = completed_trades.groupby('month')['pnl'].sum()
    
    fig.add_trace(
        go.Bar(x=monthly_pnl.index.astype(str), y=monthly_pnl.values,
               name='Monthly P&L',
               marker_color=['red' if x < 0 else 'green' for x in monthly_pnl.values]),
        row=2, col=1
    )
    
    # Individual trade P&L
    fig.add_trace(
        go.Bar(x=list(range(len(completed_trades))), 
               y=completed_trades['pnl'].values,
               name='Trade P&L',
               marker_color=['red' if x < 0 else 'green' for x in completed_trades['pnl'].values]),
        row=2, col=2
    )

fig.update_layout(
    title='Zebra Put Strategy Performance (2023-2024)',
    showlegend=False,
    height=800
)

fig.show()

# %% [markdown]
# ## 6. Compare with SPY Performance

# %%
# Compare with SPY buy and hold
spy_prices = df[df['option_type'] == 'call'].groupby('date')['underlying_last'].first()
spy_start = spy_prices[spy_prices.index >= '2023-01-01'].iloc[0]
spy_end = spy_prices[spy_prices.index <= '2024-12-31'].iloc[-1]
spy_return = (spy_end / spy_start - 1) * 100

print("\n" + "=" * 60)
print("STRATEGY COMPARISON")
print("=" * 60)
print(f"Zebra Put Return: {total_return:.1f}%")
print(f"SPY Buy & Hold: {spy_return:.1f}%")
print(f"Outperformance: {total_return - spy_return:+.1f}%")
print("\n" + "=" * 60)

# %% [markdown]
# ## 7. Trade Analysis

# %%
# Detailed trade analysis
if len(completed_trades) > 0:
    print("\nDETAILED TRADE ANALYSIS")
    print("=" * 60)
    
    # Best and worst trades
    best_trade = completed_trades.nlargest(1, 'pnl').iloc[0]
    worst_trade = completed_trades.nsmallest(1, 'pnl').iloc[0]
    
    print(f"\nBest Trade:")
    print(f"  Entry: {best_trade['entry_date'].date()} @ ${best_trade['entry_price']:.2f}")
    print(f"  Exit: {best_trade['exit_date'].date()} @ ${best_trade['exit_price']:.2f}")
    print(f"  P&L: ${best_trade['pnl']:.2f} ({best_trade['pnl_pct']:.1f}%)")
    
    print(f"\nWorst Trade:")
    print(f"  Entry: {worst_trade['entry_date'].date()} @ ${worst_trade['entry_price']:.2f}")
    print(f"  Exit: {worst_trade['exit_date'].date()} @ ${worst_trade['exit_price']:.2f}")
    print(f"  P&L: ${worst_trade['pnl']:.2f} ({worst_trade['pnl_pct']:.1f}%)")
    
    # Average hold time
    avg_hold = completed_trades['days_held'].mean()
    print(f"\nAverage Hold Time: {avg_hold:.0f} days")
    
    # Risk metrics
    print(f"\nRisk Metrics:")
    print(f"  Avg Position Size: ${(completed_trades['position_cost'].mean()):.2f}")
    print(f"  Avg Delta Exposure: {completed_trades['net_delta'].mean():.0f} deltas")
    print(f"  Max Position Cost: ${completed_trades['position_cost'].max():.2f}")

# %% [markdown]
# ## Summary
# 
# ### Zebra Put Strategy Characteristics:
# 
# 1. **Synthetic Short Position**: Mimics being short 100 shares per contract
# 2. **Limited Risk**: Maximum loss is the initial debit paid
# 3. **No Margin Required**: Unlike actual short selling
# 4. **Embedded Stop Loss**: Risk is defined at entry
# 
# ### Key Insights:
# - Works best in bearish or volatile markets
# - Monthly entry provides systematic approach
# - Position sizing crucial (25% max per trade)
# - Exit at 21 DTE to avoid gamma risk
# 
# ### When to Use:
# - Bearish outlook on underlying
# - Want short exposure without margin
# - Prefer defined risk over unlimited risk
# - Expect moderate to large downward moves

# %%
print("\n" + "=" * 60)
print("ZEBRA PUT STRATEGY COMPLETE")
print("=" * 60)
print("\nKey Takeaways:")
print("• Provides synthetic short exposure with limited risk")
print("• No margin requirements or borrowing costs")
print("• Best suited for bearish market conditions")
print("• Risk/reward profile similar to buying puts but more capital efficient")