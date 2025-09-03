# %%
"""
Fixed Simple PMCC Strategy with Correct Strike Selection
- Buy deep ITM LEAP (strike 15-20% below SPY price)
- Roll when 6 months remain to expiration
- Consistently sell 30-45 DTE short calls
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

pd.set_option('display.max_columns', None)
pd.set_option('display.float_format', '{:.2f}'.format)

print("Fixed PMCC Strategy with Correct Strike Selection")
print("="*50)

# %%
# Load SPY options data
print("Loading data...")
data_path = '../daily_strategies/data/spy_options/'

# Load 2023 and 2024 data
df_2023 = pd.read_parquet(f'{data_path}SPY_OPTIONS_2023_COMPLETE.parquet')
df_2024 = pd.read_parquet(f'{data_path}SPY_OPTIONS_2024_COMPLETE.parquet')

# Combine and prepare data
df = pd.concat([df_2023, df_2024], ignore_index=True)
df['date'] = pd.to_datetime(df['date'])
df['expiration'] = pd.to_datetime(df['expiration'])
df['dte'] = (df['expiration'] - df['date']).dt.days
df['mid_price'] = (df['bid'] + df['ask']) / 2

# IMPORTANT: Convert strike prices from cents to dollars
df['strike'] = df['strike'] / 1000  # Convert from cents to dollars

# Filter for valid data
df = df[(df['bid'] > 0) & (df['ask'] > 0) & (df['volume'] > 0)]

print(f"Data loaded: {len(df):,} option records")
print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")

# Verify strike conversion
print(f"Strike range: ${df['strike'].min():.0f} to ${df['strike'].max():.0f}")

# Get SPY prices
spy_prices = df.groupby('date')['underlying_price'].first().reset_index()
spy_prices.columns = ['date', 'spy_price']
spy_prices = spy_prices.sort_values('date')

print(f"SPY price range: ${spy_prices['spy_price'].min():.2f} to ${spy_prices['spy_price'].max():.2f}")

# %%
class FixedPMCC:
    """Fixed PMCC strategy with correct strike selection"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.leap = None
        self.short_call = None
        self.trades = []
        self.daily_values = []
        
        # LEAP parameters - Deep ITM
        self.leap_moneyness = 0.85  # Buy at 85% of SPY price (15% ITM)
        self.leap_dte_min = 365      # At least 12 months
        self.leap_dte_max = 450      # Max 15 months
        self.leap_roll_dte = 180     # Roll at 6 months
        
        # Short call parameters
        self.short_moneyness = 1.02  # Sell at 102% of SPY (2% OTM)
        self.short_dte_min = 30
        self.short_dte_max = 45
        
        # Management
        self.short_profit_target = 0.50  # 50% profit
        self.short_roll_dte = 21         # Roll at 21 days
        
    def find_leap(self, df_date, spy_price):
        """Find deep ITM LEAP - strike should be 15% below SPY"""
        target_strike = spy_price * self.leap_moneyness  # 85% of SPY price
        
        # Find calls that are deep ITM
        candidates = df_date[
            (df_date['right'] == 'C') &
            (df_date['dte'] >= self.leap_dte_min) &
            (df_date['dte'] <= self.leap_dte_max) &
            (df_date['strike'] <= target_strike) &  # Deep ITM
            (df_date['strike'] >= target_strike * 0.9) &  # Not too deep
            (df_date['volume'] > 0)
        ].copy()
        
        if len(candidates) == 0:
            # Expand search if needed
            candidates = df_date[
                (df_date['right'] == 'C') &
                (df_date['dte'] >= self.leap_dte_min - 30) &
                (df_date['dte'] <= self.leap_dte_max + 30) &
                (df_date['strike'] <= spy_price * 0.90) &  # At least 10% ITM
                (df_date['volume'] > 0)
            ].copy()
        
        if len(candidates) == 0:
            return None
            
        # Select strike closest to target (85% of SPY)
        candidates['strike_diff'] = abs(candidates['strike'] - target_strike)
        best = candidates.nsmallest(1, 'strike_diff').iloc[0]
        
        # Verify it's actually ITM
        if best['strike'] > spy_price:
            print(f"  WARNING: Selected strike ${best['strike']:.0f} is OTM (SPY=${spy_price:.2f})")
            return None
            
        return best
    
    def find_short_call(self, df_date, spy_price, leap_strike):
        """Find short call - slightly OTM"""
        target_strike = spy_price * self.short_moneyness  # 2% OTM
        
        candidates = df_date[
            (df_date['right'] == 'C') &
            (df_date['strike'] > leap_strike) &  # Above LEAP strike
            (df_date['strike'] >= target_strike * 0.98) &  # Near target
            (df_date['strike'] <= target_strike * 1.05) &  # Not too far OTM
            (df_date['dte'] >= self.short_dte_min) &
            (df_date['dte'] <= self.short_dte_max) &
            (df_date['volume'] > 0)
        ].copy()
        
        if len(candidates) == 0:
            # Expand search
            candidates = df_date[
                (df_date['right'] == 'C') &
                (df_date['strike'] > leap_strike) &
                (df_date['strike'] > spy_price) &  # At least OTM
                (df_date['dte'] >= self.short_dte_min - 5) &
                (df_date['dte'] <= self.short_dte_max + 10) &
                (df_date['volume'] > 0)
            ].copy()
        
        if len(candidates) == 0:
            return None
            
        # Select strike closest to target
        candidates['strike_diff'] = abs(candidates['strike'] - target_strike)
        return candidates.nsmallest(1, 'strike_diff').iloc[0]
    
    def get_option_value(self, df_date, position):
        """Get current value of an option position"""
        if position is None:
            return 0
            
        matches = df_date[
            (df_date['strike'] == position['strike']) &
            (df_date['expiration'] == position['expiration']) &
            (df_date['right'] == 'C')
        ]
        
        if len(matches) == 0:
            # Option expired or not found - use intrinsic value
            spy_price = df_date['underlying_price'].iloc[0]
            intrinsic = max(0, spy_price - position['strike'])
            return intrinsic * 100
            
        # Use bid for selling, ask for buying back
        if position['type'] == 'leap':
            return matches.iloc[0]['bid'] * 100  # We'd sell at bid
        else:  # short call
            return matches.iloc[0]['ask'] * 100  # We'd buy back at ask
    
    def should_roll_leap(self, date):
        """Check if LEAP should be rolled (6 months or less remaining)"""
        if self.leap is None:
            return False
        dte = (self.leap['expiration'] - date).days
        return dte <= self.leap_roll_dte
    
    def roll_leap(self, df_date, date, spy_price):
        """Roll LEAP to new position"""
        # Close current LEAP
        leap_value = self.get_option_value(df_date, self.leap)
        self.capital += leap_value
        
        old_strike = self.leap['strike']
        self.trades.append({
            'date': date,
            'action': 'SELL LEAP (ROLL)',
            'strike': old_strike,
            'expiration': self.leap['expiration'],
            'proceeds': leap_value,
            'spy_price': spy_price,
            'dte_remaining': (self.leap['expiration'] - date).days
        })
        
        # Buy new LEAP
        new_leap = self.find_leap(df_date, spy_price)
        if new_leap is not None:
            cost = new_leap['ask'] * 100
            if cost <= self.capital:
                self.leap = {
                    'type': 'leap',
                    'strike': new_leap['strike'],
                    'expiration': new_leap['expiration'],
                    'entry_date': date,
                    'entry_price': new_leap['ask'],
                    'delta': new_leap['delta'] if 'delta' in new_leap.index else np.nan
                }
                self.capital -= cost
                
                self.trades.append({
                    'date': date,
                    'action': 'BUY LEAP (ROLL)',
                    'strike': new_leap['strike'],
                    'expiration': new_leap['expiration'],
                    'cost': cost,
                    'spy_price': spy_price,
                    'moneyness': new_leap['strike'] / spy_price,
                    'dte': new_leap['dte']
                })
                
                print(f"  Rolled: ${old_strike:.0f} -> ${new_leap['strike']:.0f} (SPY=${spy_price:.2f})")
                return True
        
        self.leap = None
        return False
    
    def run_backtest(self, df):
        """Run the fixed PMCC backtest"""
        dates = sorted(df['date'].unique())
        
        for i, date in enumerate(dates):
            df_date = df[df['date'] == date].copy()
            spy_price = df_date['underlying_price'].iloc[0]
            
            # Initialize or roll LEAP
            if self.leap is None:
                # Buy initial LEAP
                leap_option = self.find_leap(df_date, spy_price)
                if leap_option is not None:
                    cost = leap_option['ask'] * 100
                    if cost <= self.capital:
                        self.leap = {
                            'type': 'leap',
                            'strike': leap_option['strike'],
                            'expiration': leap_option['expiration'],
                            'entry_date': date,
                            'entry_price': leap_option['ask'],
                            'delta': leap_option['delta'] if 'delta' in leap_option.index else np.nan
                        }
                        self.capital -= cost
                        
                        self.trades.append({
                            'date': date,
                            'action': 'BUY LEAP',
                            'strike': leap_option['strike'],
                            'expiration': leap_option['expiration'],
                            'cost': cost,
                            'spy_price': spy_price,
                            'moneyness': leap_option['strike'] / spy_price,
                            'dte': leap_option['dte']
                        })
                        
                        print(f"Initial LEAP: Strike ${leap_option['strike']:.0f}, SPY ${spy_price:.2f}, Moneyness {leap_option['strike']/spy_price:.1%}")
            
            elif self.should_roll_leap(date):
                # Roll LEAP when 6 months remain
                self.roll_leap(df_date, date, spy_price)
            
            # Manage short calls if we have a LEAP
            if self.leap is not None:
                # Check if short call expired
                if self.short_call is not None:
                    if self.short_call['expiration'] <= date:
                        # Expired worthless - good for us!
                        self.short_call = None
                    else:
                        # Check if should close short call
                        short_dte = (self.short_call['expiration'] - date).days
                        
                        # Get current price
                        matches = df_date[
                            (df_date['strike'] == self.short_call['strike']) &
                            (df_date['expiration'] == self.short_call['expiration']) &
                            (df_date['right'] == 'C')
                        ]
                        
                        if len(matches) > 0:
                            current_ask = matches.iloc[0]['ask']
                            buyback_cost = current_ask * 100
                            premium = self.short_call['premium']
                            profit_pct = (premium - buyback_cost) / premium if premium > 0 else 0
                            
                            # Close if profit target hit or time to roll
                            if profit_pct >= self.short_profit_target or short_dte <= self.short_roll_dte:
                                self.capital -= buyback_cost
                                
                                self.trades.append({
                                    'date': date,
                                    'action': 'BUY TO CLOSE',
                                    'strike': self.short_call['strike'],
                                    'expiration': self.short_call['expiration'],
                                    'cost': buyback_cost,
                                    'profit': premium - buyback_cost,
                                    'profit_pct': profit_pct * 100
                                })
                                
                                self.short_call = None
                
                # Sell new short call if we don't have one
                if self.short_call is None:
                    short = self.find_short_call(df_date, spy_price, self.leap['strike'])
                    if short is not None:
                        premium = short['bid'] * 100
                        self.short_call = {
                            'type': 'short',
                            'strike': short['strike'],
                            'expiration': short['expiration'],
                            'entry_date': date,
                            'entry_price': short['bid'],
                            'premium': premium,
                            'delta': short['delta'] if 'delta' in short.index else np.nan
                        }
                        self.capital += premium
                        
                        self.trades.append({
                            'date': date,
                            'action': 'SELL CALL',
                            'strike': short['strike'],
                            'expiration': short['expiration'],
                            'premium': premium,
                            'spy_price': spy_price,
                            'moneyness': short['strike'] / spy_price,
                            'dte': short['dte']
                        })
            
            # Calculate portfolio value
            leap_value = self.get_option_value(df_date, self.leap) if self.leap else 0
            
            # Short call is a liability if open
            short_liability = 0
            if self.short_call is not None:
                short_current = self.get_option_value(df_date, self.short_call)
                short_liability = -short_current  # Negative because it's a liability
            
            total_value = self.capital + leap_value + short_liability
            
            self.daily_values.append({
                'date': date,
                'spy_price': spy_price,
                'capital': self.capital,
                'leap_value': leap_value,
                'short_liability': short_liability,
                'total_value': total_value,
                'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100,
                'leap_strike': self.leap['strike'] if self.leap else np.nan,
                'short_strike': self.short_call['strike'] if self.short_call else np.nan
            })
            
            # Progress update every 100 days
            if i % 100 == 0:
                print(f"  Day {i}/{len(dates)}: SPY ${spy_price:.2f}, Portfolio ${total_value:.0f}")
        
        return pd.DataFrame(self.daily_values)

