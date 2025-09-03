# %%
"""
PMCC Strategy Simple Optimization - Focus on Sharpe Improvement
==============================================================

Baseline Results (to beat):
- Total Return: 88.86%
- Sharpe Ratio: 1.33
- Max Drawdown: -26.08%

Simple improvements:
1. Better entry timing (VIX-based)
2. Enhanced profit targets
3. Improved position sizing
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Use existing optionslab infrastructure
import sys
sys.path.append('/Users/nish_macbook/trading/daily-optionslab')
from optionslab.data_loader import load_data

print("=" * 60)
print("PMCC SIMPLE OPTIMIZATION")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# %%
class SimplePMCCOptimized:
    """Simplified PMCC with key optimizations"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = []
        self.trades = []
        self.daily_values = []
        
        # LEAP parameters (unchanged from baseline)
        self.leap_dte_min = 365
        self.leap_dte_max = 800
        self.leap_delta_min = 0.70
        self.leap_delta_max = 0.85
        
        # SHORT CALL OPTIMIZATIONS
        self.short_dte_min = 25  # Slightly shorter (was 30)
        self.short_dte_max = 40  # Slightly shorter (was 45)
        self.short_delta_min = 0.20
        self.short_delta_max = 0.30
        
        # ENHANCED PROFIT TARGETS
        self.profit_target_normal = 0.45  # 45% instead of 50%
        self.profit_target_high_vol = 0.60  # Higher target in high vol
        self.roll_dte_threshold = 18  # Roll earlier (was 21)
        
        # Execution costs (realistic)
        self.commission_per_contract = 0.65
        self.slippage_pct = 0.005
        
        # Performance tracking
        self.total_premiums_collected = 0
        self.net_leap_cost = 0
        self.short_call_rolls = 0
        self.leap_rolls = 0
        
    def calculate_vix_proxy(self, df_date):
        """Simple VIX proxy from ATM straddle IV"""
        spy_price = df_date['underlying_price'].iloc[0]
        
        # Find 30-day ATM options
        atm_options = df_date[
            (df_date['dte'].between(25, 35)) &
            (df_date['bid'] > 0) &
            (abs(df_date['strike'] - spy_price) < 10)
        ]
        
        if len(atm_options) == 0:
            return 20.0  # Default VIX
            
        # Use median IV as VIX proxy
        return atm_options['iv'].median() * 100
        
    def should_enter_position(self, df_date):
        """Simple entry logic"""
        # Don't enter if we already have a LEAP
        leap_positions = [p for p in self.positions if p['type'] == 'leap']
        if len(leap_positions) > 0:
            return False
            
        # Simple VIX check - enter when IV is elevated
        vix_proxy = self.calculate_vix_proxy(df_date)
        return vix_proxy > 18.0  # Lower threshold than complex version
        
    def find_best_leap(self, df_date):
        """Find best LEAP candidate"""
        leaps = df_date[
            (df_date['right'] == 'C') &
            (df_date['dte'].between(self.leap_dte_min, self.leap_dte_max)) &
            (df_date['delta'].between(self.leap_delta_min, self.leap_delta_max)) &
            (df_date['bid'] > 0) &
            (df_date['volume'] > 0)
        ].copy()
        
        if len(leaps) == 0:
            return None
            
        # Score: prefer higher delta, shorter DTE, good volume
        leaps['score'] = (
            leaps['delta'] * 0.6 +
            (1 - (leaps['dte'] - self.leap_dte_min) / (self.leap_dte_max - self.leap_dte_min)) * 0.3 +
            np.minimum(leaps['volume'] / 100, 1.0) * 0.1
        )
        
        return leaps.loc[leaps['score'].idxmax()]
        
    def find_best_short_call(self, df_date, leap_strike):
        """Find best short call"""
        shorts = df_date[
            (df_date['right'] == 'C') &
            (df_date['dte'].between(self.short_dte_min, self.short_dte_max)) &
            (df_date['delta'].between(self.short_delta_min, self.short_delta_max)) &
            (df_date['strike'] > leap_strike) &
            (df_date['bid'] > 0) &
            (df_date['volume'] > 0)
        ].copy()
        
        if len(shorts) == 0:
            return None
            
        # Score: prefer good premium, reasonable delta
        shorts['premium_per_delta'] = shorts['mid_price'] / shorts['delta']
        return shorts.loc[shorts['premium_per_delta'].idxmax()]
        
    def execute_trade(self, option_data, quantity, is_buy=True):
        """Execute with slippage and commission"""
        if is_buy:
            fill_price = option_data['ask'] * (1 + self.slippage_pct)
        else:
            fill_price = option_data['bid'] * (1 - self.slippage_pct)
            
        total_cost = fill_price * quantity * 100 + self.commission_per_contract
        return fill_price, total_cost
        
    def manage_positions(self, df_date):
        """Manage existing positions"""
        to_close = []
        vix_proxy = self.calculate_vix_proxy(df_date)
        
        for i, pos in enumerate(self.positions):
            # Find current option data
            current_option = df_date[
                (df_date['strike'] == pos['strike']) &
                (df_date['right'] == 'C') &
                (df_date['expiration'] == pos['expiration'])
            ]
            
            if len(current_option) == 0:
                continue
                
            option_data = current_option.iloc[0]
            pos['current_price'] = option_data['mid_price']
            
            if pos['type'] == 'short_call':
                # Calculate profit
                profit_pct = (pos['entry_price'] - option_data['mid_price']) / pos['entry_price']
                
                # ENHANCED PROFIT TARGET LOGIC
                target = self.profit_target_high_vol if vix_proxy > 25 else self.profit_target_normal
                
                if profit_pct >= target:
                    to_close.append(('close_profit', i))
                elif option_data['dte'] <= self.roll_dte_threshold:
                    to_close.append(('roll_time', i))
                    
            elif pos['type'] == 'leap':
                # LEAP management - roll if delta decayed or near expiration
                if option_data['dte'] < 60 or option_data['delta'] < 0.60:
                    to_close.append(('roll_leap', i))
                    
        return to_close
        
    def process_closes(self, closes, df_date):
        """Process closes and rolls"""
        for action, pos_idx in closes:
            if pos_idx >= len(self.positions):
                continue
                
            pos = self.positions[pos_idx]
            option_data = df_date[
                (df_date['strike'] == pos['strike']) &
                (df_date['right'] == 'C') &
                (df_date['expiration'] == pos['expiration'])
            ].iloc[0]
            
            if pos['type'] == 'short_call':
                # Close short call
                fill_price, cost = self.execute_trade(option_data, abs(pos['quantity']), is_buy=True)
                pnl = (pos['entry_price'] - fill_price) * abs(pos['quantity']) * 100 - self.commission_per_contract
                
                self.cash += pnl
                self.total_premiums_collected += max(0, pnl)
                
                reason = "Profit" if action == 'close_profit' else "Time"
                profit_pct = (pos['entry_price'] - fill_price) / pos['entry_price'] * 100
                
                print(f"📉 {option_data['date'].date()}: Closed ${pos['strike']} call, P&L: ${pnl:.0f} "
                      f"({reason}: {profit_pct:.1f}%)")
                
                # Record trade
                self.trades.append({
                    'date': option_data['date'],
                    'action': 'close_short',
                    'strike': pos['strike'],
                    'pnl': pnl,
                    'reason': action
                })
                
                if action == 'roll_time':
                    self.short_call_rolls += 1
                    # Try to open new short call
                    leap_pos = next((p for p in self.positions if p['type'] == 'leap'), None)
                    if leap_pos:
                        new_short = self.find_best_short_call(df_date, leap_pos['strike'])
                        if new_short is not None:
                            self.open_short_call(new_short)
                            
            elif pos['type'] == 'leap' and action == 'roll_leap':
                # Roll LEAP
                fill_price, proceeds = self.execute_trade(option_data, pos['quantity'], is_buy=False)
                pnl = (fill_price - pos['entry_price']) * pos['quantity'] * 100 - self.commission_per_contract
                
                self.cash += pnl
                print(f"🔄 {option_data['date'].date()}: Rolled LEAP ${pos['strike']}, P&L: ${pnl:.0f}")
                
                self.leap_rolls += 1
                
                # Try to open new LEAP
                new_leap = self.find_best_leap(df_date)
                if new_leap is not None:
                    self.open_leap(new_leap)
                    
        # Remove closed positions
        self.positions = [pos for i, pos in enumerate(self.positions) if i not in [idx for _, idx in closes]]
        
    def open_leap(self, leap_data):
        """Open LEAP position"""
        quantity = 1  # Simple: always 1 contract
        fill_price, cost = self.execute_trade(leap_data, quantity, is_buy=True)
        
        if cost > self.cash:
            return False
            
        self.cash -= cost
        self.net_leap_cost += cost
        
        print(f"📈 {leap_data['date'].date()}: Bought LEAP ${leap_data['strike']} @ ${fill_price:.2f} "
              f"(DTE: {leap_data['dte']}, Delta: {leap_data['delta']:.3f})")
        
        self.positions.append({
            'type': 'leap',
            'date': leap_data['date'],
            'strike': leap_data['strike'],
            'expiration': leap_data['expiration'],
            'quantity': quantity,
            'entry_price': fill_price,
            'current_price': fill_price
        })
        
        self.trades.append({
            'date': leap_data['date'],
            'action': 'buy_leap',
            'strike': leap_data['strike'],
            'price': fill_price,
            'cost': cost
        })
        
        return True
        
    def open_short_call(self, call_data):
        """Open short call position"""
        quantity = 1
        fill_price, proceeds = self.execute_trade(call_data, quantity, is_buy=False)
        
        self.cash -= proceeds  # proceeds is negative (we receive cash)
        self.total_premiums_collected += abs(proceeds)
        
        print(f"📝 {call_data['date'].date()}: Sold call ${call_data['strike']} @ ${fill_price:.2f} "
              f"(DTE: {call_data['dte']}, Delta: {call_data['delta']:.3f})")
        
        self.positions.append({
            'type': 'short_call',
            'date': call_data['date'],
            'strike': call_data['strike'],
            'expiration': call_data['expiration'],
            'quantity': -quantity,
            'entry_price': fill_price,
            'current_price': fill_price
        })
        
        self.trades.append({
            'date': call_data['date'],
            'action': 'sell_call',
            'strike': call_data['strike'],
            'price': fill_price,
            'proceeds': abs(proceeds)
        })
        
        return True
        
    def calculate_portfolio_value(self, df_date):
        """Calculate current portfolio value"""
        total_value = self.cash
        
        for pos in self.positions:
            option_data = df_date[
                (df_date['strike'] == pos['strike']) &
                (df_date['right'] == 'C') &
                (df_date['expiration'] == pos['expiration'])
            ]
            
            if len(option_data) > 0:
                current_price = option_data.iloc[0]['mid_price']
                position_value = current_price * pos['quantity'] * 100
                total_value += position_value
                
        return total_value
        
    def run_backtest(self, df):
        """Run optimized backtest"""
        dates = sorted(df['date'].unique())
        
        for date in dates:
            df_date = df[df['date'] == date].copy()
            
            # Manage existing positions
            closes = self.manage_positions(df_date)
            self.process_closes(closes, df_date)
            
            # Check for new entries
            if self.should_enter_position(df_date):
                leap_candidate = self.find_best_leap(df_date)
                if leap_candidate is not None:
                    if self.open_leap(leap_candidate):
                        # Try to open short call
                        short_candidate = self.find_best_short_call(df_date, leap_candidate['strike'])
                        if short_candidate is not None:
                            self.open_short_call(short_candidate)
            
            # Record daily value
            total_value = self.calculate_portfolio_value(df_date)
            spy_price = df_date['underlying_price'].iloc[0]
            
            self.daily_values.append({
                'date': date,
                'spy_price': spy_price,
                'total_value': total_value,
                'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100,
                'positions': len(self.positions)
            })
            
        return pd.DataFrame(self.daily_values)

