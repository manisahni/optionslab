# %%
"""
Comprehensive 2-Year LEAP Strategy Test (2020-2025)
==================================================
Test the real-world LEAP strategy across diverse market conditions:
- 2020: COVID crash and recovery
- 2021: Bull market continuation  
- 2022: Bear market with rate hikes
- 2023-2024: Recovery and new highs

Strategy:
1. Buy 2-year LEAP calls (0.70-0.80 delta) 
2. Exit during volatility spikes (>80th percentile)
3. Re-enter when volatility calms (<60th percentile)
4. Roll to new LEAP when theta acceleration starts (<120 DTE)
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
print("COMPREHENSIVE 2-YEAR LEAP STRATEGY TEST")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# %% Load comprehensive data
data_path = '/Users/nish_macbook/trading/daily-optionslab/data/spy_options/'

print("\n🔍 Loading data files...")
data_files = []
df_all_years = []

# Load all available years
for year in [2020, 2021, 2022, 2023, 2024]:
    try:
        file_path = f'{data_path}SPY_OPTIONS_{year}_COMPLETE.parquet'
        df_year = pd.read_parquet(file_path)
        print(f"✓ Loaded {year}: {len(df_year):,} records")
        df_all_years.append(df_year)
        data_files.append(year)
    except FileNotFoundError:
        print(f"⚠️  {year} data not found, skipping")
        continue

if not df_all_years:
    print("❌ No data files found!")
    exit(1)

# Combine all years
df_all = pd.concat(df_all_years, ignore_index=True)
print(f"✓ Combined dataset: {len(df_all):,} total records")

# Clean and prepare data
df_all['date'] = pd.to_datetime(df_all['date'])
df_all['expiration'] = pd.to_datetime(df_all['expiration'])
df_all['dte'] = (df_all['expiration'] - df_all['date']).dt.days
df_all['strike'] = df_all['strike'] / 1000
df_all['mid_price'] = (df_all['bid'] + df_all['ask']) / 2

# Filter for calls only and valid data
df_calls = df_all[
    (df_all['right'] == 'C') & 
    (df_all['bid'] > 0) & 
    (df_all['ask'] > 0) & 
    (df_all['volume'] > 0)
].copy()

print(f"✓ Call options: {len(df_calls):,} records")
print(f"✓ Date range: {df_calls['date'].min().date()} to {df_calls['date'].max().date()}")

# Get SPY prices for all periods
spy_prices = df_calls.groupby('date')['underlying_price'].first().reset_index()
spy_prices.columns = ['date', 'spy_price']
spy_prices = spy_prices.sort_values('date').reset_index(drop=True)

spy_start = spy_prices['spy_price'].iloc[0]
spy_end = spy_prices['spy_price'].iloc[-1]
spy_return = (spy_end - spy_start) / spy_start * 100

print(f"✓ SPY Performance: ${spy_start:.2f} → ${spy_end:.2f} (+{spy_return:.1f}%)")

# Calculate volatility percentiles for entire period
spy_prices['spy_return'] = spy_prices['spy_price'].pct_change()
spy_prices['realized_vol'] = spy_prices['spy_return'].rolling(20).std() * np.sqrt(252)
spy_prices['vol_percentile'] = spy_prices['realized_vol'].rolling(252, min_periods=50).rank(pct=True)

print(f"✓ Volatility data calculated for {len(spy_prices[~spy_prices['vol_percentile'].isna()]):,} days")

# %%
class ComprehensiveLEAPStrategy:
    """
    Real-world 2-year LEAP strategy with volatility protection
    Based on actual trading experience, not theoretical PMCC
    """
    def __init__(self, initial_capital=50000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.trades = []
        self.daily_values = []
        
        # Real-world parameters
        self.target_dte = 730        # 2-year LEAPs
        self.min_dte_buy = 600       # At least 600 days when buying
        self.max_dte_buy = 800       # No more than 800 days
        self.theta_roll_dte = 120    # Roll when theta acceleration starts
        
        # Volatility thresholds (hysteresis)
        self.vol_exit_threshold = 0.80    # Exit above 80th percentile
        self.vol_reentry_threshold = 0.60 # Re-enter below 60th percentile
        
        # Position management
        self.target_delta_range = [0.70, 0.80]  # Deep ITM for leverage
        self.max_position_value = 0.8    # 80% of capital max
        
    def find_best_leap(self, df_date, underlying_price):
        """Find optimal 2-year LEAP"""
        leap_candidates = df_date[
            (df_date['dte'] >= self.min_dte_buy) &
            (df_date['dte'] <= self.max_dte_buy) &
            (df_date['delta'] >= self.target_delta_range[0]) &
            (df_date['delta'] <= self.target_delta_range[1]) &
            (df_date['strike'] <= underlying_price * 1.1) &  # Not too far OTM
            (df_date['bid'] > 0) &
            (df_date['ask'] > 0) &
            (df_date['volume'] > 0)
        ].copy()
        
        if len(leap_candidates) == 0:
            return None
            
        # Select LEAP closest to 0.75 delta
        leap_candidates['delta_diff'] = abs(leap_candidates['delta'] - 0.75)
        best_leap = leap_candidates.loc[leap_candidates['delta_diff'].idxmin()]
        
        return {
            'strike': best_leap['strike'],
            'expiration': best_leap['expiration'],
            'delta': best_leap['delta'],
            'price': best_leap['mid_price'],
            'dte': best_leap['dte'],
            'entry_date': df_date['date'].iloc[0]
        }
    
    def get_position_value(self, df_date, position):
        """Get current value of a LEAP position"""
        option_data = df_date[
            (df_date['strike'] == position['strike']) &
            (df_date['expiration'] == position['expiration'])
        ]
        
        if len(option_data) == 0:
            return 0
            
        return option_data['mid_price'].iloc[0] * 100
    
    def should_exit_volatility(self, vol_percentile):
        """Check if we should exit due to high volatility"""
        return vol_percentile >= self.vol_exit_threshold
    
    def should_enter_volatility(self, vol_percentile):
        """Check if we can re-enter after volatility subsided"""
        return vol_percentile <= self.vol_reentry_threshold
    
    def run_comprehensive_backtest(self, df, spy_data):
        """Run backtest across full dataset"""
        dates = sorted(df['date'].unique())
        
        print(f"\n🚀 Running Comprehensive LEAP Backtest...")
        print(f"📅 {len(dates)} trading days ({dates[0].date()} to {dates[-1].date()})")
        print(f"💰 Initial capital: ${self.initial_capital:,}")
        
        in_volatility_mode = False  # Track if we're avoiding due to high vol
        
        for i, date in enumerate(dates):
            df_date = df[df['date'] == date].copy()
            spy_date = spy_data[spy_data['date'] == date]
            
            if len(df_date) == 0 or len(spy_date) == 0:
                continue
                
            underlying_price = spy_date['spy_price'].iloc[0]
            vol_percentile = spy_date['vol_percentile'].iloc[0] if not spy_date['vol_percentile'].isna().iloc[0] else 0.5
            
            # Check existing positions for rolling or expiration
            for pos_idx in range(len(self.positions) - 1, -1, -1):
                position = self.positions[pos_idx]
                current_dte = (position['expiration'] - date).days
                current_value = self.get_position_value(df_date, position)
                
                should_roll = current_dte <= self.theta_roll_dte and current_value > 0
                should_exit_vol = self.should_exit_volatility(vol_percentile)
                
                # Close position if rolling time or volatility spike
                if should_roll or should_exit_vol:
                    if current_value > 0:
                        self.capital += current_value
                        
                        # Calculate P&L
                        entry_cost = position['price'] * 100
                        pnl = current_value - entry_cost
                        pnl_pct = pnl / entry_cost * 100
                        
                        reason = "theta_roll" if should_roll else "vol_exit"
                        
                        self.trades.append({
                            'date': date,
                            'action': f'close_leap_{reason}',
                            'strike': position['strike'],
                            'expiration': position['expiration'],
                            'price': current_value / 100,
                            'entry_price': position['price'],
                            'entry_date': position['entry_date'],
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'dte': current_dte,
                            'vol_percentile': vol_percentile,
                            'reason': reason
                        })
                        
                        if i % 50 == 0 or abs(pnl) > 5000:  # Progress or significant trades
                            print(f"📊 {date.date()}: Closed ${position['strike']:.0f} LEAP ({reason}) - "
                                  f"P&L: ${pnl:.0f} ({pnl_pct:.1f}%) - Vol: {vol_percentile:.1%}")
                    
                    # Remove position
                    self.positions.pop(pos_idx)
                    
                    if should_exit_vol:
                        in_volatility_mode = True
            
            # Check if we can exit volatility mode
            if in_volatility_mode and self.should_enter_volatility(vol_percentile):
                in_volatility_mode = False
                print(f"📈 {date.date()}: Volatility subsided ({vol_percentile:.1%}), ready to re-enter")
            
            # Look for new LEAP if we have no positions and volatility is acceptable
            if len(self.positions) == 0 and not in_volatility_mode:
                new_leap = self.find_best_leap(df_date, underlying_price)
                
                if new_leap:
                    cost = new_leap['price'] * 100
                    available_capital = self.capital * self.max_position_value
                    
                    if cost <= available_capital:
                        # Buy new LEAP
                        self.capital -= cost
                        self.positions.append(new_leap)
                        
                        self.trades.append({
                            'date': date,
                            'action': 'buy_leap',
                            'strike': new_leap['strike'],
                            'expiration': new_leap['expiration'],
                            'price': new_leap['price'],
                            'delta': new_leap['delta'],
                            'dte': new_leap['dte'],
                            'cost': cost,
                            'vol_percentile': vol_percentile
                        })
                        
                        print(f"🎯 {date.date()}: Bought ${new_leap['strike']:.0f} LEAP @ ${new_leap['price']:.2f} "
                              f"(Δ={new_leap['delta']:.2f}, DTE={new_leap['dte']}, Vol={vol_percentile:.1%})")
            
            # Calculate total portfolio value
            total_position_value = sum(self.get_position_value(df_date, pos) for pos in self.positions)
            total_value = self.capital + total_position_value
            
            # Record daily values
            self.daily_values.append({
                'date': date,
                'total_value': total_value,
                'capital': self.capital,
                'position_value': total_position_value,
                'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100,
                'num_positions': len(self.positions),
                'vol_percentile': vol_percentile,
                'in_volatility_mode': in_volatility_mode,
                'underlying_price': underlying_price
            })
        
        return pd.DataFrame(self.daily_values)

# %% Run comprehensive backtest
print("\n" + "="*50)
print("RUNNING COMPREHENSIVE LEAP STRATEGY")
print("="*50)

strategy = ComprehensiveLEAPStrategy(initial_capital=50000)
results = strategy.run_comprehensive_backtest(df_calls, spy_prices)

# %% Analyze comprehensive results
print("\n" + "="*60)
print("COMPREHENSIVE RESULTS ANALYSIS")
print("="*60)

final_value = results['total_value'].iloc[-1]
total_return = results['return_pct'].iloc[-1]
years = (results['date'].iloc[-1] - results['date'].iloc[0]).days / 365.25
annualized_return = (final_value / strategy.initial_capital) ** (1/years) - 1

print(f"📈 OVERALL PERFORMANCE:")
print(f"   Test Period: {results['date'].iloc[0].date()} to {results['date'].iloc[-1].date()}")
print(f"   Duration: {years:.1f} years")
print(f"   Initial Capital: ${strategy.initial_capital:,}")
print(f"   Final Value: ${final_value:,.0f}")
print(f"   Total Return: {total_return:.1f}%")
print(f"   Annualized Return: {annualized_return:.1f}%")

# Compare to SPY
spy_total_return = (spy_end - spy_start) / spy_start * 100
spy_annualized = (spy_end / spy_start) ** (1/years) - 1

print(f"\n📊 SPY COMPARISON:")
print(f"   SPY Total Return: {spy_total_return:.1f}%")
print(f"   SPY Annualized: {spy_annualized:.1f}%")
print(f"   LEAP vs SPY: {total_return / spy_total_return:.1f}x leverage")

# Time in market analysis
invested_days = (results['num_positions'] > 0).sum()
total_days = len(results)
time_invested = invested_days / total_days

print(f"\n⏰ TIME IN MARKET:")
print(f"   Days invested: {invested_days:,} / {total_days:,}")
print(f"   Time invested: {time_invested:.1%}")
print(f"   Cash due to volatility: {(1 - time_invested):.1%}")

# Trade analysis
if len(strategy.trades) > 0:
    trades_df = pd.DataFrame(strategy.trades)
    
    leap_buys = trades_df[trades_df['action'] == 'buy_leap']
    leap_closes = trades_df[trades_df['action'].str.contains('close_leap')]
    
    print(f"\n🔧 TRADE SUMMARY:")
    print(f"   Total Trades: {len(trades_df)}")
    print(f"   LEAP Purchases: {len(leap_buys)}")
    print(f"   LEAP Closes: {len(leap_closes)}")
    
    if len(leap_closes) > 0:
        winners = leap_closes[leap_closes['pnl'] > 0]
        win_rate = len(winners) / len(leap_closes)
        avg_pnl_pct = leap_closes['pnl_pct'].mean()
        
        print(f"   Win Rate: {win_rate:.1%}")
        print(f"   Average P&L: {avg_pnl_pct:.1f}%")
        
        # Breakdown by exit reason
        vol_exits = leap_closes[leap_closes['reason'] == 'vol_exit']
        theta_rolls = leap_closes[leap_closes['reason'] == 'theta_roll']
        
        print(f"\n📋 EXIT REASONS:")
        print(f"   Volatility Exits: {len(vol_exits)} (Avg P&L: {vol_exits['pnl_pct'].mean():.1f}%)")
        print(f"   Theta Rolls: {len(theta_rolls)} (Avg P&L: {theta_rolls['pnl_pct'].mean():.1f}%)")

# Check open positions
if len(strategy.positions) > 0:
    current_pos_value = results['position_value'].iloc[-1]
    
    print(f"\n🔓 OPEN POSITIONS:")
    print(f"   Positions: {len(strategy.positions)}")
    print(f"   Total Value: ${current_pos_value:.0f}")
    
    for pos in strategy.positions:
        entry_cost = pos['price'] * 100
        current_value = current_pos_value  # Simplification for display
        unrealized_pnl_pct = (current_value - entry_cost) / entry_cost * 100
        
        print(f"   ${pos['strike']:.0f} LEAP: Entry ${pos['price']:.2f}, "
              f"Unrealized: {unrealized_pnl_pct:.1f}%")

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")