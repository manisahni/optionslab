#!/usr/bin/env python3
"""Comprehensive test of the 0DTE strangle system"""

import sys
import os
import json
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradier.core.client import TradierClient
from tradier.core.risk_monitor import RiskMonitor
from tradier.dashboard.gradio_dashboard import state, create_dashboard

print("="*60)
print("🔬 0DTE STRANGLE SYSTEM COMPREHENSIVE TEST")
print("="*60)

print("\n1. Testing Tradier connection...")
client = TradierClient(env="sandbox")
if client.is_market_open():
    print("   ✓ Connected - Market is OPEN")
else:
    print("   ✓ Connected - Market is CLOSED")

print("\n2. Checking for existing positions...")
try:
    with open('tradier/tradier_strangle_order.json', 'r') as f:
        order_data = json.load(f)
        print(f"   ✓ Found strangle order:")
        print(f"     Call: {order_data.get('call_symbol', 'N/A')}")
        print(f"     Put: {order_data.get('put_symbol', 'N/A')}")
except:
    print("   ⚠️ No existing strangle order found")

print("\n3. Testing risk monitoring...")
monitor = RiskMonitor(client, vega_limit=2.0, delta_limit=0.20)
metrics = monitor.calculate_risk_metrics()
if metrics:
    print(f"   ✓ Risk metrics calculated:")
    print(f"     SPY Price: ${metrics['spy_price']:.2f}")
    print(f"     Delta: {metrics['greeks']['delta']:.3f}")
    print(f"     Vega: {metrics['greeks']['vega']:.3f}")
    print(f"     Risk Level: {metrics['risk_levels']['overall']}")
else:
    print("   ⚠️ No position to monitor")

print("\n4. Testing dashboard components...")
success, msg = state.initialize()
print(f"   Dashboard init: {msg}")
print(f"   Price history: {len(state.price_history)} points loaded")
print(f"   Greeks history: {len(state.greeks_history)} points loaded")

print("\n5. Verifying data persistence...")
if os.path.exists('tradier/tradier_risk_metrics.json'):
    with open('tradier/tradier_risk_metrics.json', 'r') as f:
        data = json.load(f)
        history_count = len(data.get('history', []))
        print(f"   ✓ Found {history_count} historical data points")
        if history_count > 0:
            latest = data['history'][-1]
            print(f"     Latest timestamp: {latest['timestamp'][:19]}")
else:
    print("   ⚠️ No historical data file found")

print("\n" + "="*60)
print("✅ SYSTEM TEST COMPLETE")
print("="*60)
print("\nTo start the dashboard:")
print("  python tradier/dashboard/gradio_dashboard.py")
print("\nTo monitor positions:")
print("  python tradier/scripts/live_monitor.py")
print("\nDashboard will be available at: http://localhost:7870")