# %%
# Load data
print("\nLoading data...")
df = load_data("data/spy_options/", "2023-01-01", "2024-12-31")
print(f"✅ Loaded {len(df):,} records")

# Calculate DTE (days to expiration) and mid price
df['dte'] = (df['expiration'] - df['date']).dt.days
df['mid_price'] = (df['bid'] + df['ask']) / 2
print(f"✅ Calculated DTE and mid prices")

# %%
# Run backtest
print("\n" + "="*40)
print("RUNNING OPTIMIZED PMCC BACKTEST")
print("="*40)

strategy = SimplePMCCOptimized()
results = strategy.run_backtest(df)

# %%
# Calculate metrics
final_value = results['total_value'].iloc[-1]
total_return = results['return_pct'].iloc[-1]
returns = results['total_value'].pct_change().dropna()
sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
max_dd = ((results['total_value'].cummax() - results['total_value']) / results['total_value'].cummax()).max() * 100

# SPY benchmark
spy_return = (results['spy_price'].iloc[-1] - results['spy_price'].iloc[0]) / results['spy_price'].iloc[0] * 100

print(f"\n📊 OPTIMIZATION RESULTS")
print("="*50)
print(f"Final Value:        ${final_value:,.2f}")
print(f"Total Return:       {total_return:.2f}%")
print(f"Sharpe Ratio:       {sharpe:.2f}")
print(f"Max Drawdown:       {max_dd:.2f}%")
print(f"Total Trades:       {len(strategy.trades)}")
print(f"Premiums Collected: ${strategy.total_premiums_collected:.2f}")
print(f"Short Call Rolls:   {strategy.short_call_rolls}")
print(f"LEAP Rolls:         {strategy.leap_rolls}")

