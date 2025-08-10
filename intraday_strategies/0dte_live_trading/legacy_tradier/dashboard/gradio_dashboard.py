#!/usr/bin/env python3
"""
Gradio Dashboard for 0DTE Strangle Monitor
Real-time monitoring with Greeks and risk management
"""

import gradio as gr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import TradierClient, OrderManager
from core.risk_monitor import RiskMonitor
from core.cache_manager import TradierCacheManager

# Global state
class DashboardState:
    def __init__(self):
        self.client = None
        self.risk_monitor = None
        self.order_mgr = None
        self.cache_mgr = None
        self.metrics_history = []
        self.price_history = []
        self.greeks_history = []
        self.last_update = None
        
    def initialize(self):
        """Initialize connections and load historical data"""
        try:
            self.client = TradierClient(env="sandbox")
            self.risk_monitor = RiskMonitor(self.client, vega_limit=2.0, delta_limit=0.20)
            self.order_mgr = OrderManager(self.client)
            
            # Initialize cache manager with 21 days of data
            self.cache_mgr = TradierCacheManager(self.client)
            print("Initializing cache with 21 days of historical data...")
            self.cache_mgr.initialize_cache(days_back=21, force=False)
            
            # Start real-time updates
            self.cache_mgr.start_realtime_updates()
            
            # Load all available data from cache (21 days)
            try:
                # Get all SPY data from cache for complete history
                start_date = datetime.now() - timedelta(days=21)
                spy_data = self.cache_mgr.get_spy_data(start_date=start_date, session_type='regular')
                
                if not spy_data.empty:
                    print(f"Loading {len(spy_data)} data points from cache...")
                    
                    # Populate price history from cache
                    for timestamp, row in spy_data.iterrows():
                        self.price_history.append({
                            'time': timestamp,
                            'price': row['close']
                        })
                    
                    print(f"Loaded {len(self.price_history)} price points from cache")
                    
                    # Get cache statistics
                    stats = self.cache_mgr.get_cache_statistics()
                    print(f"Cache stats: {stats.get('total_spy_records', 0)} total records, "
                          f"data freshness: {'FRESH' if stats.get('data_fresh') else 'STALE'}")
                
            except Exception as e:
                print(f"Could not load data from cache: {e}")
                
            # Load Greeks history from database (preferred) or JSON fallback
            try:
                # First try loading from database
                from database import get_db_manager
                db = get_db_manager()
                
                # Get Greeks history for last 21 days
                greeks_query = """
                    SELECT timestamp, total_delta, total_gamma, total_theta, total_vega
                    FROM greeks_history
                    WHERE timestamp >= datetime('now', '-21 days')
                    ORDER BY timestamp
                """
                greeks_data = db.execute_query(greeks_query)
                
                if greeks_data:
                    print(f"Loading {len(greeks_data)} Greeks data points from database...")
                    for row in greeks_data:
                        self.greeks_history.append({
                            'time': datetime.fromisoformat(row['timestamp']),
                            'delta': row['total_delta'],
                            'gamma': row['total_gamma'],
                            'vega': row['total_vega'],
                            'theta': row['total_theta'] * 100  # Convert to percentage
                        })
                else:
                    # Fallback to JSON if no database data
                    json_path = os.path.join(os.path.dirname(__file__), '..', 'tradier_risk_metrics.json')
                    if os.path.exists(json_path):
                        with open(json_path, 'r') as f:
                            data = json.load(f)
                            if 'history' in data and data['history']:
                                for entry in data['history']:  # Load all points
                                    # Populate Greeks history if available
                                    if 'greeks' in entry:
                                        self.greeks_history.append({
                                            'time': datetime.fromisoformat(entry['timestamp']),
                                            'delta': entry['greeks'].get('delta', 0),
                                            'gamma': entry['greeks'].get('gamma', 0),
                                            'vega': entry['greeks'].get('vega', 0),
                                            'theta': entry['greeks'].get('theta', 0) * 100
                                        })
                
                print(f"Loaded {len(self.greeks_history)} Greeks history points")
                
            except Exception as e:
                print(f"Could not load Greeks history: {e}")
            
            return True, "✅ Connected to Tradier"
        except Exception as e:
            return False, f"❌ Connection failed: {e}"

state = DashboardState()

def get_status():
    """Get current system status"""
    if not state.client:
        success, msg = state.initialize()
        if not success:
            return msg
    
    market_open = state.client.is_market_open()
    status = "🟢 MARKET OPEN" if market_open else "🔴 MARKET CLOSED"
    
    return f"{status} | Last Update: {datetime.now().strftime('%I:%M:%S %p ET')}"

