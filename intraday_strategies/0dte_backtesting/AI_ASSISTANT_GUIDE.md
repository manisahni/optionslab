# AI Assistant Testing Guide

## How to Access
1. Open your browser to: **http://localhost:7866**
2. Click on the **"AI Assistant"** tab (last tab on the right)

## Interface Overview
- **Chat Interface**: A conversation-style interface where you can type questions
- **Send Button**: Click to submit your query
- **Clear Chat**: Reset the conversation
- **Example Buttons**: Quick examples to try

## What Should Happen

### Good Response (Executes Code):
```
You: Calculate hourly volatility statistics and show me which hours have the highest and lowest volatility

AI: I'll analyze the hourly volatility patterns in the SPY data.

Based on my analysis:

**Calmest Trading Hours (Lowest Volatility):**
1. 12:00 PM - 1:00 PM: Average volatility of 8.2%
2. 1:00 PM - 2:00 PM: Average volatility of 8.5%
3. 11:00 AM - 12:00 PM: Average volatility of 9.1%

**Most Volatile Trading Hours:**
1. 9:30 AM - 10:30 AM: Average volatility of 23.7%
2. 3:00 PM - 4:00 PM: Average volatility of 18.4%
3. 10:30 AM - 11:00 AM: Average volatility of 15.2%

The opening hour shows nearly 3x the volatility of midday hours.
```

### Poor Response (Only Shows Code):
```
You: Calculate hourly volatility...

AI: To analyze hourly volatility, you can use this code:

```python
df['hour'] = df['date'].dt.hour
hourly_vol = df.groupby('hour')['returns'].std()
print(hourly_vol)
```

⚠️ Note: The AI provided code but didn't execute it. Try asking for specific results...
```

## Test Sequence

1. **Start Simple**: "What's the current price of SPY?"
2. **Test Execution**: "Calculate the 20-day moving average and tell me the current value"
3. **Complex Analysis**: Use the queries from test_ai_demo.py

## Troubleshooting

- **If AI only shows code**: Your LM Studio model might not be following instructions. Try:
  - Using Qwen2.5-Coder or DeepSeek-Coder models
  - Being more explicit: "Execute the code and show me the actual numbers"
  
- **If you get errors**: The AI should self-correct, but you can help by:
  - Asking "Can you fix that error and try again?"
  - Providing hints: "Maybe check if the data has that column first"

## Success Indicators

✅ AI returns specific numbers and statistics
✅ Responses include actual calculated values
✅ Follow-up questions maintain context
✅ Visualizations appear when requested
✅ Errors are handled gracefully

❌ Only shows code without results
❌ Generic responses without data
❌ Loses context between messages