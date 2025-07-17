#!/bin/bash

# SPY Options Backtester Launcher Script

echo "🚀 Starting SPY Options Backtester..."
echo "=================================="

# Kill any existing streamlit processes
echo "Cleaning up existing processes..."
pkill -f streamlit 2>/dev/null

# Navigate to the streamlit-backtester directory
cd streamlit-backtester

# Run streamlit with proper settings
echo "Launching Streamlit app..."
streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --browser.gatherUsageStats false \
    --theme.base "dark"

echo "=================================="
echo "App should be available at:"
echo "http://127.0.0.1:8501"
echo "or"
echo "http://localhost:8501"