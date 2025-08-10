#\!/usr/bin/env python3
import subprocess
import sys
import time

print("🚀 Starting 0DTE Trading Application...")
print("=" * 50)
print("Access the application at: http://127.0.0.1:7865")
print("Press Ctrl+C to stop")
print("=" * 50)

try:
    # Run the application
    subprocess.run([sys.executable, "-m", "user_interfaces.trading_application"])
except KeyboardInterrupt:
    print("\n\n✅ Application stopped")