# %%
# Run the fixed PMCC strategy
print("\nRunning Fixed PMCC Backtest...")
print("-"*50)

pmcc = FixedPMCC(initial_capital=10000)
pmcc_results = pmcc.run_backtest(df)

print(f"\n✓ Backtest completed: {len(pmcc_results)} trading days")
print(f"✓ Total trades executed: {len(pmcc.trades)}")

# %%
# Calculate SPY benchmark
initial_capital = 10000
spy_start = spy_prices['spy_price'].iloc[0]
spy_shares = initial_capital / spy_start

spy_benchmark = spy_prices.copy()
spy_benchmark['value'] = spy_benchmark['spy_price'] * spy_shares
spy_benchmark['return_pct'] = (spy_benchmark['value'] - initial_capital) / initial_capital * 100

# %%
# Merge results for comparison
comparison = pd.merge(
    pmcc_results[['date', 'total_value', 'return_pct', 'capital', 'leap_value', 'short_liability']],
    spy_benchmark[['date', 'value', 'return_pct']],
    on='date',
    suffixes=('_pmcc', '_spy')
)

# %%
# Create performance visualization
fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=('Portfolio Value', 'Returns (%)'),
    vertical_spacing=0.1,
    row_heights=[0.6, 0.4]
)

# Portfolio value
fig.add_trace(
    go.Scatter(
        x=comparison['date'],
        y=comparison['total_value'],
        name='PMCC Strategy',
        line=dict(color='green', width=2)
    ),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=comparison['date'],
        y=comparison['value'],
        name='SPY Buy & Hold',
        line=dict(color='blue', width=2)
    ),
    row=1, col=1
)

