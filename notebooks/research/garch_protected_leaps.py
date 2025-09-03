# %%
"""
GARCH-Protected LEAP Strategy Research
=====================================
Strategy that uses GARCH volatility forecasting to provide smart protection 
for LEAP positions while preserving upside leverage.

Key Innovation:
- Buy LEAPs for leverage (no systematic call selling like PMCC)
- Use GARCH(1,1) to forecast volatility spikes
- Buy protective calls only when high volatility predicted
- Preserve upside while reducing downside volatility

Target: Higher Sharpe ratio than pure LEAPs with lower max drawdown
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Display settings
pd.set_option('display.float_format', '{:.2f}'.format)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 100)

print("="*60)
print("STRATEGY RESEARCH NOTEBOOK")
print("="*60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# %% [markdown]
# ## 1. Data Loading and Validation
# Always validate data format before processing

# %%
# Load SPY options data
data_path = 'daily_strategies/data/spy_options/'

# Select years to analyze
years = [2023, 2024]  # Modify as needed
dfs = []

for year in years:
    try:
        df_year = pd.read_parquet(f'{data_path}SPY_OPTIONS_{year}_COMPLETE.parquet')
        dfs.append(df_year)
        print(f"✓ Loaded {year}: {len(df_year):,} records")
    except FileNotFoundError:
        print(f"✗ {year} data not found")

# Combine all years
df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

if len(df) == 0:
    raise ValueError("No data loaded! Check data path and file names.")

print(f"\nTotal records loaded: {len(df):,}")

# %% [markdown]
# ## 2. Data Validation and Cleaning

# %%
# CRITICAL: Validate strike price format
print("\n" + "="*40)
print("DATA VALIDATION CHECKS")
print("="*40)

# Check 1: Strike prices (often in cents, need /1000)
strike_max = df['strike'].max()
if strike_max > 10000:
    print(f"⚠️  Strikes appear to be in cents (max: {strike_max})")
    print("   Converting to dollars...")
    df['strike'] = df['strike'] / 1000
    print(f"   New range: ${df['strike'].min():.0f} - ${df['strike'].max():.0f}")
else:
    print(f"✓ Strikes in dollars: ${df['strike'].min():.0f} - ${df['strike'].max():.0f}")

# Check 2: Date parsing
df['date'] = pd.to_datetime(df['date'])
df['expiration'] = pd.to_datetime(df['expiration'])
date_gaps = pd.date_range(df['date'].min(), df['date'].max(), freq='B')
missing_dates = set(date_gaps) - set(df['date'].unique())
print(f"✓ Date range: {df['date'].min().date()} to {df['date'].max().date()}")
if missing_dates:
    print(f"⚠️  Missing {len(missing_dates)} trading days")

# Check 3: Calculate derived fields
df['dte'] = (df['expiration'] - df['date']).dt.days
df['mid_price'] = (df['bid'] + df['ask']) / 2

# Check 4: Data quality
zero_bids = (df['bid'] == 0).sum()
zero_asks = (df['ask'] == 0).sum()
print(f"✓ Zero bids: {zero_bids:,} ({zero_bids/len(df)*100:.1f}%)")
print(f"✓ Zero asks: {zero_asks:,} ({zero_asks/len(df)*100:.1f}%)")

# Filter for valid data (keep for analysis but note the filtering)
df_clean = df[(df['bid'] > 0) & (df['volume'] > 0)].copy()
print(f"\n✓ After filtering: {len(df_clean):,} records ({len(df_clean)/len(df)*100:.1f}% retained)")

# Extract SPY prices
spy_prices = df_clean.groupby('date')['underlying_price'].first().reset_index()
spy_prices.columns = ['date', 'spy_price']
print(f"✓ SPY price range: ${spy_prices['spy_price'].min():.2f} - ${spy_prices['spy_price'].max():.2f}")

# %% [markdown]
# ## 3. Quick Data Exploration

# %%
# Show sample of option chain for most recent date
latest_date = df_clean['date'].max()
sample_chain = df_clean[
    (df_clean['date'] == latest_date) & 
    (df_clean['dte'] >= 30) & 
    (df_clean['dte'] <= 45) &
    (df_clean['right'] == 'C')
].sort_values('strike').head(10)

print(f"\nSample option chain for {latest_date.date()}:")
print(sample_chain[['strike', 'bid', 'ask', 'mid_price', 'delta', 'volume', 'dte']])

# %% [markdown]
# ## 4. Strategy Implementation
# Define your strategy logic here

# %%
class StrategyBacktest:
    """
    Template strategy class - modify for your specific strategy
    """
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.trades = []
        self.daily_values = []
        
        # TODO: Define strategy parameters
        self.param1 = None  # Example parameter
        self.param2 = None  # Example parameter
        
    def find_entry_candidates(self, df_date):
        """Find options that meet entry criteria"""
        # TODO: Implement entry logic
        pass
        
    def manage_positions(self, df_date, current_date):
        """Manage existing positions"""
        # TODO: Implement position management
        pass
        
    def calculate_portfolio_value(self, df_date):
        """Calculate current portfolio value"""
        # TODO: Implement portfolio valuation
        return self.capital
        
    def run_backtest(self, df):
        """Run the backtest across all dates"""
        dates = sorted(df['date'].unique())
        
        for date in dates:
            df_date = df[df['date'] == date].copy()
            spy_price = df_date['underlying_price'].iloc[0]
            
            # Manage existing positions
            self.manage_positions(df_date, date)
            
            # Look for new entries
            self.find_entry_candidates(df_date)
            
            # Calculate portfolio value
            total_value = self.calculate_portfolio_value(df_date)
            
            # Record daily values
            self.daily_values.append({
                'date': date,
                'spy_price': spy_price,
                'total_value': total_value,
                'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100
            })
            
        return pd.DataFrame(self.daily_values)

# %% [markdown]
# ## 5. Run Backtest

# %%
# Initialize and run strategy
print("\n" + "="*40)
print("RUNNING BACKTEST")
print("="*40)

strategy = StrategyBacktest(initial_capital=10000)
results = strategy.run_backtest(df_clean)

if len(results) > 0:
    print(f"✓ Backtest complete: {len(results)} days")
    print(f"  Final value: ${results['total_value'].iloc[-1]:,.2f}")
    print(f"  Total return: {results['return_pct'].iloc[-1]:.2f}%")
else:
    print("⚠️  No results generated - check strategy implementation")

# %% [markdown]
# ## 6. Benchmark Comparison

# %%
# Calculate SPY buy-and-hold benchmark
initial_capital = 10000
spy_start = spy_prices['spy_price'].iloc[0]
spy_shares = initial_capital / spy_start

spy_benchmark = spy_prices.copy()
spy_benchmark['portfolio_value'] = spy_benchmark['spy_price'] * spy_shares
spy_benchmark['return_pct'] = (spy_benchmark['portfolio_value'] - initial_capital) / initial_capital * 100

print("\n" + "="*40)
print("BENCHMARK COMPARISON")
print("="*40)
print(f"SPY Buy & Hold:")
print(f"  Final value: ${spy_benchmark['portfolio_value'].iloc[-1]:,.2f}")
print(f"  Total return: {spy_benchmark['return_pct'].iloc[-1]:.2f}%")

# %% [markdown]
# ## 7. Visualization

# %%
# Create comparison chart
if len(results) > 0:
    fig = go.Figure()
    
    # Add strategy line
    fig.add_trace(go.Scatter(
        x=results['date'],
        y=results['total_value'],
        mode='lines',
        name='Strategy',
        line=dict(color='green', width=2)
    ))
    
    # Add SPY benchmark
    fig.add_trace(go.Scatter(
        x=spy_benchmark['date'],
        y=spy_benchmark['portfolio_value'],
        mode='lines',
        name='SPY Buy & Hold',
        line=dict(color='blue', width=2)
    ))
    
    # Add initial capital reference
    fig.add_hline(y=initial_capital, line_dash="dash", line_color="gray", 
                  annotation_text="Initial Capital")
    
    fig.update_layout(
        title='Strategy vs SPY Buy & Hold',
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        hovermode='x unified',
        height=500
    )
    
    fig.show()

# %% [markdown]
# ## 8. Performance Metrics

# %%
def calculate_metrics(returns_series):
    """Calculate standard performance metrics"""
    metrics = {}
    
    # Basic returns
    metrics['total_return'] = returns_series.iloc[-1] if len(returns_series) > 0 else 0
    
    # Daily returns for risk metrics
    daily_returns = returns_series.pct_change().dropna()
    
    if len(daily_returns) > 0:
        metrics['sharpe'] = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
        metrics['max_dd'] = (returns_series / returns_series.cummax() - 1).min() * 100
        metrics['volatility'] = daily_returns.std() * np.sqrt(252) * 100
    else:
        metrics['sharpe'] = 0
        metrics['max_dd'] = 0
        metrics['volatility'] = 0
    
    return metrics

if len(results) > 0:
    strategy_metrics = calculate_metrics(results['total_value'])
    spy_metrics = calculate_metrics(spy_benchmark['portfolio_value'])
    
    print("\n" + "="*40)
    print("PERFORMANCE METRICS")
    print("="*40)
    print(f"{'Metric':<20} {'Strategy':>12} {'SPY':>12}")
    print("-"*44)
    print(f"{'Total Return':<20} {results['return_pct'].iloc[-1]:>11.1f}% {spy_benchmark['return_pct'].iloc[-1]:>11.1f}%")
    print(f"{'Sharpe Ratio':<20} {strategy_metrics['sharpe']:>12.2f} {spy_metrics['sharpe']:>12.2f}")
    print(f"{'Max Drawdown':<20} {strategy_metrics['max_dd']:>11.1f}% {spy_metrics['max_dd']:>11.1f}%")
    print(f"{'Volatility':<20} {strategy_metrics['volatility']:>11.1f}% {spy_metrics['volatility']:>11.1f}%")

# %% [markdown]
# ## 9. Trade Analysis

# %%
if len(strategy.trades) > 0:
    trades_df = pd.DataFrame(strategy.trades)
    
    print("\n" + "="*40)
    print("TRADE ANALYSIS")
    print("="*40)
    print(f"Total trades: {len(trades_df)}")
    
    # TODO: Add trade-specific analysis
    # Example:
    # - Win rate
    # - Average profit/loss
    # - Trade frequency
    # - Best/worst trades

# %% [markdown]
# ## 10. Conclusions and Next Steps

# %%
print("\n" + "="*60)
print("RESEARCH SUMMARY")
print("="*60)
print("""
Key Findings:
1. [TODO: Add finding 1]
2. [TODO: Add finding 2]
3. [TODO: Add finding 3]

Next Steps:
1. [TODO: Next research step]
2. [TODO: Parameter optimization]
3. [TODO: Risk analysis]

Notes:
- [TODO: Any important observations]
- [TODO: Data quality issues found]
- [TODO: Strategy limitations]
""")

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")