#!/usr/bin/env python3
"""
Create multi-day parquet files for backtesting
"""

import pandas as pd
import glob
from pathlib import Path
import sys

def create_multiday_parquet(start_date, end_date, output_file):
    """Create a combined parquet file from individual daily files"""
    
    # Get data directory
    data_dir = Path("../spy_options_downloader/spy_options_parquet")
    
    # Convert dates to string format for matching
    start_str = start_date.replace('-', '')
    end_str = end_date.replace('-', '')
    
    print(f"Creating multi-day parquet from {start_date} to {end_date}")
    
    # Get all parquet files
    all_files = sorted(glob.glob(str(data_dir / "spy_options_eod_*.parquet")))
    
    # Filter files by date range
    selected_files = []
    for file in all_files:
        file_date = Path(file).stem.split('_')[-1]
        if start_str <= file_date <= end_str:
            selected_files.append(file)
    
    print(f"Found {len(selected_files)} files in date range")
    
    if not selected_files:
        print("No files found in date range")
        return False
    
    # Read and combine all files
    dfs = []
    for i, file in enumerate(selected_files):
        if i % 50 == 0:
            print(f"Processing file {i+1}/{len(selected_files)}")
        try:
            df = pd.read_parquet(file)
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue
    
    if not dfs:
        print("No data could be loaded")
        return False
    
    # Combine all dataframes
    print("Combining dataframes...")
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Sort by date
    if 'date' in combined_df.columns:
        combined_df = combined_df.sort_values('date')
    
    # Save to output file
    output_path = data_dir / output_file
    print(f"Saving to {output_path}")
    combined_df.to_parquet(output_path, index=False)
    
    print(f"Created {output_file} with {len(combined_df)} rows")
    return True


if __name__ == "__main__":
    # Create multi-day files for common date ranges
    ranges = [
        ("2022-01-01", "2022-12-31", "spy_options_2022_full_year.parquet"),
        ("2022-01-01", "2022-06-30", "spy_options_2022_h1.parquet"),
        ("2022-07-01", "2022-12-31", "spy_options_2022_h2.parquet"),
        ("2023-01-01", "2023-12-31", "spy_options_2023_full_year.parquet"),
    ]
    
    for start, end, output in ranges:
        print(f"\n{'='*60}")
        success = create_multiday_parquet(start, end, output)
        if success:
            print(f"✅ Successfully created {output}")
        else:
            print(f"❌ Failed to create {output}")