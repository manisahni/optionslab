#!/bin/bash

echo "🚀 Starting OptionsLab Auditable Backtesting System..."
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "auditable_gradio_app.py" ]; then
    echo "❌ Error: auditable_gradio_app.py not found!"
    echo "Please run this script from the thetadata-api directory."
    exit 1
fi

# Check if auditable_backtest.py exists
if [ ! -f "auditable_backtest.py" ]; then
    echo "❌ Error: auditable_backtest.py not found!"
    echo "The auditable backtest engine is required."
    exit 1
fi

# Check if simple_test_strategy.yaml exists in parent directory
if [ ! -f "../simple_test_strategy.yaml" ]; then
    echo "❌ Error: simple_test_strategy.yaml not found in parent directory!"
    echo "The test strategy configuration is required."
    exit 1
fi

echo "✅ All required files found!"

# Check for data files (in parent directory)
if [ -d "../spy_options_downloader/spy_options_parquet/repaired" ]; then
    echo "✅ Found repaired data files"
else
    echo "⚠️  No repaired data files found"
fi

if [ -d "../spy_options_downloader/spy_options_parquet" ]; then
    echo "✅ Found main data directory"
else
    echo "⚠️  No main data directory found"
fi

# Check for strategy files (in parent directory)
if [ -f "../simple_test_strategy.yaml" ] || [ -f "../advanced_test_strategy.yaml" ]; then
    echo "✅ Found strategy configurations"
else
    echo "⚠️  No strategy configurations found"
fi

echo ""
echo "🌐 Starting Auditable Gradio App..."
echo "   URL: http://localhost:7860"
echo "   Press Ctrl+C to stop"
echo ""

# Start the app
python auditable_gradio_app.py 