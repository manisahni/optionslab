"""
ORB Backtest Visualizer
Interactive dashboard to visualize backtest results
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import gradio as gr
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))


def load_backtest_results(timeframe='60min'):
    """Load backtest results from CSV"""
    file_path = Path(f'/Users/nish_macbook/0dte/orb_strategy/data/backtest_results/orb_{timeframe}_simple.csv')
    
    if file_path.exists():
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'])
        return df
    else:
        return pd.DataFrame()


def create_performance_charts(df):
    """Create performance visualization charts"""
    
    if df.empty:
        return None
    
    # Create subplot figure
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            'Cumulative P&L', 'Daily P&L Distribution',
            'Win Rate by Month', 'Trade Entry Times',
            'Opening Range Analysis', 'Trade Type Distribution'
        ),
        specs=[
            [{"type": "scatter"}, {"type": "histogram"}],
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "scatter"}, {"type": "pie"}]
        ]
    )
    
    # 1. Cumulative P&L
    df['cumulative_pnl'] = df['pnl'].cumsum()
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['cumulative_pnl'],
            mode='lines',
            name='Cumulative P&L',
            line=dict(color='green', width=2)
        ),
        row=1, col=1
    )
    
    # 2. P&L Distribution
    fig.add_trace(
        go.Histogram(
            x=df['pnl'],
            nbinsx=30,
            name='P&L Distribution',
            marker_color='lightblue'
        ),
        row=1, col=2
    )
    
    # 3. Monthly Win Rate
    df['month'] = df['date'].dt.to_period('M')
    monthly_stats = df.groupby('month').agg({
        'pnl': ['count', lambda x: (x > 0).sum()]
    }).reset_index()
    monthly_stats.columns = ['month', 'total_trades', 'winning_trades']
    monthly_stats['win_rate'] = monthly_stats['winning_trades'] / monthly_stats['total_trades']
    
    fig.add_trace(
        go.Bar(
            x=monthly_stats['month'].astype(str),
            y=monthly_stats['win_rate'] * 100,
            name='Win Rate %',
            marker_color='purple'
        ),
        row=2, col=1
    )
    
    # 4. Entry Times
    df['entry_hour'] = pd.to_datetime(df['entry_time'], format='%H:%M:%S').dt.hour
    entry_times = df['entry_hour'].value_counts().sort_index()
    
    fig.add_trace(
        go.Bar(
            x=entry_times.index,
            y=entry_times.values,
            name='Entry Hour',
            marker_color='orange'
        ),
        row=2, col=2
    )
    
    # 5. Opening Range Analysis
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['range_pct'] * 100,
            mode='markers',
            name='OR Width %',
            marker=dict(
                size=8,
                color=df['pnl'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="P&L", x=1.1)
            )
        ),
        row=3, col=1
    )
    
    # 6. Trade Type Distribution
    trade_types = df['type'].value_counts()
    fig.add_trace(
        go.Pie(
            labels=trade_types.index,
            values=trade_types.values,
            name='Trade Types'
        ),
        row=3, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=900,
        showlegend=False,
        title_text="ORB Strategy Backtest Analysis",
        title_x=0.5
    )
    
    # Update axes
    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative P&L ($)", row=1, col=1)
    
    fig.update_xaxes(title_text="P&L ($)", row=1, col=2)
    fig.update_yaxes(title_text="Frequency", row=1, col=2)
    
    fig.update_xaxes(title_text="Month", row=2, col=1)
    fig.update_yaxes(title_text="Win Rate (%)", row=2, col=1)
    
    fig.update_xaxes(title_text="Hour", row=2, col=2)
    fig.update_yaxes(title_text="Number of Trades", row=2, col=2)
    
    fig.update_xaxes(title_text="Date", row=3, col=1)
    fig.update_yaxes(title_text="Opening Range (%)", row=3, col=1)
    
    return fig


def calculate_statistics(df):
    """Calculate performance statistics"""
    
    if df.empty:
        return "No data available"
    
    total_trades = len(df)
    winning_trades = len(df[df['pnl'] > 0])
    losing_trades = len(df[df['pnl'] <= 0])
    
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    total_pnl = df['pnl'].sum()
    avg_pnl = df['pnl'].mean()
    
    avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = abs(df[df['pnl'] <= 0]['pnl'].mean()) if losing_trades > 0 else 0
    
    profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades) if losing_trades > 0 else 0
    
    # Max drawdown
    cumulative = df['pnl'].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = cumulative - running_max
    max_dd = drawdown.min()
    
    # Sharpe ratio (simplified)
    if len(df) > 1:
        daily_returns = df.groupby('date')['pnl'].sum()
        sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
    else:
        sharpe = 0
    
    stats_text = f"""
    ## Performance Statistics
    
    ### Trade Summary
    - **Total Trades**: {total_trades}
    - **Winning Trades**: {winning_trades}
    - **Losing Trades**: {losing_trades}
    - **Win Rate**: {win_rate:.1%}
    
    ### P&L Analysis
    - **Total P&L**: ${total_pnl:,.0f}
    - **Average P&L**: ${avg_pnl:.0f}
    - **Average Win**: ${avg_win:.0f}
    - **Average Loss**: ${avg_loss:.0f}
    
    ### Risk Metrics
    - **Profit Factor**: {profit_factor:.2f}
    - **Max Drawdown**: ${max_dd:,.0f}
    - **Sharpe Ratio**: {sharpe:.2f}
    
    ### Trade Characteristics
    - **Most Common Type**: {df['type'].mode()[0] if not df.empty else 'N/A'}
    - **Avg OR Width**: {df['range_pct'].mean():.3%}
    - **Avg Entry Hour**: {df['entry_hour'].mean():.1f}
    """
    
    return stats_text


def compare_strategies():
    """Compare all three ORB strategies"""
    
    results = []
    
    for timeframe in ['15min', '30min', '60min']:
        df = load_backtest_results(timeframe)
        
        if not df.empty:
            total_trades = len(df)
            win_rate = len(df[df['pnl'] > 0]) / total_trades
            total_pnl = df['pnl'].sum()
            avg_pnl = df['pnl'].mean()
            
            # Max drawdown
            cumulative = df['pnl'].cumsum()
            running_max = cumulative.expanding().max()
            drawdown = cumulative - running_max
            max_dd = drawdown.min()
            
            results.append({
                'Strategy': f'{timeframe.replace("min", "-min")} ORB',
                'Trades': total_trades,
                'Win Rate': f'{win_rate:.1%}',
                'Total P&L': f'${total_pnl:,.0f}',
                'Avg P&L': f'${avg_pnl:.0f}',
                'Max DD': f'${max_dd:,.0f}'
            })
    
    comparison_df = pd.DataFrame(results)
    
    # Add article results for comparison
    article_results = pd.DataFrame([
        {'Strategy': 'Article 15-min', 'Win Rate': '78.1%', 'Total P&L': '$19,053', 'Avg P&L': '$35', 'Max DD': '-$7,602'},
        {'Strategy': 'Article 30-min', 'Win Rate': '82.6%', 'Total P&L': '$19,555', 'Avg P&L': '$31', 'Max DD': '-$8,306'},
        {'Strategy': 'Article 60-min', 'Win Rate': '88.8%', 'Total P&L': '$30,708', 'Avg P&L': '$51', 'Max DD': '-$3,231'}
    ])
    
    return comparison_df, article_results


def create_interface():
    """Create Gradio interface"""
    
    with gr.Blocks(title="ORB Backtest Dashboard", theme=gr.themes.Soft()) as demo:
        
        gr.Markdown("# 📊 ORB Strategy Backtest Dashboard")
        gr.Markdown("Analyze Opening Range Breakout strategy performance across different timeframes")
        
        with gr.Tab("Performance Analysis"):
            with gr.Row():
                timeframe_select = gr.Dropdown(
                    choices=['15min', '30min', '60min'],
                    value='60min',
                    label="Select Timeframe"
                )
                refresh_btn = gr.Button("Refresh Data", variant="primary")
            
            with gr.Row():
                with gr.Column(scale=2):
                    performance_plot = gr.Plot(label="Performance Charts")
                with gr.Column(scale=1):
                    stats_display = gr.Markdown(label="Statistics")
        
        with gr.Tab("Strategy Comparison"):
            gr.Markdown("## Backtest Results vs Article Performance")
            
            with gr.Row():
                backtest_table = gr.DataFrame(label="Backtest Results")
                article_table = gr.DataFrame(label="Article Results")
            
            comparison_notes = gr.Markdown("""
            ### Key Observations:
            - **60-min ORB** shows the best performance in both backtest and article
            - Our backtest shows higher win rates (likely due to simplified P&L calculation)
            - Profit factors exceed article results significantly
            - Real trading would include commissions and slippage
            """)
        
        with gr.Tab("Trade Log"):
            trade_log_df = gr.DataFrame(label="Recent Trades")
            
            export_btn = gr.Button("Export to CSV")
            export_status = gr.Textbox(label="Export Status", interactive=False)
        
        # Event handlers
        def update_analysis(timeframe):
            df = load_backtest_results(timeframe)
            fig = create_performance_charts(df)
            stats = calculate_statistics(df)
            return fig, stats
        
        def update_comparison():
            backtest_df, article_df = compare_strategies()
            return backtest_df, article_df
        
        def update_trade_log(timeframe):
            df = load_backtest_results(timeframe)
            if not df.empty:
                # Show last 20 trades
                return df[['date', 'type', 'entry_time', 'exit_time', 'range_pct', 'pnl']].tail(20)
            return pd.DataFrame()
        
        def export_trades(timeframe):
            df = load_backtest_results(timeframe)
            if not df.empty:
                export_path = f'orb_{timeframe}_export.csv'
                df.to_csv(export_path, index=False)
                return f"Exported {len(df)} trades to {export_path}"
            return "No data to export"
        
        # Connect events
        timeframe_select.change(
            update_analysis,
            inputs=[timeframe_select],
            outputs=[performance_plot, stats_display]
        )
        
        refresh_btn.click(
            update_analysis,
            inputs=[timeframe_select],
            outputs=[performance_plot, stats_display]
        )
        
        demo.load(
            update_analysis,
            inputs=[timeframe_select],
            outputs=[performance_plot, stats_display]
        )
        
        demo.load(
            update_comparison,
            outputs=[backtest_table, article_table]
        )
        
        timeframe_select.change(
            update_trade_log,
            inputs=[timeframe_select],
            outputs=[trade_log_df]
        )
        
        export_btn.click(
            export_trades,
            inputs=[timeframe_select],
            outputs=[export_status]
        )
    
    return demo


if __name__ == "__main__":
    print("Starting ORB Backtest Dashboard...")
    print("Open http://localhost:7860 in your browser")
    
    demo = create_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860)