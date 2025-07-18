# OptionsLab Quick Start Guide

## Prerequisites

1. Python 3.8+ installed
2. pip package manager
3. Access to SPY options data (parquet files)

## Installation

```bash
# Clone the repository (if not already done)
git clone https://github.com/yourusername/thetadata-api.git
cd thetadata-api

# Install dependencies
pip install -r requirements.txt

# For AI features (optional)
pip install google-generativeai
```

## Running the Application

### Option 1: Using the provided scripts (Recommended)

```bash
# Terminal 1: Start the AI service (optional, for AI features)
./run_ai_service.sh

# Terminal 2: Start the API server
./run_api.sh

# Terminal 3: Start the Streamlit UI
./run_streamlit.sh
```

### Option 2: Manual setup

```bash
# Terminal 1: Set Python path and start API
export PYTHONPATH=/path/to/thetadata-api:$PYTHONPATH
uvicorn optionslab.api.server:app --reload

# Terminal 2: Set Python path and start Streamlit
export PYTHONPATH=/path/to/thetadata-api:$PYTHONPATH
streamlit run optionslab/ui/app_api.py
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'optionslab'"

This means Python can't find the optionslab module. Solutions:

1. Use the provided run scripts (`./run_api.sh` and `./run_streamlit.sh`)
2. Set PYTHONPATH manually: `export PYTHONPATH=/path/to/thetadata-api:$PYTHONPATH`
3. Install the package in development mode: `pip install -e .` (from the project root)

### "Cannot connect to API server"

1. Make sure the API server is running (Terminal 1)
2. Check that it's running on port 8000
3. Visit http://localhost:8000 in your browser - you should see a status message

### AI Features Not Working

1. Set your Gemini API key: `export GEMINI_API_KEY='your-key-here'`
2. Install the package: `pip install google-generativeai`
3. Check AI status in the Streamlit sidebar

## Basic Usage

1. **Start both services** (API server and Streamlit UI)
2. **Open Streamlit** - It should automatically open in your browser at http://localhost:8501
3. **Configure your backtest** in the sidebar:
   - Select a strategy (e.g., Long Call)
   - Set date range
   - Adjust parameters
4. **Click "Run Backtest"**
5. **View results** in the different tabs:
   - Overview: Performance metrics and equity curve
   - Trade Analysis: Individual trade details
   - Daily Stats: Day-by-day performance
   - AI Analysis: Deep insights (if AI is configured)
   - AI Chat: Ask questions about your results (if AI is configured)

## Next Steps

- Read the [AI Features Guide](AI_FEATURES_GUIDE.md) to enable AI analysis
- Check the main [README](optionslab/README.md) for detailed documentation
- Explore different strategies and parameters
- Create custom strategy configurations