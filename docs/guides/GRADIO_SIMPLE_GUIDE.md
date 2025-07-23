# 🚀 OptionsLab with Gradio - Ultra Simple!

## Complete System in 2 Steps

### Step 1: Run Backtest
```bash
python run_backtest_simple.py --strategy long_call --start 2025-01-01 --end 2025-06-30
```

Output: `<backtest_id>_<memorable_name>_<timestamp>.csv`

### Step 2: View Results with AI
```bash
# Set API key (one time)
export GEMINI_API_KEY='your-key-here'

# Start viewer
python view_results_gradio.py
```

Open: http://localhost:7860

## That's It! 🎉

### What You Get:
- 📈 **Performance Tab**: Metrics and equity curve
- 📋 **Trade Log Tab**: All executed trades
- 🤖 **AI Analysis Tab**: Chat with full code context
- 📝 **Code Tab**: View strategy implementation

### Why Gradio is Better:
✅ No crashes or memory issues  
✅ Built for AI/ML demos  
✅ Simpler chat interface  
✅ Upload any backtest CSV  
✅ Just ~200 lines of code  

### Example AI Questions:
- "Why did this strategy lose money?"
- "What parameters should I change?"
- "Analyze the risk profile"
- "Compare this to buy-and-hold"

### Available Strategies:
- `long_call` - Buy call options
- `long_put` - Buy put options
- `long_straddle` - Call + put at same strike
- `covered_call` - Stock + sell calls
- `cash_secured_put` - Sell puts with cash
- `iron_condor` - 4-leg spread

## No Framework Hell!
Just Python, CSV files, and a simple UI. The way it should be.