# 📋 GOLDEN CHECKLIST: Options Backtesting Standards

This is the definitive checklist for ALL options backtests. Follow these steps IN ORDER to ensure accurate, reproducible results.

## 1. Data Quality Checks

**Requirements:**
- ✅ Verify option chain data exists for every trade day
- ✅ Log missing/partial days (don't silently skip)
- ✅ Confirm bid ≤ mid ≤ ask, and spreads aren't excessive
- ✅ Ensure option timestamps are at or before market close (no lookahead)

```python
def validate_option_chain(df, trade_dates):
    """Complete data quality validation"""
    issues = []
    
    # Check for missing trade days
    missing_days = set(trade_dates) - set(df['date'].unique())
    if missing_days:
        issues.append(f"Missing data for {len(missing_days)} days: {sorted(missing_days)[:5]}...")
    
    # Validate bid/ask/mid relationships
    invalid_spreads = df[(df['bid'] > df['mid_price']) | (df['mid_price'] > df['ask'])]
    if len(invalid_spreads) > 0:
        issues.append(f"Found {len(invalid_spreads)} records with invalid bid/ask/mid")
    
    # Check for excessive spreads
    df['spread_pct'] = (df['ask'] - df['bid']) / df['mid_price'] * 100
    wide_spreads = df[df['spread_pct'] > 20]
    if len(wide_spreads) > 0:
        issues.append(f"Found {len(wide_spreads)} options with >20% spread")
    
    # Verify no lookahead bias
    if 'timestamp' in df.columns:
        after_close = df[pd.to_datetime(df['timestamp']).dt.hour >= 16]
        if len(after_close) > 0:
            issues.append(f"Found {len(after_close)} records after market close")
    
    return issues
```

## 2. Underlying Alignment

**Requirements:**
- ✅ Fetch underlying price (e.g., SPY) for same timestamp window
- ✅ Cross-check against external source to catch stale data

```python
def align_underlying(options_df, underlying_df):
    """Ensure underlying prices match option data dates"""
    # Merge underlying prices with options data
    merged = options_df.merge(
        underlying_df[['date', 'close']].rename(columns={'close': 'spy_close'}),
        on='date',
        how='left'
    )
    
    # Check for mismatches
    if merged['spy_close'].isna().any():
        missing_dates = merged[merged['spy_close'].isna()]['date'].unique()
        print(f"⚠️ Missing underlying data for {len(missing_dates)} dates")
    
    # Validate against option's underlying_price field
    price_diff = abs(merged['underlying_price'] - merged['spy_close'])
    if (price_diff > 0.50).any():
        print(f"⚠️ Found {(price_diff > 0.50).sum()} days with >$0.50 price discrepancy")
    
    return merged
```

## 3. Strike & Expiry Selection

**Requirements:**
- ✅ Apply clear, documented rule (delta target, % moneyness, DTE window)
- ✅ Check liquidity: OI, volume, and spread thresholds
- ✅ Record why each contract was selected

```python
def select_option_contract(df, target_delta=0.30, min_volume=10, max_spread_pct=10):
    """Select option with clear criteria and logging"""
    candidates = df[
        (df['volume'] >= min_volume) &
        (df['spread_pct'] <= max_spread_pct)
    ].copy()
    
    if len(candidates) == 0:
        return None, "No liquid options found"
    
    # Find closest to target delta
    candidates['delta_diff'] = abs(candidates['delta'] - target_delta)
    best = candidates.nsmallest(1, 'delta_diff').iloc[0]
    
    reason = f"Selected strike ${best['strike']:.0f} with delta {best['delta']:.3f} (target: {target_delta})"
    return best, reason
```

## 4. Pricing & Fills

**Requirements:**
- ✅ Decide on fill rule (mid, bid/ask conservative, mid ± slippage)
- ✅ Round to valid tick size before multiplying by 100× contract multiplier
- ✅ Deduct commissions/fees per contract at entry/exit

```python
def calculate_fill_price(option, direction='buy', fill_rule='mid_slippage', slippage_pct=0.5):
    """Calculate realistic fill price with proper rounding"""
    if fill_rule == 'mid':
        fill = option['mid_price']
    elif fill_rule == 'mid_slippage':
        slippage = option['mid_price'] * (slippage_pct / 100)
        fill = option['mid_price'] + slippage if direction == 'buy' else option['mid_price'] - slippage
    elif fill_rule == 'conservative':
        fill = option['ask'] if direction == 'buy' else option['bid']
    
    # Round to nearest nickel for options < $3, dime otherwise
    if fill < 3:
        fill = round(fill * 20) / 20  # Nearest $0.05
    else:
        fill = round(fill * 10) / 10  # Nearest $0.10
    
    # Add commission (e.g., $0.65 per contract)
    commission_per_contract = 0.65
    total_cost = (fill * 100) + commission_per_contract
    
    return fill, total_cost
```

## 5. Position Tracking & P&L

**Requirements:**
- ✅ Track daily mark-to-market values until expiry/exit
- ✅ Compute both realized and unrealized P&L
- ✅ Always scale by contract multiplier (100) for dollars
- ✅ Reconcile expiry payoff against theoretical payoff

```python
class PositionTracker:
    def __init__(self):
        self.positions = []
        self.closed_trades = []
    
    def open_position(self, date, option, contracts=1, fill_price=None):
        """Open new position with proper scaling"""
        if fill_price is None:
            fill_price = option['mid_price']
        
        position = {
            'entry_date': date,
            'strike': option['strike'],
            'expiration': option['expiration'],
            'type': option['right'],
            'contracts': contracts,
            'entry_price': fill_price,
            'entry_cost': fill_price * 100 * contracts,  # ALWAYS multiply by 100
            'current_value': fill_price * 100 * contracts,
            'unrealized_pnl': 0
        }
        self.positions.append(position)
        return position
    
    def mark_to_market(self, date, options_df):
        """Update all positions to current market prices"""
        for pos in self.positions:
            current = options_df[
                (options_df['date'] == date) &
                (options_df['strike'] == pos['strike']) &
                (options_df['expiration'] == pos['expiration'])
            ]
            
            if len(current) > 0:
                current_price = current.iloc[0]['mid_price']
                pos['current_value'] = current_price * 100 * pos['contracts']
                pos['unrealized_pnl'] = pos['current_value'] - pos['entry_cost']
    
    def close_position(self, position, exit_price, date):
        """Close position and record realized P&L"""
        exit_value = exit_price * 100 * position['contracts']
        realized_pnl = exit_value - position['entry_cost']
        
        trade = {
            **position,
            'exit_date': date,
            'exit_price': exit_price,
            'exit_value': exit_value,
            'realized_pnl': realized_pnl,
            'pnl_pct': (realized_pnl / position['entry_cost']) * 100
        }
        self.closed_trades.append(trade)
        self.positions.remove(position)
        return trade
```

## 6. Rolls & Exits

**Requirements:**
- ✅ Document exact roll triggers (DTE < X, delta drift, scheduled rebalance)
- ✅ Close old positions before opening new ones
- ✅ Log realized P&L from rolls separately

```python
def check_roll_conditions(position, current_option, spy_price):
    """Check if position needs rolling"""
    reasons = []
    
    # DTE trigger
    current_dte = (position['expiration'] - pd.Timestamp.now()).days
    if current_dte < 120:  # Roll LEAPs at 120 DTE
        reasons.append(f"DTE trigger: {current_dte} days remaining")
    
    # Delta drift (for delta-hedged strategies)
    if abs(current_option['delta'] - 0.80) > 0.15:  # Target was 0.80
        reasons.append(f"Delta drift: current {current_option['delta']:.3f}")
    
    # Profit target
    pnl_pct = (position['unrealized_pnl'] / position['entry_cost']) * 100
    if pnl_pct > 50:
        reasons.append(f"Profit target: {pnl_pct:.1f}% gain")
    
    # Stop loss
    if pnl_pct < -25:
        reasons.append(f"Stop loss: {pnl_pct:.1f}% loss")
    
    return len(reasons) > 0, reasons
```

## 7. Risk & Performance Metrics

**Requirements:**
- ✅ Generate: equity curve, drawdowns, CAGR, Sharpe, Sortino, win/loss ratio
- ✅ Compare against SPY buy-and-hold baseline
- ✅ Track tail losses and maximum adverse excursion

```python
def calculate_performance_metrics(trades_df, equity_curve, spy_returns):
    """Comprehensive performance metrics"""
    metrics = {}
    
    # Basic returns
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    cagr = ((equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (365/days) - 1) * 100
    
    # Risk metrics
    daily_returns = equity_curve.pct_change().dropna()
    sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
    sortino = daily_returns.mean() / daily_returns[daily_returns < 0].std() * np.sqrt(252)
    
    # Drawdown
    rolling_max = equity_curve.expanding().max()
    drawdown = (equity_curve - rolling_max) / rolling_max * 100
    max_dd = drawdown.min()
    
    # Win/loss statistics
    wins = trades_df[trades_df['realized_pnl'] > 0]
    losses = trades_df[trades_df['realized_pnl'] < 0]
    win_rate = len(wins) / len(trades_df) * 100
    
    # Tail risk
    var_95 = daily_returns.quantile(0.05) * 100
    cvar_95 = daily_returns[daily_returns <= daily_returns.quantile(0.05)].mean() * 100
    
    metrics = {
        'total_return_pct': total_return,
        'cagr_pct': cagr,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown_pct': max_dd,
        'win_rate_pct': win_rate,
        'avg_win': wins['realized_pnl'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['realized_pnl'].mean() if len(losses) > 0 else 0,
        'var_95_pct': var_95,
        'cvar_95_pct': cvar_95,
        'total_trades': len(trades_df)
    }
    
    # Compare to SPY
    spy_total_return = (spy_returns + 1).prod() - 1
    metrics['excess_return_vs_spy'] = total_return - (spy_total_return * 100)
    
    return metrics
```

## 8. Cent-Dollar Sanity Checks

**Requirements:**
- ✅ Always apply 100× multiplier to option prices
- ✅ Express results in both dollars and % of premium
- ✅ Round fills to nearest tradable tick
- ✅ Adjust for dividends if holding LEAPS

```python
def sanity_check_prices(trades_df):
    """Verify all prices and P&L make sense"""
    checks = []
    
    # Check for unrealistic option prices
    if (trades_df['entry_price'] > 1000).any():
        checks.append("❌ Entry prices > $1000 - likely missing /100 conversion")
    
    # Check for tiny P&L (indicates missing *100 multiplier)
    if (trades_df['realized_pnl'].abs() < 1).any():
        checks.append("❌ P&L < $1 - likely missing *100 multiplier")
    
    # Verify tick sizes
    prices = pd.concat([trades_df['entry_price'], trades_df['exit_price']])
    for price in prices:
        if price < 3 and (price * 20) % 1 != 0:
            checks.append(f"⚠️ Price ${price:.3f} not on $0.05 tick")
        elif price >= 3 and (price * 10) % 1 != 0:
            checks.append(f"⚠️ Price ${price:.3f} not on $0.10 tick")
    
    return checks if checks else ["✅ All price checks passed"]
```

## 9. Validation & Audit

**Requirements:**
- ✅ Spot-check trades manually: entry price, exit payoff, deltas
- ✅ Check put-call parity to detect bad quotes
- ✅ Document % of valid trades vs skipped days
- ✅ Save logs, configs, and metrics for reproducibility

```python
def create_audit_report(backtest_results):
    """Generate comprehensive audit trail"""
    report = {
        'run_date': datetime.now().isoformat(),
        'config': {
            'fill_rule': 'mid_slippage',
            'slippage_pct': 0.5,
            'commission_per_contract': 0.65,
            'target_delta': 0.80,
            'roll_dte_threshold': 120
        },
        'data_quality': {
            'total_days': len(backtest_results['dates']),
            'valid_trades': len(backtest_results['trades']),
            'skipped_days': len(backtest_results['skipped_days']),
            'skip_reasons': backtest_results['skip_reasons']
        },
        'performance': backtest_results['metrics'],
        'sample_trades': backtest_results['trades'].head(5).to_dict('records'),
        'validation_checks': sanity_check_prices(backtest_results['trades'])
    }
    
    # Save to JSON for reproducibility
    with open(f'backtest_audit_{datetime.now():%Y%m%d_%H%M%S}.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    return report
```

## Complete Backtest Template

Use this template as your starting point for any options backtest:

```python
"""
Options Backtest Template - Implements All Golden Checklist Items
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json

class OptionsBacktest:
    def __init__(self, config):
        self.config = config
        self.tracker = PositionTracker()
        self.audit_log = []
    
    def run(self, start_date, end_date):
        # 1. Data Quality Checks
        options_df = self.load_and_validate_data()
        
        # 2. Underlying Alignment
        spy_df = self.load_underlying_data()
        df = align_underlying(options_df, spy_df)
        
        # 3-6. Main backtest loop
        for date in pd.date_range(start_date, end_date, freq='B'):
            if date not in df['date'].values:
                self.audit_log.append(f"Skipped {date}: No data")
                continue
            
            daily_options = df[df['date'] == date]
            
            # Check for rolls/exits
            for position in self.tracker.positions[:]:
                should_roll, reasons = check_roll_conditions(position, daily_options, spy_df)
                if should_roll:
                    self.execute_roll(position, daily_options, reasons)
            
            # New entries
            if len(self.tracker.positions) < self.config['max_positions']:
                self.check_entry_signals(daily_options)
            
            # Mark to market
            self.tracker.mark_to_market(date, daily_options)
        
        # 7. Performance Metrics
        metrics = calculate_performance_metrics(
            pd.DataFrame(self.tracker.closed_trades),
            self.get_equity_curve(),
            spy_df['returns']
        )
        
        # 8-9. Validation & Audit
        audit = create_audit_report({
            'dates': df['date'].unique(),
            'trades': pd.DataFrame(self.tracker.closed_trades),
            'metrics': metrics,
            'skipped_days': self.audit_log
        })
        
        return metrics, audit

# Run backtest
config = {
    'max_positions': 1,
    'target_delta': 0.80,
    'fill_rule': 'mid_slippage',
    'slippage_pct': 0.5
}

backtest = OptionsBacktest(config)
results, audit = backtest.run('2023-01-01', '2024-12-31')
print(json.dumps(audit, indent=2, default=str))
```

## 🎯 Quick Reference: Common Pitfalls to Avoid

1. **Forgetting the 100× multiplier** - Option prices must be multiplied by 100 for dollar P&L
2. **Silent data gaps** - Always log when data is missing, don't skip silently
3. **Unrealistic fills** - Use appropriate slippage and respect tick sizes
4. **Ignoring commissions** - $0.65 per contract adds up quickly
5. **No baseline comparison** - Always compare to SPY buy-and-hold
6. **Missing roll costs** - Each roll has transaction costs and slippage
7. **Lookahead bias** - Ensure you can't see future data
8. **Survivorship bias** - Include delisted options in historical data

## Strategy Comparison Framework

Always compare against these benchmarks:
1. **Buy & Hold SPY** - Market baseline
2. **Pure LEAP** - For leveraged strategies
3. **Strategy variations** - Different parameters