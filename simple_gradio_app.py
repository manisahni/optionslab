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

def get_feature_flags():
    """Get feature flags from the API"""
    try:
        response = requests.get(f"{API_URL}/flags", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def get_strategies():
    """Get available strategies from the API"""
    try:
        response = requests.get(f"{API_URL}/strategies", timeout=5)
        if response.status_code == 200:
            return response.json()["strategies"]
        return []
    except:
        return []

def run_backtest(strategy, start_date, end_date, initial_capital):
    """Run a backtest and return results"""
    try:
        # Prepare request data
        data = {
            "strategy": strategy,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": float(initial_capital)
        }
        
        # Make API request
        response = requests.post(f"{API_URL}/run_backtest", json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                return format_results(result["results"], result["plot_base64"])
            else:
                return f"❌ Backtest failed: {result['error']}"
        else:
            return f"❌ API Error: {response.status_code}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"

def format_results(results, plot_base64):
    """Format backtest results for display"""
    try:
        # Decode plot
        plot_data = base64.b64decode(plot_base64)
        plot_image = Image.open(io.BytesIO(plot_data))
        
        # Format metrics
        metrics = results.get("metrics", {})
        metrics_text = f"""
## 📊 Backtest Results

### Performance Metrics:
- **Total Return**: {metrics.get('total_return', 'N/A'):.2%}
- **Annualized Return**: {metrics.get('annualized_return', 'N/A'):.2%}
- **Sharpe Ratio**: {metrics.get('sharpe_ratio', 'N/A'):.2f}
- **Max Drawdown**: {metrics.get('max_drawdown', 'N/A'):.2%}
- **Win Rate**: {metrics.get('win_rate', 'N/A'):.2%}

### Trade Summary:
- **Total Trades**: {metrics.get('total_trades', 'N/A')}
- **Winning Trades**: {metrics.get('winning_trades', 'N/A')}
- **Losing Trades**: {metrics.get('losing_trades', 'N/A')}
- **Average Win**: {metrics.get('avg_win', 'N/A'):.2%}
- **Average Loss**: {metrics.get('avg_loss', 'N/A'):.2%}

### Portfolio:
- **Final Value**: ${metrics.get('final_value', 'N/A'):,.2f}
- **Initial Capital**: ${metrics.get('initial_capital', 'N/A'):,.2f}
- **Net Profit**: ${metrics.get('net_profit', 'N/A'):,.2f}
        """
        
        return metrics_text, plot_image
        
    except Exception as e:
        return f"❌ Error formatting results: {str(e)}", None

def create_interface():
    """Create the Gradio interface"""
    
    # Check API status
    api_running = check_api_status()
    if not api_running:
        return gr.Interface(
            fn=lambda: "❌ API server is not running. Please start it with: python backend.py",
            inputs=[],
            outputs=gr.Textbox(label="Status"),
            title="🚀 OptionsLab Backtester",
            description="Options backtesting system with AI analysis"
        )
    
    # Get feature flags
    flags_data = get_feature_flags()
    flags_text = ""
    if flags_data:
        flags = flags_data.get("feature_flags", {})
        flags_text = f"""
## 🚩 Feature Flags Status

- **AI Analysis**: {'✅ Enabled' if flags.get('ai_analysis') else '❌ Disabled'}
- **Advanced Plots**: {'✅ Enabled' if flags.get('advanced_plots') else '❌ Disabled'}
- **Real-time Data**: {'✅ Enabled' if flags.get('real_time_data') else '❌ Disabled'}
- **Multi-Strategy**: {'✅ Enabled' if flags.get('multi_strategy') else '❌ Disabled'}

**Version**: {flags_data.get('version', 'N/A')} | **Environment**: {flags_data.get('environment', 'N/A')}
        """
    
    # Get strategies
    strategies = get_strategies()
    strategy_choices = [s["label"] for s in strategies]
    strategy_values = [s["value"] for s in strategies]
    
    # Default dates
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    with gr.Blocks(title="🚀 OptionsLab Backtester", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🚀 OptionsLab Backtester")
        gr.Markdown("Simple options backtesting system with AI analysis")
        
        # Feature flags section
        if flags_text:
            gr.Markdown(flags_text)
        
        gr.Markdown("---")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📋 Configuration")
                
                strategy = gr.Dropdown(
                    choices=strategy_choices,
                    value=strategy_choices[0] if strategy_choices else None,
                    label="Strategy",
                    info="Select the options strategy to backtest"
                )
                
                start_date_input = gr.Textbox(
                    value=start_date,
                    label="Start Date",
                    info="Format: YYYY-MM-DD"
                )
                
                end_date_input = gr.Textbox(
                    value=end_date, 
                    label="End Date", 
                    info="Format: YYYY-MM-DD"
                )
                
                initial_capital = gr.Number(
                    value=100000,
                    label="Initial Capital ($)",
                    info="Starting portfolio value"
                )
                
                run_button = gr.Button("🚀 Run Backtest", variant="primary")
                
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results")
                
                results_text = gr.Markdown("Ready to run backtest...")
                results_plot = gr.Image(label="Portfolio Performance")
        
        # Event handler
        def run_backtest_wrapper(strategy_label, start, end, capital):
            # Find strategy value from label
            try:
                strategy_idx = strategy_choices.index(strategy_label)
                strategy_value = strategy_values[strategy_idx]
            except:
                return "❌ Invalid strategy selected", None
            
            return run_backtest(strategy_value, start, end, capital)
        
        run_button.click(
            fn=run_backtest_wrapper,
            inputs=[strategy, start_date_input, end_date_input, initial_capital],
            outputs=[results_text, results_plot]
        )
        
        # Status footer
        gr.Markdown("---")
        gr.Markdown(f"**API Status**: {'✅ Running' if api_running else '❌ Not Available'} | **API URL**: {API_URL}")
    
    return app

if __name__ == "__main__":
    app = create_interface()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False) 