def update_metrics():
    """Update all metrics and return display data"""
    if not state.risk_monitor:
        state.initialize()
    
    try:
        # Get latest metrics
        metrics = state.risk_monitor.calculate_risk_metrics()
        
        if not metrics:
            return (
                "No Position", "", "", "",
                {"Delta": 0, "Gamma": 0, "Theta": 0, "Vega": 0},
                {"Vega": "N/A", "Delta": "N/A", "Strike": "N/A", "Overall": "N/A"},
                [], None, None, None, "No active position"
            )
        
        # Store in history
        state.metrics_history.append(metrics)
        timestamp = datetime.now()
        
        # SPY Price
        spy_price = metrics['spy_price']
        state.price_history.append({'time': timestamp, 'price': spy_price})
        
        # Greeks history
        state.greeks_history.append({
            'time': timestamp,
            'delta': metrics['greeks'].get('delta', 0),
            'gamma': metrics['greeks'].get('gamma', 0),
            'vega': metrics['greeks'].get('vega', 0),
            'theta': metrics['greeks'].get('theta', 0) * 100  # Convert to $/day
        })
        
        # Keep only last 100 points
        if len(state.price_history) > 100:
            state.price_history = state.price_history[-100:]
        if len(state.greeks_history) > 100:
            state.greeks_history = state.greeks_history[-100:]
        
        # Format displays
        spy_display = f"${spy_price:.2f}"
        
        # Position info
        position_info = ""
        if 'call' in metrics['positions']:
            call = metrics['positions']['call']
            position_info += f"📈 CALL: Strike ${call['strike']:.0f} | "
        if 'put' in metrics['positions']:
            put = metrics['positions']['put']
            position_info += f"📉 PUT: Strike ${put['strike']:.0f}"
        
        # P&L (simplified for now)
        pnl_display = "+$22.00"  # Would need to calculate from actual position data
        
        # Time remaining
        close_time = datetime.now().replace(hour=15, minute=59, second=0)
        time_remaining = close_time - datetime.now()
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)
        time_display = f"{hours}h {minutes}m until close"
        
        # Greeks
        greeks = metrics['greeks']
        greeks_display = {
            "Delta": f"{greeks.get('delta', 0):+.3f}",
            "Gamma": f"{greeks.get('gamma', 0):+.3f}",
            "Theta": f"{greeks.get('theta', 0) * 100:+.2f} $/day",
            "Vega": f"{greeks.get('vega', 0):+.3f}"
        }
        
        # Risk levels
        risk_levels = metrics['risk_levels']
        
        # Warnings
        warnings = metrics.get('warnings', [])
        
        # Create charts
        price_chart = create_price_chart()
        greeks_chart = create_greeks_chart()
        strike_map = create_strike_map(metrics)
        
        # Exit recommendation
        should_exit, reason = state.risk_monitor.should_exit(metrics)
        if should_exit:
            exit_rec = f"🚨 EXIT SIGNAL: {reason}"
        else:
            exit_rec = f"✅ Hold position: {reason}"
        
        return (
            spy_display, position_info, pnl_display, time_display,
            greeks_display, risk_levels, warnings,
            price_chart, greeks_chart, strike_map, exit_rec
        )
        
    except Exception as e:
        return (
            "Error", str(e), "", "",
            {"Delta": 0, "Gamma": 0, "Theta": 0, "Vega": 0},
            {"Vega": "ERROR", "Delta": "ERROR", "Strike": "ERROR", "Overall": "ERROR"},
            [str(e)], None, None, None, f"Error: {e}"
        )

