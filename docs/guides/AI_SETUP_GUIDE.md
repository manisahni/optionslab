# OptionsLab AI Setup Guide

This guide will help you set up the AI features in OptionsLab using Google Generative AI (Gemini).

## Prerequisites

1. **Python 3.8+** installed
2. **Google Generative AI API Key** (free tier available)

## Step 1: Get Your Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key (starts with "AIza...")

## Step 2: Install Dependencies

Run the following command to install required packages:

```bash
pip install google-generativeai>=0.8.0 streamlit>=1.28.0 pandas>=1.5.0 plotly>=5.0.0 python-dotenv>=1.0.0
```

## Step 3: Configure API Key

### Option A: Using the Setup Script (Recommended)

```bash
python setup_ai_key.py
```

This script will:
- Install dependencies automatically
- Prompt you for your API key
- Save it securely in Streamlit secrets
- Test the connection

### Option B: Manual Configuration

1. Create the `.streamlit` directory:
```bash
mkdir -p .streamlit
```

2. Create `.streamlit/secrets.toml`:
```toml
# OptionsLab AI Configuration
GEMINI_API_KEY = "your-api-key-here"

# AI Feature Settings
ENABLE_AI_FEATURES = true
GEMINI_MODEL = "gemini-1.5-flash"
AI_TEMPERATURE = 0.7
AI_MAX_TOKENS = 2000

# Enable all AI features
ENABLE_STRATEGY_ANALYSIS = true
ENABLE_CHAT_ASSISTANT = true
ENABLE_STRATEGY_GENERATION = true
ENABLE_TRADE_ANALYSIS = true
```

## Step 4: Test the Setup

Run the test script to verify everything is working:

```bash
python test_ai_features.py
```

You should see:
```
🔍 OptionsLab AI Features Test
==================================================
📦 Checking Dependencies...
   ✅ google-generativeai
   ✅ streamlit
   ✅ pandas
   ✅ plotly

🤖 Testing AI Components...

🧪 Testing AI Config...
   ✅ PASS

🧪 Testing Gemini Client...
   ✅ PASS

🧪 Testing Strategy Analyzer...
   ✅ PASS

🧪 Testing Chat Assistant...
   ✅ PASS

📊 Test Results:
   ✅ AI Config
   ✅ Gemini Client
   ✅ Strategy Analyzer
   ✅ Chat Assistant

Overall: 4/4 tests passed
🎉 All AI components are working!
```

## Step 5: Start the Application

```bash
./run_streamlit.sh
```

## AI Features Available

Once configured, you'll have access to:

### 1. AI Strategy Builder
- Generate trading strategies using natural language
- Save strategies as YAML files
- Access strategies from both Traditional and YAML modes

### 2. AI Analysis
- Analyze backtest results with AI insights
- Get performance, risk, and optimization recommendations
- Export analysis reports

### 3. AI Chat Assistant
- Ask questions about options trading
- Get explanations of trades and strategies
- Receive market insights and recommendations

### 4. AI Trade Analysis
- Get AI-powered analysis of individual trades
- Understand why trades succeeded or failed
- Receive improvement suggestions

## Troubleshooting

### "google-generativeai not installed"
```bash
pip install google-generativeai
```

### "GEMINI_API_KEY not set"
Make sure your API key is in `.streamlit/secrets.toml` or set as environment variable:
```bash
export GEMINI_API_KEY="your-api-key"
```

### "Connection failed"
1. Check your internet connection
2. Verify your API key is correct
3. Check if you have API quota remaining

### "Import errors"
Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Security Notes

- Never commit your API key to version control
- The `.streamlit/secrets.toml` file is automatically ignored by git
- API keys are stored securely in Streamlit's secrets management

## API Usage and Costs

- Google Generative AI offers a free tier
- Free tier includes 15 requests per minute
- Monitor usage at [Google AI Studio](https://makersuite.google.com/app/apikey)

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Run `python test_ai_features.py` to diagnose problems
3. Check the logs in the Streamlit interface

## Advanced Configuration

You can customize AI behavior by modifying `.streamlit/secrets.toml`:

```toml
# Model settings
GEMINI_MODEL = "gemini-1.5-flash"  # or "gemini-1.5-pro"
AI_TEMPERATURE = 0.7               # 0.0-1.0 (creativity)
AI_MAX_TOKENS = 2000               # Response length

# Feature toggles
ENABLE_STRATEGY_ANALYSIS = true
ENABLE_CHAT_ASSISTANT = true
ENABLE_STRATEGY_GENERATION = true
ENABLE_TRADE_ANALYSIS = true
``` 