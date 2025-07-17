import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime

# Get all parquet files
parquet_files = sorted(glob.glob('spy_options_parquet/*.parquet'))
print(f"Total files found: {len(parquet_files)}")

# Initialize tracking variables
all_dates = []
delta_coverage = []
missing_dates = []
zero_delta_files = []

print("\n=== DATE COVERAGE ===")
# Extract dates from filenames
for file in parquet_files:
    # Extract date from filename (format: spy_options_eod_YYYYMMDD.parquet)
    date_str = os.path.basename(file).split('_')[-1].split('.')[0]
    all_dates.append(datetime.strptime(date_str, '%Y%m%d'))

# Sort dates and find gaps
all_dates.sort()
print(f"First date: {all_dates[0].strftime('%Y-%m-%d')}")
print(f"Last date: {all_dates[-1].strftime('%Y-%m-%d')}")
print(f"Total trading days covered: {len(all_dates)}")

# Check for gaps in dates (excluding weekends)
print("\n=== DATE GAPS (excluding weekends) ===")
for i in range(1, len(all_dates)):
    prev_date = all_dates[i-1]
    curr_date = all_dates[i]
    days_diff = (curr_date - prev_date).days
    
    # If more than 1 day apart and not a weekend gap
    if days_diff > 1:
        # Check if it's just a weekend
        expected_next = prev_date
        gap_days = []
        for j in range(1, days_diff):
            expected_next = prev_date + pd.Timedelta(days=j)
            if expected_next.weekday() < 5:  # Monday = 0, Friday = 4
                gap_days.append(expected_next)
        
        if gap_days:
            print(f"Gap found: {prev_date.strftime('%Y-%m-%d')} to {curr_date.strftime('%Y-%m-%d')} ({len(gap_days)} missing weekdays)")
            for day in gap_days[:5]:  # Show first 5 missing days
                print(f"  - Missing: {day.strftime('%Y-%m-%d')} ({day.strftime('%A')})")
            if len(gap_days) > 5:
                print(f"  - ... and {len(gap_days) - 5} more days")

print("\n=== DELTA COVERAGE ANALYSIS ===")
# Sample analysis - check first, middle, and last files for delta coverage
sample_files = [parquet_files[0], parquet_files[len(parquet_files)//2], parquet_files[-1]]

for file in sample_files:
    date_str = os.path.basename(file).split('_')[-1].split('.')[0]
    df = pd.read_parquet(file)
    
    # Filter for non-zero delta values
    non_zero_delta = df[df['delta'] != 0]
    
    print(f"\nDate: {date_str}")
    print(f"Total options: {len(df)}")
    print(f"Options with delta != 0: {len(non_zero_delta)}")
    print(f"Percentage with delta: {len(non_zero_delta)/len(df)*100:.1f}%")
    
    if len(non_zero_delta) > 0:
        print(f"Delta range: [{non_zero_delta['delta'].min():.4f}, {non_zero_delta['delta'].max():.4f}]")
        
        # Show delta distribution by moneyness
        calls = non_zero_delta[non_zero_delta['right'] == 'C']
        puts = non_zero_delta[non_zero_delta['right'] == 'P']
        
        if len(calls) > 0:
            print(f"Call deltas: min={calls['delta'].min():.4f}, max={calls['delta'].max():.4f}, mean={calls['delta'].mean():.4f}")
        if len(puts) > 0:
            print(f"Put deltas: min={puts['delta'].min():.4f}, max={puts['delta'].max():.4f}, mean={puts['delta'].mean():.4f}")

# Comprehensive delta check across all files
print("\n=== COMPREHENSIVE DELTA CHECK ===")
print("Checking all files for delta coverage...")

files_with_no_deltas = []
total_options = 0
options_with_deltas = 0

for i, file in enumerate(parquet_files):
    if i % 50 == 0:
        print(f"Progress: {i}/{len(parquet_files)} files...")
    
    df = pd.read_parquet(file)
    total_options += len(df)
    non_zero_delta = len(df[df['delta'] != 0])
    options_with_deltas += non_zero_delta
    
    if non_zero_delta == 0:
        date_str = os.path.basename(file).split('_')[-1].split('.')[0]
        files_with_no_deltas.append(date_str)

print(f"\nTotal options across all files: {total_options:,}")
print(f"Options with non-zero delta: {options_with_deltas:,}")
print(f"Overall delta coverage: {options_with_deltas/total_options*100:.1f}%")
print(f"Files with no delta values: {len(files_with_no_deltas)}")

if files_with_no_deltas:
    print("\nDates with no delta values:")
    for date in files_with_no_deltas[:10]:
        print(f"  - {date}")
    if len(files_with_no_deltas) > 10:
        print(f"  - ... and {len(files_with_no_deltas) - 10} more dates")

# Check for specific delta ranges
print("\n=== DELTA DISTRIBUTION CHECK ===")
# Sample a recent file with deltas
recent_files = parquet_files[-30:]  # Last 30 files
for file in reversed(recent_files):
    df = pd.read_parquet(file)
    if len(df[df['delta'] != 0]) > 0:
        date_str = os.path.basename(file).split('_')[-1].split('.')[0]
        print(f"\nDelta distribution for {date_str}:")
        
        # Create delta bins
        df_with_delta = df[df['delta'] != 0]
        
        # Separate calls and puts
        calls = df_with_delta[df_with_delta['right'] == 'C']
        puts = df_with_delta[df_with_delta['right'] == 'P']
        
        # Delta ranges for calls
        if len(calls) > 0:
            print("\nCall option deltas:")
            delta_ranges = [(0.9, 1.0), (0.7, 0.9), (0.5, 0.7), (0.3, 0.5), (0.1, 0.3), (0, 0.1)]
            for low, high in delta_ranges:
                count = len(calls[(calls['delta'] > low) & (calls['delta'] <= high)])
                if count > 0:
                    print(f"  Delta {low:.1f}-{high:.1f}: {count} options")
        
        # Delta ranges for puts (negative deltas)
        if len(puts) > 0:
            print("\nPut option deltas:")
            delta_ranges = [(-0.1, 0), (-0.3, -0.1), (-0.5, -0.3), (-0.7, -0.5), (-0.9, -0.7), (-1.0, -0.9)]
            for low, high in delta_ranges:
                count = len(puts[(puts['delta'] > low) & (puts['delta'] <= high)])
                if count > 0:
                    print(f"  Delta {low:.1f}-{high:.1f}: {count} options")
        
        break  # Just show one example