def create_price_chart():
    """Create SPY price chart"""
    fig = go.Figure()
    
    if not state.price_history:
        # Empty chart with message
        fig.add_annotation(
            text="Collecting price data...<br>Click Refresh to update",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
    elif len(state.price_history) == 1:
        # Single point as marker
        df = pd.DataFrame(state.price_history)
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['price'],
            mode='markers',
            marker=dict(size=12, color='#00D9FF'),
            name='SPY Price',
            text=[f"${p:.2f}" for p in df['price']],
            hovertemplate='%{text}<br>%{x}'
        ))
    else:
        # Multiple points as line
        df = pd.DataFrame(state.price_history)
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['price'],
            mode='lines+markers',
            name='SPY Price',
            line=dict(color='#00D9FF', width=2),
            marker=dict(size=6),
            text=[f"${p:.2f}" for p in df['price']],
            hovertemplate='%{text}<br>%{x}'
        ))
    
    # Add strike lines if we have position data
    if state.metrics_history:
        latest = state.metrics_history[-1]
        if 'positions' in latest:
            if 'call' in latest['positions']:
                call_strike = latest['positions']['call']['strike']
                fig.add_hline(y=call_strike, line_dash="dash", 
                            line_color="red", annotation_text="Call Strike")
            if 'put' in latest['positions']:
                put_strike = latest['positions']['put']['strike']
                fig.add_hline(y=put_strike, line_dash="dash", 
                            line_color="green", annotation_text="Put Strike")
    
    fig.update_layout(
        title="SPY Price Movement",
        xaxis_title="Time",
        yaxis_title="Price ($)",
        template="plotly_dark",
        height=400,
        showlegend=True
    )
    
    return fig

