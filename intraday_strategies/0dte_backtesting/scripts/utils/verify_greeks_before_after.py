#!/usr/bin/env python3
"""Quick script to compare Greeks before and after correction"""

import pandas as pd
import sys
sys.path.append('core')
from greeks_validator import GreeksValidator

def check_sample_file():
    """Check a sample file's Greeks"""
    # Load sample data - check one of the corrected files
    file_path = "options_data/spy_0dte_minute/20240805/zero_dte_spy_20240805.parquet"
    df = pd.read_parquet(file_path)
    
    # Get 10 AM data
    time_10am = df[df['timestamp'] == '2024-08-05T10:00:00']
    calls = time_10am[time_10am['right'] == 'CALL'].sort_values('strike')
    
    print("CURRENT GREEKS IN FILE:")
    print("="*80)
    
    # Show sample
    sample = calls.head(10)
    columns_to_show = ['strike', 'delta']
    if 'gamma' in sample.columns:
        columns_to_show.append('gamma')
    else:
        print("⚠️  GAMMA is MISSING from dataset")
    columns_to_show.extend(['theta', 'vega', 'implied_vol'])
    
    # Only show columns that exist
    available_cols = [col for col in columns_to_show if col in sample.columns]
    print(sample[available_cols].to_string())
    
    # Validate
    validator = GreeksValidator()
    result = validator.validate_options_data(time_10am)
    
    print(f"\nValidation Score: {result.score:.1f}/100")
    print(f"Issues: {len(result.issues)}")
    print(f"Warnings: {len(result.warnings)}")
    
    # Check for correction markers
    if 'greeks_corrected' in df.columns:
        print(f"\n✅ File has been corrected!")
        print(f"Correction date: {df['correction_date'].iloc[0] if 'correction_date' in df.columns else 'Unknown'}")
    else:
        print(f"\n❌ File has NOT been corrected yet")
    
    # Summary stats
    print(f"\nSummary Statistics:")
    print(f"Delta = 1.0 count: {len(calls[calls['delta'] == 1.0])} / {len(calls)}")
    print(f"Gamma NaN count: {calls['gamma'].isna().sum() if 'gamma' in calls.columns else 'N/A'}")
    print(f"Theta = 0 count: {len(calls[calls['theta'] == 0])} / {len(calls)}")
    print(f"Vega = 0 count: {len(calls[calls['vega'] == 0])} / {len(calls)}")


if __name__ == "__main__":
    check_sample_file()