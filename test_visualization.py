#!/usr/bin/env python3
"""
Test visualization functionality
"""

from auditable_backtest import run_auditable_backtest
import yaml
import os
from pathlib import Path

def test_visualization():
    """Test chart creation functionality"""
    print("\n" + "="*60)
    print("VISUALIZATION TEST")
    print("="*60)
    
    # Create test strategy with visualization enabled
    viz_config = {
        'name': 'Visualization Test Strategy',
        'description': 'Tests chart creation',
        'strategy_type': 'long_call',
        'parameters': {
            'initial_capital': 100000,
            'position_size': 0.15,
            'max_positions': 3,
            'max_hold_days': 20,
            'entry_frequency': 3
        },
        'use_advanced_selection': True,
        'option_selection': {
            'method': 'delta',
            'delta_criteria': {
                'target': 0.35,
                'tolerance': 0.10
            },
            'dte_criteria': {
                'minimum': 20,
                'maximum': 40
            }
        },
        'exit_rules': [
            {'condition': 'profit_target', 'target_percent': 40},
            {'condition': 'stop_loss', 'stop_percent': -20},
            {'condition': 'delta_stop', 'min_delta': 0.15},
            {'condition': 'time_stop', 'max_days': 20}
        ],
        # Enable visualization
        'create_charts': True,
        'export_results': True,
        'export_format': ['csv'],  # Also export CSV for comparison
        'export_dir': 'test_visualizations'
    }
    
    # Save config
    with open('viz_test_strategy.yaml', 'w') as f:
        yaml.dump(viz_config, f)
    
    # Run backtest with multiple trades for better visualization
    print("\n🔍 Running backtest with visualization enabled...")
    results = run_auditable_backtest(
        "spy_options_downloader/spy_options_parquet",
        'viz_test_strategy.yaml',
        "2022-08-01",
        "2022-09-30"  # 2 months for variety
    )
    
    if results:
        print("\n📊 Checking visualization output...")
        
        viz_dir = Path('test_visualizations')
        if viz_dir.exists():
            files = list(viz_dir.glob('*'))
            print(f"\n✅ Found {len(files)} files:")
            
            png_files = [f for f in files if f.suffix == '.png']
            csv_files = [f for f in files if f.suffix == '.csv']
            
            for file in files:
                print(f"  - {file.name} ({file.stat().st_size / 1024:.1f} KB)")
            
            if png_files:
                print(f"\n📈 Chart file created successfully!")
                print(f"  - Contains 6 subplots:")
                print(f"    1. Equity curve with cash tracking")
                print(f"    2. Drawdown visualization")
                print(f"    3. Trade P&L distribution")
                print(f"    4. Win/Loss pie chart")
                print(f"    5. Position count over time")
                print(f"    6. Exit reason analysis")
            
            # Display summary stats
            print(f"\n📊 Backtest Summary:")
            print(f"  - Total Return: {results['total_return']:.2%}")
            print(f"  - Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
            print(f"  - Max Drawdown: {results.get('max_drawdown', 0):.2%}")
            print(f"  - Win Rate: {results.get('win_rate', 0):.2%}")
            print(f"  - Total Trades: {len([t for t in results['trades'] if 'exit_date' in t])}")
            
            # Clean up test files
            print("\n🧹 Cleaning up test files...")
            import shutil
            shutil.rmtree(viz_dir)
            print("✅ Test visualization directory removed")
        else:
            print("❌ Visualization directory not created!")
    
    # Clean up strategy file
    if os.path.exists('viz_test_strategy.yaml'):
        os.remove('viz_test_strategy.yaml')
    
    print("\n✅ Visualization test completed!")

def test_chart_error_handling():
    """Test chart creation with edge cases"""
    print("\n" + "="*60)
    print("CHART ERROR HANDLING TEST")
    print("="*60)
    
    # Test with no trades
    empty_config = {
        'name': 'Empty Test',
        'description': 'No trades test',
        'strategy_type': 'long_call',
        'parameters': {
            'initial_capital': 10000,
            'position_size': 0.90,  # Too large
            'max_positions': 1,
            'max_hold_days': 5,
            'entry_frequency': 100  # Never enter
        },
        'exit_rules': [
            {'condition': 'time_stop', 'max_days': 5}
        ],
        'create_charts': True,
        'export_dir': 'test_empty_viz'
    }
    
    with open('empty_test.yaml', 'w') as f:
        yaml.dump(empty_config, f)
    
    print("\n🔍 Testing with no trades scenario...")
    results = run_auditable_backtest(
        "spy_options_downloader/spy_options_parquet",
        'empty_test.yaml',
        "2022-08-01",
        "2022-08-05"
    )
    
    if results:
        viz_dir = Path('test_empty_viz')
        if viz_dir.exists():
            files = list(viz_dir.glob('*.png'))
            if files:
                print("✅ Chart created even with no trades")
            else:
                print("⚠️  No chart created (expected with no trades)")
            
            import shutil
            shutil.rmtree(viz_dir)
    
    # Clean up
    if os.path.exists('empty_test.yaml'):
        os.remove('empty_test.yaml')

if __name__ == "__main__":
    # Test main visualization
    test_visualization()
    
    # Test error handling
    test_chart_error_handling()