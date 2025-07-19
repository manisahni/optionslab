#!/bin/bash
# Start the Gradio app for OptionsLab

echo "🚀 Starting OptionsLab Gradio App..."
echo "📂 Working directory: $(pwd)"

# Activate virtual environment
source venv/bin/activate

# Change to optionslab directory
cd optionslab

# Run the app
echo "🌐 Starting server..."
python auditable_gradio_app.py