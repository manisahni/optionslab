#!/usr/bin/env python3
"""Test the log refresh functionality"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'optionslab'))

from auditable_gradio_app import get_all_trade_logs, get_trade_logs_dir
from pathlib import Path

print("Testing log management functions...")
print(f"Trade logs directory: {get_trade_logs_dir()}")

# Get all logs
logs = get_all_trade_logs()
print(f"\nFound {len(logs)} logs:")

for log in logs:
    print(f"\n- Strategy: {log.get('strategy')}")
    print(f"  Path: {log.get('path')}")
    print(f"  Date: {log.get('backtest_date')}")
    print(f"  Trades: {log.get('total_trades')}")
    print(f"  Return: {log.get('total_return', 0):.2%}")
    print(f"  Win Rate: {log.get('win_rate', 0):.1%}")
    print(f"  Size: {log.get('size', 0) / 1024:.1f} KB")
    
    # Check if files exist
    json_path = Path(log['path'])
    csv_path = json_path.with_suffix('.csv')
    print(f"  JSON exists: {json_path.exists()}")
    print(f"  CSV exists: {csv_path.exists()}")