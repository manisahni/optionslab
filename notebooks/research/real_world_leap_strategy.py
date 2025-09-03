# %%
"""
Real-World 2-Year LEAP Strategy
==============================
Based on actual trading experience:

Strategy Logic:
1. Buy 2-year LEAPs (730 DTE, 0.70-0.80 delta) 
2. Hold for 18+ months to maximize time value
3. Roll when theta acceleration starts (~120 DTE)
4. Exit to cash during vol spikes (>80th percentile)
5. Resume positions when vol normalizes (<60th percentile)

Test Period: 2020-2025 (diverse market conditions)
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
print("REAL-WORLD 2-YEAR LEAP STRATEGY")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# %% Load extended data (start with 2023-2024 for speed)
data_path = '/Users/nish_macbook/trading/daily-optionslab/data/spy_options/'

print("Loading dataset (2023-2024 for initial test)...")
dfs = []
years = [2023, 2024]  # Start smaller for testing

for year in years:
    try:
        df_year = pd.read_parquet(f'{data_path}SPY_OPTIONS_{year}_COMPLETE.parquet')
        # Calculate DTE first
        df_year['date'] = pd.to_datetime(df_year['date'])
        df_year['expiration'] = pd.to_datetime(df_year['expiration'])
        df_year['dte'] = (df_year['expiration'] - df_year['date']).dt.days
        
        # Pre-filter for calls only and reasonable DTE range to speed up
        df_year = df_year[
            (df_year['right'] == 'C') & 
            (df_year['dte'] >= 30) & 
            (df_year['dte'] <= 800)
        ]
        dfs.append(df_year)
        print(f"✓ Loaded {year}: {len(df_year):,} call options")
    except FileNotFoundError:
        print(f"⚠️  {year} data not found, skipping")

# Combine all years
df_all = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

if len(df_all) == 0:
    raise ValueError("No data loaded! Check data files.")

# Data preparation (dates already converted above)
df_all['strike'] = df_all['strike'] / 1000  # Convert cents to dollars
df_all['mid_price'] = (df_all['bid'] + df_all['ask']) / 2

# Filter for valid data
df_clean = df_all[(df_all['bid'] > 0) & (df_all['volume'] > 0)].copy()

print(f"✓ Total records: {len(df_clean):,}")
print(f"✓ Date range: {df_clean['date'].min().date()} to {df_clean['date'].max().date()}")

# Get SPY prices and calculate volatility
spy_prices = df_clean.groupby('date')['underlying_price'].first().reset_index()
spy_prices.columns = ['date', 'spy_price']
spy_prices = spy_prices.sort_values('date').reset_index(drop=True)

# Calculate volatility metrics
spy_prices['returns'] = spy_prices['spy_price'].pct_change()
spy_prices['vol_20d'] = spy_prices['returns'].rolling(20).std() * np.sqrt(252) * 100
spy_prices['vol_percentile'] = spy_prices['vol_20d'].rolling(252).rank(pct=True)

# Volatility regime signals (with hysteresis)
spy_prices['high_vol_signal'] = False
spy_prices['exit_signal'] = False

high_vol_active = False
for i in range(len(spy_prices)):
    if pd.notna(spy_prices.loc[i, 'vol_percentile']):
        # High vol detection
        if not high_vol_active and spy_prices.loc[i, 'vol_percentile'] > 0.8:
            high_vol_active = True
        elif high_vol_active and spy_prices.loc[i, 'vol_percentile'] < 0.6:
            high_vol_active = False
        spy_prices.loc[i, 'high_vol_signal'] = high_vol_active
        spy_prices.loc[i, 'exit_signal'] = high_vol_active

print(f"✓ SPY range: ${spy_prices['spy_price'].min():.2f} - ${spy_prices['spy_price'].max():.2f}")
high_vol_days = spy_prices['high_vol_signal'].sum()
print(f"✓ High vol periods: {high_vol_days} days ({high_vol_days/len(spy_prices)*100:.1f}%)")

# %%
class RealWorld2YearLEAP:
    """
    Real-world 2-year LEAP strategy based on actual trading experience
    """
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = None
        self.trades = []
        self.daily_values = []
        
        # Real-world parameters
        self.target_dte = 730        # 2-year LEAPs
        self.min_dte_buy = 600       # Min 600 days (close to 2 years)
        self.max_dte_buy = 800       # Max 800 days
        self.theta_roll_dte = 120    # Roll when theta acceleration starts
        
        self.target_delta_min = 0.70 # Conservative delta range
        self.target_delta_max = 0.80
        self.max_otm_pct = 0.15      # Max 15% OTM for safety
        
        # Volatility-based exits
        self.vol_exit_threshold = 0.8    # Exit above 80th percentile
        self.vol_reentry_threshold = 0.6 # Re-enter below 60th percentile
        
    def find_2year_leap(self, df_date, spy_price):
        """Find best 2-year LEAP option"""
        # Strike range: Current price to 15% OTM
        max_strike = spy_price * (1 + self.max_otm_pct)
        min_strike = spy_price * 0.90  # Allow some ITM
        
        leap_candidates = df_date[
            (df_date['right'] == 'C') & 
            (df_date['dte'] >= self.min_dte_buy) &
            (df_date['dte'] <= self.max_dte_buy) &
            (df_date['delta'] >= self.target_delta_min) &
            (df_date['delta'] <= self.target_delta_max) &
            (df_date['strike'] >= min_strike) &
            (df_date['strike'] <= max_strike) &
            (df_date['bid'] > 0) &
            (df_date['ask'] > 0) &
            (df_date['volume'] > 0)
        ].copy()
        
        if len(leap_candidates) == 0:
            return None
        
        # Prefer longest time, then best delta
        leap_candidates['dte_score'] = leap_candidates['dte'] / self.target_dte
        leap_candidates['delta_score'] = 1 - abs(leap_candidates['delta'] - 0.75)
        leap_candidates['total_score'] = leap_candidates['dte_score'] + leap_candidates['delta_score']
        
        best_leap = leap_candidates.loc[leap_candidates['total_score'].idxmax()]
        
        return {
            'strike': best_leap['strike'],
            'expiration': best_leap['expiration'],
            'delta': best_leap['delta'],
            'price': best_leap['mid_price'],
            'dte': best_leap['dte']
        }
    
    def get_position_value(self, df_date):
        """Get current value of LEAP position"""
        if self.position is None:
            return 0
            
        option_data = df_date[
            (df_date['strike'] == self.position['strike']) &
            (df_date['expiration'] == self.position['expiration']) &
            (df_date['right'] == 'C')
        ]
        
        if len(option_data) == 0:
            return 0  # Option expired or not found
            
        return option_data['mid_price'].iloc[0] * 100
    
    def should_exit_for_volatility(self, spy_data, current_date):
        """Check if we should exit due to high volatility"""
        spy_row = spy_data[spy_data['date'] == current_date]
        if len(spy_row) == 0:
            return False
        return spy_row['exit_signal'].iloc[0]
    
    def should_reenter_from_volatility(self, spy_data, current_date):
        """Check if we should re-enter after volatility subsides"""
        spy_row = spy_data[spy_data['date'] == current_date]
        if len(spy_row) == 0:
            return False
        return not spy_row['high_vol_signal'].iloc[0]
    
    def run_backtest(self, df, spy_data):
        """Run real-world 2-year LEAP backtest"""
        dates = sorted(df['date'].unique())
        dates = [d for d in dates if d in spy_data['date'].values]  # Ensure vol data
        
        print(f"\n🚀 Running Real-World 2-Year LEAP Strategy...")
        print(f"📅 {len(dates)} trading days")
        
        vol_exits = 0
        theta_rolls = 0
        
        for i, date in enumerate(dates):
            df_date = df[df['date'] == date].copy()
            spy_price = spy_data[spy_data['date'] == date]['spy_price'].iloc[0]
            
            if len(df_date) == 0:
                continue
            
            # Check volatility exit signal
            should_exit = self.should_exit_for_volatility(spy_data, date)
            should_reenter = self.should_reenter_from_volatility(spy_data, date)
            
            # Manage existing position
            if self.position is not None:
                current_dte = (self.position['expiration'] - date).days
                position_value = self.get_position_value(df_date)
                
                # Exit for high volatility
                if should_exit and position_value > 0:
                    self.capital += position_value
                    
                    # Calculate P&L
                    entry_cost = self.position['entry_price'] * 100
                    pnl = position_value - entry_cost
                    pnl_pct = pnl / entry_cost * 100
                    
                    self.trades.append({
                        'date': date,
                        'action': 'exit_vol',
                        'strike': self.position['strike'],
                        'price': position_value / 100,
                        'entry_price': self.position['entry_price'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'dte': current_dte,
                        'reason': 'volatility_exit'
                    })
                    
                    print(f"📤 {date.date()}: Vol Exit - LEAP ${self.position['strike']:.0f} "
                          f"P&L: ${pnl:.0f} ({pnl_pct:.1f}%) - DTE: {current_dte}")
                    vol_exits += 1
                    self.position = None
                
                # Roll for theta acceleration
                elif current_dte <= self.theta_roll_dte and position_value > 0:
                    self.capital += position_value
                    
                    # Calculate P&L
                    entry_cost = self.position['entry_price'] * 100
                    pnl = position_value - entry_cost
                    pnl_pct = pnl / entry_cost * 100
                    
                    self.trades.append({
                        'date': date,
                        'action': 'roll_theta',
                        'strike': self.position['strike'],
                        'price': position_value / 100,
                        'entry_price': self.position['entry_price'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'dte': current_dte,
                        'reason': 'theta_roll'
                    })
                    
                    print(f"🔄 {date.date()}: Theta Roll - LEAP ${self.position['strike']:.0f} "
                          f"P&L: ${pnl:.0f} ({pnl_pct:.1f}%) - DTE: {current_dte}")
                    theta_rolls += 1
                    self.position = None
            
            # Look for new LEAP entry
            if self.position is None and should_reenter:
                new_leap = self.find_2year_leap(df_date, spy_price)
                
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
                    
                    print(f"🎯 {date.date()}: New 2Y LEAP ${new_leap['strike']:.0f} @ ${new_leap['price']:.2f} "
                          f"(Δ={new_leap['delta']:.2f}, DTE={new_leap['dte']}) SPY=${spy_price:.2f}")
            
            # Calculate portfolio value
            position_value = self.get_position_value(df_date)
            total_value = self.capital + position_value
            
            # Get volatility info
            vol_data = spy_data[spy_data['date'] == date]
            vol_percentile = vol_data['vol_percentile'].iloc[0] if len(vol_data) > 0 else np.nan
            high_vol = vol_data['high_vol_signal'].iloc[0] if len(vol_data) > 0 else False
            
            # Record daily values
            self.daily_values.append({
                'date': date,
                'total_value': total_value,
                'capital': self.capital,
                'position_value': position_value,
                'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100,
                'has_position': self.position is not None,
                'spy_price': spy_price,
                'vol_percentile': vol_percentile,
                'high_vol': high_vol
            })
        
        print(f"\n📊 Strategy Summary:")
        print(f"   Volatility exits: {vol_exits}")
        print(f"   Theta rolls: {theta_rolls}")
        print(f"   Total trades: {len(self.trades)}")
        
        return pd.DataFrame(self.daily_values)

# %% Run the strategy
print("\n" + "="*60)
print("RUNNING REAL-WORLD 2-YEAR LEAP STRATEGY")
print("="*60)

strategy = RealWorld2YearLEAP(initial_capital=10000)
results = strategy.run_backtest(df_clean, spy_prices)

# %% Analyze results
print("\n" + "="*60)
print("PERFORMANCE ANALYSIS")
print("="*60)

if len(results) > 0:
    final_value = results['total_value'].iloc[-1]
    total_return = results['return_pct'].iloc[-1]
    max_dd = (results['total_value'] / results['total_value'].cummax() - 1).min() * 100
    
    # SPY benchmark
    spy_start = results['spy_price'].iloc[0]
    spy_end = results['spy_price'].iloc[-1]
    spy_return = (spy_end - spy_start) / spy_start * 100
    
    print(f"📈 STRATEGY PERFORMANCE:")
    print(f"   Initial Capital: $10,000")
    print(f"   Final Value: ${final_value:,.0f}")
    print(f"   Total Return: {total_return:.1f}%")
    print(f"   Max Drawdown: {max_dd:.1f}%")
    
    print(f"\n📊 VS SPY BUY & HOLD:")
    print(f"   SPY Return: {spy_return:.1f}%")
    print(f"   LEAP Return: {total_return:.1f}%")
    if spy_return > 0:
        leverage = total_return / spy_return
        print(f"   LEAP Leverage: {leverage:.1f}x")
    
    # Position statistics
    days_invested = results['has_position'].sum()
    total_days = len(results)
    print(f"\n📅 POSITION STATS:")
    print(f"   Days invested: {days_invested} ({days_invested/total_days*100:.1f}%)")
    print(f"   Days in cash: {total_days-days_invested} ({(total_days-days_invested)/total_days*100:.1f}%)")
    
    # Trade analysis
    if len(strategy.trades) > 0:
        trades_df = pd.DataFrame(strategy.trades)
        
        closed_trades = trades_df[trades_df['action'].isin(['exit_vol', 'roll_theta'])]
        if len(closed_trades) > 0:
            avg_pnl = closed_trades['pnl_pct'].mean()
            win_rate = (closed_trades['pnl_pct'] > 0).mean() * 100
            
            print(f"\n💰 TRADE PERFORMANCE:")
            print(f"   Closed trades: {len(closed_trades)}")
            print(f"   Average P&L: {avg_pnl:.1f}%")
            print(f"   Win rate: {win_rate:.1f}%")
            
            print(f"\n📋 RECENT TRADES:")
            for _, trade in closed_trades.tail(5).iterrows():
                print(f"   {trade['date'].date()}: ${trade['strike']:.0f} LEAP "
                      f"({trade['reason']}) = ${trade['pnl']:.0f} ({trade['pnl_pct']:.1f}%)")

# Check if we have open position
if strategy.position is not None:
    current_pos_value = results['position_value'].iloc[-1]
    entry_cost = strategy.position['entry_price'] * 100
    open_pnl = current_pos_value - entry_cost
    open_pnl_pct = open_pnl / entry_cost * 100
    current_dte = (strategy.position['expiration'] - results['date'].iloc[-1]).days
    
    print(f"\n🔓 OPEN POSITION:")
    print(f"   Strike: ${strategy.position['strike']:.0f}")
    print(f"   Entry: ${strategy.position['entry_price']:.2f}")
    print(f"   Current Value: ${current_pos_value:.0f}")
    print(f"   DTE Remaining: {current_dte}")
    print(f"   Unrealized P&L: ${open_pnl:.0f} ({open_pnl_pct:.1f}%)")

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")