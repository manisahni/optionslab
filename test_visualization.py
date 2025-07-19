#!/usr/bin/env python3
"""
Quick test of visualization functionality
"""

import json
from pathlib import Path
from optionslab.visualization import plot_pnl_curve, create_summary_dashboard

# Find a trade log
log_file = Path("optionslab/trade_logs/2025/07/trades_long-put-dynamic-stops_2022-01-01_to_2022-12-31_20250719_140931.json")

if log_file.exists():
    print(f"📊 Testing visualization with: {log_file.name}")
    
    with open(log_file, 'r') as f:
        data = json.load(f)
    
    trades = data.get('trades', [])
    metadata = data.get('metadata', {})
    
    print(f"   Found {len(trades)} trades")
    print(f"   Initial capital: ${metadata.get('initial_capital', 10000):,.2f}")
    
    # Test P&L curve
    try:
        fig = plot_pnl_curve(trades, metadata.get('initial_capital', 10000))
        print("✅ P&L curve generated successfully")
    except Exception as e:
        print(f"❌ Failed to generate P&L curve: {e}")
    
    # Test summary dashboard
    try:
        fig = create_summary_dashboard(trades, metadata.get('initial_capital', 10000))
        print("✅ Summary dashboard generated successfully")
    except Exception as e:
        print(f"❌ Failed to generate summary dashboard: {e}")
else:
    print("❌ Trade log file not found")