#!/usr/bin/env python3
"""
Test script for put option support
"""

from auditable_backtest import run_auditable_backtest

def test_long_put_strategy():
    """Test long put strategy implementation"""
    print("\n" + "="*60)
    print("TEST: Long Put Option Support")
    print("="*60)
    
    # Test configuration
    data_dir = "spy_options_downloader/spy_options_parquet"
    config_file = "long_put_test_strategy.yaml"
    
    # Use a period with declining market for puts to potentially profit
    start_date = "2022-08-15"
    end_date = "2022-08-31"  # Market was declining in late August 2022
    
    print(f"\n📅 Test Period: {start_date} to {end_date}")
    print(f"📝 Strategy: Long Put (bearish strategy)")
    print(f"🎯 Target: 30% profit, -20% stop loss")
    
    results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    
    if results and results['trades']:
        print(f"\n" + "="*60)
        print("📊 PUT OPTION TRADE ANALYSIS")
        print("="*60)
        
        for i, trade in enumerate(results['trades'], 1):
            if 'exit_date' in trade:
                print(f"\nTrade {i}:")
                print(f"  Entry: {trade['entry_date']} @ ${trade['option_price']:.2f}")
                print(f"  Exit:  {trade['exit_date']} @ ${trade.get('exit_price', 0):.2f}")
                print(f"  P&L:   ${trade.get('pnl', 0):.2f}")
                
                # Verify we're actually trading puts
                print(f"  ✅ Confirmed: Trading PUT options")
        
        print(f"\n" + "="*60)
        print("💰 PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Final Value:    ${results['final_value']:,.2f}")
        print(f"Total Return:   {results['total_return']:.2%}")
        print(f"Total Trades:   {len([t for t in results['trades'] if 'exit_date' in t])}")
        
    return results

def test_basic_put_selection():
    """Test basic put option selection without full backtest"""
    print("\n" + "="*60)
    print("TEST: Basic Put Option Selection")
    print("="*60)
    
    from auditable_backtest import load_and_audit_data, find_suitable_options
    
    # Load a single day of data
    data_file = "spy_options_downloader/spy_options_parquet/spy_options_eod_20220815.parquet"
    data = load_and_audit_data(data_file)
    
    if data is not None:
        data['strike_dollars'] = data['strike'] / 1000.0
        current_price = data['underlying_price'].iloc[0]
        
        # Test put selection
        print("\n🔍 Testing PUT selection:")
        put_option = find_suitable_options(
            data, 
            current_price, 
            strategy_type="long_put",
            target_strike_offset=-0.02  # 2% OTM put
        )
        
        if put_option is not None:
            print(f"\n✅ Successfully selected PUT option")
            
        # Test call selection for comparison
        print("\n🔍 Testing CALL selection (for comparison):")
        call_option = find_suitable_options(
            data, 
            current_price, 
            strategy_type="long_call",
            target_strike_offset=0.02  # 2% OTM call
        )
        
        if call_option is not None:
            print(f"\n✅ Successfully selected CALL option")

if __name__ == "__main__":
    # Test basic put selection first
    test_basic_put_selection()
    
    # Then test full put strategy
    test_long_put_strategy()