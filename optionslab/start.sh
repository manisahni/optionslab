#!/bin/bash

echo "🚀 Starting OptionsLab..."
echo "========================"
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found!"
    echo "Please run this script from the optionslab directory."
    exit 1
fi

echo "✅ Starting the app..."
echo "🌐 Access at: http://localhost:7860"
echo "Press Ctrl+C to stop"
echo ""

# Start the app
python app.py