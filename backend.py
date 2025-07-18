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

# Feature flags
FEATURE_FLAGS = {
    "ai_analysis": os.getenv("ENABLE_AI_ANALYSIS", "true").lower() == "true",
    "advanced_plots": os.getenv("ENABLE_ADVANCED_PLOTS", "true").lower() == "true",
    "real_time_data": os.getenv("ENABLE_REAL_TIME_DATA", "false").lower() == "true",
    "multi_strategy": os.getenv("ENABLE_MULTI_STRATEGY", "true").lower() == "true"
}

# Custom JSON encoder to handle numpy types and pandas timestamps
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int_)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float_)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, pd.Series):
            return obj.tolist()
        elif hasattr(obj, 'isoformat'):  # Handle datetime/timestamp objects
            return obj.isoformat()
        return super(NumpyEncoder, self).default(obj)

# Create FastAPI app
app = FastAPI(title="Options Backtester API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class BacktestRequest(BaseModel):
    strategy: str
    start_date: date
    end_date: date
    initial_capital: float = 100000

# Response model
class BacktestResponse(BaseModel):
    success: bool
    results: dict
    plot_base64: str = ""
    error: str = ""

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "running", "message": "Options Backtester API"}

@app.get("/flags")
async def get_feature_flags():
    """Get current feature flag status"""
    return {
        "feature_flags": FEATURE_FLAGS,
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.post("/run_backtest", response_model=BacktestResponse)
async def run_backtest_endpoint(request: BacktestRequest):
    """Run a backtest and return results"""
    try:
        # Convert dates to strings
        start_str = request.start_date.strftime("%Y-%m-%d")
        end_str = request.end_date.strftime("%Y-%m-%d")
        
        # Run backtest
        results = run_backtest(
            strategy_type=request.strategy,
            start_date=start_str,
            end_date=end_str,
            initial_capital=int(request.initial_capital)
        )
        
        if not results:
            return BacktestResponse(
                success=False,
                results={},
                error="No data found for the specified period"
            )
        
        # Generate plot and convert to base64
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            plot_results(results, save_path=tmp.name)
            tmp.flush()
            with open(tmp.name, 'rb') as f:
                plot_base64 = base64.b64encode(f.read()).decode('utf-8')
            import os
            os.unlink(tmp.name)  # Clean up temp file
        plt.close('all')  # Clean up
        
        # Convert results to JSON-serializable format
        results_json = json.loads(json.dumps(results, cls=NumpyEncoder))
        
        return BacktestResponse(
            success=True,
            results=results_json,
            plot_base64=plot_base64
        )
        
    except Exception as e:
        return BacktestResponse(
            success=False,
            results={},
            error=str(e)
        )

@app.get("/strategies")
async def get_strategies():
    """Get available strategies"""
    strategies = [
        {"value": "long_call", "label": "Long Call"},
        {"value": "long_put", "label": "Long Put"}
    ]
    
    # Add multi-strategy support if enabled
    if FEATURE_FLAGS["multi_strategy"]:
        strategies.extend([
            {"value": "covered_call", "label": "Covered Call"},
            {"value": "cash_secured_put", "label": "Cash Secured Put"}
        ])
    
    return {"strategies": strategies}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)