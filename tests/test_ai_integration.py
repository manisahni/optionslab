#!/usr/bin/env python3
"""
Test script for AI integration
Tests the AI components and API endpoints
"""
import os
import sys
import requests
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test 1: Check AI configuration
print("🔍 Test 1: Checking AI configuration...")
try:
    from optionslab.config.ai_config import get_ai_config
    config = get_ai_config()
    validation = config.validate_config()
    
    if validation['valid'] and validation['ai_enabled']:
        print("✅ AI configuration is valid")
        print(f"   Model: {validation['model']}")
    else:
        print("❌ AI configuration issues:")
        for issue in validation['issues']:
            print(f"   - {issue}")
except Exception as e:
    print(f"❌ Error checking AI config: {e}")

# Test 2: Check Gemini client
print("\n🔍 Test 2: Testing Gemini client...")
if os.getenv('GEMINI_API_KEY'):
    try:
        from optionslab.ai_system import GeminiClient
        client = GeminiClient()
        if client.test_connection():
            print("✅ Gemini client connection successful")
        else:
            print("❌ Gemini client connection failed")
    except Exception as e:
        print(f"❌ Error testing Gemini client: {e}")
else:
    print("⚠️  GEMINI_API_KEY not set in environment")

# Test 3: Check API endpoints
print("\n🔍 Test 3: Testing API endpoints...")
api_url = "http://localhost:8000"

# Check if API is running
try:
    response = requests.get(f"{api_url}/", timeout=2)
    if response.status_code == 200:
        print("✅ API server is running")
        
        # Check AI status endpoint
        response = requests.get(f"{api_url}/api/ai/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ AI status endpoint working")
            print(f"   Status: {status['status']}")
            print(f"   Features: {json.dumps(status['features'], indent=6)}")
        else:
            print("❌ AI status endpoint failed")
    else:
        print("❌ API server not responding")
except Exception as e:
    print(f"❌ Cannot connect to API server: {e}")
    print("   Make sure to run: uvicorn optionslab.api.server:app --reload")

# Test 4: Test AI components
print("\n🔍 Test 4: Testing AI components...")
if os.getenv('GEMINI_API_KEY'):
    try:
        from optionslab.ai_system import StrategyAnalyzer, ChatAssistant
        
        # Create test results
        test_results = {
            'performance_metrics': {
                'total_return': 0.15,
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.08,
                'win_rate': 0.55,
                'total_trades': 50,
                'final_value': 115000
            },
            'metadata': {
                'strategy_config': {'type': 'long_call'},
                'start_date': '20240101',
                'end_date': '20241231'
            }
        }
        
        print("   Testing StrategyAnalyzer...")
        analyzer = StrategyAnalyzer(client)
        # Just test initialization, not actual analysis (to save API calls)
        print("   ✅ StrategyAnalyzer initialized")
        
        print("   Testing ChatAssistant...")
        assistant = ChatAssistant(client)
        print("   ✅ ChatAssistant initialized")
        
    except Exception as e:
        print(f"❌ Error testing AI components: {e}")

print("\n📊 Summary:")
print("=" * 50)
print("To use AI features:")
print("1. Set GEMINI_API_KEY environment variable")
print("2. Run FastAPI server: uvicorn optionslab.api.server:app --reload")
print("3. Run Streamlit app: streamlit run optionslab/ui/app_api.py")
print("4. AI features will appear in the UI after running a backtest")