#!/usr/bin/env python3
"""
Debug wrapper for OptionsLab startup
This script provides detailed output during app startup
"""
import sys
import os
import time
import subprocess

print("🔍 OptionsLab Debug Startup Script")
print("="*60)

# Check Python environment
print(f"\n📍 Environment Check:")
print(f"   Python executable: {sys.executable}")
print(f"   Working directory: {os.getcwd()}")
print(f"   Virtual env active: {'VIRTUAL_ENV' in os.environ}")

# Check for existing processes
print(f"\n🔎 Checking for existing processes...")
try:
    result = subprocess.run(['lsof', '-i', ':7862'], capture_output=True, text=True)
    if result.stdout:
        print("   ⚠️  Port 7862 is already in use!")
        print("   Killing existing process...")
        subprocess.run(['pkill', '-f', 'python.*optionslab'], capture_output=True)
        time.sleep(1)
    else:
        print("   ✅ Port 7862 is free")
except Exception as e:
    print(f"   ⚠️  Could not check port: {e}")

# Start the app
print(f"\n🚀 Starting OptionsLab...")
print("="*60)

try:
    # Run the app module
    from optionslab.app import create_simple_interface
    import logging
    
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    port = int(os.getenv("GRADIO_SERVER_PORT", "7862"))
    print(f"\n📊 Creating interface...")
    
    app = create_simple_interface()
    
    print(f"\n🌐 Starting server...")
    print(f"\n" + "="*60)
    print(f"✅ OptionsLab is starting!")
    print(f"\n📱 Access the app at:")
    print(f"   • http://localhost:{port}")
    print(f"   • http://127.0.0.1:{port}")
    print(f"\n⏳ Please wait a few seconds for the server to fully start...")
    print(f"⌨️  Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    # Launch with all debug info
    app.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True,
        inbrowser=False,
        quiet=False,
        debug=True
    )
    
except KeyboardInterrupt:
    print("\n\n🛑 Server stopped by user")
except Exception as e:
    print(f"\n❌ Error starting app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)