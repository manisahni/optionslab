# %%
"""
Fixed PMCC vs SPY Backtest - Corrected position calculations
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

pd.set_option('display.max_columns', None)
pd.set_option('display.float_format', '{:.2f}'.format)

print("Loading data...")

# %%
# Load SPY options data
data_path = '../daily_strategies/data/spy_options/'
df_2023 = pd.read_parquet(f'{data_path}SPY_OPTIONS_2023_COMPLETE.parquet')
df_2024 = pd.read_parquet(f'{data_path}SPY_OPTIONS_2024_COMPLETE.parquet')

# Combine datasets
df = pd.concat([df_2023, df_2024], ignore_index=True)
df['date'] = pd.to_datetime(df['date'])
df['expiration'] = pd.to_datetime(df['expiration'])
df['dte'] = (df['expiration'] - df['date']).dt.days
df['mid_price'] = (df['bid'] + df['ask']) / 2

# Filter for valid data
df = df[(df['bid'] > 0) & (df['ask'] > 0) & (df['volume'] > 0)]

print(f"Data loaded: {len(df):,} option records")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")

# Extract SPY prices
spy_prices = df.groupby('date')['underlying_price'].first().reset_index()
spy_prices.columns = ['date', 'spy_price']
spy_prices = spy_prices.sort_values('date')

# %%
class PMCCStrategyFixed:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {'leap': None, 'short_call': None}
        self.trades = []
        self.daily_values = []
        
        # Strategy parameters
        self.leap_delta_min = 0.70
        self.leap_delta_max = 0.90
        self.leap_dte_min = 180
        
        self.short_delta_min = 0.20
        self.short_delta_max = 0.30
        self.short_dte_min = 30
        self.short_dte_max = 45
        
        self.short_profit_target = 0.50  # Take profit at 50%
        self.short_dte_exit = 21  # Roll at 21 DTE
        
    def find_leap_option(self, df_date, spy_price):
        """Find suitable LEAP call option"""
        candidates = df_date[
            (df_date['right'] == 'C') &
            (df_date['dte'] >= self.leap_dte_min) &
            (df_date['delta'] >= self.leap_delta_min) &
            (df_date['delta'] <= self.leap_delta_max) &
            (df_date['volume'] > 10)
        ].copy()
        
        if len(candidates) == 0:
            return None
            
        # Select LEAP with delta closest to 0.80
        candidates['delta_diff'] = abs(candidates['delta'] - 0.80)
        best = candidates.nsmallest(1, 'delta_diff').iloc[0]
        return best
    
    def find_short_call(self, df_date, leap_strike):
        """Find suitable short call to sell against LEAP"""
        candidates = df_date[
            (df_date['right'] == 'C') &
            (df_date['strike'] > leap_strike) &  # Must be above LEAP strike
            (df_date['dte'] >= self.short_dte_min) &
            (df_date['dte'] <= self.short_dte_max) &
            (df_date['delta'] >= self.short_delta_min) &
            (df_date['delta'] <= self.short_delta_max) &
            (df_date['volume'] > 10)
        ].copy()
        
        if len(candidates) == 0:
            return None
            
        # Select short call with delta closest to 0.25
        candidates['delta_diff'] = abs(candidates['delta'] - 0.25)
        best = candidates.nsmallest(1, 'delta_diff').iloc[0]
        return best
    
    def calculate_position_value(self, current_data, position):
        """Calculate current value of a position - FIXED VERSION"""
        if position is None:
            return 0
            
        # Find current price for the option
        matches = current_data[
            (current_data['strike'] == position['strike']) &
            (current_data['expiration'] == position['expiration']) &
            (current_data['right'] == position['right'])
        ]
        
        if len(matches) == 0:
            # Option expired or not found - use intrinsic value
            if position['right'] == 'C':
                spy_price = current_data['underlying_price'].iloc[0]
                intrinsic = max(0, spy_price - position['strike'])
                if position['side'] == 'long':
                    return intrinsic * 100
                else:
                    # Short position - we owe the intrinsic value
                    return -(intrinsic * 100)
            return 0
            
        current_price = matches.iloc[0]['mid_price']
        
        if position['side'] == 'long':
            # Long position: current value
            return current_price * 100
        else:
            # Short position: we owe the current value (negative)
            # Our P&L is: premium collected - current cost to close
            # But for portfolio value, we show the liability (negative)
            return -(current_price * 100)
    
    def run_backtest(self, df):
        """Run the PMCC backtest with fixed calculations"""
        dates = sorted(df['date'].unique())
        
        for date in dates:
            df_date = df[df['date'] == date].copy()
            spy_price = df_date['underlying_price'].iloc[0]
            
            # Initialize position on first suitable date
            if self.positions['leap'] is None:
                leap = self.find_leap_option(df_date, spy_price)
                if leap is not None:
                    # Buy LEAP
                    leap_cost = leap['ask'] * 100
                    if leap_cost <= self.capital:
                        self.positions['leap'] = {
                            'strike': leap['strike'],
                            'expiration': leap['expiration'],
                            'right': 'C',
                            'side': 'long',
                            'entry_date': date,
                            'entry_price': leap['ask'],
                            'entry_cost': leap_cost,
                            'delta': leap['delta']
                        }
                        self.capital -= leap_cost
                        self.trades.append({
                            'date': date,
                            'action': 'BUY LEAP',
                            'strike': leap['strike'],
                            'expiration': leap['expiration'],
                            'price': leap['ask'],
                            'cost': leap_cost
                        })
            
            # Manage short call if we have a LEAP
            if self.positions['leap'] is not None:
                # Check if LEAP has expired
                if self.positions['leap']['expiration'] <= date:
                    # LEAP expired - close position
                    leap_value = self.calculate_position_value(df_date, self.positions['leap'])
                    self.capital += leap_value
                    self.positions['leap'] = None
                
                # If we still have LEAP, manage short call
                if self.positions['leap'] is not None:
                    if self.positions['short_call'] is None:
                        # Sell new short call
                        short = self.find_short_call(df_date, self.positions['leap']['strike'])
                        if short is not None:
                            self.positions['short_call'] = {
                                'strike': short['strike'],
                                'expiration': short['expiration'],
                                'right': 'C',
                                'side': 'short',
                                'entry_date': date,
                                'entry_price': short['bid'],
                                'premium_collected': short['bid'] * 100,
                                'delta': short['delta']
                            }
                            premium = short['bid'] * 100
                            self.capital += premium
                            self.trades.append({
                                'date': date,
                                'action': 'SELL CALL',
                                'strike': short['strike'],
                                'expiration': short['expiration'],
                                'price': short['bid'],
                                'premium': premium
                            })
                    else:
                        # Check if short call expired
                        if self.positions['short_call']['expiration'] <= date:
                            # Short call expired worthless (good for us!)
                            self.positions['short_call'] = None
                        else:
                            # Check if we should close short call
                            short_dte = (self.positions['short_call']['expiration'] - date).days
                            
                            # Get current value of short position
                            matches = df_date[
                                (df_date['strike'] == self.positions['short_call']['strike']) &
                                (df_date['expiration'] == self.positions['short_call']['expiration']) &
                                (df_date['right'] == 'C')
                            ]
                            
                            if len(matches) > 0:
                                current_ask = matches.iloc[0]['ask']
                                buyback_cost = current_ask * 100
                                premium_collected = self.positions['short_call']['premium_collected']
                                profit_pct = (premium_collected - buyback_cost) / premium_collected
                                
                                # Close if profit target hit or DTE threshold reached
                                if profit_pct >= self.short_profit_target or short_dte <= self.short_dte_exit:
                                    self.capital -= buyback_cost
                                    
                                    self.trades.append({
                                        'date': date,
                                        'action': 'BUY TO CLOSE',
                                        'strike': self.positions['short_call']['strike'],
                                        'expiration': self.positions['short_call']['expiration'],
                                        'price': current_ask,
                                        'cost': buyback_cost,
                                        'profit': premium_collected - buyback_cost
                                    })
                                    
                                    self.positions['short_call'] = None
            
            # Calculate total portfolio value
            leap_value = self.calculate_position_value(df_date, self.positions['leap'])
            short_value = self.calculate_position_value(df_date, self.positions['short_call'])
            
            # Total value = cash + long positions - short liabilities
            total_value = self.capital + leap_value + short_value
            
            self.daily_values.append({
                'date': date,
                'spy_price': spy_price,
                'capital': self.capital,
                'leap_value': leap_value,
                'short_value': short_value,  # This will be negative when we have a short position
                'total_value': total_value,
                'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100
            })
        
        return pd.DataFrame(self.daily_values)

# %%
# Run the fixed PMCC strategy
print("\nRunning PMCC backtest...")
pmcc = PMCCStrategyFixed(initial_capital=10000)
pmcc_results = pmcc.run_backtest(df)

print(f"PMCC Backtest completed: {len(pmcc_results)} days")
print(f"Total trades: {len(pmcc.trades)}")
print(f"\nFinal Results:")
print(f"Starting Capital: ${pmcc.initial_capital:,.2f}")
print(f"Final Value: ${pmcc_results['total_value'].iloc[-1]:,.2f}")
print(f"Total Return: {pmcc_results['return_pct'].iloc[-1]:.2f}%")

# %%
# SPY Buy-and-Hold Benchmark
initial_capital = 10000
spy_start_price = spy_prices['spy_price'].iloc[0]
spy_shares = initial_capital / spy_start_price

spy_benchmark = spy_prices.copy()
spy_benchmark['portfolio_value'] = spy_benchmark['spy_price'] * spy_shares
spy_benchmark['return_pct'] = (spy_benchmark['portfolio_value'] - initial_capital) / initial_capital * 100

print(f"\nSPY Buy-and-Hold Results:")
print(f"Starting Capital: ${initial_capital:,.2f}")
print(f"Final Portfolio Value: ${spy_benchmark['portfolio_value'].iloc[-1]:,.2f}")
print(f"Total Return: {spy_benchmark['return_pct'].iloc[-1]:.2f}%")

# %%
# Merge and compare results
comparison = pd.merge(
    pmcc_results[['date', 'total_value', 'return_pct', 'capital', 'leap_value', 'short_value']],
    spy_benchmark[['date', 'portfolio_value', 'return_pct']],
    on='date',
    suffixes=('_pmcc', '_spy')
)

# %%
# Plot the corrected equity curves
fig = go.Figure()

# Add PMCC strategy line
fig.add_trace(go.Scatter(
    x=comparison['date'],
    y=comparison['total_value'],
    mode='lines',
    name='PMCC Strategy',
    line=dict(color='green', width=2),
    hovertemplate='Date: %{x}<br>Value: $%{y:,.0f}<br>Cash: $%{customdata[0]:,.0f}<br>LEAP: $%{customdata[1]:,.0f}<br>Short: $%{customdata[2]:,.0f}',
    customdata=np.column_stack((comparison['capital'], comparison['leap_value'], comparison['short_value']))
))

# Add SPY buy & hold line
fig.add_trace(go.Scatter(
    x=comparison['date'],
    y=comparison['portfolio_value'],
    mode='lines',
    name='SPY Buy & Hold',
    line=dict(color='blue', width=2)
))

# Add initial capital reference line
fig.add_hline(y=initial_capital, line_dash="dash", line_color="gray", 
              annotation_text="Initial Capital")

fig.update_layout(
    title='PMCC vs SPY Buy & Hold - Portfolio Value (Fixed)',
    xaxis_title='Date',
    yaxis_title='Portfolio Value ($)',
    hovermode='x unified',
    height=500,
    yaxis=dict(
        rangemode='tozero',
        tickformat='$,.0f'
    )
)

fig.show()

# %%
# Show detailed position tracking
print("\nPMCC Position Tracking (Last 30 days):")
print("="*60)
last_30 = pmcc_results.tail(30)[['date', 'capital', 'leap_value', 'short_value', 'total_value']]
print(last_30.to_string(index=False))

# %%
# Analyze trades
if len(pmcc.trades) > 0:
    trades_df = pd.DataFrame(pmcc.trades)
    print(f"\nTotal Trades: {len(trades_df)}")
    print("\nTrade Breakdown:")
    print(trades_df['action'].value_counts())
    
    # Calculate income from short calls
    sell_calls = trades_df[trades_df['action'] == 'SELL CALL']
    buy_closes = trades_df[trades_df['action'] == 'BUY TO CLOSE']
    
    if len(sell_calls) > 0:
        total_premium = sell_calls['premium'].sum()
        total_buyback = buy_closes['cost'].sum() if len(buy_closes) > 0 else 0
        net_income = total_premium - total_buyback
        
        print("\nShort Call Income Analysis:")
        print(f"Calls Sold: {len(sell_calls)}")
        print(f"Calls Closed: {len(buy_closes)}")
        print(f"Total Premium Collected: ${total_premium:,.2f}")
        print(f"Total Buyback Cost: ${total_buyback:,.2f}")
        print(f"Net Income from Short Calls: ${net_income:,.2f}")

# %%
print("\n" + "="*60)
print("FINAL COMPARISON:")
print("="*60)

pmcc_final = comparison['total_value'].iloc[-1]
spy_final = comparison['portfolio_value'].iloc[-1]
pmcc_return = (pmcc_final - initial_capital) / initial_capital * 100
spy_return = (spy_final - initial_capital) / initial_capital * 100

print(f"PMCC Final Value: ${pmcc_final:,.2f} ({pmcc_return:+.1f}%)")
print(f"SPY Final Value: ${spy_final:,.2f} ({spy_return:+.1f}%)")
print(f"Difference: ${pmcc_final - spy_final:,.2f} ({pmcc_return - spy_return:+.1f}%)")

if pmcc_return > spy_return:
    print(f"\n✅ PMCC outperformed SPY by {pmcc_return - spy_return:.1f}%")
else:
    print(f"\n❌ SPY outperformed PMCC by {spy_return - pmcc_return:.1f}%")