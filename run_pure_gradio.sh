#!/bin/bash

echo "🚀 Starting OptionsLab Pure Gradio App..."
echo "📦 Installing dependencies..."

# Install required packages
pip install gradio pandas plotly pyyaml

echo "🔍 Checking dependencies..."
python -c "import gradio, pandas, plotly, yaml; print('✅ All dependencies installed')"

echo "🌐 Starting Pure Gradio app on http://localhost:7860"
echo "   Press Ctrl+C to stop"
echo ""

# Start the pure Gradio app
python pure_gradio_app.py 