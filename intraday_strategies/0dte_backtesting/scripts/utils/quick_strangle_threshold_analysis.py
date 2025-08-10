#!/usr/bin/env python3
"""
Quick Strangle Threshold Analysis
Efficient analysis of how often prices stay within thresholds
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from core.zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase


def analyze_single_day(date_str, db):
    """Analyze a single day's price movements"""
    df = db.load_zero_dte_data(date_str)
    if df.empty:
        return None
    
    # Get unique prices by minute
    prices = df.groupby('timestamp')['underlying_price'].first().reset_index()
    prices['time'] = pd.to_datetime(prices['timestamp']).dt.strftime('%H:%M')
    prices = prices.set_index('time')['underlying_price']
    
    # Entry times and thresholds to analyze
    entry_times = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00']
    thresholds = [0.1, 0.2, 0.3, 0.5, 0.75, 1.0]
    
    # Close price at 3:50 PM
    close_price = prices.get('15:50', prices.iloc[-1])
    
    results = []
    for entry_time in entry_times:
        if entry_time not in prices:
            continue
            
        entry_price = prices[entry_time]
        
        # Get prices from entry to close
        entry_idx = prices.index.get_loc(entry_time)
        period_prices = prices.iloc[entry_idx:]
        
        # Calculate max move
        max_price = period_prices.max()
        min_price = period_prices.min()
        max_move = max(
            abs(max_price - entry_price) / entry_price * 100,
            abs(min_price - entry_price) / entry_price * 100
        )
        
        for threshold in thresholds:
            results.append({
                'date': date_str,
                'entry_time': entry_time,
                'threshold': threshold,
                'stayed_within': max_move <= threshold,
                'max_move': max_move,
                'entry_price': entry_price,
                'close_price': close_price
            })
    
    return results


def main():
    print("Starting Quick Strangle Threshold Analysis...")
    
    # Initialize database
    db = ZeroDTESPYOptionsDatabase()
    
    # Get last 20 trading days
    data_path = Path(db.data_dir)
    dates = []
    for folder in data_path.iterdir():
        if folder.is_dir() and folder.name.isdigit() and len(folder.name) == 8:
            dates.append(folder.name)
    dates.sort()
    dates = dates[-20:]  # Last 20 days only
    
    print(f"Analyzing {len(dates)} recent trading days...")
    
    # Analyze each day
    all_results = []
    for i, date in enumerate(dates):
        print(f"  Processing {date} ({i+1}/{len(dates)})")
        day_results = analyze_single_day(date, db)
        if day_results:
            all_results.extend(day_results)
    
    # Convert to DataFrame
    df = pd.DataFrame(all_results)
    
    # Calculate win rates
    print("\nCalculating win rates...")
    win_rates = df.groupby(['entry_time', 'threshold'])['stayed_within'].agg(['mean', 'count'])
    win_rates['win_rate'] = win_rates['mean'] * 100
    
    # Create pivot table for visualization
    pivot = win_rates['win_rate'].reset_index().pivot(
        index='entry_time', 
        columns='threshold', 
        values='win_rate'
    )
    
    # Create heatmap
    plt.figure(figsize=(10, 6))
    sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', 
                cbar_kws={'label': 'Win Rate (%)'}, 
                vmin=0, vmax=100)
    plt.title('Strangle Win Rates: Probability of Staying Within Threshold\n(Last 20 Trading Days)')
    plt.xlabel('Movement Threshold (%)')
    plt.ylabel('Entry Time')
    plt.tight_layout()
    plt.savefig('quick_strangle_win_rates.png', dpi=150)
    print("Saved visualization to quick_strangle_win_rates.png")
    
    # Print summary table
    print("\n" + "="*60)
    print("STRANGLE WIN RATE SUMMARY")
    print("="*60)
    print("\nWin Rate Table (%):")
    print(pivot.round(1).to_string())
    
    # Calculate average moves by entry time
    avg_moves = df.groupby('entry_time')['max_move'].agg(['mean', 'std'])
    print("\n\nAverage Maximum Move by Entry Time:")
    print(f"{'Entry Time':<12} {'Avg Move (%)':<15} {'Std Dev (%)':<15}")
    print("-" * 42)
    for idx, row in avg_moves.iterrows():
        print(f"{idx:<12} {row['mean']:<15.2f} {row['std']:<15.2f}")
    
    # Best configurations
    print("\n\nBest Configurations (>80% win rate):")
    high_win_configs = win_rates[win_rates['mean'] > 0.8].sort_values('mean', ascending=False)
    print(f"{'Entry Time':<12} {'Threshold':<12} {'Win Rate (%)':<15} {'Sample Size':<15}")
    print("-" * 54)
    for (entry_time, threshold), row in high_win_configs.iterrows():
        print(f"{entry_time:<12} {threshold:<12.1f} {row['mean']*100:<15.1f} {row['count']:<15}")
    
    plt.show()


if __name__ == '__main__':
    main()