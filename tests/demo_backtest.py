#!/usr/bin/env python3
"""
Demo script showing the refactored system in action
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optionslab.backtest_engine import run_auditable_backtest


def main():
    """Run a demo backtest"""
    print("🚀 OptionsLab Demo Backtest")
    print("=" * 60)
    print("\nThis demonstrates the refactored modular architecture:")
    print("- backtest_engine.py orchestrates the backtest")
    print("- data_loader.py loads market data and configs")
    print("- option_selector.py finds suitable options")
    print("- market_filters.py checks market conditions")
    print("- greek_tracker.py tracks option Greeks")
    print("- trade_recorder.py records all trades")
    print("- exit_conditions.py manages exits")
    print("- backtest_metrics.py calculates performance")
    print("\n" + "=" * 60)
    
    # Configuration
    data_file = "spy_options_downloader/spy_options_parquet/SPY_OPTIONS_2022_COMPLETE.parquet"
    config_file = "simple_test_strategy.yaml"
    start_date = "2022-01-03"
    end_date = "2022-01-31"
    
    print(f"\n📅 Backtesting from {start_date} to {end_date}")
    print(f"📁 Using data: {data_file}")
    print(f"📋 Strategy: {config_file}")
    print("\nRunning backtest...\n")
    
    try:
        # Run the backtest
        results = run_auditable_backtest(
            data_file,
            config_file,
            start_date,
            end_date
        )
        
        if results:
            print("\n✅ Backtest completed successfully!")
            print("\n📊 Performance Summary:")
            print(f"   Initial Capital: ${results.get('initial_capital', 10000):,.2f}")
            print(f"   Final Value: ${results['final_value']:,.2f}")
            print(f"   Total Return: {results['total_return']:.2%}")
            print(f"   Trades Executed: {len(results['trades'])}")
            
            if results['trades']:
                # Show first trade details
                print("\n📈 First Trade Example:")
                trade = results['trades'][0]
                print(f"   Entry Date: {trade['entry_date']}")
                print(f"   Strike: ${trade['strike']}")
                print(f"   Delta: {trade['entry_delta']:.2f}")
                print(f"   DTE: {trade['entry_dte']}")
                
                if 'exit_date' in trade:
                    print(f"   Exit Date: {trade['exit_date']}")
                    print(f"   P&L: ${trade.get('pnl', 0):.2f}")
                    print(f"   Exit Reason: {trade.get('exit_reason', 'N/A')}")
            
            # Show compliance scorecard if available
            if 'compliance_scorecard' in results:
                print("\n✔️  Compliance Scorecard:")
                scorecard = results['compliance_scorecard']
                print(f"   Overall Score: {scorecard.get('overall_score', 0):.1%}")
                print(f"   Delta Compliance: {scorecard.get('delta_compliance', 0):.1%}")
                print(f"   DTE Compliance: {scorecard.get('dte_compliance', 0):.1%}")
        else:
            print("\n❌ Backtest failed - no results returned")
            
    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        print("\nPlease ensure you have the SPY options data downloaded.")
        print("The data should be in: spy_options_downloader/spy_options_parquet/")
        
    except Exception as e:
        print(f"\n❌ Error during backtest: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("\n💡 The Gradio app is available at: http://localhost:7862")
    print("   You can run more detailed backtests there with visualizations!")


if __name__ == "__main__":
    main()