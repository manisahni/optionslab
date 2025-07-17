#!/usr/bin/env python3
"""
Example usage of the SPY Options Backtester
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta


def run_command(cmd):
    """Run a command and print the result"""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")


def example_basic_strategies():
    """Run examples of basic strategies"""
    print("="*80)
    print("BASIC STRATEGY EXAMPLES")
    print("="*80)
    
    # Example date range (1 year)
    start_date = "20220101"
    end_date = "20221231"
    
    strategies = [
        ("long_call", "Long Call Strategy"),
        ("long_put", "Long Put Strategy"), 
        ("straddle", "Long Straddle Strategy"),
        ("covered_call", "Covered Call Strategy")
    ]
    
    for strategy, description in strategies:
        print(f"\n{'-'*50}")
        print(f"Example: {description}")
        print(f"{'-'*50}")
        
        cmd = [
            "python", "backtester.py",
            "--strategy", strategy,
            "--start-date", start_date,
            "--end-date", end_date,
            "--initial-capital", "50000",  # Smaller capital for examples
            "--delta-threshold", "0.30"
        ]
        
        run_command(cmd)


def example_parameter_sweep():
    """Example of testing different parameters"""
    print("\n" + "="*80)
    print("PARAMETER SENSITIVITY ANALYSIS")
    print("="*80)
    
    print("\nTesting different delta thresholds for long calls...")
    
    start_date = "20220601"
    end_date = "20220831"  # Shorter period for faster execution
    
    for delta in ["0.20", "0.30", "0.40"]:
        print(f"\n{'-'*50}")
        print(f"Delta Threshold: {delta}")
        print(f"{'-'*50}")
        
        cmd = [
            "python", "backtester.py",
            "--strategy", "long_call",
            "--start-date", start_date,
            "--end-date", end_date,
            "--delta-threshold", delta,
            "--initial-capital", "25000"
        ]
        
        run_command(cmd)


def example_risk_parameters():
    """Example of different risk management settings"""
    print("\n" + "="*80)
    print("RISK MANAGEMENT EXAMPLES")
    print("="*80)
    
    start_date = "20220101"
    end_date = "20220630"
    
    risk_configs = [
        ("Conservative", "0.25", "0.50", "0.02"),
        ("Moderate", "0.50", "1.00", "0.05"),
        ("Aggressive", "1.00", "2.00", "0.10")
    ]
    
    for name, stop_loss, profit_target, position_size in risk_configs:
        print(f"\n{'-'*50}")
        print(f"{name} Risk Profile")
        print(f"Stop Loss: {float(stop_loss)*100}%, Profit Target: {float(profit_target)*100}%")
        print(f"Position Size: {float(position_size)*100}%")
        print(f"{'-'*50}")
        
        cmd = [
            "python", "backtester.py",
            "--strategy", "straddle",
            "--start-date", start_date,
            "--end-date", end_date,
            "--stop-loss", stop_loss,
            "--profit-target", profit_target,
            "--position-size", position_size,
            "--initial-capital", "50000"
        ]
        
        run_command(cmd)


def example_different_periods():
    """Example of testing different market periods"""
    print("\n" + "="*80)
    print("DIFFERENT MARKET PERIODS")
    print("="*80)
    
    periods = [
        ("20200301", "20200630", "COVID Crash Period"),
        ("20200701", "20201231", "Recovery Period"),
        ("20210101", "20211231", "Bull Market 2021"),
        ("20220101", "20220630", "Bear Market 2022")
    ]
    
    for start, end, description in periods:
        print(f"\n{'-'*50}")
        print(f"Period: {description} ({start} to {end})")
        print(f"{'-'*50}")
        
        cmd = [
            "python", "backtester.py",
            "--strategy", "straddle",  # Straddles work well in volatile periods
            "--start-date", start,
            "--end-date", end,
            "--initial-capital", "50000",
            "--delta-threshold", "0.50"
        ]
        
        run_command(cmd)


def example_with_output():
    """Example showing how to save results"""
    print("\n" + "="*80)
    print("SAVING RESULTS EXAMPLE")
    print("="*80)
    
    # Create output directory
    output_dir = Path("example_results")
    output_dir.mkdir(exist_ok=True)
    
    print(f"\nSaving results to: {output_dir.absolute()}")
    
    cmd = [
        "python", "backtester.py",
        "--strategy", "long_call",
        "--start-date", "20220101",
        "--end-date", "20220331",
        "--initial-capital", "25000",
        "--output", str(output_dir / "long_call_example")
    ]
    
    run_command(cmd)
    
    print(f"\nGenerated files:")
    for file in output_dir.glob("*"):
        print(f"  - {file.name}")


def test_data_loader():
    """Test the data loader functionality"""
    print("\n" + "="*80)
    print("DATA LOADER TEST")
    print("="*80)
    
    cmd = ["python", "data_loader.py"]
    run_command(cmd)


def main():
    """Run all examples"""
    print("SPY Options Backtester - Examples")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    examples = [
        ("1", "Test Data Loader", test_data_loader),
        ("2", "Basic Strategies", example_basic_strategies),
        ("3", "Parameter Sensitivity", example_parameter_sweep),
        ("4", "Risk Management", example_risk_parameters),
        ("5", "Different Market Periods", example_different_periods),
        ("6", "Save Results", example_with_output),
        ("all", "Run All Examples", None)
    ]
    
    print("\nAvailable examples:")
    for code, desc, _ in examples:
        print(f"  {code}: {desc}")
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nEnter example number (or 'all' for all examples): ").strip()
    
    if choice == "all":
        print("\nRunning all examples...")
        for code, desc, func in examples[:-1]:  # Skip 'all' option
            if func:
                func()
    else:
        for code, desc, func in examples:
            if code == choice and func:
                func()
                break
        else:
            print(f"Invalid choice: {choice}")
            sys.exit(1)
    
    print("\n" + "="*80)
    print("EXAMPLES COMPLETED")
    print("="*80)


if __name__ == "__main__":
    main()