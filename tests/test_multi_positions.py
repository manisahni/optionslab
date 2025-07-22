#!/usr/bin/env python3
"""
Test script for multiple concurrent positions support
"""

from optionslab.backtest_engine import run_auditable_backtest

def test_multi_positions():
    """Test multiple concurrent positions functionality"""
    print("\n" + "="*60)
    print("TEST: Multiple Concurrent Positions")
    print("="*60)
    
    # Test configuration
    data_dir = "spy_options_downloader/spy_options_parquet"
    config_file = "multi_position_test_strategy.yaml"
    
    # Use a period with some volatility
    start_date = "2022-08-01"
    end_date = "2022-08-20"
    
    print(f"\n📅 Test Period: {start_date} to {end_date}")
    print(f"📝 Strategy: Up to 3 concurrent positions")
    print(f"💰 Position Size: 5% each (max 15% total)")
    print(f"🕐 Entry Frequency: Every 2 days")
    
    results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    
    if results and results['trades']:
        print(f"\n" + "="*60)
        print("📊 MULTI-POSITION ANALYSIS")
        print("="*60)
        
        # Track concurrent positions over time
        position_timeline = {}
        
        for trade in results['trades']:
            entry = trade['entry_date']
            exit = trade.get('exit_date', 'ongoing')
            
            # Count positions on each day
            entry_dt = pd.to_datetime(entry)
            exit_dt = pd.to_datetime(exit) if exit != 'ongoing' else pd.to_datetime(end_date)
            
            current = entry_dt
            while current <= exit_dt:
                date_str = current.strftime('%Y-%m-%d')
                position_timeline[date_str] = position_timeline.get(date_str, 0) + 1
                current += pd.Timedelta(days=1)
        
        # Find max concurrent positions
        max_concurrent = max(position_timeline.values()) if position_timeline else 0
        
        print(f"\n📈 Position Statistics:")
        print(f"  Total Trades: {len(results['trades'])}")
        print(f"  Max Concurrent Positions: {max_concurrent}")
        
        # Show trades with overlapping periods
        print(f"\n📋 Trade Timeline:")
        for i, trade in enumerate(results['trades'], 1):
            entry = trade['entry_date']
            exit = trade.get('exit_date', 'ongoing')
            strike = trade.get('strike', 'unknown')
            print(f"  Trade {i}: {entry} to {exit} (Strike: ${strike:.2f})")
        
        # Check equity curve for position counts
        print(f"\n📊 Daily Position Count:")
        for point in results['equity_curve'][-10:]:  # Last 10 days
            print(f"  {point['date']}: {point['positions']} positions, Value: ${point['total_value']:,.2f}")
        
        print(f"\n" + "="*60)
        print("💰 PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Final Value:    ${results['final_value']:,.2f}")
        print(f"Total Return:   {results['total_return']:.2%}")
        
    return results

if __name__ == "__main__":
    import pandas as pd
    test_multi_positions()