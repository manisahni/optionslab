#!/usr/bin/env python3
"""
Performance benchmark test for the backtesting system
Tests execution time and memory usage with large datasets
"""

import time
import psutil
import os
from optionslab.backtest_engine import run_auditable_backtest

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def benchmark_backtest(period_days, max_positions=1):
    """Run a benchmark test for specified period"""
    print(f"\n🔍 Benchmarking {period_days}-day backtest with {max_positions} max positions...")
    
    # Simple strategy for consistent benchmarking
    strategy = {
        'name': f'Benchmark {period_days} days',
        'description': 'Performance benchmark strategy',
        'strategy_type': 'long_call',
        'parameters': {
            'initial_capital': 100000,
            'position_size': 0.1,
            'max_positions': max_positions,
            'max_hold_days': 21,
            'entry_frequency': 5
        },
        'exit_rules': [
            {'condition': 'profit_target', 'target_percent': 50},
            {'condition': 'stop_loss', 'stop_percent': -25},
            {'condition': 'time_stop', 'max_days': 21}
        ]
    }
    
    import yaml
    config_file = f'benchmark_{period_days}d.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(strategy, f)
    
    # Define date ranges
    periods = {
        30: ("2022-08-01", "2022-08-31"),
        90: ("2022-07-01", "2022-09-30"),
        180: ("2022-04-01", "2022-09-30"),
        365: ("2022-01-01", "2022-12-31")
    }
    
    if period_days not in periods:
        print(f"❌ Invalid period: {period_days} days")
        return None
    
    start_date, end_date = periods[period_days]
    
    # Measure performance
    start_memory = get_memory_usage()
    start_time = time.time()
    
    # Suppress output for benchmarking
    import sys
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    
    try:
        results = run_auditable_backtest(
            "spy_options_downloader/spy_options_parquet",
            config_file,
            start_date,
            end_date
        )
        
        execution_time = time.time() - start_time
        end_memory = get_memory_usage()
        memory_used = end_memory - start_memory
        
        # Restore stdout
        sys.stdout = old_stdout
        
        # Calculate metrics
        if results:
            num_days = len(results['equity_curve'])
            num_trades = len(results['trades'])
            
            print(f"  ⏱️  Execution Time: {execution_time:.2f}s")
            print(f"  💾 Memory Used: {memory_used:.1f} MB")
            print(f"  📅 Days Processed: {num_days}")
            print(f"  📊 Trades Executed: {num_trades}")
            print(f"  ⚡ Speed: {num_days/execution_time:.1f} days/second")
            
            # Clean up
            os.remove(config_file)
            
            return {
                'period_days': period_days,
                'execution_time': execution_time,
                'memory_used': memory_used,
                'days_processed': num_days,
                'trades': num_trades,
                'speed': num_days/execution_time
            }
    except Exception as e:
        sys.stdout = old_stdout
        print(f"  ❌ Error: {e}")
        if os.path.exists(config_file):
            os.remove(config_file)
        return None

def main():
    """Run performance benchmarks"""
    print("="*60)
    print("PERFORMANCE BENCHMARK TEST")
    print("="*60)
    
    # Check available data first
    data_dir = "spy_options_downloader/spy_options_parquet"
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        return
    
    # Run benchmarks
    benchmarks = []
    
    # Test different time periods
    for days in [30, 90]:  # Start with shorter periods
        result = benchmark_backtest(days, max_positions=1)
        if result:
            benchmarks.append(result)
    
    # Test with multiple positions (more complex)
    result = benchmark_backtest(30, max_positions=3)
    if result:
        result['test'] = '3 positions'
        benchmarks.append(result)
    
    # Summary
    if benchmarks:
        print(f"\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)
        print(f"{'Test':<20} {'Time(s)':<10} {'Memory(MB)':<12} {'Days/Sec':<10}")
        print("-"*60)
        
        for b in benchmarks:
            test_name = b.get('test', f"{b['period_days']} days")
            print(f"{test_name:<20} {b['execution_time']:<10.2f} {b['memory_used']:<12.1f} {b['speed']:<10.1f}")
        
        # Performance assessment
        avg_speed = sum(b['speed'] for b in benchmarks) / len(benchmarks)
        print(f"\n📊 Average Processing Speed: {avg_speed:.1f} days/second")
        
        if avg_speed > 10:
            print("✅ Excellent performance!")
        elif avg_speed > 5:
            print("✅ Good performance")
        else:
            print("⚠️  Performance could be improved")

if __name__ == "__main__":
    main()