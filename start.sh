#!/bin/bash

echo "🎯 Starting OptionsLab..."
echo "================================"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or not in PATH"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "start.py" ]; then
    echo "❌ Please run this script from the OptionsLab directory"
    exit 1
fi

# Make start.py executable
chmod +x start.py

# Start OptionsLab
echo "🚀 Launching OptionsLab..."
python start.py 