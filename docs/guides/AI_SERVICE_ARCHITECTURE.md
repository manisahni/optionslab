# AI Service Architecture

## Overview

To avoid Streamlit caching issues and provide better performance, the AI features are now implemented as a separate service that runs independently from the Streamlit app.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│  Streamlit UI   │────▶│  AI Service      │────▶│  Gemini API     │
│  (Port 8501)    │ HTTP│  (Port 8001)     │     │                 │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                                                    
        │               ┌──────────────────┐                
        └──────────────▶│  FastAPI Backend │                
                   HTTP │  (Port 8000)     │                
                        │                  │                
                        └──────────────────┘                
```

## Components

### 1. AI Service (`optionslab/ai_service/server.py`)
- Standalone FastAPI service running on port 8001
- Manages all AI interactions with Gemini
- Handles chat sessions and analysis requests
- No Streamlit dependencies = no caching issues

### 2. AI Client (`optionslab/ai_service/client.py`)
- HTTP client library used by Streamlit
- Communicates with AI service via REST API
- Handles streaming responses
- Includes error handling and retries

### 3. Streamlit Components (`optionslab/ui/ai_components_service.py`)
- UI components that use the AI client
- No direct AI/Gemini imports
- Clean separation of concerns

## Benefits

1. **No Caching Issues**: AI code runs outside Streamlit's process
2. **Better Performance**: AI service can be scaled independently
3. **Cleaner Architecture**: Clear separation between UI and AI logic
4. **Easier Debugging**: AI service has its own logs and API docs
5. **Flexibility**: Can run AI service on a different machine if needed

## Running the Services

You need to run 3 services:

### Terminal 1: AI Service
```bash
./run_ai_service.sh
# Or: python -m uvicorn optionslab.ai_service.server:app --port 8001
```

### Terminal 2: Main API
```bash
./run_api.sh
# Or: uvicorn optionslab.api.server:app --port 8000
```

### Terminal 3: Streamlit UI
```bash
./run_streamlit.sh
# Or: streamlit run optionslab/ui/app_api.py
```

## API Endpoints

The AI Service provides these endpoints:

- `GET /` - Health check
- `GET /status` - Detailed service status
- `POST /analyze` - General AI analysis
- `POST /analyze/stream` - Streaming analysis
- `POST /analyze/backtest` - Analyze backtest results
- `POST /chat` - Chat interaction
- `POST /chat/stream` - Streaming chat
- `DELETE /chat/session/{id}` - Clear chat session

## Configuration

Set these environment variables before starting the AI service:

```bash
export GEMINI_API_KEY='your-api-key-here'
export GEMINI_MODEL='gemini-1.5-flash'  # Optional
export AI_TEMPERATURE='0.7'             # Optional
export AI_MAX_TOKENS='2000'             # Optional
```

## Testing

Check if the AI service is running:
```bash
curl http://localhost:8001/status
```

Test AI analysis:
```bash
curl -X POST http://localhost:8001/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is a bull call spread?"}'
```

## Troubleshooting

### AI features not showing in Streamlit
1. Check AI service is running: `http://localhost:8001/`
2. Check GEMINI_API_KEY is set
3. Look at AI service logs for errors

### Connection errors
1. Ensure all 3 services are running
2. Check ports 8000, 8001, and 8501 are not in use
3. Verify firewall settings

### Performance issues
1. AI service caches sessions in memory
2. Restart AI service to clear all sessions
3. Monitor memory usage of AI service

## Future Enhancements

1. Add Redis for session persistence
2. Implement rate limiting
3. Add authentication for multi-user setups
4. Deploy AI service to cloud for better performance
5. Add request queuing for heavy loads