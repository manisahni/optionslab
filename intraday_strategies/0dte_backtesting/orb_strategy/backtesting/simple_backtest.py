"""
Simplified ORB Backtest
Focus on price action and breakout logic
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import pytz
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))


def run_simple_orb_backtest(data, timeframe_minutes=60, spread_width=15):
    """
    Simple ORB backtest focusing on core logic
    """
    
    trades = []
    
    # Get unique trading days
    trading_days = data.index.normalize().unique()
    
    print(f"Testing {len(trading_days)} trading days with {timeframe_minutes}-min ORB")
    
    for date in trading_days[-90:]:  # Last 90 days
        # Get day's data
        day_data = data[data.index.date == date.date()]
        
        if len(day_data) < 100:  # Skip incomplete days
            continue
        
        # Calculate opening range (9:30 to 10:30 for 60-min)
        market_open = pd.Timestamp.combine(date.date(), time(9, 30))
        or_end = market_open + pd.Timedelta(minutes=timeframe_minutes)
        
        # Handle timezone
        if day_data.index.tz is not None:
            market_open = market_open.tz_localize(day_data.index.tz)
            or_end = or_end.tz_localize(day_data.index.tz)
        
        # Get opening range data
        or_data = day_data[(day_data.index >= market_open) & (day_data.index < or_end)]
        
        if len(or_data) < 10:  # Need enough bars
            continue
        
        # Calculate range
        or_high = or_data['high'].max()
        or_low = or_data['low'].min()
        or_range = or_high - or_low
        
        # Check minimum range (0.2% of price)
        open_price = or_data['open'].iloc[0]
        range_pct = or_range / open_price
        
        if range_pct < 0.002:  # Skip if range too narrow
            continue
        
        # Look for breakout after OR period
        post_or_data = day_data[day_data.index >= or_end]
        
        if post_or_data.empty:
            continue
        
        # Track if we took a trade today
        trade_taken = False
        
        for idx, bar in post_or_data.iterrows():
            if trade_taken:
                break
                
            # Check time - no new trades after 3:30 PM
            if idx.time() > time(15, 30):
                break
            
            current_price = bar['close']
            
            # Bullish breakout
            if current_price > or_high + 0.01:
                # Short put spread entry
                short_strike = round(or_low - 0.01)
                long_strike = short_strike - spread_width
                
                # Estimate P&L (simplified)
                # Assume credit is 35% of spread width
                credit = spread_width * 0.35 * 100  # Per contract
                
                # Simulate exit at 3:59 PM or stop/target
                exit_data = post_or_data[post_or_data.index > idx]
                
                if not exit_data.empty:
                    # Check each bar until close
                    for exit_idx, exit_bar in exit_data.iterrows():
                        if exit_idx.time() >= time(15, 59):
                            # Time exit - check if spread is ITM
                            final_price = exit_bar['close']
                            if final_price > short_strike:
                                # OTM - keep credit
                                pnl = credit * 0.8  # Keep 80% after costs
                            else:
                                # ITM - take loss
                                intrinsic = min(short_strike - final_price, spread_width)
                                pnl = credit - (intrinsic * 100)
                            
                            trades.append({
                                'date': date.date(),
                                'type': 'PUT_SPREAD',
                                'entry_time': idx.time(),
                                'exit_time': exit_idx.time(),
                                'or_range': or_range,
                                'range_pct': range_pct,
                                'pnl': pnl,
                                'exit_reason': 'time'
                            })
                            trade_taken = True
                            break
            
            # Bearish breakout  
            elif current_price < or_low - 0.01:
                # Short call spread entry
                short_strike = round(or_high + 0.01)
                long_strike = short_strike + spread_width
                
                credit = spread_width * 0.35 * 100
                
                # Simulate exit
                exit_data = post_or_data[post_or_data.index > idx]
                
                if not exit_data.empty:
                    for exit_idx, exit_bar in exit_data.iterrows():
                        if exit_idx.time() >= time(15, 59):
                            final_price = exit_bar['close']
                            if final_price < short_strike:
                                # OTM - keep credit
                                pnl = credit * 0.8
                            else:
                                # ITM - take loss
                                intrinsic = min(final_price - short_strike, spread_width)
                                pnl = credit - (intrinsic * 100)
                            
                            trades.append({
                                'date': date.date(),
                                'type': 'CALL_SPREAD',
                                'entry_time': idx.time(),
                                'exit_time': exit_idx.time(),
                                'or_range': or_range,
                                'range_pct': range_pct,
                                'pnl': pnl,
                                'exit_reason': 'time'
                            })
                            trade_taken = True
                            break
    
    return trades


def analyze_results(trades):
    """Analyze backtest results"""
    
    if not trades:
        print("No trades executed")
        return
    
    df = pd.DataFrame(trades)
    
    # Calculate metrics
    total_trades = len(df)
    winning_trades = len(df[df['pnl'] > 0])
    losing_trades = len(df[df['pnl'] <= 0])
    
    win_rate = winning_trades / total_trades
    total_pnl = df['pnl'].sum()
    avg_pnl = df['pnl'].mean()
    
    avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = abs(df[df['pnl'] <= 0]['pnl'].mean()) if losing_trades > 0 else 0
    
    profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades) if losing_trades > 0 else 0
    
    # Max drawdown
    cumulative = df['pnl'].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = cumulative - running_max
    max_dd = drawdown.min()
    
    print("\n" + "="*70)
    print("SIMPLIFIED ORB BACKTEST RESULTS")
    print("="*70)
    
    print(f"\nTotal Trades:    {total_trades}")
    print(f"Winning Trades:  {winning_trades}")
    print(f"Losing Trades:   {losing_trades}")
    print(f"Win Rate:        {win_rate:.1%}")
    
    print(f"\nTotal P&L:       ${total_pnl:,.0f}")
    print(f"Average P&L:     ${avg_pnl:.0f}")
    print(f"Average Win:     ${avg_win:.0f}")
    print(f"Average Loss:    ${avg_loss:.0f}")
    
    print(f"\nProfit Factor:   {profit_factor:.2f}")
    print(f"Max Drawdown:    ${max_dd:,.0f}")
    
    # Trade type breakdown
    print(f"\nTrade Types:")
    print(df['type'].value_counts())
    
    # Average range
    print(f"\nAverage OR Range: ${df['range_pct'].mean():.3%}")
    
    # Show sample trades
    print("\nSample Trades (Last 5):")
    print("-"*70)
    for _, trade in df.tail(5).iterrows():
        print(f"{trade['date']} | {trade['type']:12} | "
              f"{trade['entry_time']} -> {trade['exit_time']} | "
              f"P&L: ${trade['pnl']:>7.0f}")
    
    # Comparison to article
    print("\n" + "="*70)
    print("COMPARISON TO ARTICLE (60-min ORB)")
    print("="*70)
    print(f"{'Metric':<20} {'Article':>15} {'Backtest':>15}")
    print("-"*50)
    print(f"{'Win Rate':<20} {'88.8%':>15} {f'{win_rate:.1%}':>15}")
    print(f"{'Avg P&L':<20} {'$51':>15} {f'${avg_pnl:.0f}':>15}")
    print(f"{'Profit Factor':<20} {'1.59':>15} {f'{profit_factor:.2f}':>15}")
    
    return df


def main():
    """Run simplified backtest"""
    
    print("Loading SPY data...")
    
    # Load data
    data_path = Path('/Users/nish_macbook/0dte/data/SPY.parquet')
    if data_path.exists():
        data = pd.read_parquet(data_path)
        if 'date' in data.columns:
            data.set_index('date', inplace=True)
        print(f"Loaded {len(data)} bars")
    else:
        print("Data not found")
        return
    
    # Run backtests for different timeframes
    for timeframe in [60, 30, 15]:
        print(f"\n{'='*70}")
        print(f"Running {timeframe}-minute ORB backtest...")
        
        trades = run_simple_orb_backtest(data, timeframe_minutes=timeframe)
        
        if trades:
            df = analyze_results(trades)
            
            # Save results
            output_path = f'/Users/nish_macbook/0dte/orb_strategy/data/backtest_results/orb_{timeframe}min_simple.csv'
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(trades).to_csv(output_path, index=False)
            print(f"\nResults saved to: {output_path}")
        else:
            print("No trades found")


if __name__ == "__main__":
    main()