def create_greeks_chart():
    """Create Greeks evolution chart"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Delta', 'Gamma', 'Theta ($/day)', 'Vega')
    )
    
    if not state.greeks_history:
        # Return empty chart with proper layout
        fig.update_layout(
            template="plotly_dark",
            height=400,
            showlegend=False,
            annotations=[{
                'text': 'Waiting for Greeks data...',
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.5,
                'showarrow': False,
                'font': {'size': 20, 'color': 'gray'}
            }]
        )
        return fig
    
    df = pd.DataFrame(state.greeks_history)
    
    # Determine mode based on number of points
    mode = 'markers' if len(df) == 1 else 'lines+markers'
    
    # Delta
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['delta'],
        mode=mode, name='Delta',
        line=dict(color='#00D9FF', width=2) if len(df) > 1 else None,
        marker=dict(size=8 if len(df) == 1 else 6, color='#00D9FF')
    ), row=1, col=1)
    
    # Gamma
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['gamma'],
        mode=mode, name='Gamma',
        line=dict(color='#FF6B6B', width=2) if len(df) > 1 else None,
        marker=dict(size=8 if len(df) == 1 else 6, color='#FF6B6B')
    ), row=1, col=2)
    
    # Theta
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['theta'],
        mode=mode, name='Theta',
        line=dict(color='#4ECDC4', width=2) if len(df) > 1 else None,
        marker=dict(size=8 if len(df) == 1 else 6, color='#4ECDC4')
    ), row=2, col=1)
    
    # Vega
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['vega'],
        mode=mode, name='Vega',
        line=dict(color='#FFD93D', width=2) if len(df) > 1 else None,
        marker=dict(size=8 if len(df) == 1 else 6, color='#FFD93D')
    ), row=2, col=2)
    
    # Add Vega limit line
    fig.add_hline(y=2.0, line_dash="dash", line_color="red", 
                  annotation_text="Vega Limit", row=2, col=2)
    
    fig.update_layout(
        template="plotly_dark",
        height=400,
        showlegend=False
    )
    
    return fig

def create_strike_map(metrics):
    """Create visual strike map"""
    if not metrics or 'positions' not in metrics:
        return None
    
    spy_price = metrics['spy_price']
    
    # Get strikes
    call_strike = metrics['positions'].get('call', {}).get('strike', 0)
    put_strike = metrics['positions'].get('put', {}).get('strike', 0)
    
    if not call_strike or not put_strike:
        return None
    
    # Create gauge chart showing position
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=spy_price,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "SPY Position"},
        delta={'reference': (call_strike + put_strike) / 2},
        gauge={
            'axis': {'range': [put_strike - 2, call_strike + 2]},
            'bar': {'color': "white"},
            'steps': [
                {'range': [put_strike - 2, put_strike], 'color': "red"},
                {'range': [put_strike, put_strike + 1], 'color': "orange"},
                {'range': [put_strike + 1, call_strike - 1], 'color': "green"},
                {'range': [call_strike - 1, call_strike], 'color': "orange"},
                {'range': [call_strike, call_strike + 2], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': spy_price
            }
        }
    ))
    
    fig.update_layout(
        template="plotly_dark",
        height=250,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def close_position_action():
    """Close the strangle position"""
    if not state.order_mgr or not state.metrics_history:
        return "❌ No position to close"
    
    try:
        latest = state.metrics_history[-1]
        call_symbol = latest['positions'].get('call', {}).get('symbol')
        put_symbol = latest['positions'].get('put', {}).get('symbol')
        
        if call_symbol and put_symbol:
            result = state.order_mgr.close_strangle(call_symbol, put_symbol, quantity=1)
            if result:
                return "✅ Position closed successfully!"
            else:
                return "❌ Failed to close position"
        else:
            return "❌ Could not find position symbols"
    except Exception as e:
        return f"❌ Error: {e}"

def create_dashboard():
    """Create the Gradio dashboard"""
    
    with gr.Blocks(theme=gr.themes.Soft(), title="0DTE Strangle Monitor") as dashboard:
        gr.Markdown("# 🎯 0DTE Strangle Monitor - Live Dashboard")
        
        # Status bar
        with gr.Row():
            status_text = gr.Textbox(label="System Status", value="Initializing...")
        
        # Main metrics row
        with gr.Row():
            spy_price = gr.Textbox(label="📈 SPY Price", value="---.--")
            position_info = gr.Textbox(label="📊 Position", value="Loading...")
            pnl = gr.Textbox(label="💰 P&L", value="$0.00")
            time_remaining = gr.Textbox(label="⏰ Time to Close", value="--:--")
        
        # Greeks display
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Greeks")
                greeks_json = gr.JSON(label="Current Greeks", value={})
            
            with gr.Column(scale=1):
                gr.Markdown("### Risk Levels")
                risk_json = gr.JSON(label="Risk Assessment", value={})
        
        # Warnings
        with gr.Row():
            warnings_box = gr.Textbox(
                label="⚠️ Warnings",
                lines=3,
                value="No warnings"
            )
        
        # Strike map
        with gr.Row():
            strike_map = gr.Plot(label="Strike Position Map")
        
        # Charts
        with gr.Row():
            price_chart = gr.Plot(label="SPY Price History")
            greeks_chart = gr.Plot(label="Greeks Evolution")
        
        # Exit recommendation
        with gr.Row():
            exit_recommendation = gr.Textbox(
                label="📤 Exit Strategy",
                value="Calculating...",
                lines=2
            )
        
        # Action buttons
        with gr.Row():
            refresh_btn = gr.Button("🔄 Refresh", variant="secondary")
            close_btn = gr.Button("🚨 CLOSE POSITION", variant="stop")
            close_result = gr.Textbox(label="Action Result", visible=False)
        
        # Auto-refresh function
        def refresh_all():
            status = get_status()
            metrics_data = update_metrics()
            
            return [
                status,  # status_text
                metrics_data[0],  # spy_price
                metrics_data[1],  # position_info
                metrics_data[2],  # pnl
                metrics_data[3],  # time_remaining
                metrics_data[4],  # greeks_json
                metrics_data[5],  # risk_json
                "\n".join(metrics_data[6]) if metrics_data[6] else "No warnings",  # warnings
                metrics_data[9],  # strike_map
                metrics_data[7],  # price_chart
                metrics_data[8],  # greeks_chart
                metrics_data[10],  # exit_recommendation
            ]
        
        # Set up event handlers
        refresh_btn.click(
            refresh_all,
            outputs=[
                status_text, spy_price, position_info, pnl, time_remaining,
                greeks_json, risk_json, warnings_box, strike_map,
                price_chart, greeks_chart, exit_recommendation
            ]
        )
        
        close_btn.click(
            close_position_action,
            outputs=[close_result]
        ).then(
            lambda x: gr.update(visible=True),
            inputs=[close_result],
            outputs=[close_result]
        )
        
        # Auto-refresh on load
        dashboard.load(
            refresh_all,
            outputs=[
                status_text, spy_price, position_info, pnl, time_remaining,
                greeks_json, risk_json, warnings_box, strike_map,
                price_chart, greeks_chart, exit_recommendation
            ]
        )
    
    return dashboard

if __name__ == "__main__":
    # Initialize state
    success, msg = state.initialize()
    print(msg)
    
    # Create and launch dashboard
    dashboard = create_dashboard()
    
    print("\n" + "="*60)
    print("🚀 Launching 0DTE Strangle Dashboard")
    print("="*60)
    print("Access at: http://localhost:7870")
    print("Dashboard will auto-refresh every 10 seconds")
    print("Press Ctrl+C to stop")
    
    try:
        dashboard.launch(
            server_name="0.0.0.0",
            server_port=7870,
            share=False,
            quiet=True
        )
    except OSError:
        # Port in use, try alternative port
        print("Port 7870 in use, trying port 7871...")
        dashboard.launch(
            server_name="0.0.0.0",
            server_port=7871,
            share=False,
            quiet=True
        )