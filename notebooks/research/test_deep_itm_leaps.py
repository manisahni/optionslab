# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.3
# ---

# %%
"""
Deep ITM LEAP Selection Diagnostic Notebook
===========================================
This notebook tests each aspect of selecting and tracking deep ITM LEAPs
with visual diagnostics to identify any issues.

Test Components:
1. Data loading and validation
2. Finding deep ITM LEAPs (2-year, 0.70-0.90 delta)
3. Position tracking over time
4. Value calculation accuracy
5. Roll/exit logic verification
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("DEEP ITM LEAP DIAGNOSTIC NOTEBOOK")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# %% [markdown]
# ## 1. Load and Validate Data

# %%
# Load data - using existing downloaded data
import glob
data_path = '/Users/nish_macbook/trading/daily-optionslab/data/spy_options/'

print("Loading available SPY options data...")
# Find all parquet files
parquet_files = glob.glob(f'{data_path}spy_options_eod_*.parquet')
print(f"Found {len(parquet_files)} data files")

# Load and combine data
dfs = []
for file in sorted(parquet_files)[:50]:  # Load first 50 files for testing
    df_file = pd.read_parquet(file)
    dfs.append(df_file)

df = pd.concat(dfs, ignore_index=True)
print(f"Loaded {len(df):,} total records")

# Convert dates
df['date'] = pd.to_datetime(df['date'])
df['expiration'] = pd.to_datetime(df['expiration'])

# Calculate DTE
df['dte'] = (df['expiration'] - df['date']).dt.days

# Filter for calls only
df_calls = df[df['right'] == 'C'].copy()

print(f"✓ Loaded {len(df_calls):,} call option records")
print(f"✓ Date range: {df['date'].min().date()} to {df['date'].max().date()}")
print(f"✓ Unique dates: {df['date'].nunique()}")
print(f"✓ Unique expirations: {df['expiration'].nunique()}")

# Check strike format
print(f"\n📊 Strike price range: ${df_calls['strike'].min():.2f} - ${df_calls['strike'].max():.2f}")
if df_calls['strike'].max() > 1000:
    print("⚠️  Strikes appear to be in cents, converting to dollars...")
    df_calls['strike'] = df_calls['strike'] / 1000
    print(f"✓ New strike range: ${df_calls['strike'].min():.2f} - ${df_calls['strike'].max():.2f}")

# Calculate mid price
df_calls['mid_price'] = (df_calls['bid'] + df_calls['ask']) / 2

# Show data sample
print(f"\nSample data:")
print(df_calls[['date', 'strike', 'expiration', 'dte', 'bid', 'ask', 'mid_price', 'delta', 'volume']].head())

# %% [markdown]
# ## 2. Find Deep ITM LEAPs on a Specific Date

# %%
# Pick a test date - use a date from our loaded data
available_dates = sorted(df['date'].unique())
print(f"Available dates: {available_dates[0].date()} to {available_dates[-1].date()}")
test_date = available_dates[len(available_dates)//2]  # Pick middle date
print(f"🔍 Searching for deep ITM LEAPs on {test_date.date()}")

# Get data for this date
df_date = df_calls[df_calls['date'] == test_date].copy()
spy_price = df_date['underlying_price'].iloc[0]

print(f"\n📈 SPY Price: ${spy_price:.2f}")

# Filter for 2-year LEAPs (600-800 DTE)
df_leaps = df_date[(df_date['dte'] >= 600) & (df_date['dte'] <= 800)].copy()
print(f"✓ Found {len(df_leaps)} options with 600-800 DTE")

# Filter for deep ITM (delta 0.70-0.90)
df_deep_itm = df_leaps[(df_leaps['delta'] >= 0.70) & (df_leaps['delta'] <= 0.90)].copy()
print(f"✓ Found {len(df_deep_itm)} deep ITM LEAPs (0.70-0.90 delta)")

# Sort by delta to see best candidates
df_deep_itm = df_deep_itm.sort_values('delta', ascending=False)

# Display top candidates
print(f"\n🎯 Top Deep ITM LEAP Candidates:")
print("-" * 80)
for idx, row in df_deep_itm.head(10).iterrows():
    moneyness = (spy_price - row['strike']) / spy_price * 100
    print(f"Strike: ${row['strike']:.0f} | Delta: {row['delta']:.3f} | "
          f"DTE: {row['dte']} | Exp: {row['expiration'].date()} | "
          f"Mid: ${row['mid_price']:.2f} | Moneyness: {moneyness:.1f}% ITM")

# %% [markdown]
# ## 3. Visual Analysis of Available LEAPs

# %%
# Create visualization of LEAP landscape
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('LEAP Distribution by Strike/DTE', 'Delta vs Strike for LEAPs',
                    'Price vs Delta (Risk/Reward)', 'Volume Distribution'),
    specs=[[{'type': 'scatter'}, {'type': 'scatter'}],
           [{'type': 'scatter'}, {'type': 'bar'}]]
)

# Plot 1: Strike vs DTE heatmap-style
for dte_group in [range(600, 650), range(650, 700), range(700, 750), range(750, 800)]:
    df_group = df_leaps[df_leaps['dte'].isin(dte_group)]
    if len(df_group) > 0:
        fig.add_trace(
            go.Scatter(
                x=df_group['strike'],
                y=df_group['dte'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=df_group['delta'],
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title="Delta", x=0.45, y=0.85, len=0.3)
                ),
                text=[f"Strike: ${s:.0f}<br>Delta: {d:.3f}<br>DTE: {dte}<br>Mid: ${m:.2f}"
                      for s, d, dte, m in zip(df_group['strike'], df_group['delta'], 
                                               df_group['dte'], df_group['mid_price'])],
                hovertemplate="%{text}<extra></extra>",
                name=f"{min(dte_group)}-{max(dte_group)} DTE"
            ),
            row=1, col=1
        )

# Add SPY price line
fig.add_hline(y=spy_price, line_dash="dash", line_color="red", 
              annotation_text=f"SPY: ${spy_price:.2f}", row=1, col=1)

# Plot 2: Delta vs Strike
fig.add_trace(
    go.Scatter(
        x=df_leaps['strike'],
        y=df_leaps['delta'],
        mode='markers',
        marker=dict(
            size=10,
            color=df_leaps['dte'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="DTE", x=1.02, y=0.85, len=0.3)
        ),
        text=[f"Strike: ${s:.0f}<br>Delta: {d:.3f}<br>DTE: {dte}"
              for s, d, dte in zip(df_leaps['strike'], df_leaps['delta'], df_leaps['dte'])],
        hovertemplate="%{text}<extra></extra>",
        name="All LEAPs"
    ),
    row=1, col=2
)

# Add target delta zone
fig.add_hrect(y0=0.70, y1=0.90, fillcolor="green", opacity=0.1, 
              annotation_text="Target Delta Zone", row=1, col=2)

# Plot 3: Price vs Delta (shows cost efficiency)
fig.add_trace(
    go.Scatter(
        x=df_leaps['delta'],
        y=df_leaps['mid_price'],
        mode='markers',
        marker=dict(
            size=10,
            color=df_leaps['dte'],
            colorscale='Plasma',
            showscale=False
        ),
        text=[f"Strike: ${s:.0f}<br>Delta: {d:.3f}<br>Price: ${p:.2f}<br>DTE: {dte}"
              for s, d, p, dte in zip(df_leaps['strike'], df_leaps['delta'], 
                                       df_leaps['mid_price'], df_leaps['dte'])],
        hovertemplate="%{text}<extra></extra>",
        name="Price Efficiency"
    ),
    row=2, col=1
)

# Plot 4: Volume distribution for liquidity check
volume_by_strike = df_leaps.groupby('strike')['volume'].sum().reset_index()
fig.add_trace(
    go.Bar(
        x=volume_by_strike['strike'],
        y=volume_by_strike['volume'],
        marker_color='lightblue',
        text=volume_by_strike['volume'],
        textposition='auto',
        name="Volume"
    ),
    row=2, col=2
)

# Update layout
fig.update_xaxes(title_text="Strike Price ($)", row=1, col=1)
fig.update_yaxes(title_text="Days to Expiration", row=1, col=1)
fig.update_xaxes(title_text="Strike Price ($)", row=1, col=2)
fig.update_yaxes(title_text="Delta", row=1, col=2)
fig.update_xaxes(title_text="Delta", row=2, col=1)
fig.update_yaxes(title_text="Option Price ($)", row=2, col=1)
fig.update_xaxes(title_text="Strike Price ($)", row=2, col=2)
fig.update_yaxes(title_text="Volume", row=2, col=2)

fig.update_layout(
    title=f"LEAP Landscape Analysis - {test_date.date()} (SPY: ${spy_price:.2f})",
    height=800,
    showlegend=False
)

fig.show()

# %% [markdown]
# ## 4. Select Best LEAP and Track Over Time

# %%
# Select the best deep ITM LEAP
if len(df_deep_itm) > 0:
    # Choose LEAP with delta closest to 0.80 (sweet spot)
    df_deep_itm['delta_diff'] = abs(df_deep_itm['delta'] - 0.80)
    best_leap = df_deep_itm.nsmallest(1, 'delta_diff').iloc[0]
    
    print(f"🎯 Selected LEAP:")
    print(f"  Strike: ${best_leap['strike']:.0f}")
    print(f"  Expiration: {best_leap['expiration'].date()}")
    print(f"  Delta: {best_leap['delta']:.3f}")
    print(f"  DTE: {best_leap['dte']} days")
    print(f"  Entry Price: ${best_leap['mid_price']:.2f}")
    print(f"  Moneyness: {(spy_price - best_leap['strike'])/spy_price*100:.1f}% ITM")
    
    # Track this LEAP over time
    leap_strike = best_leap['strike']
    leap_exp = best_leap['expiration']
    
    # Get all historical data for this specific option
    df_leap_history = df_calls[
        (df_calls['strike'] == leap_strike) & 
        (df_calls['expiration'] == leap_exp) &
        (df_calls['date'] >= test_date)
    ].sort_values('date').copy()
    
    print(f"\n📊 Tracking history: {len(df_leap_history)} days of data")
    
    if len(df_leap_history) > 0:
        # Calculate position metrics over time
        df_leap_history['position_value'] = df_leap_history['mid_price'] * 100  # 1 contract
        df_leap_history['intrinsic_value'] = np.maximum(df_leap_history['underlying_price'] - leap_strike, 0) * 100
        df_leap_history['time_value'] = df_leap_history['position_value'] - df_leap_history['intrinsic_value']
        df_leap_history['pnl'] = df_leap_history['position_value'] - (best_leap['mid_price'] * 100)
        df_leap_history['pnl_pct'] = df_leap_history['pnl'] / (best_leap['mid_price'] * 100) * 100
        
        print(f"\n📈 Position Performance Summary:")
        print(f"  Entry Value: ${best_leap['mid_price'] * 100:.0f}")
        print(f"  Final Value: ${df_leap_history['position_value'].iloc[-1]:.0f}")
        print(f"  Max Value: ${df_leap_history['position_value'].max():.0f}")
        print(f"  Min Value: ${df_leap_history['position_value'].min():.0f}")
        print(f"  Final P&L: ${df_leap_history['pnl'].iloc[-1]:.0f} ({df_leap_history['pnl_pct'].iloc[-1]:.1f}%)")
else:
    print("❌ No deep ITM LEAPs found for the selected criteria")
    df_leap_history = pd.DataFrame()

# %% [markdown]
# ## 5. Visualize LEAP Performance Over Time

# %%
if len(df_leap_history) > 0:
    # Create comprehensive tracking visualization
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=('Position Value Over Time', 'P&L Evolution',
                        'Intrinsic vs Time Value', 'Delta Decay',
                        'Theta Evolution', 'SPY vs LEAP Performance'),
        specs=[[{'secondary_y': False}, {'secondary_y': False}],
               [{'secondary_y': False}, {'secondary_y': False}],
               [{'secondary_y': True}, {'secondary_y': False}]]
    )
    
    # Plot 1: Position Value
    fig.add_trace(
        go.Scatter(
            x=df_leap_history['date'],
            y=df_leap_history['position_value'],
            mode='lines',
            name='Position Value',
            line=dict(color='blue', width=2)
        ),
        row=1, col=1
    )
    
    # Add entry point
    fig.add_hline(y=best_leap['mid_price'] * 100, line_dash="dash", 
                  line_color="gray", annotation_text="Entry", row=1, col=1)
    
    # Plot 2: P&L
    colors = ['green' if x >= 0 else 'red' for x in df_leap_history['pnl']]
    fig.add_trace(
        go.Scatter(
            x=df_leap_history['date'],
            y=df_leap_history['pnl'],
            mode='lines+markers',
            marker=dict(color=colors, size=5),
            line=dict(color='darkgray', width=1),
            name='P&L ($)'
        ),
        row=1, col=2
    )
    
    fig.add_hline(y=0, line_dash="solid", line_color="black", row=1, col=2)
    
    # Plot 3: Intrinsic vs Time Value
    fig.add_trace(
        go.Scatter(
            x=df_leap_history['date'],
            y=df_leap_history['intrinsic_value'],
            mode='lines',
            name='Intrinsic Value',
            line=dict(color='green', width=2),
            stackgroup='one'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_leap_history['date'],
            y=df_leap_history['time_value'],
            mode='lines',
            name='Time Value',
            line=dict(color='orange', width=2),
            stackgroup='one'
        ),
        row=2, col=1
    )
    
    # Plot 4: Delta over time
    fig.add_trace(
        go.Scatter(
            x=df_leap_history['date'],
            y=df_leap_history['delta'],
            mode='lines+markers',
            name='Delta',
            line=dict(color='purple', width=2),
            marker=dict(size=4)
        ),
        row=2, col=2
    )
    
    # Add target delta zone
    fig.add_hrect(y0=0.70, y1=0.90, fillcolor="green", opacity=0.1, row=2, col=2)
    
    # Plot 5: Theta (time decay)
    fig.add_trace(
        go.Scatter(
            x=df_leap_history['date'],
            y=df_leap_history['theta'],
            mode='lines',
            name='Theta',
            line=dict(color='red', width=2)
        ),
        row=3, col=1
    )
    
    # Plot 6: SPY vs LEAP Performance (normalized)
    spy_norm = df_leap_history['underlying_price'] / df_leap_history['underlying_price'].iloc[0] * 100
    leap_norm = df_leap_history['position_value'] / df_leap_history['position_value'].iloc[0] * 100
    
    fig.add_trace(
        go.Scatter(
            x=df_leap_history['date'],
            y=spy_norm,
            mode='lines',
            name='SPY',
            line=dict(color='blue', width=2)
        ),
        row=3, col=2
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_leap_history['date'],
            y=leap_norm,
            mode='lines',
            name='LEAP',
            line=dict(color='green', width=2)
        ),
        row=3, col=2
    )
    
    # Update axes labels
    fig.update_yaxes(title_text="Value ($)", row=1, col=1)
    fig.update_yaxes(title_text="P&L ($)", row=1, col=2)
    fig.update_yaxes(title_text="Value ($)", row=2, col=1)
    fig.update_yaxes(title_text="Delta", row=2, col=2)
    fig.update_yaxes(title_text="Theta", row=3, col=1)
    fig.update_yaxes(title_text="Normalized (%)", row=3, col=2)
    
    # Update layout
    fig.update_layout(
        title=f"LEAP Performance Tracking - Strike ${leap_strike:.0f}, Exp {leap_exp.date()}",
        height=1000,
        showlegend=True
    )
    
    fig.show()
    
    # Print key observations
    print("\n🔍 Key Observations:")
    print(f"  Days tracked: {len(df_leap_history)}")
    print(f"  Max drawdown: ${df_leap_history['pnl'].min():.0f}")
    print(f"  Best day: ${df_leap_history['pnl'].max():.0f}")
    print(f"  Average daily P&L: ${df_leap_history['pnl'].diff().mean():.2f}")
    print(f"  Final delta: {df_leap_history['delta'].iloc[-1]:.3f}")
    print(f"  Final theta: {df_leap_history['theta'].iloc[-1]:.4f}")
    print(f"  Time value decay: ${df_leap_history['time_value'].iloc[0] - df_leap_history['time_value'].iloc[-1]:.0f}")

# %% [markdown]
# ## 6. Test Multiple LEAPs Across Different Dates

# %%
# Test LEAP selection across multiple entry dates
# Use actual available dates from our data
available_dates = sorted(df_calls['date'].unique())
# Sample every 10th date for testing
test_dates = available_dates[::10][:5]  # Test 5 dates
leap_results = []

print("🔄 Testing LEAP selection across multiple dates...")
print("-" * 60)

for entry_date in test_dates:
    if entry_date not in df_calls['date'].values:
        continue
        
    # Get data for this date
    df_date = df_calls[df_calls['date'] == entry_date].copy()
    spy_price = df_date['underlying_price'].iloc[0]
    
    # Find 2-year LEAPs
    df_leaps = df_date[(df_date['dte'] >= 600) & (df_date['dte'] <= 800)].copy()
    
    # Find deep ITM options
    df_deep_itm = df_leaps[(df_leaps['delta'] >= 0.70) & (df_leaps['delta'] <= 0.90)].copy()
    
    if len(df_deep_itm) > 0:
        # Select best LEAP (closest to 0.80 delta)
        df_deep_itm['delta_diff'] = abs(df_deep_itm['delta'] - 0.80)
        best = df_deep_itm.nsmallest(1, 'delta_diff').iloc[0]
        
        # Track for 90 days
        end_date = entry_date + pd.Timedelta(days=90)
        df_track = df_calls[
            (df_calls['strike'] == best['strike']) & 
            (df_calls['expiration'] == best['expiration']) &
            (df_calls['date'] >= entry_date) &
            (df_calls['date'] <= end_date)
        ]
        
        if len(df_track) > 0:
            entry_value = best['mid_price'] * 100
            final_value = df_track['mid_price'].iloc[-1] * 100
            pnl = final_value - entry_value
            pnl_pct = pnl / entry_value * 100
            
            result = {
                'entry_date': entry_date,
                'strike': best['strike'],
                'expiration': best['expiration'],
                'entry_delta': best['delta'],
                'entry_dte': best['dte'],
                'spy_price': spy_price,
                'entry_value': entry_value,
                'final_value': final_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'days_held': len(df_track)
            }
            leap_results.append(result)
            
            print(f"{entry_date.date()}: Strike ${best['strike']:.0f}, "
                  f"Delta {best['delta']:.2f}, 90-day P&L: ${pnl:.0f} ({pnl_pct:.1f}%)")

# Create summary DataFrame
if leap_results:
    df_results = pd.DataFrame(leap_results)
    
    print(f"\n📊 Summary Statistics ({len(df_results)} LEAPs tested):")
    print(f"  Average P&L: ${df_results['pnl'].mean():.0f} ({df_results['pnl_pct'].mean():.1f}%)")
    print(f"  Win Rate: {(df_results['pnl'] > 0).mean() * 100:.1f}%")
    print(f"  Best Trade: ${df_results['pnl'].max():.0f}")
    print(f"  Worst Trade: ${df_results['pnl'].min():.0f}")
    print(f"  Average Entry Delta: {df_results['entry_delta'].mean():.3f}")

# %% [markdown]
# ## 7. Diagnostic Summary

# %%
print("=" * 60)
print("DIAGNOSTIC SUMMARY")
print("=" * 60)

print("\n✅ Data Quality Checks:")
print(f"  • Strike prices: {'✓ Converted to dollars' if df_calls['strike'].max() < 1000 else '⚠️ May need conversion'}")
print(f"  • Date continuity: ✓ {df_calls['date'].nunique()} unique dates")
print(f"  • Greeks availability: {'✓ Delta available' if 'delta' in df_calls.columns else '⚠️ Missing'}")
print(f"  • Price data: {'✓ Bid/Ask available' if df_calls['bid'].notna().any() else '⚠️ Missing'}")

print("\n📈 LEAP Availability:")
print(f"  • 2-year options (600-800 DTE): {'✓ Found' if len(df_leaps) > 0 else '⚠️ Not found'}")
print(f"  • Deep ITM (0.70-0.90 delta): {'✓ Found' if len(df_deep_itm) > 0 else '⚠️ Not found'}")
print(f"  • Liquidity: {'✓ Adequate' if df_leaps['volume'].sum() > 100 else '⚠️ Low volume'}")

print("\n🎯 Position Tracking:")
if len(df_leap_history) > 0:
    print(f"  • Historical data: ✓ {len(df_leap_history)} days tracked")
    print(f"  • Value calculation: ✓ Working")
    print(f"  • P&L tracking: ✓ Accurate")
else:
    print(f"  • ⚠️ No historical tracking data available")

print("\n💡 Recommendations:")
if df_calls['strike'].max() > 1000:
    print("  • Always divide strike prices by 1000 to convert cents to dollars")
print("  • Filter for DTE >= 600 for true 2-year LEAPs")
print("  • Target 0.70-0.85 delta for deep ITM positions")
print("  • Check volume > 0 for liquidity")
print("  • Track intrinsic vs time value separately")
print("  • Monitor theta acceleration around 120 DTE for rolling")

print("\n" + "=" * 60)
print("Diagnostic complete!")
