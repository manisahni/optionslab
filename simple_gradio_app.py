#!/usr/bin/env python3
"""
Simple Gradio App for OptionsLab
A lightweight alternative to Streamlit
"""
import gradio as gr
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
import json
import requests
import os

# Configuration
API_URL = "http://localhost:8000"
AI_SERVICE_URL = "http://localhost:8001"

def check_api_health():
    """Check if API server is running"""
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_ai_service():
    """Check if AI service is running"""
    try:
        response = requests.get(f"{AI_SERVICE_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("ai_available", False)
        return False
    except:
        return False

def run_backtest(strategy, start_date, end_date, initial_capital):
    """Run a backtest with the given parameters"""
    if not check_api_health():
        return "❌ API server is not running. Please start the FastAPI server first.", None, None
    
    # Prepare backtest request
    backtest_data = {
        "strategy": strategy,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": float(initial_capital)
    }
    
    try:
        response = requests.post(f"{API_URL}/run_backtest", json=backtest_data, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            
            if not response_data.get('success', False):
                return f"❌ Backtest failed: {response_data.get('error', 'Unknown error')}", None, None
            
            results = response_data.get('results', {})
            performance = results.get('performance_metrics', {})
            
            # Create summary
            summary = f"""
## 📊 Backtest Results

**Strategy:** {strategy}
**Period:** {start_date} to {end_date}
**Initial Capital:** ${initial_capital:,.2f}
**Final Value:** ${performance.get('final_value', 0):,.2f}
**Total Return:** {performance.get('total_return', 0):.2%}
**Sharpe Ratio:** {performance.get('sharpe_ratio', 0):.2f}
**Max Drawdown:** {performance.get('max_drawdown', 0):.2%}
**Win Rate:** {performance.get('win_rate', 0):.2%}
**Total Trades:** {performance.get('total_trades', 0)}
            """
            
            # Create equity curve plot
            if 'equity_curve' in results and results['equity_curve']:
                df = pd.DataFrame(results['equity_curve'])
                # Use 'total_value' instead of 'equity' as that's what the API returns
                if 'total_value' in df.columns:
                    fig = px.line(df, x='date', y='total_value', title='Portfolio Equity Curve')
                    fig.update_layout(xaxis_title='Date', yaxis_title='Portfolio Value ($)')
                else:
                    # Fallback to first numeric column if total_value not found
                    numeric_cols = df.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        fig = px.line(df, x='date', y=numeric_cols[0], title='Portfolio Equity Curve')
                        fig.update_layout(xaxis_title='Date', yaxis_title='Portfolio Value ($)')
                    else:
                        fig = None
            else:
                fig = None
            
            # Create trade analysis
            if 'trade_logs' in results and results['trade_logs']:
                trades_df = pd.DataFrame(results['trade_logs'])
                if not trades_df.empty and 'entry_date' in trades_df.columns:
                    # Use available columns: entry_date, exit_date, option_type, pnl, exit_reason
                    available_cols = ['entry_date', 'exit_date', 'option_type', 'pnl', 'exit_reason']
                    trades_table = trades_df[available_cols].head(10)
                else:
                    trades_table = pd.DataFrame()
            else:
                trades_table = pd.DataFrame()
            
            return summary, fig, trades_table
            
        else:
            return f"❌ Backtest failed: {response.text}", None, None
            
    except Exception as e:
        return f"❌ Error running backtest: {str(e)}", None, None

def get_ai_analysis(backtest_results):
    """Get AI analysis of backtest results"""
    if not check_ai_service():
        return "❌ AI service is not available. Please check if the AI service is running."
    
    try:
        response = requests.post(f"{AI_SERVICE_URL}/analyze/backtest", json=backtest_results, timeout=30)
        
        if response.status_code == 200:
            analysis = response.json()
            return f"## 🤖 AI Analysis\n\n{analysis.get('analysis', 'No analysis available')}"
        else:
            return f"❌ AI analysis failed: {response.text}"
            
    except Exception as e:
        return f"❌ Error getting AI analysis: {str(e)}"

def create_interface():
    """Create the Gradio interface"""
    
    # Available strategies
    strategies = [
        "long_call",
        "long_put"
    ]
    
    with gr.Blocks(title="OptionsLab - Simple Gradio Interface", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🎯 OptionsLab - Simple Backtesting Interface")
        gr.Markdown("A lightweight options backtesting tool")
        
        # System Status
        with gr.Row():
            api_status = gr.Textbox(label="API Status", value="Checking...", interactive=False)
            ai_status = gr.Textbox(label="AI Status", value="Checking...", interactive=False)
        
        # Main Interface
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## ⚙️ Configuration")
                
                strategy = gr.Dropdown(
                    choices=strategies,
                    value="long_call",
                    label="Strategy"
                )
                
                start_date = gr.Textbox(
                    value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    label="Start Date (YYYY-MM-DD)"
                )
                
                end_date = gr.Textbox(
                    value=datetime.now().strftime("%Y-%m-%d"),
                    label="End Date (YYYY-MM-DD)"
                )
                
                initial_capital = gr.Number(
                    value=100000,
                    label="Initial Capital ($)",
                    minimum=1000
                )
                
                position_size = gr.Slider(
                    value=0.05,
                    minimum=0.01,
                    maximum=0.5,
                    step=0.01,
                    label="Position Size"
                )
                
                run_btn = gr.Button("🚀 Run Backtest", variant="primary")
            
            with gr.Column(scale=2):
                gr.Markdown("## 📊 Results")
                
                results_text = gr.Markdown()
                equity_plot = gr.Plot()
                trades_table = gr.Dataframe(
                    headers=["Entry Date", "Exit Date", "Option Type", "P&L", "Exit Reason"],
                    label="Recent Trades"
                )
        
        # AI Analysis Section
        with gr.Row():
            gr.Markdown("## 🤖 AI Analysis")
            ai_analysis = gr.Markdown()
        
        # Event handlers
        def update_status():
            api_ok = check_api_health()
            ai_ok = check_ai_service()
            
            return (
                "✅ API Server Running" if api_ok else "❌ API Server Not Available",
                "✅ AI Service Available" if ai_ok else "❌ AI Service Not Available"
            )
        
        def run_backtest_wrapper(strategy, start_date, end_date, initial_capital, position_size):
            summary, fig, trades = run_backtest(strategy, start_date, end_date, initial_capital)
            
            # Try to get AI analysis if we have results
            ai_result = ""
            if "❌" not in summary and fig is not None:
                # Create a simple results dict for AI analysis
                results_dict = {
                    "strategy": strategy,
                    "period": f"{start_date} to {end_date}",
                    "initial_capital": initial_capital,
                    "summary": summary
                }
                ai_result = get_ai_analysis(results_dict)
            
            return summary, fig, trades, ai_result
        
        # Bind events
        app.load(update_status, outputs=[api_status, ai_status])
        run_btn.click(
            run_backtest_wrapper,
            inputs=[strategy, start_date, end_date, initial_capital, position_size],
            outputs=[results_text, equity_plot, trades_table, ai_analysis]
        )
    
    return app

if __name__ == "__main__":
    # Install gradio if not available
    try:
        import gradio as gr
    except ImportError:
        print("Installing gradio...")
        os.system("pip install gradio")
        import gradio as gr
    
    # Create and launch the app
    app = create_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    ) 