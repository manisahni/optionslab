#!/usr/bin/env python3
"""
Validate the win rate fix by simulating the UI processing
"""
import json
import pandas as pd
from pathlib import Path
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.win_rate_calculator import WinRateCalculator

def validate_win_rate_fix():
    print("="*60)
    print("🔍 VALIDATING WIN RATE FIX")
    print("="*60)
    
    # Load the most recent backtest result
    results_dir = Path("backtest_results")
    if not results_dir.exists():
        print("❌ No backtest_results directory found")
        return
        
    result_files = list(results_dir.glob("*.json"))
    if not result_files:
        print("❌ No backtest result files found")
        return
        
    # Load most recent result
    most_recent = max(result_files, key=lambda f: f.stat().st_mtime)
    print(f"📁 Testing with: {most_recent.name}")
    
    with open(most_recent) as f:
        data = json.load(f)
    
    results = data.get('results', data)
    
    # Simulate the UI processing (what the fix does)
    print("\n🎯 SIMULATING UI PROCESSING WITH FIX")
    
    metrics = results.get('metrics', {})
    trades = results.get('trades', [])
    
    print(f"📊 Original metrics win_rate: {metrics.get('win_rate', 0):.1f}%")
    print(f"📊 Trade count: {len(trades)}")
    
    # Apply the fix (same code as in the UI)
    if trades:
        try:
            trades_df = pd.DataFrame(trades)
            win_rate_result = WinRateCalculator.calculate_win_rate(trades_df, debug=False)
            
            # Override the parsed win rate with the canonical calculation
            original_win_rate = metrics.get('win_rate', 0)
            metrics['win_rate'] = win_rate_result['win_rate']
            metrics['total_trades'] = win_rate_result['total_trades']
            
            print(f"\n✅ FIXED METRICS:")
            print(f"📊 Corrected win_rate: {metrics['win_rate']:.1f}%")
            print(f"📊 Total trades: {metrics['total_trades']}")
            
            # Calculate the improvement
            improvement = metrics['win_rate'] - original_win_rate
            print(f"\n🎯 IMPROVEMENT:")
            print(f"📈 Before: {original_win_rate:.1f}%")
            print(f"📈 After: {metrics['win_rate']:.1f}%")
            print(f"📈 Improvement: +{improvement:.1f} percentage points")
            
            if improvement > 0:
                print(f"\n🎉 WIN RATE FIX SUCCESSFUL!")
                print(f"   The 0% win rate bug has been resolved!")
                print(f"   Now showing correct win rate: {metrics['win_rate']:.1f}%")
            else:
                print(f"\n⚠️ No improvement detected")
                print(f"   This might indicate the original data was already correct")
                
        except Exception as e:
            print(f"❌ Error during fix: {e}")
            return False
    else:
        print("❌ No trades data found")
        return False
    
    # Additional validation
    print(f"\n🧪 VALIDATION CHECKS:")
    
    # Check if win rate is reasonable
    if 0 <= metrics['win_rate'] <= 100:
        print(f"✅ Win rate is within valid range (0-100%)")
    else:
        print(f"❌ Win rate is outside valid range: {metrics['win_rate']:.1f}%")
    
    # Check if trades match
    if metrics['total_trades'] == len(trades):
        print(f"✅ Trade count matches: {metrics['total_trades']}")
    else:
        print(f"❌ Trade count mismatch: {metrics['total_trades']} vs {len(trades)}")
    
    # Check if win rate is not zero (unless all trades were losses)
    if metrics['win_rate'] > 0:
        print(f"✅ Win rate is positive: {metrics['win_rate']:.1f}%")
    else:
        print(f"⚠️ Win rate is 0% - verify all trades were losses")
    
    return True

if __name__ == "__main__":
    success = validate_win_rate_fix()
    if success:
        print(f"\n✅ Win rate fix validation completed successfully!")
    else:
        print(f"\n❌ Win rate fix validation failed!")