print(f"\n📈 COMPARISON")
print("="*30)
print(f"SPY Return:         {spy_return:.2f}%")
print(f"Strategy Return:    {total_return:.2f}%")
print(f"Excess Return:      {total_return - spy_return:.2f}%")

# Baseline comparison
baseline_return = 88.86
baseline_sharpe = 1.33

print(f"\n🎯 VS BASELINE")
print("="*30)
print(f"Baseline Return:    {baseline_return:.2f}%")
print(f"Optimized Return:   {total_return:.2f}%")
print(f"Return Improvement: {total_return - baseline_return:+.2f}%")
print(f"")
print(f"Baseline Sharpe:    {baseline_sharpe:.2f}")
print(f"Optimized Sharpe:   {sharpe:.2f}")
print(f"Sharpe Improvement: {sharpe - baseline_sharpe:+.2f}")

# %%
# Visualization
fig = go.Figure()

# Strategy performance
fig.add_trace(go.Scatter(
    x=results['date'],
    y=results['total_value'],
    mode='lines',
    name='Optimized PMCC',
    line=dict(color='green', width=2)
))

# SPY benchmark
spy_values = results['spy_price'] / results['spy_price'].iloc[0] * strategy.initial_capital
fig.add_trace(go.Scatter(
    x=results['date'],
    y=spy_values,
    mode='lines',
    name='SPY Buy & Hold',
    line=dict(color='blue', width=2)
))

# Initial capital reference
fig.add_hline(y=strategy.initial_capital, line_dash="dash", line_color="gray")

fig.update_layout(
    title=f'PMCC Optimization Results (Sharpe: {sharpe:.2f})',
    xaxis_title='Date',
    yaxis_title='Portfolio Value ($)',
    height=500
)

fig.show()

print(f"\n✅ {'SUCCESS' if sharpe > baseline_sharpe else 'NEEDS MORE WORK'}: "
      f"Sharpe improved by {sharpe - baseline_sharpe:+.2f}")