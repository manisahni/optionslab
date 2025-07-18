#!/usr/bin/env python3
"""
Simple Gradio App for OptionsLab
A lightweight alternative to Streamlit
"""
import gradio as gr
import requests
import json
import base64
import io
from PIL import Image
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

# API configuration
API_URL = "http://localhost:8000"

def check_api_status():
    """Check if the API server is running"""
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_strategies():
    """Get available strategies from API"""
    try:
        response = requests.get(f"{API_URL}/strategies", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [strategy["name"] for strategy in data["strategies"]]
        return ["Long Call", "Long Put"]  # Fallback
    except:
        return ["Long Call", "Long Put"]  # Fallback

def run_backtest(strategy, start_date, end_date, initial_capital):
    """Run backtest via API"""
    try:
        # Prepare request data
        data = {
            "strategy": strategy,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": float(initial_capital)
        }
        
        # Make API request
        response = requests.post(f"{API_URL}/backtest", json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return format_results(result["results"], result.get("plots", {}))
            else:
                return f"❌ Backtest failed: {result.get('error', 'Unknown error')}"
        else:
            return f"❌ API Error: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        return f"❌ Connection Error: {str(e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def format_results(results, plots):
    """Format backtest results for display"""
    try:
        # Extract key metrics
        total_return = results.get("total_return", 0)
        sharpe_ratio = results.get("sharpe_ratio", 0)
        max_drawdown = results.get("max_drawdown", 0)
        win_rate = results.get("win_rate", 0)
        num_trades = results.get("num_trades", 0)
        
        # Format the results
        formatted = f"""
## 📊 Backtest Results

### 📈 Performance Metrics
- **Total Return**: {total_return:.2%}
- **Sharpe Ratio**: {sharpe_ratio:.2f}
- **Max Drawdown**: {max_drawdown:.2%}
- **Win Rate**: {win_rate:.2%}
- **Number of Trades**: {num_trades}

### 📋 Trade Log
"""
        
        # Add trade log if available
        if "trade_log" in results:
            trades = results["trade_log"]
            if isinstance(trades, list) and len(trades) > 0:
                formatted += "\n| Date | Action | Price | Quantity | P&L |\n"
                formatted += "|------|--------|-------|----------|-----|\n"
                
                for trade in trades[:10]:  # Show first 10 trades
                    date = trade.get("date", "N/A")
                    action = trade.get("action", "N/A")
                    price = trade.get("price", 0)
                    quantity = trade.get("quantity", 0)
                    pnl = trade.get("pnl", 0)
                    
                    formatted += f"| {date} | {action} | ${price:.2f} | {quantity} | ${pnl:.2f} |\n"
                
                if len(trades) > 10:
                    formatted += f"\n*... and {len(trades) - 10} more trades*"
            else:
                formatted += "\nNo trades executed during this period."
        
        # Add plots if available
        if plots:
            formatted += "\n\n### 📊 Charts\n"
            for plot_name, plot_data in plots.items():
                if plot_data:
                    formatted += f"\n**{plot_name}**\n"
                    formatted += f"![{plot_name}](data:image/png;base64,{plot_data})\n"
        
        return formatted
        
    except Exception as e:
        return f"❌ Error formatting results: {str(e)}"

def create_interface():
    """Create the Gradio interface"""
    
    # Check API status
    api_running = check_api_status()
    strategies = get_strategies() if api_running else ["Long Call", "Long Put"]
    
    with gr.Blocks(title="OptionsLab - Simple Backtester", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🚀 OptionsLab - Simple Options Backtester")
        
        # Status indicator
        status_color = "🟢" if api_running else "🔴"
        status_text = "API Connected" if api_running else "API Not Connected"
        gr.Markdown(f"**Status**: {status_color} {status_text}")
        
        if not api_running:
            gr.Markdown("⚠️ **Please start the API server first**: `python backend.py`")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ Configuration")
                
                strategy = gr.Dropdown(
                    choices=strategies,
                    value=strategies[0] if strategies else "Long Call",
                    label="Strategy",
                    info="Select the options strategy to backtest"
                )
                
                start_date = gr.Textbox(
                    value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    label="Start Date",
                    info="Start date for backtest (YYYY-MM-DD)"
                )
                
                end_date = gr.Textbox(
                    value=datetime.now().strftime("%Y-%m-%d"),
                    label="End Date", 
                    info="End date for backtest (YYYY-MM-DD)"
                )
                
                initial_capital = gr.Number(
                    value=10000.0,
                    label="Initial Capital ($)",
                    info="Starting capital for the backtest"
                )
                
                run_btn = gr.Button("🚀 Run Backtest", variant="primary")
            
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results")
                results_output = gr.Markdown("Ready to run backtest...")
        
        # Event handlers
        run_btn.click(
            fn=run_backtest,
            inputs=[strategy, start_date, end_date, initial_capital],
            outputs=results_output
        )
        
        # Auto-refresh strategies when API comes online
        def refresh_strategies():
            api_running = check_api_status()
            if api_running:
                return gr.Dropdown(choices=get_strategies())
            return gr.Dropdown(choices=["Long Call", "Long Put"])
        
        # Refresh button
        refresh_btn = gr.Button("🔄 Refresh", size="sm")
        refresh_btn.click(fn=refresh_strategies, outputs=strategy)
    
    return app

if __name__ == "__main__":
    app = create_interface()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False) 