#!/usr/bin/env python3
"""Debug script to test CSV export functionality"""

import pandas as pd
import os
import tempfile
from pathlib import Path

# Check the permanent log file
perm_csv = "/Users/nish_macbook/thetadata-api/optionslab/trade_logs/2025/07/trades_long-put-dynamic-stops_2022-01-01_to_2022-12-31_20250719_141129.csv"
print(f"Checking permanent CSV: {perm_csv}")

if os.path.exists(perm_csv):
    df = pd.read_csv(perm_csv)
    print(f"Permanent CSV shape: {df.shape}")
    print(f"Columns: {len(df.columns)}")
    print(f"First few columns: {list(df.columns)[:10]}")
    
    # Check temp file creation
    temp_csv = os.path.join(tempfile.gettempdir(), "test_export.csv")
    df.to_csv(temp_csv, index=False)
    print(f"\nTemp CSV created at: {temp_csv}")
    print(f"Temp CSV size: {os.path.getsize(temp_csv)} bytes")
    print(f"Perm CSV size: {os.path.getsize(perm_csv)} bytes")
    
    # Compare files
    temp_df = pd.read_csv(temp_csv)
    print(f"\nTemp CSV shape: {temp_df.shape}")
    print(f"Files are identical: {df.equals(temp_df)}")
else:
    print("Permanent CSV not found!")

# Check temp directory
print(f"\nTemp directory: {tempfile.gettempdir()}")
temp_logs = list(Path(tempfile.gettempdir()).glob("trades_log_*.csv"))
print(f"Found {len(temp_logs)} temp trade log files")
for log in temp_logs[:5]:  # Show first 5
    print(f"  - {log.name} ({log.stat().st_size} bytes)")