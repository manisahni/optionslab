#!/usr/bin/env python3
"""
Test script to verify integration of all components
"""

import sys
import json
from pathlib import Path

print("🧪 Testing OptionsLab Integration...")
print("=" * 50)

# Test 1: Check if all modules can be imported
print("\n📦 Testing module imports...")
try:
    from optionslab.auditable_backtest import run_auditable_backtest
    print("✅ auditable_backtest imported successfully")
except Exception as e:
    print(f"❌ Failed to import auditable_backtest: {e}")

try:
    from optionslab.visualization import plot_pnl_curve, plot_trade_markers
    print("✅ visualization module imported successfully")
except Exception as e:
    print(f"❌ Failed to import visualization: {e}")

try:
    from optionslab.ai_assistant import AIAssistant
    print("✅ ai_assistant module imported successfully")
except Exception as e:
    print(f"❌ Failed to import ai_assistant: {e}")

# Test 2: Check if trade logs directory exists
print("\n📁 Testing file system...")
trade_logs_dir = Path("optionslab/trade_logs")
if trade_logs_dir.exists():
    print(f"✅ Trade logs directory exists: {trade_logs_dir}")
    # Count log files
    log_files = list(trade_logs_dir.rglob("*.json"))
    print(f"   Found {len(log_files)} trade log files")
else:
    print(f"❌ Trade logs directory not found")

# Test 3: Check if .env file exists and has API key
print("\n🔑 Testing API configuration...")
env_file = Path(".env")
if env_file.exists():
    print("✅ .env file exists")
    with open(env_file, 'r') as f:
        content = f.read()
        if "GEMINI_API_KEY" in content:
            print("✅ GEMINI_API_KEY found in .env")
        else:
            print("❌ GEMINI_API_KEY not found in .env")
else:
    print("❌ .env file not found")

# Test 4: Test AI Assistant initialization
print("\n🤖 Testing AI Assistant...")
try:
    ai = AIAssistant()
    if ai.is_configured():
        print("✅ AI Assistant configured successfully")
        print(f"   API Key loaded: {'Yes' if ai.api_key else 'No'}")
    else:
        print("❌ AI Assistant not configured")
except Exception as e:
    print(f"❌ Failed to initialize AI Assistant: {e}")

# Test 5: Check if Gradio app is running
print("\n🌐 Testing Gradio app...")
import requests
try:
    response = requests.get("http://localhost:7862", timeout=5)
    if response.status_code == 200:
        print("✅ Gradio app is running on port 7862")
    else:
        print(f"⚠️  Gradio app responded with status: {response.status_code}")
except requests.exceptions.ConnectionError:
    print("❌ Gradio app is not running on port 7862")
except Exception as e:
    print(f"❌ Error checking Gradio app: {e}")

# Test 6: Check sample trade log
print("\n📊 Testing sample trade log...")
sample_logs = list(trade_logs_dir.rglob("*.json"))[:1] if trade_logs_dir.exists() else []
if sample_logs:
    sample_log = sample_logs[0]
    print(f"✅ Reading sample log: {sample_log.name}")
    try:
        with open(sample_log, 'r') as f:
            data = json.load(f)
            metadata = data.get('metadata', {})
            trades = data.get('trades', [])
            print(f"   Strategy: {metadata.get('strategy', 'Unknown')}")
            print(f"   Total trades: {len(trades)}")
            print(f"   Total return: {metadata.get('total_return', 0):.2%}")
    except Exception as e:
        print(f"❌ Failed to read log: {e}")
else:
    print("ℹ️  No trade logs found to test")

print("\n" + "=" * 50)
print("🎯 Integration test complete!")
print("\nNext steps:")
print("1. Open http://localhost:7862 in your browser")
print("2. Run a backtest in the 'Run Backtest' tab")
print("3. Check visualizations in the 'Visualizations' tab")
print("4. Test AI chat in the 'AI Assistant' tab")