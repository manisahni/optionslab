#!/usr/bin/env python3
"""
Simple test script for Gemini AI integration
This helps diagnose issues with the AI setup
"""
import os
import sys

print("🤖 Gemini AI Test Script")
print("=" * 50)

# Step 1: Check if API key is set
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ GEMINI_API_KEY environment variable is not set!")
    print("\nTo fix this:")
    print("1. Get an API key from: https://makersuite.google.com/app/apikey")
    print("2. Set it in your environment:")
    print("   export GEMINI_API_KEY='your-api-key-here'")
    sys.exit(1)
else:
    print(f"✅ GEMINI_API_KEY is set (length: {len(api_key)} chars)")

# Step 2: Check if google-generativeai is installed
print("\n📦 Checking package installation...")
try:
    import google.generativeai as genai
    print("✅ google-generativeai is installed")
except ImportError:
    print("❌ google-generativeai is not installed!")
    print("\nTo fix this:")
    print("   pip install google-generativeai")
    sys.exit(1)

# Step 3: Test basic API connection
print("\n🔗 Testing API connection...")
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Simple test prompt
    response = model.generate_content("Say 'Hello, OptionsLab!' if you can hear me.")
    print("✅ API connection successful!")
    print(f"   Response: {response.text[:100]}...")
    
except Exception as e:
    print(f"❌ API connection failed: {e}")
    print("\nPossible issues:")
    print("1. Invalid API key")
    print("2. Network connection issues")
    print("3. API quota exceeded")
    sys.exit(1)

# Step 4: Test the OptionsLab integration
print("\n🧪 Testing OptionsLab AI integration...")
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from optionslab.ai_system import GeminiClient
    
    client = GeminiClient()
    test_result = client.test_connection()
    
    if test_result:
        print("✅ OptionsLab AI integration is working!")
    else:
        print("⚠️  GeminiClient initialized but test failed")
        
except Exception as e:
    print(f"❌ OptionsLab AI integration failed: {e}")
    print("\nMake sure you're running from the project root directory")

# Step 5: Test a simple analysis
print("\n📊 Testing AI analysis capability...")
try:
    test_prompt = """
    Analyze these options trading results:
    - Total Return: 15.3%
    - Sharpe Ratio: 1.24
    - Win Rate: 68%
    - Max Drawdown: -12.5%
    
    Provide a one-sentence assessment.
    """
    
    response = client.generate_content(test_prompt)
    print("✅ AI analysis working!")
    print(f"   Analysis: {response[:200]}...")
    
except Exception as e:
    print(f"❌ AI analysis failed: {e}")

print("\n" + "=" * 50)
print("✨ Summary:")
if 'client' in locals() and test_result:
    print("AI features are properly configured and ready to use!")
    print("\nNext steps:")
    print("1. Start the API server: ./run_api.sh")
    print("2. Start Streamlit: ./run_streamlit.sh")
    print("3. Run a backtest and check the AI tabs!")
else:
    print("Please fix the issues above before using AI features.")