# Returns
fig.add_trace(
    go.Scatter(
        x=comparison['date'],
        y=comparison['return_pct_pmcc'],
        name='PMCC Return',
        line=dict(color='green', width=1),
        showlegend=False
    ),
    row=2, col=1
)

fig.add_trace(
    go.Scatter(
        x=comparison['date'],
        y=comparison['return_pct_spy'],
        name='SPY Return',
        line=dict(color='blue', width=1),
        showlegend=False
    ),
    row=2, col=1
)

fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

fig.update_xaxes(title_text="Date", row=2, col=1)
fig.update_yaxes(title_text="Value ($)", row=1, col=1)
fig.update_yaxes(title_text="Return (%)", row=2, col=1)

fig.update_layout(
    title='Fixed PMCC (Deep ITM) vs SPY Buy & Hold',
    height=700,
    hovermode='x unified'
)

fig.show()

# %%
# Analyze trades
trades_df = pd.DataFrame(pmcc.trades)

print("\n" + "="*60)
print("TRADE ANALYSIS")
print("="*60)

# Count trade types
trade_counts = trades_df['action'].value_counts()
print("\nTrade Breakdown:")
for action, count in trade_counts.items():
    print(f"  {action}: {count}")

# LEAP analysis
leap_trades = trades_df[trades_df['action'].str.contains('LEAP')]
if len(leap_trades) > 0:
    print(f"\nLEAP Positions:")
    print(f"  Total LEAP buys: {len(leap_trades[leap_trades['action'].str.contains('BUY')])}")
    print(f"  LEAP rolls: {len(leap_trades[leap_trades['action'].str.contains('ROLL')]) // 2}")
    
    # Show LEAP trades with moneyness
    print("\nLEAP Trade History:")
    for _, trade in leap_trades.iterrows():
        if 'BUY' in trade['action']:
            moneyness = trade['moneyness'] if 'moneyness' in trade else trade['strike']/trade['spy_price']
            print(f"  {trade['date'].date()}: BUY Strike ${trade['strike']:.0f} (SPY=${trade['spy_price']:.2f}, {moneyness:.1%} of SPY)")
        elif 'SELL' in trade['action']:
            print(f"  {trade['date'].date()}: SELL Strike ${trade['strike']:.0f} for ${trade['proceeds']:.0f}")

