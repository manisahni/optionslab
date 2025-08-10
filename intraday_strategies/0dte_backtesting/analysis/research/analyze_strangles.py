#!/usr/bin/env python3
"""
Simple command-line strangle analyzer
"""

import sys
import pandas as pd
from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase
from zero_dte_analysis_tools import ZeroDTEAnalyzer

def main():
    # Initialize
    db = ZeroDTESPYOptionsDatabase()
    analyzer = ZeroDTEAnalyzer(db)
    
    # Default date range
    start_date = "20250728"
    end_date = "20250801"
    
    if len(sys.argv) > 2:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    
    print(f"\n{'='*60}")
    print(f"0DTE STRANGLE STRATEGY ANALYSIS")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"{'='*60}\n")
    
    # Test different parameters
    results = []
    
    entry_times = ["09:35", "10:00", "10:30", "11:00", "11:30", "12:00"]
    deltas = [0.15, 0.20, 0.25, 0.30, 0.35]
    
    print("Testing parameter combinations...")
    total_tests = len(entry_times) * len(deltas)
    completed = 0
    
    for entry_time in entry_times:
        for delta in deltas:
            completed += 1
            print(f"\rProgress: {completed}/{total_tests}", end="", flush=True)
            
            # Run backtest
            df = analyzer.backtest_strangle_strategy(
                start_date, end_date,
                entry_time=entry_time,
                delta_target=delta
            )
            
            if len(df) > 0:
                win_rate = df['won'].mean() * 100
                avg_pnl = df['pnl'].mean()
                total_pnl = df['pnl'].sum()
                avg_pnl_pct = df['pnl_pct'].mean() * 100
                
                # Calculate Sharpe
                if df['pnl_pct'].std() > 0:
                    sharpe = (df['pnl_pct'].mean() / df['pnl_pct'].std()) * (252 ** 0.5)
                else:
                    sharpe = 0
                
                results.append({
                    'Entry': entry_time,
                    'Delta': f"{delta:.2f}",
                    'Trades': len(df),
                    'Win%': f"{win_rate:.0f}",
                    'Avg P&L': f"${avg_pnl:.2f}",
                    'Avg %': f"{avg_pnl_pct:.1f}%",
                    'Total': f"${total_pnl:.2f}",
                    'Sharpe': f"{sharpe:.2f}"
                })
    
    print("\n")
    
    if results:
        # Create DataFrame and sort by Sharpe
        results_df = pd.DataFrame(results)
        
        # Convert Sharpe to numeric for sorting
        results_df['Sharpe_num'] = results_df['Sharpe'].str.replace('', '').astype(float)
        results_df = results_df.sort_values('Sharpe_num', ascending=False)
        results_df = results_df.drop('Sharpe_num', axis=1)
        
        print("\nTOP 10 PARAMETER COMBINATIONS (by Sharpe Ratio):")
        print("="*80)
        print(results_df.head(10).to_string(index=False))
        
        # Find best by different metrics
        print("\n\nBEST PARAMETERS BY METRIC:")
        print("-"*40)
        
        # Best win rate
        best_win_idx = max(range(len(results)), key=lambda i: float(results[i]['Win%']))
        print(f"Highest Win Rate: Entry={results[best_win_idx]['Entry']}, Delta={results[best_win_idx]['Delta']} ({results[best_win_idx]['Win%']}%)")
        
        # Best average P&L
        best_avg_idx = max(range(len(results)), key=lambda i: float(results[i]['Avg P&L'].replace('$', '')))
        print(f"Best Avg P&L: Entry={results[best_avg_idx]['Entry']}, Delta={results[best_avg_idx]['Delta']} ({results[best_avg_idx]['Avg P&L']})")
        
        # Best total P&L
        best_total_idx = max(range(len(results)), key=lambda i: float(results[i]['Total'].replace('$', '')))
        print(f"Best Total P&L: Entry={results[best_total_idx]['Entry']}, Delta={results[best_total_idx]['Delta']} ({results[best_total_idx]['Total']})")
        
        # Summary stats
        print(f"\n\nOVERALL STATISTICS:")
        print("-"*40)
        all_win_rates = [float(r['Win%']) for r in results]
        print(f"Average Win Rate: {sum(all_win_rates)/len(all_win_rates):.1f}%")
        print(f"Win Rate Range: {min(all_win_rates):.0f}% - {max(all_win_rates):.0f}%")
        
        # Entry time analysis
        print(f"\n\nBEST ENTRY TIMES (averaged across all deltas):")
        print("-"*40)
        entry_stats = {}
        for r in results:
            entry = r['Entry']
            if entry not in entry_stats:
                entry_stats[entry] = []
            entry_stats[entry].append(float(r['Sharpe']))
        
        for entry, sharpes in sorted(entry_stats.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
            avg_sharpe = sum(sharpes) / len(sharpes)
            print(f"{entry}: Average Sharpe = {avg_sharpe:.2f}")
        
        # Delta analysis
        print(f"\n\nBEST DELTAS (averaged across all entry times):")
        print("-"*40)
        delta_stats = {}
        for r in results:
            delta = r['Delta']
            if delta not in delta_stats:
                delta_stats[delta] = []
            delta_stats[delta].append(float(r['Sharpe']))
        
        for delta, sharpes in sorted(delta_stats.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
            avg_sharpe = sum(sharpes) / len(sharpes)
            print(f"{delta}: Average Sharpe = {avg_sharpe:.2f}")
            
    else:
        print("No results found!")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()