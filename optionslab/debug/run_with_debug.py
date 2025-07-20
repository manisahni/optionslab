#!/usr/bin/env python3
"""Run the auditable gradio app with full debug output"""

import sys
import os
import traceback

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== Starting OptionsLab Auditable App with Debug ===")
print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")
print("")

try:
    print("Importing auditable_gradio_app module...")
    import auditable_gradio_app
    
    print("✅ Import successful")
    print("\nStarting the application...")
    print("Access the app at: http://localhost:7860")
    print("Press Ctrl+C to stop\n")
    
    # The app should start when the module is imported
    # If not, we need to call a specific function
    
except KeyboardInterrupt:
    print("\n\nApp stopped by user.")
except Exception as e:
    print(f"\n❌ Error starting app: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    
    # Try to give more specific error information
    if "Address already in use" in str(e):
        print("\n💡 Port 7860 is already in use. Try:")
        print("   1. Close other applications using this port")
        print("   2. Or modify the port in auditable_gradio_app.py")
    elif "No module named" in str(e):
        print("\n💡 Missing dependency. Try:")
        print("   pip install -r requirements.txt")
    
    sys.exit(1)