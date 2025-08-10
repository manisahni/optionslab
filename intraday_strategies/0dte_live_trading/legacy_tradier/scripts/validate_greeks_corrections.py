#!/usr/bin/env python3
"""
Validate Greeks Corrections and Compare with Backtests
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List

def validate_greeks_corrections():
    """Validate that Greeks corrections match backtest expectations"""
    
    conn = sqlite3.connect('database/market_data.db')
    
    # 1. Check Greeks at entry time (3:00 PM)
    print("="*80)
    print("GREEKS VALIDATION REPORT")
    print("="*80)
    
    # Get all days with Greeks data
    days_query = """
    SELECT DISTINCT date(timestamp) as trading_date
    FROM greeks_history
    ORDER BY trading_date DESC
    """
    
    days_df = pd.read_sql_query(days_query, conn)
    
    print(f"\n1. DATA COVERAGE")
    print(f"   Days with Greeks data: {len(days_df)}")
    print(f"   Date range: {days_df['trading_date'].min()} to {days_df['trading_date'].max()}")
    
    # 2. Check Greeks at entry for each day
    print(f"\n2. GREEKS AT ENTRY (3:00 PM)")
    print("-"*60)
    print(f"{'Date':<12} {'Delta':<10} {'Gamma':<10} {'Theta':<10} {'Vega':<10} {'IV':<8}")
    print("-"*60)
    
    entry_greeks = []
    for date in days_df['trading_date']:
        query = f"""
        SELECT *
        FROM greeks_history
        WHERE date(timestamp) = '{date}'
        AND time(timestamp) = '15:00:00'
        """
        
        entry_data = pd.read_sql_query(query, conn)
        if not entry_data.empty:
            row = entry_data.iloc[0]
            entry_greeks.append({
                'date': date,
                'delta': row['total_delta'],
                'gamma': row['total_gamma'],
                'theta': row['total_theta'],
                'vega': row['total_vega'],
                'iv': row['call_iv']
            })
            print(f"{date:<12} {row['total_delta']:>9.4f} {row['total_gamma']:>9.4f} "
                  f"{row['total_theta']:>9.4f} {row['total_vega']:>9.4f} {row['call_iv']*100:>7.1f}%")
    
    # 3. Statistical summary
    if entry_greeks:
        df = pd.DataFrame(entry_greeks)
        print(f"\n3. STATISTICAL SUMMARY (Entry Greeks)")
        print("-"*60)
        print(f"                  Mean        Std       Min       Max")
        print("-"*60)
        for col in ['delta', 'gamma', 'theta', 'vega']:
            mean_val = df[col].mean()
            std_val = df[col].std()
            min_val = df[col].min()
            max_val = df[col].max()
            print(f"{col.capitalize():<10} {mean_val:>10.4f} {std_val:>9.4f} {min_val:>9.4f} {max_val:>9.4f}")
        
        print(f"IV %       {df['iv'].mean()*100:>10.1f} {df['iv'].std()*100:>9.1f} "
              f"{df['iv'].min()*100:>9.1f} {df['iv'].max()*100:>9.1f}")
    
    # 4. Check Greeks evolution through time
    print(f"\n4. GREEKS EVOLUTION (3:00 PM to 4:00 PM)")
    print("-"*60)
    
    latest_date = days_df['trading_date'].max()
    evolution_query = f"""
    SELECT 
        time(timestamp) as time,
        total_delta,
        total_gamma,
        total_theta,
        total_vega
    FROM greeks_history
    WHERE date(timestamp) = '{latest_date}'
    AND time(timestamp) >= '15:00:00'
    ORDER BY timestamp
    """
    
    evolution_df = pd.read_sql_query(evolution_query, conn)
    
    if not evolution_df.empty:
        # Sample at key times
        key_times = ['15:00:00', '15:15:00', '15:30:00', '15:45:00', '15:59:00']
        
        print(f"Time      Delta     Gamma     Theta      Vega")
        print("-"*60)
        for time in key_times:
            row = evolution_df[evolution_df['time'] == time]
            if not row.empty:
                r = row.iloc[0]
                print(f"{time:<10} {r['total_delta']:>8.4f} {r['total_gamma']:>8.4f} "
                      f"{r['total_theta']:>9.4f} {r['total_vega']:>8.4f}")
    
    # 5. Validation checks
    print(f"\n5. VALIDATION CHECKS")
    print("-"*60)
    
    validations = []
    
    # Check 1: Entry delta should be between 0.05 and 0.25
    if entry_greeks:
        df = pd.DataFrame(entry_greeks)
        avg_delta = abs(df['delta'].mean())
        if 0.05 <= avg_delta <= 0.25:
            validations.append("✅ Entry delta in expected range (0.05-0.25)")
        else:
            validations.append(f"❌ Entry delta out of range: {avg_delta:.4f}")
    
    # Check 2: IV should be between 20% and 50%
    if entry_greeks:
        avg_iv = df['iv'].mean()
        if 0.20 <= avg_iv <= 0.50:
            validations.append(f"✅ IV in expected range (20-50%): {avg_iv*100:.1f}%")
        else:
            validations.append(f"❌ IV out of range: {avg_iv*100:.1f}%")
    
    # Check 3: Greeks should decay towards zero by close
    if not evolution_df.empty:
        final_row = evolution_df[evolution_df['time'] >= '15:55:00']
        if not final_row.empty:
            final_delta = abs(final_row.iloc[-1]['total_delta'])
            if final_delta < 0.05:
                validations.append("✅ Greeks decay to near zero by close")
            else:
                validations.append(f"❌ Greeks not decaying properly: {final_delta:.4f} at close")
    
    # Check 4: No extreme values (delta > 0.9)
    extreme_query = """
    SELECT COUNT(*) as count
    FROM greeks_history
    WHERE ABS(total_delta) > 0.9
    """
    extreme_df = pd.read_sql_query(extreme_query, conn)
    extreme_count = extreme_df.iloc[0]['count']
    
    if extreme_count == 0:
        validations.append("✅ No extreme delta values (>0.9)")
    else:
        validations.append(f"❌ Found {extreme_count} records with extreme delta")
    
    for validation in validations:
        print(f"   {validation}")
    
    # 6. Compare with backtest expectations
    print(f"\n6. BACKTEST COMPARISON")
    print("-"*60)
    print("Expected (from 93.7% win rate backtests):")
    print("  - Entry Delta: 0.20-0.25 per leg")
    print("  - Entry IV: 25-35%")
    print("  - Theta: $50-100/day at entry")
    print("  - Vega: 1.0-2.0 at entry")
    
    if entry_greeks:
        df = pd.DataFrame(entry_greeks)
        print("\nActual (from corrected Greeks):")
        print(f"  - Entry Delta: {abs(df['delta'].mean()):.4f} (avg)")
        print(f"  - Entry IV: {df['iv'].mean()*100:.1f}% (avg)")
        print(f"  - Theta: {df['theta'].mean():.4f} at entry")
        print(f"  - Vega: {abs(df['vega'].mean()):.4f} at entry")
    
    # 7. Summary
    print(f"\n7. SUMMARY")
    print("-"*60)
    
    all_valid = all("✅" in v for v in validations)
    if all_valid:
        print("✅ ALL VALIDATIONS PASSED!")
        print("Greeks are now correctly calibrated to market reality.")
        print("Dashboard should display accurate risk metrics.")
    else:
        print("⚠️ Some validations failed. Review the corrections.")
    
    conn.close()
    
    return all_valid

if __name__ == "__main__":
    success = validate_greeks_corrections()
    sys.exit(0 if success else 1)