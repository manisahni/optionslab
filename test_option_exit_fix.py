#!/usr/bin/env python3
"""
Test script to verify option exit pricing fix
"""

from auditable_backtest import run_auditable_backtest

def test_option_exit_pricing():
    """Test that options exit at correct prices, not $0"""
    print("\n" + "="*60)
    print("TEST: Option Exit Pricing Fix")
    print("="*60)
    
    data_dir = "spy_options_downloader/spy_options_parquet"
    config_file = "simple_test_strategy.yaml"  # 5-day hold
    start_date = "2022-08-01"
    end_date = "2022-08-08"  # 6 trading days to ensure exit
    
    results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    
    if results and results['trades']:
        print(f"\n📊 Trade Analysis:")
        for i, trade in enumerate(results['trades'], 1):
            if 'exit_date' in trade:
                print(f"\nTrade {i}:")
                print(f"  Entry: {trade['entry_date']} @ ${trade['option_price']:.2f}")
                print(f"  Exit: {trade['exit_date']} @ ${trade['exit_price']:.2f}")
                print(f"  P&L: ${trade['pnl']:.2f}")
                
                # Check if exit price is reasonable (not $0)
                if trade['exit_price'] > 0.01:
                    print(f"  ✅ Exit price looks reasonable")
                else:
                    print(f"  ❌ Exit price is too low (possible bug)")
        
        # Check equity curve
        print(f"\n📈 Equity Curve:")
        print(f"{'Date':^12} | {'Cash':^10} | {'Pos Value':^10} | {'Total':^10}")
        print("-" * 50)
        for point in results['equity_curve']:
            print(f"{point['date']} | ${point['cash']:8,.0f} | ${point['position_value']:8,.0f} | ${point['total_value']:8,.0f}")
    
    return results

if __name__ == "__main__":
    test_option_exit_pricing()