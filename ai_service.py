#!/usr/bin/env python3
"""
Simple AI Service Server
Provides HTTP endpoints for AI functionality
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import json

from simple_ai_system import get_ai_system

app = FastAPI(title="OptionsLab AI Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class StrategyRequest(BaseModel):
    market_conditions: str
    risk_tolerance: str
    strategy_type: str

class AnalysisRequest(BaseModel):
    results: Dict

class KeyRequest(BaseModel):
    api_key: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "OptionsLab AI Service", "status": "running"}

@app.get("/status")
async def status():
    """Service status"""
    ai_system = get_ai_system()
    return {
        "status": "running",
        "ai_configured": ai_system.is_configured(),
        "service": "OptionsLab AI Service"
    }

@app.post("/generate_strategy")
async def generate_strategy(request: StrategyRequest):
    """Generate an options strategy using AI"""
    try:
        ai_system = get_ai_system()
        result = ai_system.generate_strategy(
            market_conditions=request.market_conditions,
            risk_tolerance=request.risk_tolerance,
            strategy_type=request.strategy_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_backtest")
async def analyze_backtest(request: AnalysisRequest):
    """Analyze backtest results using AI"""
    try:
        ai_system = get_ai_system()
        result = ai_system.analyze_backtest(request.results)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set_api_key")
async def set_api_key(request: KeyRequest):
    """Set the Gemini API key"""
    try:
        ai_system = get_ai_system()
        # Test the key first
        if ai_system._test_api_key(request.api_key):
            ai_system.api_key = request.api_key
            ai_system._save_api_key(request.api_key)
            return {"success": True, "message": "API key set successfully"}
        else:
            raise HTTPException(status_code=400, detail="Invalid API key")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api_key_status")
async def api_key_status():
    """Check if API key is configured"""
    ai_system = get_ai_system()
    return {
        "configured": ai_system.is_configured(),
        "has_key": ai_system.api_key is not None
    }

if __name__ == "__main__":
    print("🤖 Starting OptionsLab AI Service...")
    print("📍 Service will be available at: http://localhost:8001")
    print("📋 API Documentation: http://localhost:8001/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    ) 