#!/usr/bin/env python3
"""
Test AI Assistant functionality
"""

from optionslab.ai_assistant import AIAssistant

print("🤖 Testing AI Assistant...")
print("=" * 50)

# Initialize AI
ai = AIAssistant()

# Check configuration
print(f"✅ AI Configured: {ai.is_configured()}")
print(f"✅ API Key loaded from .env: {'Yes' if ai.api_key else 'No'}")

# Test context loading
print("\n📥 Testing context loading...")
result = ai.load_context("trades")
print(f"   Result: {result[:100]}..." if len(result) > 100 else f"   Result: {result}")

# Test basic chat
print("\n💬 Testing chat...")
response = ai.chat("What trading strategies are available?")
print(f"   Response: {response[:200]}..." if len(response) > 200 else f"   Response: {response}")

print("\n✅ AI Assistant test complete!")