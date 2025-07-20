#!/usr/bin/env python3
"""
Quick script to run the AI Implementation Expert and show the analysis
"""

import sys
from pathlib import Path
from ai_implementation_expert import ImplementationExpert


def main():
    # Get the most recent backtest path
    trade_logs_dir = Path(__file__).parent / "trade_logs"
    
    # Look for the specific backtest
    backtest_path = "/Users/nish_macbook/thetadata-api/optionslab/trade_logs/2025/07/trades_advanced-test-strategy_2022-01-01_to_2022-12-31_20250719_235259.json"
    
    if len(sys.argv) > 1:
        backtest_path = sys.argv[1]
    
    print(f"Running AI Expert Analysis on: {Path(backtest_path).name}")
    print("="*60)
    
    # Create expert and load backtest
    expert = ImplementationExpert()
    
    if expert.load_backtest(backtest_path):
        # Generate the analysis
        print("\nGenerating implementation adequacy assessment...\n")
        assessment = expert.generate_adequacy_report()
        print(assessment)
        
        print("\n" + "="*60)
        print("Analysis complete!")
        print("\nTo interact with the expert, run:")
        print(f"python ai_implementation_expert.py --backtest '{backtest_path}'")
    else:
        print("Failed to load backtest")


if __name__ == "__main__":
    main()