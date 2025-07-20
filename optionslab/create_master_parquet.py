#!/usr/bin/env python3
"""
Create a master multi-year parquet file combining ALL SPY options data
This will create one file to rule them all and stop the constant file selection issues
"""

import pandas as pd
import glob
from pathlib import Path
import sys
from datetime import datetime

def create_master_parquet():
    """Create a single master parquet file with ALL data"""
    
    # Get data directory
    data_dir = Path("../spy_options_downloader/spy_options_parquet")
    
    print("🚀 Creating MASTER SPY Options parquet file")
    print("=" * 60)
    
    # Get ALL parquet files
    all_files = sorted(glob.glob(str(data_dir / "spy_options_eod_*.parquet")))
    
    print(f"Found {len(all_files)} individual daily files")
    
    if not all_files:
        print("❌ No files found!")
        return False
    
    # Extract date range
    first_file = Path(all_files[0]).stem.split('_')[-1]
    last_file = Path(all_files[-1]).stem.split('_')[-1]
    
    print(f"Date range: {first_file} to {last_file}")
    
    # Read and combine all files
    dfs = []
    errors = 0
    success = 0
    
    print("\nReading files...")
    for i, file in enumerate(all_files):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(all_files)} files ({i/len(all_files)*100:.1f}%)")
        
        try:
            # Try pyarrow first
            df = pd.read_parquet(file, engine='pyarrow')
            dfs.append(df)
            success += 1
        except Exception as e1:
            # Fallback to fastparquet
            try:
                df = pd.read_parquet(file, engine='fastparquet')
                dfs.append(df)
                success += 1
            except Exception as e2:
                print(f"❌ Failed to read {Path(file).name}: {e1} / {e2}")
                errors += 1
                continue
    
    print(f"\n✅ Successfully read {success} files")
    if errors > 0:
        print(f"❌ Failed to read {errors} files")
    
    if not dfs:
        print("❌ No data could be loaded!")
        return False
    
    # Combine all dataframes
    print("\n🔄 Combining all dataframes...")
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Sort by date
    if 'date' in combined_df.columns:
        print("📅 Sorting by date...")
        combined_df = combined_df.sort_values('date')
    
    # Get date range for filename
    min_date = combined_df['date'].min()
    max_date = combined_df['date'].max()
    
    # Convert to datetime if needed
    if isinstance(min_date, str):
        min_date = pd.to_datetime(min_date)
    if isinstance(max_date, str):
        max_date = pd.to_datetime(max_date)
    
    # Create output filename
    output_file = f"SPY_OPTIONS_MASTER_{min_date.strftime('%Y%m%d')}_{max_date.strftime('%Y%m%d')}.parquet"
    output_path = data_dir / output_file
    
    # Save to output file
    print(f"\n💾 Saving master file: {output_file}")
    print(f"   Total rows: {len(combined_df):,}")
    print(f"   Total columns: {len(combined_df.columns)}")
    print(f"   Date range: {min_date} to {max_date}")
    
    # Save with compression for smaller file size
    combined_df.to_parquet(output_path, index=False, compression='snappy')
    
    # Check file size
    file_size = output_path.stat().st_size / (1024 * 1024 * 1024)  # GB
    print(f"   File size: {file_size:.2f} GB")
    
    print(f"\n✅ SUCCESS! Master file created: {output_file}")
    print(f"   Path: {output_path}")
    
    # Also create year-specific files for convenience
    print("\n📊 Creating year-specific files...")
    # Convert date column to datetime if it's not already
    if combined_df['date'].dtype == 'object':
        combined_df['date'] = pd.to_datetime(combined_df['date'])
    years = combined_df['date'].dt.year.unique()
    
    for year in sorted(years):
        year_df = combined_df[combined_df['date'].dt.year == year]
        year_file = f"SPY_OPTIONS_{year}_COMPLETE.parquet"
        year_path = data_dir / year_file
        
        print(f"   Creating {year_file} ({len(year_df):,} rows)...")
        year_df.to_parquet(year_path, index=False, compression='snappy')
    
    print("\n🎉 All files created successfully!")
    
    return True


if __name__ == "__main__":
    success = create_master_parquet()
    
    if success:
        print("\n📌 IMPORTANT: Update your code to use the MASTER file by default!")
        print("   This will prevent future file selection issues.")
    else:
        print("\n❌ Failed to create master file")
        sys.exit(1)