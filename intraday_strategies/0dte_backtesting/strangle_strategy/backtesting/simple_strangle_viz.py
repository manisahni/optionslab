#!/usr/bin/env python3
"""
Simple Strangle Strategy Visualizer
"""

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase
from zero_dte_analysis_tools import ZeroDTEAnalyzer

# Initialize
db = ZeroDTESPYOptionsDatabase()
analyzer = ZeroDTEAnalyzer(db)

def analyze_parameters(start_date, end_date):
    """Simple parameter analysis"""
    
    # Get available dates in range
    all_dates = sorted(db.metadata.get('downloaded_dates', []))
    dates_in_range = [d for d in all_dates if start_date <= d <= end_date]
    
    if not dates_in_range:
        return "No data available in date range", None
    
    # Test a few parameter combinations
    results = []
    
    for entry_time in ["09:35", "10:00", "10:30", "11:00"]:
        for delta in [0.20, 0.25, 0.30]:
            # Run backtest
            df = analyzer.backtest_strangle_strategy(
                start_date, end_date,
                entry_time=entry_time,
                delta_target=delta
            )
            
            if len(df) > 0:
                results.append({
                    'Entry Time': entry_time,
                    'Delta': delta,
                    'Trades': len(df),
                    'Win Rate': f"{df['won'].mean() * 100:.1f}%",
                    'Avg P&L': f"${df['pnl'].mean():.2f}",
                    'Total P&L': f"${df['pnl'].sum():.2f}"
                })
    
    # Create results table
    if results:
        results_df = pd.DataFrame(results)
        
        # Create simple bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=[f"{r['Entry Time']} / {r['Delta']}" for r in results],
                y=[float(r['Total P&L'].replace('$', '')) for r in results],
                text=[r['Win Rate'] for r in results],
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title='Total P&L by Entry Time and Delta',
            xaxis_title='Entry Time / Delta',
            yaxis_title='Total P&L ($)',
            height=400
        )
        
        status = f"Analyzed {len(dates_in_range)} trading days"
        return status, fig
    else:
        return "No results found", None

# Create Gradio interface
with gr.Blocks(title="0DTE Strangle Analyzer") as app:
    gr.Markdown("# Simple 0DTE Strangle Strategy Analyzer")
    
    with gr.Row():
        start_date = gr.Textbox(label="Start Date", value="20250728")
        end_date = gr.Textbox(label="End Date", value="20250801")
        analyze_btn = gr.Button("Analyze", variant="primary")
    
    status = gr.Textbox(label="Status")
    chart = gr.Plot(label="Results")
    
    analyze_btn.click(
        fn=analyze_parameters,
        inputs=[start_date, end_date],
        outputs=[status, chart]
    )

if __name__ == "__main__":
    print("Starting Simple Strangle Analyzer on http://localhost:7865")
    app.launch(server_port=7865)