#!/usr/bin/env python3
"""Quick test of dashboard components"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("1. Testing imports...")
try:
    from tradier.dashboard.gradio_dashboard import state, create_dashboard
    print("   ✓ Imports successful")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

print("\n2. Testing state initialization...")
try:
    success, msg = state.initialize()
    print(f"   Result: {msg}")
    print(f"   Price history: {len(state.price_history)} points")
    print(f"   Greeks history: {len(state.greeks_history)} points")
except Exception as e:
    print(f"   ✗ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n3. Testing dashboard creation...")
try:
    dashboard = create_dashboard()
    print("   ✓ Dashboard created successfully")
except Exception as e:
    print(f"   ✗ Dashboard creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All tests passed!")
print("\nTo start the dashboard, run:")
print("  python tradier/dashboard/gradio_dashboard.py")