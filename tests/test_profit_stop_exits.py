#!/usr/bin/env python3
"""
Test script for profit target and stop loss exits
"""

from optionslab.backtest_engine import run_auditable_backtest
from datetime import datetime, timedelta

def test_profit_stop_exits():
    """Test profit target and stop loss exit functionality"""
    print("\n" + "="*60)
    print("TEST: Profit Target and Stop Loss Exits")
    print("="*60)
    
    # Test configuration
    data_dir = "spy_options_downloader/spy_options_parquet"
    config_file = "test_profit_stop_strategy.yaml"
    
    # Use a longer date range to see more exit scenarios
    start_date = "2022-08-01"
    end_date = "2022-08-31"  # Full month
    
    print(f"\n📅 Test Period: {start_date} to {end_date}")
    print(f"📝 Strategy: Profit Target = 25%, Stop Loss = -15%")
    print(f"⏰ Max Hold Days = 21 (fallback)")
    
    results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    
    if results and results['trades']:
        print(f"\n" + "="*60)
        print("📊 TRADE ANALYSIS")
        print("="*60)
        
        exit_reasons = {
            'profit_target': 0,
            'stop_loss': 0,
            'time_stop': 0,
            'end_of_period': 0
        }
        
        for i, trade in enumerate(results['trades'], 1):
            if 'exit_date' in trade:
                print(f"\nTrade {i}:")
                print(f"  Entry: {trade['entry_date']} @ ${trade['option_price']:.2f}")
                print(f"  Exit:  {trade['exit_date']} @ ${trade['exit_price']:.2f}")
                print(f"  P&L:   ${trade['pnl']:.2f} ({(trade['pnl']/trade['cost'])*100:.1f}%)")
                
                # Track exit reasons
                exit_reason = trade.get('exit_reason', 'unknown')
                print(f"  Reason: {exit_reason}")
                
                # Categorize exits
                if 'profit target' in exit_reason:
                    exit_reasons['profit_target'] += 1
                    print(f"  ✅ Profit target exit")
                elif 'stop loss' in exit_reason:
                    exit_reasons['stop_loss'] += 1
                    print(f"  🛑 Stop loss exit")
                elif 'time stop' in exit_reason:
                    exit_reasons['time_stop'] += 1
                    print(f"  ⏰ Time-based exit")
                else:
                    exit_reasons['end_of_period'] += 1
                    print(f"  📅 End of period exit")
        
        # Summary statistics
        print(f"\n" + "="*60)
        print("📈 EXIT REASON SUMMARY")
        print("="*60)
        total_exits = sum(exit_reasons.values())
        
        for reason, count in exit_reasons.items():
            if count > 0:
                pct = (count / total_exits) * 100
                print(f"{reason.replace('_', ' ').title():20}: {count:3} ({pct:5.1f}%)")
        
        print(f"\n" + "="*60)
        print("💰 PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Final Value:    ${results['final_value']:,.2f}")
        print(f"Total Return:   {results['total_return']:.2%}")
        print(f"Total Trades:   {len([t for t in results['trades'] if 'exit_date' in t])}")
        
        # Calculate win rate by exit type
        profit_exits = [t for t in results['trades'] if 'exit_date' in t and t['pnl'] > 0]
        loss_exits = [t for t in results['trades'] if 'exit_date' in t and t['pnl'] <= 0]
        
        print(f"Winning Trades: {len(profit_exits)}")
        print(f"Losing Trades:  {len(loss_exits)}")
        
    return results

def test_extreme_scenario():
    """Test with very tight profit/stop to ensure exits trigger quickly"""
    print("\n" + "="*60)
    print("TEST: Extreme Scenario (5% profit / 5% stop)")
    print("="*60)
    
    # Create an extreme test config
    import yaml
    
    extreme_config = {
        'name': 'Extreme Test',
        'description': 'Very tight profit/stop for testing',
        'strategy_type': 'long_call',
        'parameters': {
            'initial_capital': 10000,
            'position_size': 0.1,
            'max_hold_days': 21,
            'entry_frequency': 2
        },
        'exit_rules': [
            {'condition': 'profit_target', 'target_percent': 5},
            {'condition': 'stop_loss', 'stop_percent': -5},
            {'condition': 'time_stop', 'max_days': 21}
        ]
    }
    
    with open('extreme_test_strategy.yaml', 'w') as f:
        yaml.dump(extreme_config, f)
    
    data_dir = "spy_options_downloader/spy_options_parquet"
    start_date = "2022-08-01"
    end_date = "2022-08-15"
    
    results = run_auditable_backtest(data_dir, 'extreme_test_strategy.yaml', start_date, end_date)
    
    if results:
        print(f"\nExtreme test completed:")
        print(f"  Final Value: ${results['final_value']:,.2f}")
        print(f"  Total Return: {results['total_return']:.2%}")

if __name__ == "__main__":
    # Run main test
    test_profit_stop_exits()
    
    # Run extreme scenario test
    test_extreme_scenario()