# Short call analysis
short_sells = trades_df[trades_df['action'] == 'SELL CALL']
short_closes = trades_df[trades_df['action'] == 'BUY TO CLOSE']

if len(short_sells) > 0:
    total_premium = short_sells['premium'].sum()
    total_buyback = short_closes['cost'].sum() if len(short_closes) > 0 else 0
    net_income = total_premium - total_buyback
    
    print(f"\nShort Call Income:")
    print(f"  Calls sold: {len(short_sells)}")
    print(f"  Calls closed: {len(short_closes)}")
    print(f"  Premium collected: ${total_premium:,.0f}")
    print(f"  Buyback costs: ${total_buyback:,.0f}")
    print(f"  Net income: ${net_income:+,.0f}")
    
    if len(short_sells) > 0:
        print(f"  Avg premium/trade: ${total_premium/len(short_sells):.0f}")
        
        # Check moneyness of short calls
        avg_moneyness = short_sells['moneyness'].mean()
        print(f"  Avg short strike: {avg_moneyness:.1%} of SPY")

# %%
# Performance metrics
def calculate_metrics(values):
    """Calculate performance metrics"""
    returns = values.pct_change().dropna()
    
    # Annual return
    total_return = (values.iloc[-1] / values.iloc[0]) - 1
    years = len(values) / 252
    annual_return = (1 + total_return) ** (1/years) - 1
    
    # Volatility
    volatility = returns.std() * np.sqrt(252)
    
    # Sharpe (3% risk-free)
    sharpe = (annual_return - 0.03) / volatility if volatility > 0 else 0
    
    # Max drawdown
    cummax = values.expanding().max()
    drawdown = (values - cummax) / cummax
    max_dd = drawdown.min()
    
    return {
        'Total Return': f"{total_return*100:.1f}%",
        'Annual Return': f"{annual_return*100:.1f}%",
        'Volatility': f"{volatility*100:.1f}%",
        'Sharpe Ratio': f"{sharpe:.2f}",
        'Max Drawdown': f"{max_dd*100:.1f}%"
    }

