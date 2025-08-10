"""
Web Dashboard Backend for Tradier Strangle Monitor
FastAPI server with WebSocket support for real-time updates
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, List
import uvicorn

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import TradierClient, OrderManager
from core.risk_monitor import RiskMonitor

app = FastAPI(title="0DTE Strangle Monitor")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
class DashboardState:
    def __init__(self):
        self.client = None
        self.risk_monitor = None
        self.order_mgr = None
        self.connected_clients: List[WebSocket] = []
        self.latest_metrics = None
        self.position_history = []
        self.is_monitoring = False
        
    def initialize(self):
        """Initialize Tradier connections"""
        try:
            self.client = TradierClient(env="sandbox")
            self.risk_monitor = RiskMonitor(self.client, vega_limit=2.0, delta_limit=0.20)
            self.order_mgr = OrderManager(self.client)
            return True
        except Exception as e:
            print(f"Failed to initialize: {e}")
            return False

state = DashboardState()

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    """Serve the dashboard HTML"""
    return FileResponse('frontend/index.html')

@app.get("/api/status")
async def get_status():
    """Get system status"""
    if not state.client:
        state.initialize()
    
    return {
        "connected": state.client is not None,
        "is_monitoring": state.is_monitoring,
        "market_open": state.client.is_market_open() if state.client else False,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/metrics")
async def get_metrics():
    """Get latest risk metrics"""
    if not state.risk_monitor:
        return {"error": "Not initialized"}
    
    try:
        metrics = state.risk_monitor.calculate_risk_metrics()
        state.latest_metrics = metrics
        
        # Add to history
        if metrics:
            state.position_history.append({
                'timestamp': metrics['timestamp'],
                'spy_price': metrics['spy_price'],
                'delta': metrics['greeks'].get('delta', 0),
                'vega': metrics['greeks'].get('vega', 0),
                'theta': metrics['greeks'].get('theta', 0)
            })
            
            # Keep only last 100 points
            if len(state.position_history) > 100:
                state.position_history = state.position_history[-100:]
        
        return metrics
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/positions")
async def get_positions():
    """Get current positions"""
    if not state.client:
        return {"error": "Not initialized"}
    
    try:
        positions = state.client.get_positions()
        orders = state.client.get_orders()
        balances = state.client.get_balances()
        
        return {
            "positions": positions,
            "orders": orders,
            "balances": balances,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/history")
async def get_history():
    """Get position history"""
    return {
        "history": state.position_history,
        "count": len(state.position_history)
    }

@app.post("/api/close-position")
async def close_position():
    """Close the strangle position"""
    if not state.order_mgr or not state.latest_metrics:
        return {"error": "No position to close"}
    
    try:
        # Get position symbols
        call_symbol = state.latest_metrics['positions'].get('call', {}).get('symbol')
        put_symbol = state.latest_metrics['positions'].get('put', {}).get('symbol')
        
        if call_symbol and put_symbol:
            result = state.order_mgr.close_strangle(call_symbol, put_symbol, quantity=1)
            return {"success": True, "result": result}
        else:
            return {"error": "Could not find position symbols"}
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    state.connected_clients.append(websocket)
    
    try:
        # Start monitoring if not already running
        if not state.is_monitoring:
            state.is_monitoring = True
            asyncio.create_task(monitor_loop())
        
        # Keep connection alive
        while True:
            # Wait for any message from client (ping/pong)
            data = await websocket.receive_text()
            
            # Echo back for ping/pong
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        state.connected_clients.remove(websocket)
        
        # Stop monitoring if no clients
        if not state.connected_clients:
            state.is_monitoring = False

async def monitor_loop():
    """Background monitoring loop"""
    if not state.risk_monitor:
        state.initialize()
    
    while state.is_monitoring and state.connected_clients:
        try:
            # Get latest metrics
            metrics = state.risk_monitor.calculate_risk_metrics()
            
            if metrics:
                # Prepare broadcast data
                broadcast_data = {
                    "type": "metrics_update",
                    "data": metrics,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Send to all connected clients
                disconnected = []
                for client in state.connected_clients:
                    try:
                        await client.send_json(broadcast_data)
                    except:
                        disconnected.append(client)
                
                # Remove disconnected clients
                for client in disconnected:
                    if client in state.connected_clients:
                        state.connected_clients.remove(client)
                
                # Check for exit signals
                should_exit, reason = state.risk_monitor.should_exit(metrics)
                if should_exit:
                    alert_data = {
                        "type": "exit_signal",
                        "reason": reason,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    for client in state.connected_clients:
                        try:
                            await client.send_json(alert_data)
                        except:
                            pass
            
            # Wait before next update
            await asyncio.sleep(10)  # Update every 10 seconds
            
        except Exception as e:
            print(f"Monitor loop error: {e}")
            await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    state.initialize()
    print("Dashboard backend started")
    print("Access dashboard at: http://localhost:8000")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)