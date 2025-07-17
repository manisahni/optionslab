#!/usr/bin/env python3
"""
Test the win rate fix with real data
"""
import json
import pandas as pd
from pathlib import Path
from core.results_analyzer import ResultsAnalyzer
from core.win_rate_calculator import WinRateCalculator

def test_win_rate_fix():
    print("="*60)
    print("🧪 TESTING WIN RATE FIX")
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
    trades_df = pd.DataFrame(results['trades'])
    
    print(f"📊 Trade Data: {len(trades_df)} trades")
    print(f"📊 Columns: {list(trades_df.columns)}")
    
    # Test 1: Canonical Win Rate Calculator
    print("\n🎯 TEST 1: Canonical Win Rate Calculator")
    win_rate_result = WinRateCalculator.calculate_win_rate(trades_df, debug=True)
    canonical_win_rate = win_rate_result['win_rate']
    print(f"✅ Canonical Win Rate: {canonical_win_rate:.1f}%")
    
    # Test 2: Results Analyzer (Fixed)
    print("\n🎯 TEST 2: Results Analyzer (Fixed)")
    try:
        analyzer = ResultsAnalyzer(results, initial_capital=100000)
        analyzer._calculate_trade_metrics()
        analyzer_win_rate = analyzer.metrics['win_rate']
        print(f"✅ Results Analyzer Win Rate: {analyzer_win_rate:.1f}%")
    except Exception as e:
        print(f"❌ Results Analyzer Error: {e}")
        analyzer_win_rate = 0
    
    # Test 3: Manual P&L Calculation (Ground Truth)
    print("\n🎯 TEST 3: Manual Ground Truth Calculation")
    pnl_values = trades_df['P&L'].str.replace('$', '', regex=False).str.replace(',', '').astype(float)
    winning_trades = (pnl_values > 0).sum()
    total_trades = len(pnl_values)
    manual_win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    print(f"✅ Manual Win Rate: {manual_win_rate:.1f}%")
    
    # Test 4: Comparison & Validation
    print("\n🎯 TEST 4: Win Rate Comparison")
    print(f"📊 Canonical Calculator: {canonical_win_rate:.1f}%")
    print(f"📊 Results Analyzer: {analyzer_win_rate:.1f}%")
    print(f"📊 Manual Calculation: {manual_win_rate:.1f}%")
    
    # Check if all methods agree
    tolerance = 0.1
    canonical_matches = abs(canonical_win_rate - manual_win_rate) < tolerance
    analyzer_matches = abs(analyzer_win_rate - manual_win_rate) < tolerance
    
    print(f"\n✅ VALIDATION RESULTS:")
    print(f"  Canonical Calculator: {'✅ PASS' if canonical_matches else '❌ FAIL'}")
    print(f"  Results Analyzer: {'✅ PASS' if analyzer_matches else '❌ FAIL'}")
    
    if canonical_matches and analyzer_matches:
        print(f"\n🎉 WIN RATE FIX SUCCESSFUL!")
        print(f"   All methods agree: {manual_win_rate:.1f}%")
        print(f"   Previous broken value: 0.0%")
        print(f"   Improvement: +{manual_win_rate:.1f} percentage points")
    else:
        print(f"\n❌ WIN RATE FIX INCOMPLETE")
        print(f"   Some methods still disagree")
    
    # Test 5: Data Quality Check
    print(f"\n🎯 TEST 5: Data Quality Check")
    validation = WinRateCalculator.validate_win_rate(canonical_win_rate, trades_df)
    print(f"  Valid: {validation['is_valid']}")
    if validation['warnings']:
        print(f"  Warnings: {validation['warnings']}")
    if validation['issues']:
        print(f"  Issues: {validation['issues']}")
    
    return {
        'canonical_win_rate': canonical_win_rate,
        'analyzer_win_rate': analyzer_win_rate,
        'manual_win_rate': manual_win_rate,
        'fix_successful': canonical_matches and analyzer_matches,
        'validation': validation
    }

if __name__ == "__main__":
    test_win_rate_fix()