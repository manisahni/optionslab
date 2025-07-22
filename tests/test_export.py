#!/usr/bin/env python3
"""
Test export functionality
"""

from optionslab.backtest_engine import run_auditable_backtest
import yaml
import os
from pathlib import Path
import pandas as pd
import json

def test_export_functionality():
    """Test CSV and JSON export"""
    print("\n" + "="*60)
    print("EXPORT FUNCTIONALITY TEST")
    print("="*60)
    
    # Create test strategy with export enabled
    export_config = {
        'name': 'Export Test Strategy',
        'description': 'Tests export functionality',
        'strategy_type': 'long_call',
        'parameters': {
            'initial_capital': 50000,
            'position_size': 0.20,
            'max_positions': 2,
            'max_hold_days': 10,
            'entry_frequency': 3
        },
        'exit_rules': [
            {'condition': 'profit_target', 'target_percent': 30},
            {'condition': 'stop_loss', 'stop_percent': -15},
            {'condition': 'time_stop', 'max_days': 10}
        ],
        # Enable export
        'export_results': True,
        'export_format': ['csv', 'json'],
        'export_dir': 'test_exports'
    }
    
    # Save config
    with open('export_test_strategy.yaml', 'w') as f:
        yaml.dump(export_config, f)
    
    # Run backtest
    print("\n🔍 Running backtest with export enabled...")
    results = run_auditable_backtest(
        "spy_options_downloader/spy_options_parquet",
        'export_test_strategy.yaml',
        "2022-08-01",
        "2022-08-15"  # Short period for testing
    )
    
    if results:
        print("\n📊 Checking exported files...")
        
        export_dir = Path('test_exports')
        if export_dir.exists():
            files = list(export_dir.glob('*'))
            print(f"\n✅ Found {len(files)} exported files:")
            
            csv_files = []
            json_files = []
            
            for file in files:
                print(f"  - {file.name}")
                if file.suffix == '.csv':
                    csv_files.append(file)
                elif file.suffix == '.json':
                    json_files.append(file)
            
            # Verify CSV files
            if csv_files:
                print("\n📄 CSV Files:")
                for csv_file in csv_files:
                    if 'trades' in csv_file.name:
                        df = pd.read_csv(csv_file)
                        print(f"  - Trades CSV: {len(df)} rows, {len(df.columns)} columns")
                        print(f"    Columns: {', '.join(df.columns[:5])}...")
                    elif 'equity' in csv_file.name:
                        df = pd.read_csv(csv_file)
                        print(f"  - Equity CSV: {len(df)} rows")
                        print(f"    Columns: {', '.join(df.columns)}")
                    elif 'summary' in csv_file.name:
                        df = pd.read_csv(csv_file)
                        print(f"  - Summary CSV:")
                        for _, row in df.iterrows():
                            print(f"    {row['Metric']}: {row['Value']}")
            
            # Verify JSON files
            if json_files:
                print("\n📄 JSON Files:")
                for json_file in json_files:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    
                    print(f"  - Full results JSON:")
                    print(f"    Metadata: {data['metadata']['strategy_name']}")
                    print(f"    Date range: {data['metadata']['start_date']} to {data['metadata']['end_date']}")
                    print(f"    Results: {len(data['trades'])} trades")
                    print(f"    Final return: {data['results']['total_return']:.2%}")
            
            # Clean up test files
            print("\n🧹 Cleaning up test files...")
            import shutil
            shutil.rmtree(export_dir)
            print("✅ Test export directory removed")
        else:
            print("❌ Export directory not created!")
    
    # Clean up strategy file
    if os.path.exists('export_test_strategy.yaml'):
        os.remove('export_test_strategy.yaml')
    
    print("\n✅ Export functionality test completed!")

if __name__ == "__main__":
    test_export_functionality()