pmcc_metrics = calculate_metrics(comparison['total_value'])
spy_metrics = calculate_metrics(comparison['value'])

# %%
# Final summary
print("\n" + "="*60)
print("PERFORMANCE SUMMARY")
print("="*60)

metrics_df = pd.DataFrame({
    'PMCC Strategy': pmcc_metrics,
    'SPY Buy & Hold': spy_metrics
}).T

print(metrics_df.to_string())

print("\n" + "="*60)
print("FINAL RESULTS")
print("="*60)

pmcc_final = comparison['total_value'].iloc[-1]
spy_final = comparison['value'].iloc[-1]
pmcc_return = (pmcc_final - initial_capital) / initial_capital * 100
spy_return = (spy_final - initial_capital) / initial_capital * 100

print(f"Initial Capital: ${initial_capital:,.0f}")
print(f"\nPMCC Final Value: ${pmcc_final:,.0f} ({pmcc_return:+.1f}%)")
print(f"SPY Final Value: ${spy_final:,.0f} ({spy_return:+.1f}%)")
print(f"\nDifference: ${pmcc_final - spy_final:,.0f} ({pmcc_return - spy_return:+.1f}%)")

if pmcc_return > spy_return:
    print(f"\n✅ PMCC outperformed SPY by {pmcc_return - spy_return:.1f}%")
else:
    print(f"\n❌ SPY outperformed PMCC by {spy_return - pmcc_return:.1f}%")

# Position status
print(f"\nFinal Position Status:")
print(f"  Cash: ${pmcc_results['capital'].iloc[-1]:,.0f}")
print(f"  LEAP Value: ${pmcc_results['leap_value'].iloc[-1]:,.0f}")
print(f"  Short Liability: ${pmcc_results['short_liability'].iloc[-1]:,.0f}")

# %%
print("\n" + "="*60)
print("Fixed strategy complete. Strike selection corrected.")
print("="*60)