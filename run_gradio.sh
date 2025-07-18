#!/bin/bash

echo "🚀 Starting OptionsLab Gradio App..."

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: Not in a virtual environment"
fi

# Install required packages
echo "📦 Installing dependencies..."
pip install gradio pandas plotly requests

# Check if API server is running
echo "🔍 Checking API server..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API server is running"
else
    echo "❌ API server is not running"
    echo "   Please start it with: uvicorn optionslab.api.server:app --reload"
fi

# Check if AI service is running
echo "🔍 Checking AI service..."
if curl -s http://localhost:8001/ > /dev/null; then
    echo "✅ AI service is running"
else
    echo "❌ AI service is not running"
    echo "   Please start it with: python -m optionslab.ai_service.server"
fi

echo ""
echo "🌐 Starting Gradio app on http://localhost:7860"
echo "   Press Ctrl+C to stop"
echo ""

# Run the Gradio app
python simple_gradio_app.py 