#!/usr/bin/env python3
"""
Verify dashboard is running and accessible
"""

import requests
import time
import subprocess
import sys
import threading

def run_dashboard():
    """Run dashboard in a thread"""
    subprocess.run([sys.executable, "dashboards/comprehensive_strangle_dashboard.py"])

# Start dashboard in background thread
print("Starting dashboard in background...")
dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
dashboard_thread.start()

# Wait for it to start
print("Waiting for dashboard to initialize...")
time.sleep(5)

# Check if it's running
try:
    response = requests.get("http://localhost:7860", timeout=5)
    if response.status_code == 200:
        print("\n" + "="*80)
        print("✅ SUCCESS! Dashboard is running!")
        print("="*80)
        print("\nDashboard is accessible at: http://localhost:7860")
        print("\nOpen this URL in your web browser to use the dashboard.")
        print("\nThe dashboard includes:")
        print("  - Parameter Sweep Analysis")
        print("  - Trade Inspector")
        print("  - Greek Visualizer")
        print("  - Education Center")
        print("  - Settings Panel")
        print("\nPress Ctrl+C to stop the dashboard.")
        print("="*80 + "\n")
        
        # Keep running
        while True:
            time.sleep(1)
    else:
        print(f"❌ Dashboard returned status code: {response.status_code}")
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Could not connect to dashboard on port 7860")
    print("\nPossible issues:")
    print("  1. Another process may be using port 7860")
    print("  2. Dashboard failed to start properly")
except KeyboardInterrupt:
    print("\n\nStopping dashboard...")
except Exception as e:
    print(f"❌ ERROR: {e}")