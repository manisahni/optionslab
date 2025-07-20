#!/usr/bin/env python3
"""
Test AI context loading functionality
"""

from optionslab.ai_assistant import AIAssistant
import json
from pathlib import Path

print("🧪 Testing AI Context Loading...")
print("=" * 50)

# Initialize AI
ai = AIAssistant()
print(f"✅ AI Configured: {ai.is_configured()}")
print(f"📁 Trade logs dir: {ai.trade_logs_dir}")
print(f"   Exists: {ai.trade_logs_dir.exists()}")

# Test loading different context types
print("\n📥 Testing context types...")

# Test trade logs
print("\n1. Testing trade logs context:")
trade_context = ai._load_trade_logs()
if trade_context:
    print(f"✅ Trade logs loaded: {len(trade_context)} characters")
    print(f"   Preview: {trade_context[:200]}...")
else:
    print("❌ No trade logs loaded")

# Test strategies
print("\n2. Testing strategies context:")
strategy_context = ai._load_strategies()
if strategy_context:
    print(f"✅ Strategies loaded: {len(strategy_context)} characters")
    print(f"   Preview: {strategy_context[:200]}...")
else:
    print("❌ No strategies loaded")

# Test source code
print("\n3. Testing source code context:")
code_context = ai._load_source_code()
if code_context:
    print(f"✅ Source code loaded: {len(code_context)} characters")
    print(f"   Preview: {code_context[:200]}...")
else:
    print("❌ No source code loaded")

# Test full context loading
print("\n4. Testing full context loading:")
try:
    result = ai.load_context("all")
    print(f"✅ Result: {result}")
    print(f"   Context loaded flag: {ai.context_loaded}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 50)
print("✅ Context loading test complete!")