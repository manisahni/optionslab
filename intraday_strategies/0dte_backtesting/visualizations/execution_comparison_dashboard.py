#!/usr/bin/env python3
"""Interactive dashboard to compare execution modes and delta corrections"""

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys
sys.path.append('../core')
sys.path.append('../backtesting')
from enhanced_strangle_backtester import EnhancedStrangleBacktester, ExecutionConfig
import numpy as np

class ExecutionComparisonDashboard:
    """Dashboard for comparing execution modes and delta corrections"""
    
    def __init__(self):
        self.cached_results = {}
    
    def run_backtest_comparison(self, start_date, end_date, modes_to_test, use_delta_correction):
        """Run backtests with different configurations"""
        # Convert date format
        start = start_date.replace("-", "")
        end = end_date.replace("-", "")
        
        results = {}
        
        for mode in modes_to_test:
            for use_corrected in ([False, True] if use_delta_correction else [False]):
                config_name = f"{mode} + {'Corrected' if use_corrected else 'Original'} Deltas"
                
                # Check cache
                cache_key = f"{start}_{end}_{mode}_{use_corrected}"
                if cache_key in self.cached_results:
                    results[config_name] = self.cached_results[cache_key]
                    continue
                
                # Run backtest
                config = ExecutionConfig(mode=mode.lower(), use_corrected_deltas=use_corrected)
                backtester = EnhancedStrangleBacktester(exec_config=config)
                
                df = backtester.backtest_period(start, end)
                report = backtester.generate_comparison_report()
                
                results[config_name] = {
                    'dataframe': df,
                    'report': report,
                    'trades': backtester.trades
                }
                
                # Cache result
                self.cached_results[cache_key] = results[config_name]
        
        return results
    
    def create_pnl_comparison_chart(self, results):
        """Create P&L comparison chart"""
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set3
        
        for i, (name, data) in enumerate(results.items()):
            df = data['dataframe']
            if df.empty:
                continue
            
            # Add cumulative P&L line
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(df['date'], format='%Y%m%d'),
                y=df['cumulative_pnl'],
                mode='lines+markers',
                name=name,
                line=dict(color=colors[i % len(colors)], width=2),
                hovertemplate=(
                    '<b>%{fullData.name}</b><br>' +
                    'Date: %{x|%Y-%m-%d}<br>' +
                    'Cumulative P&L: $%{y:.2f}<br>' +
                    '<extra></extra>'
                )
            ))
        
        fig.update_layout(
            title="Cumulative P&L Comparison",
            xaxis_title="Date",
            yaxis_title="Cumulative P&L ($)",
            hovermode='x unified',
            height=500,
            showlegend=True,
            legend=dict(
                yanchor="bottom",
                y=0.01,
                xanchor="left",
                x=0.01
            )
        )
        
        return fig
    
    def create_execution_cost_chart(self, results):
        """Create execution cost breakdown chart"""
        data = []
        
        for name, result in results.items():
            report = result['report']
            if not report:
                continue
            
            data.append({
                'Configuration': name,
                'Gross P&L': report['pnl_breakdown']['gross_pnl'],
                'Entry Slippage': -abs(report['execution_costs']['avg_entry_slippage'] * report['summary']['total_trades']),
                'Exit Slippage': -abs(report['execution_costs']['avg_exit_slippage'] * report['summary']['total_trades']),
                'Net P&L': report['pnl_breakdown']['net_pnl']
            })
        
        df = pd.DataFrame(data)
        
        # Create stacked bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Gross P&L',
            x=df['Configuration'],
            y=df['Gross P&L'],
            marker_color='lightgreen'
        ))
        
        fig.add_trace(go.Bar(
            name='Entry Slippage',
            x=df['Configuration'],
            y=df['Entry Slippage'],
            marker_color='lightcoral'
        ))
        
        fig.add_trace(go.Bar(
            name='Exit Slippage',
            x=df['Configuration'],
            y=df['Exit Slippage'],
            marker_color='lightsalmon'
        ))
        
        fig.update_layout(
            title="Execution Cost Breakdown",
            xaxis_title="Configuration",
            yaxis_title="P&L ($)",
            barmode='relative',
            height=500,
            showlegend=True
        )
        
        return fig
    
    def create_delta_distribution_chart(self, results):
        """Create delta distribution comparison"""
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Call Delta Distribution", "Put Delta Distribution")
        )
        
        for name, data in results.items():
            if 'Original' in name:
                continue  # Only show corrected for clarity
            
            trades = data['trades']
            if not trades:
                continue
            
            # Extract deltas
            call_deltas = [t.call_delta_corrected or t.call_delta_original for t in trades]
            put_deltas = [t.put_delta_corrected or t.put_delta_original for t in trades]
            
            # Add histograms
            fig.add_trace(
                go.Histogram(
                    x=call_deltas,
                    name=f"{name} - Calls",
                    opacity=0.7,
                    nbinsx=20
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Histogram(
                    x=put_deltas,
                    name=f"{name} - Puts",
                    opacity=0.7,
                    nbinsx=20
                ),
                row=1, col=2
            )
        
        # Add target lines
        fig.add_vline(x=0.30, line_dash="dash", line_color="red", 
                     annotation_text="Target 0.30", row=1, col=1)
        fig.add_vline(x=-0.30, line_dash="dash", line_color="red",
                     annotation_text="Target -0.30", row=1, col=2)
        
        fig.update_layout(
            title="Delta Distribution Analysis",
            height=400,
            showlegend=True
        )
        
        return fig
    
    def create_quality_score_chart(self, results):
        """Create data quality comparison"""
        data = []
        
        for name, result in results.items():
            trades = result['trades']
            if not trades:
                continue
            
            quality_scores = [t.data_quality_score for t in trades]
            
            data.append({
                'Configuration': name,
                'Mean Quality': np.mean(quality_scores),
                'Min Quality': np.min(quality_scores),
                'Max Quality': np.max(quality_scores),
                'Std Quality': np.std(quality_scores)
            })
        
        df = pd.DataFrame(data)
        
        # Create box plot
        fig = go.Figure()
        
        for _, row in df.iterrows():
            fig.add_trace(go.Box(
                y=[row['Min Quality'], row['Mean Quality'] - row['Std Quality'],
                   row['Mean Quality'], row['Mean Quality'] + row['Std Quality'],
                   row['Max Quality']],
                name=row['Configuration'],
                boxpoints=False
            ))
        
        fig.update_layout(
            title="Data Quality Score Distribution",
            yaxis_title="Quality Score",
            height=400,
            showlegend=False
        )
        
        return fig
    
    def generate_summary_table(self, results):
        """Generate summary statistics table"""
        data = []
        
        for name, result in results.items():
            report = result['report']
            if not report:
                continue
            
            data.append({
                'Configuration': name,
                'Total Trades': report['summary']['total_trades'],
                'Gross P&L': f"${report['pnl_breakdown']['gross_pnl']:.2f}",
                'Total Slippage': f"${report['execution_costs']['total_slippage_cost']:.2f}",
                'Net P&L': f"${report['pnl_breakdown']['net_pnl']:.2f}",
                'Slippage %': f"{report['execution_costs']['slippage_as_pct_gross']:.1f}%",
                'Avg Quality': f"{report['data_quality']['avg_quality_score']:.2f}",
                'Sharpe Ratio': self.calculate_sharpe(result['dataframe'])
            })
        
        df = pd.DataFrame(data)
        return df
    
    def calculate_sharpe(self, df):
        """Calculate Sharpe ratio"""
        if df.empty or 'total_pnl' not in df:
            return "N/A"
        
        returns = df['total_pnl']
        if len(returns) < 2:
            return "N/A"
        
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        return f"{sharpe:.2f}"
    
    def create_interface(self):
        """Create Gradio interface"""
        with gr.Blocks(title="Execution Comparison Dashboard", theme=gr.themes.Base()) as interface:
            gr.Markdown("""
            # 🎯 Execution Mode & Delta Correction Comparison Dashboard
            
            This dashboard compares different execution assumptions and the impact of Black-Scholes delta corrections.
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    start_date = gr.Textbox(
                        label="Start Date",
                        value="2025-07-28",
                        info="YYYY-MM-DD format"
                    )
                    end_date = gr.Textbox(
                        label="End Date", 
                        value="2025-08-01",
                        info="YYYY-MM-DD format"
                    )
                
                with gr.Column(scale=1):
                    execution_modes = gr.CheckboxGroup(
                        label="Execution Modes to Test",
                        choices=["Conservative", "Midpoint", "Aggressive"],
                        value=["Conservative", "Midpoint"],
                        info="Select execution assumptions"
                    )
                    
                    compare_deltas = gr.Checkbox(
                        label="Compare Original vs Corrected Deltas",
                        value=True,
                        info="Test both delta calculation methods"
                    )
                
                with gr.Column(scale=1):
                    run_btn = gr.Button("Run Comparison", variant="primary", size="lg")
                    
                    gr.Markdown("""
                    ### Execution Modes:
                    - **Conservative**: Always cross the spread
                    - **Midpoint**: Execute at mid + small slippage  
                    - **Aggressive**: Try to get inside the spread
                    """)
            
            # Results section
            with gr.Row():
                summary_table = gr.Dataframe(
                    label="Summary Statistics",
                    interactive=False
                )
            
            with gr.Tabs():
                with gr.Tab("P&L Comparison"):
                    pnl_chart = gr.Plot(label="Cumulative P&L")
                
                with gr.Tab("Execution Costs"):
                    execution_chart = gr.Plot(label="Execution Cost Breakdown")
                
                with gr.Tab("Delta Distribution"):
                    delta_chart = gr.Plot(label="Delta Distribution")
                
                with gr.Tab("Data Quality"):
                    quality_chart = gr.Plot(label="Quality Scores")
            
            # Key insights
            with gr.Row():
                insights = gr.Markdown("""
                ### Key Insights:
                
                1. **Delta Corrections**: Black-Scholes corrections fix the "all deltas = 1.0" issue
                2. **Execution Impact**: Choice of execution mode can change P&L by 20-50%
                3. **Slippage Costs**: Conservative execution has highest slippage
                4. **Data Quality**: Lower quality scores indicate problematic data points
                """)
            
            # Run analysis
            def run_analysis(start, end, modes, compare_delta):
                if not modes:
                    return None, None, None, None, None, "Please select at least one execution mode"
                
                # Run backtests
                results = self.run_backtest_comparison(start, end, modes, compare_delta)
                
                # Generate outputs
                summary = self.generate_summary_table(results)
                pnl_fig = self.create_pnl_comparison_chart(results)
                exec_fig = self.create_execution_cost_chart(results)
                delta_fig = self.create_delta_distribution_chart(results) 
                quality_fig = self.create_quality_score_chart(results)
                
                return summary, pnl_fig, exec_fig, delta_fig, quality_fig, ""
            
            run_btn.click(
                fn=run_analysis,
                inputs=[start_date, end_date, execution_modes, compare_deltas],
                outputs=[summary_table, pnl_chart, execution_chart, delta_chart, quality_chart, insights]
            )
        
        return interface


def main():
    """Launch the dashboard"""
    dashboard = ExecutionComparisonDashboard()
    interface = dashboard.create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7864,
        share=False
    )


if __name__ == "__main__":
    main()