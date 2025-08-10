#!/usr/bin/env python3
"""
0DTE Strangle Strategy Optimizer with Advanced Visualizations
Discovers optimal entry times and parameters through interactive analysis
"""

import os
import sys
import numpy as np
import pandas as pd
import gradio as gr
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Tuple, Dict, List
import warnings
warnings.filterwarnings('ignore')

# Add the market_data directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase
from zero_dte_analysis_tools import ZeroDTEAnalyzer


class StrangleOptimizer:
    """Advanced visualization and optimization for 0DTE strangle strategies"""
    
    def __init__(self):
        self.db = ZeroDTESPYOptionsDatabase()
        self.analyzer = ZeroDTEAnalyzer(self.db)
        self.results_cache = {}
        
    def generate_profit_landscape(self, start_date: str, end_date: str, 
                                 exit_time: str = "15:50") -> go.Figure:
        """Generate 3D surface plot of profit landscape"""
        
        # Define parameter ranges
        entry_times = ["09:35", "10:00", "10:30", "11:00", "11:30", 
                      "12:00", "12:30", "13:00", "13:30", "14:00", "14:30"]
        delta_targets = np.arange(0.10, 0.41, 0.05)
        
        # Create mesh grid for 3D plot
        profit_matrix = []
        sharpe_matrix = []
        
        for delta in delta_targets:
            profit_row = []
            sharpe_row = []
            
            for entry_time in entry_times:
                # Run backtest for this combination
                results_df = self.analyzer.backtest_strangle_strategy(
                    start_date, end_date, 
                    entry_time=entry_time,
                    exit_time=exit_time,
                    delta_target=delta
                )
                
                if len(results_df) > 0:
                    avg_pnl = results_df['pnl_pct'].mean() * 100
                    # Calculate Sharpe ratio
                    if results_df['pnl_pct'].std() > 0:
                        sharpe = (results_df['pnl_pct'].mean() / results_df['pnl_pct'].std()) * (252 ** 0.5)
                    else:
                        sharpe = 0
                else:
                    avg_pnl = 0
                    sharpe = 0
                
                profit_row.append(avg_pnl)
                sharpe_row.append(sharpe)
            
            profit_matrix.append(profit_row)
            sharpe_matrix.append(sharpe_row)
        
        # Create 3D surface plot
        fig = go.Figure(data=[go.Surface(
            x=entry_times,
            y=delta_targets,
            z=profit_matrix,
            colorscale='RdYlGn',
            text=[[f"Sharpe: {s:.2f}" for s in row] for row in sharpe_matrix],
            hovertemplate='Entry: %{x}<br>Delta: %{y:.2f}<br>Avg P&L: %{z:.2%}<br>%{text}<extra></extra>'
        )])
        
        # Find optimal point
        max_idx = np.unravel_index(np.argmax(profit_matrix), np.array(profit_matrix).shape)
        optimal_entry = entry_times[max_idx[1]]
        optimal_delta = delta_targets[max_idx[0]]
        
        # Add marker for optimal point
        fig.add_trace(go.Scatter3d(
            x=[optimal_entry],
            y=[optimal_delta],
            z=[np.max(profit_matrix)],
            mode='markers+text',
            marker=dict(size=10, color='red'),
            text=['Optimal'],
            textposition='top center',
            name='Optimal Point'
        ))
        
        fig.update_layout(
            title={
                'text': f'Profit Landscape: Entry Time vs Delta Target<br><sub>Optimal: {optimal_entry} @ {optimal_delta:.2f} delta</sub>',
                'x': 0.5,
                'xanchor': 'center'
            },
            scene=dict(
                xaxis_title='Entry Time',
                yaxis_title='Delta Target',
                zaxis_title='Average P&L %',
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
            ),
            height=600
        )
        
        return fig
    
    def generate_heatmap_grid(self, start_date: str, end_date: str) -> go.Figure:
        """Generate interactive heatmap of entry times vs delta targets"""
        
        # Define parameter ranges
        entry_times = ["09:35", "10:00", "10:30", "11:00", "11:30", 
                      "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00"]
        delta_targets = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
        
        # Build results matrix
        results_matrix = []
        annotations = []
        
        for i, delta in enumerate(delta_targets):
            row = []
            for j, entry_time in enumerate(entry_times):
                results_df = self.analyzer.backtest_strangle_strategy(
                    start_date, end_date,
                    entry_time=entry_time,
                    exit_time="15:50",
                    delta_target=delta
                )
                
                if len(results_df) > 0:
                    win_rate = results_df['won'].mean() * 100
                    avg_pnl = results_df['pnl_pct'].mean() * 100
                    row.append(avg_pnl)
                    
                    # Add annotation
                    annotations.append(dict(
                        x=j, y=i,
                        text=f"{avg_pnl:.1f}%<br>{win_rate:.0f}%",
                        showarrow=False,
                        font=dict(size=10)
                    ))
                else:
                    row.append(0)
            
            results_matrix.append(row)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=results_matrix,
            x=entry_times,
            y=[f"{d:.2f}" for d in delta_targets],
            colorscale='RdYlGn',
            zmid=0,
            text=[[f"P&L: {val:.1f}%" for val in row] for row in results_matrix],
            hovertemplate='Entry: %{x}<br>Delta: %{y}<br>%{text}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Entry Time vs Delta Target Performance Heatmap<br><sub>Values show Average P&L % and Win Rate</sub>',
            xaxis_title='Entry Time',
            yaxis_title='Delta Target',
            annotations=annotations,
            height=500
        )
        
        return fig
    
    def generate_time_animation(self, date: str) -> go.Figure:
        """Generate animated scatter showing how optimal parameters change during the day"""
        
        # Load data for the specific date
        df = self.db.load_zero_dte_data(date)
        if df.empty:
            return go.Figure().add_annotation(text="No data available for this date")
        
        # Sample different times throughout the day
        times = pd.date_range(start=f"{date} 09:35", end=f"{date} 15:30", freq='30min')
        
        frames = []
        for time in times:
            time_str = time.strftime('%H:%M')
            
            # Get available strangles at this time
            strangles = self.db.get_zero_dte_strangles(date, time_str)
            
            if not strangles.empty:
                # Calculate metrics for each strangle
                strangles['spread_cost'] = strangles['call_ask'] + strangles['put_ask']
                strangles['delta_diff'] = abs(abs(strangles['call_delta']) - abs(strangles['put_delta']))
                
                frame_data = go.Frame(
                    data=[go.Scatter(
                        x=strangles['avg_delta'],
                        y=strangles['spread_cost'],
                        mode='markers',
                        marker=dict(
                            size=10,
                            color=strangles['delta_diff'],
                            colorscale='Viridis',
                            showscale=True
                        ),
                        text=[f"Call: {row['call_strike']}<br>Put: {row['put_strike']}<br>Cost: ${row['spread_cost']:.2f}" 
                              for _, row in strangles.iterrows()],
                        hovertemplate='Delta: %{x:.3f}<br>%{text}<extra></extra>'
                    )],
                    name=time_str
                )
                frames.append(frame_data)
        
        # Create initial figure
        if frames:
            fig = go.Figure(
                data=frames[0].data,
                frames=frames
            )
            
            # Add play/pause buttons
            fig.update_layout(
                title='Strangle Opportunities Throughout the Day',
                xaxis_title='Average Delta',
                yaxis_title='Total Premium Cost ($)',
                updatemenus=[{
                    'type': 'buttons',
                    'showactive': False,
                    'buttons': [
                        {'label': 'Play', 'method': 'animate', 'args': [None, {'frame': {'duration': 1000}}]},
                        {'label': 'Pause', 'method': 'animate', 'args': [[None], {'frame': {'duration': 0}, 'mode': 'immediate'}]}
                    ]
                }],
                sliders=[{
                    'currentvalue': {'prefix': 'Time: ', 'visible': True, 'xanchor': 'right'},
                    'steps': [{'label': f.name, 'method': 'animate', 'args': [[f.name]]} for f in frames]
                }],
                height=600
            )
        else:
            fig = go.Figure().add_annotation(text="No strangle data available")
        
        return fig
    
    def generate_clock_chart(self, start_date: str, end_date: str) -> go.Figure:
        """Generate radial clock chart showing profitability by time"""
        
        # Define hours and deltas for radial chart
        hours = list(range(10, 16))  # 10 AM to 3 PM
        deltas = [0.15, 0.20, 0.25, 0.30, 0.35]
        
        # Create radial data
        fig = go.Figure()
        
        for delta in deltas:
            profits = []
            angles = []
            
            for hour in hours:
                entry_time = f"{hour:02d}:00"
                results_df = self.analyzer.backtest_strangle_strategy(
                    start_date, end_date,
                    entry_time=entry_time,
                    exit_time="15:50",
                    delta_target=delta
                )
                
                avg_pnl = results_df['pnl_pct'].mean() * 100 if len(results_df) > 0 else 0
                profits.append(max(0, avg_pnl + 5))  # Offset for visibility
                angles.append(hour * 30 - 300)  # Convert to degrees (10 AM = 0°)
            
            # Close the loop
            profits.append(profits[0])
            angles.append(angles[0])
            
            # Add trace
            fig.add_trace(go.Scatterpolar(
                r=profits,
                theta=angles,
                name=f'Delta {delta:.2f}',
                fill='toself',
                opacity=0.6
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(10, max([max(t.r) for t in fig.data]))]
                ),
                angularaxis=dict(
                    tickmode='array',
                    tickvals=[(h * 30 - 300) for h in hours],
                    ticktext=[f"{h}:00" for h in hours],
                    direction='clockwise',
                    rotation=90
                )
            ),
            title='Profitability Clock Chart<br><sub>Distance from center = Average P&L %</sub>',
            height=600,
            showlegend=True
        )
        
        return fig
    
    def find_optimal_parameters(self, start_date: str, end_date: str) -> Dict:
        """Use grid search to find optimal parameters"""
        
        best_sharpe = -np.inf
        best_params = {}
        all_results = []
        
        # Parameter ranges
        entry_times = ["09:35", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00"]
        exit_times = ["14:00", "14:30", "15:00", "15:30", "15:50"]
        delta_targets = np.arange(0.10, 0.41, 0.05)
        
        total_combinations = len(entry_times) * len(exit_times) * len(delta_targets)
        progress = 0
        
        for entry in entry_times:
            for exit in exit_times:
                # Skip invalid combinations
                entry_hour = int(entry.split(':')[0])
                exit_hour = int(exit.split(':')[0])
                if exit_hour <= entry_hour:
                    continue
                
                for delta in delta_targets:
                    progress += 1
                    
                    # Run backtest
                    results_df = self.analyzer.backtest_strangle_strategy(
                        start_date, end_date,
                        entry_time=entry,
                        exit_time=exit,
                        delta_target=delta
                    )
                    
                    if len(results_df) > 10:  # Minimum trades for validity
                        # Calculate Sharpe ratio
                        if results_df['pnl_pct'].std() > 0:
                            sharpe = (results_df['pnl_pct'].mean() / results_df['pnl_pct'].std()) * (252 ** 0.5)
                        else:
                            sharpe = 0
                        
                        all_results.append({
                            'entry_time': entry,
                            'exit_time': exit,
                            'delta_target': delta,
                            'sharpe_ratio': sharpe,
                            'avg_pnl': results_df['pnl_pct'].mean() * 100,
                            'win_rate': results_df['won'].mean() * 100,
                            'total_trades': len(results_df)
                        })
                        
                        if sharpe > best_sharpe:
                            best_sharpe = sharpe
                            best_params = {
                                'entry_time': entry,
                                'exit_time': exit,
                                'delta_target': delta,
                                'sharpe_ratio': sharpe,
                                'avg_pnl': results_df['pnl_pct'].mean() * 100,
                                'win_rate': results_df['won'].mean() * 100,
                                'max_drawdown': ((results_df['cumulative_pnl'] - results_df['cumulative_pnl'].cummax()).min() / results_df['entry_credit'].iloc[0]) * 100 if len(results_df) > 0 else 0
                            }
        
        # Sort all results by Sharpe ratio
        all_results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
        
        return {
            'best_params': best_params,
            'top_10': all_results[:10]
        }


def create_gradio_interface():
    """Create the Gradio interface for the optimizer"""
    
    optimizer = StrangleOptimizer()
    
    # Get available date range
    metadata = optimizer.db.metadata
    available_dates = sorted(metadata.get('downloaded_dates', []))
    
    if available_dates:
        default_start = available_dates[max(0, len(available_dates) - 30)]
        default_end = available_dates[-1]
    else:
        default_start = "20250701"
        default_end = "20250801"
    
    with gr.Blocks(title="0DTE Strangle Optimizer", theme=gr.themes.Soft()) as app:
        
        gr.Markdown("""
        # 🎯 0DTE Strangle Strategy Optimizer
        
        Discover optimal entry times and parameters through advanced visualizations
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Analysis Parameters")
                start_date = gr.Textbox(
                    label="Start Date (YYYYMMDD)", 
                    value=default_start,
                    info="Beginning of analysis period"
                )
                end_date = gr.Textbox(
                    label="End Date (YYYYMMDD)", 
                    value=default_end,
                    info="End of analysis period"
                )
                
                analyze_btn = gr.Button("🔍 Run Analysis", variant="primary", size="lg")
                
                gr.Markdown("### Quick Actions")
                optimize_btn = gr.Button("⚡ Find Optimal Parameters", variant="secondary")
                
            with gr.Column(scale=3):
                # Status and results area
                status_text = gr.Markdown("Ready to analyze...")
                optimal_params = gr.JSON(label="Optimal Parameters", visible=False)
        
        with gr.Tabs():
            with gr.Tab("📊 Profit Landscape"):
                landscape_plot = gr.Plot(label="3D Profit Landscape")
                gr.Markdown("""
                **How to read this chart:**
                - Higher surfaces indicate more profitable parameter combinations
                - X-axis: Entry time during the trading day
                - Y-axis: Target delta for the strangle
                - Z-axis: Average profit/loss percentage
                - Red marker shows the optimal combination
                """)
            
            with gr.Tab("🔥 Performance Heatmap"):
                heatmap_plot = gr.Plot(label="Entry Time vs Delta Heatmap")
                gr.Markdown("""
                **How to read this chart:**
                - Green cells: Profitable combinations
                - Red cells: Loss-making combinations
                - Numbers show: Average P&L % and Win Rate
                - Darker colors indicate stronger performance
                """)
            
            with gr.Tab("⏰ Time Animation"):
                with gr.Row():
                    animation_date = gr.Textbox(
                        label="Date for Animation (YYYYMMDD)",
                        value=default_end,
                        scale=1
                    )
                    animation_btn = gr.Button("Generate Animation", scale=1)
                
                animation_plot = gr.Plot(label="Intraday Parameter Evolution")
                gr.Markdown("""
                **How to read this chart:**
                - Shows how strangle opportunities change throughout the day
                - X-axis: Average delta of the strangle
                - Y-axis: Total premium cost
                - Color: Delta balance (lighter = more balanced)
                - Use the play button to see evolution
                """)
            
            with gr.Tab("🕐 Clock Chart"):
                clock_plot = gr.Plot(label="Profitability Clock")
                gr.Markdown("""
                **How to read this chart:**
                - Each ring represents a different delta target
                - Distance from center shows profitability
                - Best entry times appear as peaks
                - Compare different deltas visually
                """)
        
        # Event handlers
        def run_analysis(start, end):
            status_text = "🔄 Generating visualizations... This may take a minute..."
            
            try:
                # Generate all plots
                landscape = optimizer.generate_profit_landscape(start, end)
                heatmap = optimizer.generate_heatmap_grid(start, end)
                clock = optimizer.generate_clock_chart(start, end)
                
                status_text = f"✅ Analysis complete for {start} to {end}"
                
                return status_text, landscape, heatmap, clock
                
            except Exception as e:
                status_text = f"❌ Error: {str(e)}"
                empty_fig = go.Figure().add_annotation(text="Error generating chart")
                return status_text, empty_fig, empty_fig, empty_fig
        
        def find_optimal(start, end):
            status_text = "🔄 Searching for optimal parameters... This may take several minutes..."
            
            try:
                results = optimizer.find_optimal_parameters(start, end)
                
                status_text = "✅ Optimization complete!"
                
                # Format results for display
                display_results = {
                    "Best Parameters": results['best_params'],
                    "Top 10 Combinations": results['top_10']
                }
                
                return status_text, gr.JSON(value=display_results, visible=True)
                
            except Exception as e:
                status_text = f"❌ Error: {str(e)}"
                return status_text, gr.JSON(visible=False)
        
        def generate_animation(date):
            try:
                animation = optimizer.generate_time_animation(date)
                return animation
            except Exception as e:
                return go.Figure().add_annotation(text=f"Error: {str(e)}")
        
        # Connect events
        analyze_btn.click(
            fn=run_analysis,
            inputs=[start_date, end_date],
            outputs=[status_text, landscape_plot, heatmap_plot, clock_plot]
        )
        
        optimize_btn.click(
            fn=find_optimal,
            inputs=[start_date, end_date],
            outputs=[status_text, optimal_params]
        )
        
        animation_btn.click(
            fn=generate_animation,
            inputs=[animation_date],
            outputs=[animation_plot]
        )
        
        # Load initial visualizations
        app.load(
            fn=run_analysis,
            inputs=[start_date, end_date],
            outputs=[status_text, landscape_plot, heatmap_plot, clock_plot]
        )
    
    return app


if __name__ == "__main__":
    print("Starting 0DTE Strangle Optimizer...")
    print("Access at: http://localhost:7864")
    
    app = create_gradio_interface()
    app.launch(server_name="0.0.0.0", server_port=7864, share=False)