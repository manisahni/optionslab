# OptionsLab AI Features Guide

## Overview

OptionsLab now includes comprehensive AI-powered features using Google's Gemini API to enhance your options backtesting experience. The AI provides:

- **Strategy Analysis**: Deep insights into backtest performance
- **Risk Assessment**: AI-powered risk analysis and recommendations
- **Optimization Suggestions**: Specific parameter adjustments to improve performance
- **Interactive Chat**: Ask questions about your trades and strategies
- **Trade Explanations**: Understand why specific trades won or lost

## Setup

### 1. Get a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key

### 2. Set Environment Variable

```bash
export GEMINI_API_KEY='your-api-key-here'
```

For permanent setup, add this to your `.bashrc` or `.zshrc`:
```bash
echo "export GEMINI_API_KEY='your-api-key-here'" >> ~/.bashrc
source ~/.bashrc
```

### 3. Install Dependencies

```bash
pip install google-generativeai
```

### 4. Run the Services

Start the FastAPI server:
```bash
uvicorn optionslab.api.server:app --reload
```

In another terminal, start Streamlit:
```bash
streamlit run optionslab/ui/app_api.py
```

## AI Features

### 1. AI Analysis Tab

After running a backtest, navigate to the "🤖 AI Analysis" tab to see:

- **Performance Analysis**: Overall strategy quality assessment
- **Risk Assessment**: Risk profile and management recommendations
- **Optimization Suggestions**: Specific parameter adjustments
- **Market Analysis**: Performance across different market conditions
- **Executive Summary**: Quick overview of strategy viability

### 2. AI Chat Assistant

The "💬 AI Chat" tab provides an interactive assistant that can:

- Answer questions about your backtest results
- Explain specific trades
- Suggest strategy improvements
- Provide market insights
- Help with risk management

**Quick Actions:**
- **Analyze Results**: Get instant analysis of current backtest
- **Suggest Improvements**: Receive optimization recommendations
- **Market Insights**: Understand market conditions
- **Clear Chat**: Start a fresh conversation

### 3. Quick Insights

On the Overview tab, you'll find "Quick AI Insights" that provide:
- 3 key takeaways from your backtest
- Instant actionable recommendations
- Performance highlights

## API Endpoints

The FastAPI server provides several AI endpoints:

### Analyze Backtest
```bash
POST /api/ai/analyze/{job_id}
```
Analyzes completed backtest results.

### Chat
```bash
POST /api/ai/chat
```
Send messages to the AI assistant.

### Stream Chat
```bash
POST /api/ai/chat/stream
```
Get streaming responses from the AI.

### Generate Strategy
```bash
POST /api/ai/generate-strategy
```
Generate new strategy recommendations.

### AI Status
```bash
GET /api/ai/status
```
Check AI service status and configuration.

## Configuration

Environment variables for customization:

- `GEMINI_API_KEY`: Your Gemini API key (required)
- `ENABLE_AI_FEATURES`: Enable/disable AI features (default: true)
- `GEMINI_MODEL`: Model to use (default: gemini-1.5-flash)
- `AI_TEMPERATURE`: Response creativity (0-1, default: 0.7)
- `AI_MAX_TOKENS`: Maximum response length (default: 2000)

## Best Practices

1. **Run Quality Backtests**: AI insights are only as good as your data
2. **Ask Specific Questions**: The more specific, the better the answers
3. **Iterate on Suggestions**: Test AI recommendations with new backtests
4. **Use Multiple Analysis Types**: Combine performance, risk, and optimization insights

## Troubleshooting

### AI Features Not Showing
1. Check that `GEMINI_API_KEY` is set
2. Verify API server is running
3. Look for errors in the Streamlit sidebar

### Connection Errors
1. Ensure you have internet connectivity
2. Verify your API key is valid
3. Check the FastAPI logs for errors

### Rate Limits
Google's free tier has limits. If you hit them:
1. Wait a few minutes
2. Consider upgrading your API plan
3. Reduce request frequency

## Privacy & Security

- Your data is sent to Google's Gemini API for processing
- No trading data is stored by Google
- API keys are never logged or stored
- All communications use HTTPS

## Future Enhancements

Planned features include:
- Strategy comparison AI
- Portfolio-level analysis
- Real-time market integration
- Custom AI prompts
- Export AI reports