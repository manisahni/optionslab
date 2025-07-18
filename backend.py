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

@app.post("/backtest")
async def run_backtest_api(request: BacktestRequest):
    """Run a backtest"""
    try:
        # Run the backtest
        results = run_backtest(
            strategy=request.strategy,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital
        )
        
        # Create plots
        plot_data = plot_results(results)
        
        return {
            "success": True,
            "results": results,
            "plots": plot_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)