#!/usr/bin/env python3
"""
FastAPI backend for options backtesting
Simple REST API that runs backtests and returns results
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date
import base64
import io
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import json
import os

from backtest_engine import run_backtest, plot_results

# Import AI system
import requests

# AI Service configuration
AI_SERVICE_URL = "http://localhost:8001"
AI_AVAILABLE = True

app = FastAPI(title="OptionsLab API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BacktestRequest(BaseModel):
    strategy: str
    start_date: str
    end_date: str
    initial_capital: float = 10000.0

class AIStrategyRequest(BaseModel):
    market_conditions: str
    risk_tolerance: str
    strategy_type: str

class AIAnalysisRequest(BaseModel):
    results: dict

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "OptionsLab API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "OptionsLab API"}

@app.get("/strategies")
async def get_strategies():
    """Get available strategies"""
    strategies = [
        {"name": "Long Call", "description": "Buy call options"},
        {"name": "Long Put", "description": "Buy put options"}
    ]
    return {"strategies": strategies}

@app.get("/ai/status")
async def get_ai_status():
    """Get AI system status"""
    if not AI_AVAILABLE:
        return {"available": False, "error": "AI system not available"}
    
    try:
        response = requests.get(f"{AI_SERVICE_URL}/status", timeout=5)
        if response.status_code == 200:
            ai_status = response.json()
            return {
                "available": True,
                "configured": ai_status.get("ai_configured", False),
                "service_status": ai_status.get("status", "unknown")
            }
        else:
            return {"available": False, "error": f"AI service error: {response.status_code}"}
    except Exception as e:
        return {"available": False, "error": f"AI service not reachable: {str(e)}"}

@app.post("/ai/generate-strategy")
async def generate_strategy(request: AIStrategyRequest):
    """Generate an AI strategy"""
    if not AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI system not available")
    
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/generate_strategy",
            json={
                "market_conditions": request.market_conditions,
                "risk_tolerance": request.risk_tolerance,
                "strategy_type": request.strategy_type
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=f"AI service error: {response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

@app.post("/ai/analyze-backtest")
async def analyze_backtest(request: AIAnalysisRequest):
    """Analyze backtest results with AI"""
    if not AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI system not available")
    
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/analyze_backtest",
            json={"results": request.results},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=f"AI service error: {response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

@app.post("/backtest")
async def run_backtest_api(request: BacktestRequest):
    """Run a backtest"""
    try:
        # Run the backtest
        results = run_backtest(
            strategy_type=request.strategy,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=int(request.initial_capital)
        )
        
        if results is None:
            raise HTTPException(status_code=400, detail="Backtest failed - no results returned")
        
        # Create plots with error handling
        try:
            plot_data = {}
            fig = plot_results(results)
            if fig:
                # Convert plot to base64
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                buf.seek(0)
                plot_data['equity_curve'] = base64.b64encode(buf.getvalue()).decode('utf-8')
                plt.close(fig)  # Close the figure to free memory
        except Exception as e:
            print(f"Plotting error: {e}")
            plot_data = None
        
        return {
            "success": True,
            "results": results,
            "plots": plot_data
        }
    except Exception as e:
        import traceback
        error_details = f"Error: {str(e)}\nTraceback: {traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_details)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)