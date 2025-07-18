# 🚀 Quick Start Guide

## Simple Startup Options

### Option 1: One-Command Startup (Recommended)
```bash
./start.sh
```

### Option 2: Python Script
```bash
python start.py
```

### Option 3: Manual Startup (Advanced)
```bash
# Terminal 1: Backend
python backend.py

# Terminal 2: AI Service  
python ai_service.py

# Terminal 3: Frontend
python simple_gradio_app.py
```

## What the Startup Script Does

The `start.py` script automatically:

1. ✅ **Checks Dependencies** - Verifies all required files exist
2. 🧹 **Cleans Up Ports** - Kills any existing processes on ports 8000, 8001, 7860
3. 🚀 **Starts Backend** - Launches FastAPI server on port 8000
4. 🤖 **Starts AI Service** - Launches AI service on port 8001  
5. 📊 **Starts Frontend** - Launches Gradio interface on port 7860
6. ✅ **Verifies Services** - Confirms all services are running properly

## Access Points

Once started, you can access:

- **📊 Main Interface**: http://localhost:7860
- **🔧 API Documentation**: http://localhost:8000/docs
- **🤖 AI Service Status**: http://localhost:8001/status

## Stopping Services

Press `Ctrl+C` in the terminal where you ran the startup script to stop all services cleanly.

## Troubleshooting

### Port Already in Use
The startup script automatically cleans up ports, but if you get port conflicts:
```bash
# Kill processes on specific ports
lsof -ti:8000 | xargs kill -9
lsof -ti:8001 | xargs kill -9  
lsof -ti:7860 | xargs kill -9
```

### Missing Dependencies
Install required packages:
```bash
pip install -r requirements.txt
```

### API Key Setup
1. Go to http://localhost:7860
2. Navigate to the "🔑 Key Manager" tab
3. Enter your Gemini API key
4. Click "💾 Save and Verify Key"

## Features Available

- ✅ **Backtesting** - Run options strategies with detailed results
- ✅ **AI Strategy Generation** - Create strategies with AI assistance
- ✅ **Performance Analysis** - Get AI-powered insights on backtest results
- ✅ **Interactive Charts** - View equity curves and trade logs
- ✅ **Collapsible Trade Details** - Expandable trade information with Greeks, DTE, IV 