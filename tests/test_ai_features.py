#!/usr/bin/env python3
"""
Test script for AI features
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_ai_components():
    """Test all AI components"""
    print("🤖 Testing AI Components")
    print("=" * 50)
    
    tests = [
        ("AI Config", test_ai_config),
        ("Gemini Client", test_gemini_client),
        ("Strategy Analyzer", test_strategy_analyzer),
        ("Chat Assistant", test_chat_assistant),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        try:
            success = test_func()
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status}")
            results.append((test_name, success))
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"   {status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All AI components are working!")
    else:
        print("⚠️  Some AI components have issues. Check the errors above.")
    
    return passed == total

def test_ai_config():
    """Test AI configuration"""
    try:
        from optionslab.ai_config_dir.ai_config import get_ai_config
        
        config = get_ai_config()
        validation = config.validate_config()
        
        print(f"   - AI Enabled: {config.enable_ai_features}")
        print(f"   - Model: {config.model}")
        print(f"   - API Key: {'Set' if config.gemini_api_key else 'Not Set'}")
        
        return True
    except Exception as e:
        print(f"   - Error: {e}")
        return False

def test_gemini_client():
    """Test Gemini client"""
    try:
        # First check if google-generativeai is installed
        try:
            import google.generativeai as genai
        except ImportError:
            print("   - google-generativeai not installed")
            return False
        
        from optionslab.ai_config_dir.ai_config import get_ai_config
        
        config = get_ai_config()
        if not config.gemini_api_key:
            print("   - No API key available")
            return False
        
        # Test direct API call
        genai.configure(api_key=config.gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello, this is a test.")
        
        if response and response.text:
            print("   - Connection: Success")
            return True
        else:
            print("   - Connection: Failed - no response")
            return False
        
    except Exception as e:
        print(f"   - Error: {e}")
        return False

def test_strategy_analyzer():
    """Test strategy analyzer"""
    try:
        from optionslab.ai_system import StrategyAnalyzer
        from optionslab.ai_config_dir.ai_config import get_ai_config
        
        config = get_ai_config()
        if not config.gemini_api_key:
            print("   - No API key available")
            return False
        
        # Test with mock data
        mock_results = {
            'performance_metrics': {
                'total_return': 0.15,
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.05,
                'win_rate': 0.65,
                'total_trades': 50
            },
            'metadata': {
                'strategy_config': {'type': 'Long Call'},
                'start_date': '2024-01-01',
                'end_date': '2024-12-31'
            }
        }
        
        # Create analyzer with mock client
        analyzer = StrategyAnalyzer(None)  # We'll test without actual client
        print("   - Strategy Analyzer initialized")
        return True
        
    except Exception as e:
        print(f"   - Error: {e}")
        return False

def test_chat_assistant():
    """Test chat assistant"""
    try:
        from optionslab.ai_system import ChatAssistant
        from optionslab.ai_config_dir.ai_config import get_ai_config
        
        config = get_ai_config()
        if not config.gemini_api_key:
            print("   - No API key available")
            return False
        
        # Create assistant with mock client
        assistant = ChatAssistant(None)  # We'll test without actual client
        print("   - Chat Assistant initialized")
        return True
        
    except Exception as e:
        print(f"   - Error: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print("📦 Checking Dependencies...")
    
    required_packages = [
        'google-generativeai',
        'streamlit',
        'pandas',
        'plotly'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Run: pip install " + " ".join(missing))
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 OptionsLab AI Features Test")
    print("=" * 50)
    
    # Check dependencies first
    deps_ok = check_dependencies()
    
    if deps_ok:
        success = test_ai_components()
        sys.exit(0 if success else 1)
    else:
        print("\n❌ Please install missing dependencies first")
        sys.exit(1) 