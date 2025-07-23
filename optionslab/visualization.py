#!/usr/bin/env python3
"""
Visualization module for OptionsLab
Provides interactive Plotly charts for trade analysis
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from pathlib import Path
import traceback


def create_backtest_charts(results, export_dir='backtest_results'):
    """Create visualization charts for backtest results"""
    try:
        # Create export directory if it doesn't exist
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        strategy_name = results['config']['name'].replace(' ', '_').lower()
        
        # Convert equity curve to DataFrame
        equity_df = pd.DataFrame(results['equity_curve'])
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        
        # Create figure with subplots
        fig = plt.figure(figsize=(15, 12))
        gs = GridSpec(4, 2, figure=fig, hspace=0.3, wspace=0.3)
        
        # 1. Equity Curve
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(equity_df['date'], equity_df['total_value'], 'b-', linewidth=2, label='Total Value')
        ax1.plot(equity_df['date'], equity_df['cash'], 'g--', linewidth=1, label='Cash')
        ax1.axhline(y=results['initial_capital'], color='r', linestyle=':', label='Initial Capital')
        ax1.set_title(f"{results['config']['name']} - Equity Curve", fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # 2. Drawdown
        ax2 = fig.add_subplot(gs[1, :])
        # Calculate drawdown
        rolling_max = equity_df['total_value'].expanding().max()
        drawdown = (equity_df['total_value'] - rolling_max) / rolling_max * 100
        ax2.fill_between(equity_df['date'], drawdown, 0, color='red', alpha=0.3)
        ax2.plot(equity_df['date'], drawdown, 'r-', linewidth=1)
        ax2.set_title('Drawdown (%)', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Drawdown %')
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # 3. Trade P&L Distribution
        ax3 = fig.add_subplot(gs[2, 0])
        completed_trades = [t for t in results['trades'] if 'pnl' in t]
        if completed_trades:
            pnls = [t['pnl'] for t in completed_trades]
            colors = ['green' if pnl > 0 else 'red' for pnl in pnls]
            bars = ax3.bar(range(len(pnls)), pnls, color=colors, alpha=0.7)
            ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax3.set_title('Trade P&L', fontsize=12, fontweight='bold')
            ax3.set_xlabel('Trade Number')
            ax3.set_ylabel('P&L ($)')
            ax3.grid(True, alpha=0.3)
            
            # Add average line
            avg_pnl = np.mean(pnls)
            ax3.axhline(y=avg_pnl, color='blue', linestyle='--', label=f'Avg: ${avg_pnl:.2f}')
            ax3.legend()
        
        # 4. Win/Loss Statistics
        ax4 = fig.add_subplot(gs[2, 1])
        if completed_trades:
            wins = sum(1 for t in completed_trades if t['pnl'] > 0)
            losses = sum(1 for t in completed_trades if t['pnl'] <= 0)
            
            # Pie chart
            sizes = [wins, losses]
            labels = [f'Wins ({wins})', f'Losses ({losses})']
            colors = ['green', 'red']
            explode = (0.1, 0)  # explode wins slice
            
            ax4.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                    shadow=True, startangle=90)
            ax4.set_title('Win/Loss Distribution', fontsize=12, fontweight='bold')
        
        # 5. Position Count Over Time
        ax5 = fig.add_subplot(gs[3, 0])
        ax5.plot(equity_df['date'], equity_df['positions'], 'b-', linewidth=2, marker='o', markersize=4)
        ax5.set_title('Active Positions Over Time', fontsize=12, fontweight='bold')
        ax5.set_xlabel('Date')
        ax5.set_ylabel('Number of Positions')
        ax5.grid(True, alpha=0.3)
        ax5.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45)
        
        # 6. Exit Reasons
        ax6 = fig.add_subplot(gs[3, 1])
        if completed_trades:
            exit_reasons = {}
            for trade in completed_trades:
                reason = trade.get('exit_reason', 'unknown')
                # Simplify exit reason
                if 'profit target' in reason:
                    reason = 'Profit Target'
                elif 'stop loss' in reason:
                    reason = 'Stop Loss'
                elif 'time stop' in reason:
                    reason = 'Time Stop'
                elif 'delta stop' in reason:
                    reason = 'Delta Stop'
                elif 'RSI exit' in reason:
                    reason = 'RSI Exit'
                elif 'BB exit' in reason:
                    reason = 'BB Exit'
                else:
                    reason = 'Other'
                
                exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
            
            # Bar chart
            reasons = list(exit_reasons.keys())
            counts = list(exit_reasons.values())
            bars = ax6.bar(reasons, counts, color='skyblue', alpha=0.7)
            ax6.set_title('Exit Reasons', fontsize=12, fontweight='bold')
            ax6.set_xlabel('Exit Type')
            ax6.set_ylabel('Count')
            ax6.grid(True, alpha=0.3, axis='y')
            plt.setp(ax6.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Add count labels on bars
            for bar, count in zip(bars, counts):
                ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        str(count), ha='center', va='bottom')
        
        # Add overall title and metrics
        fig.suptitle(f"Backtest Results: {results['config']['name']}\n" +
                    f"Period: {results['start_date']} to {results['end_date']} | " +
                    f"Return: {results['total_return']:.2%} | " +
                    f"Sharpe: {results.get('sharpe_ratio', 0):.2f} | " +
                    f"Max DD: {results.get('max_drawdown', 0):.2%}",
                    fontsize=16, fontweight='bold')
        
        # Save the figure
        chart_file = Path(export_dir) / f"{strategy_name}_charts_{timestamp}.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        print(f"✅ AUDIT: Charts saved to {chart_file}")
        
        # Close the figure to free memory
        plt.close()
        
    except Exception as e:
        print(f"⚠️ AUDIT: Error creating charts: {e}")
        traceback.print_exc()


def plot_pnl_curve(trades: List[Dict], initial_capital: float = 10000) -> go.Figure:
    """Plot P&L curve over time with trade markers"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Create DataFrame from trades
    df = pd.DataFrame(trades)
    completed_trades = df[df['exit_date'].notna()].copy()
    
    if completed_trades.empty:
        return go.Figure().add_annotation(text="No completed trades to display", showarrow=False)
    
    # Sort by exit date
    completed_trades['exit_date'] = pd.to_datetime(completed_trades['exit_date'])
    completed_trades = completed_trades.sort_values('exit_date')
    
    # Calculate cumulative P&L
    completed_trades['cumulative_pnl'] = completed_trades['pnl'].cumsum()
    completed_trades['portfolio_value'] = initial_capital + completed_trades['cumulative_pnl']
    
    # Create figure
    fig = go.Figure()
    
    # Add portfolio value line
    fig.add_trace(go.Scatter(
        x=completed_trades['exit_date'],
        y=completed_trades['portfolio_value'],
        mode='lines+markers',
        name='Portfolio Value',
        line=dict(color='blue', width=2),
        marker=dict(size=8)
    ))
    
    # Add initial capital reference line
    fig.add_hline(y=initial_capital, line_dash="dash", line_color="gray",
                  annotation_text=f"Initial Capital: ${initial_capital:,.0f}")
    
    # Color markers based on profit/loss
    colors = ['green' if pnl > 0 else 'red' for pnl in completed_trades['pnl']]
    
    # Add trade markers
    fig.add_trace(go.Scatter(
        x=completed_trades['exit_date'],
        y=completed_trades['portfolio_value'],
        mode='markers',
        name='Trades',
        marker=dict(
            size=12,
            color=colors,
            symbol='circle',
            line=dict(width=2, color='DarkSlateGrey')
        ),
        text=[f"Trade {row['trade_id']}<br>P&L: ${row['pnl']:.2f}<br>Exit: {row['exit_reason']}" 
              for _, row in completed_trades.iterrows()],
        hovertemplate='%{text}<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title='Portfolio Value Over Time',
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        hovermode='closest',
        showlegend=True,
        template='plotly_white'
    )
    
    return fig


def plot_trade_markers(trades: List[Dict], show_underlying: bool = True) -> go.Figure:
    """Plot trade entry and exit points with underlying price"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    df = pd.DataFrame(trades)
    completed_trades = df[df['exit_date'].notna()].copy()
    
    if completed_trades.empty:
        return go.Figure().add_annotation(text="No completed trades to display", showarrow=False)
    
    # Convert dates
    completed_trades['entry_date'] = pd.to_datetime(completed_trades['entry_date'])
    completed_trades['exit_date'] = pd.to_datetime(completed_trades['exit_date'])
    
    # Create figure with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=('Option Prices', 'Underlying Price'),
        row_heights=[0.7, 0.3]
    )
    
    # Plot each trade
    for _, trade in completed_trades.iterrows():
        color = 'green' if trade['pnl'] > 0 else 'red'
        
        # Option price line
        # Handle both 'option_price' and 'entry_price' column names
        entry_price = trade.get('option_price', trade.get('entry_price', 0))
        
        fig.add_trace(go.Scatter(
            x=[trade['entry_date'], trade['exit_date']],
            y=[entry_price, trade['exit_price']],
            mode='lines+markers',
            name=f"Trade {trade['trade_id']}",
            line=dict(color=color, width=2),
            marker=dict(size=10),
            text=[f"Entry: ${entry_price:.2f}<br>Strike: ${trade['strike']:.0f}",
                  f"Exit: ${trade['exit_price']:.2f}<br>P&L: ${trade['pnl']:.2f}"],
            hovertemplate='%{text}<extra></extra>',
            showlegend=False
        ), row=1, col=1)
        
        # Entry marker
        fig.add_trace(go.Scatter(
            x=[trade['entry_date']],
            y=[trade['option_price']],
            mode='markers',
            marker=dict(symbol='triangle-up', size=12, color='blue'),
            name='Entry',
            showlegend=False,
            hovertext=f"Entry: {trade['entry_reason']}",
        ), row=1, col=1)
        
        # Exit marker
        fig.add_trace(go.Scatter(
            x=[trade['exit_date']],
            y=[trade['exit_price']],
            mode='markers',
            marker=dict(symbol='triangle-down', size=12, color=color),
            name='Exit',
            showlegend=False,
            hovertext=f"Exit: {trade['exit_reason']}",
        ), row=1, col=1)
        
        if show_underlying and 'underlying_at_entry' in trade:
            # Underlying price line
            fig.add_trace(go.Scatter(
                x=[trade['entry_date'], trade['exit_date']],
                y=[trade['underlying_at_entry'], trade['underlying_at_exit']],
                mode='lines+markers',
                line=dict(color='black', width=1, dash='dot'),
                showlegend=False,
                hovertemplate='Underlying: $%{y:.2f}<extra></extra>'
            ), row=2, col=1)
    
    # Update layout
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Option Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Underlying Price ($)", row=2, col=1)
    
    fig.update_layout(
        title='Trade Entry and Exit Points',
        hovermode='x unified',
        template='plotly_white',
        height=600
    )
    
    return fig


def plot_greeks_evolution(trades: List[Dict]) -> go.Figure:
    """Plot Greeks evolution for trades"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Create subplots for different Greeks
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Delta', 'Gamma', 'Theta', 'Vega'),
        shared_xaxes=True,
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    # Process trades with Greeks data
    trades_with_greeks = []
    for trade in trades:
        if 'greeks_history' in trade and trade['greeks_history']:
            trades_with_greeks.append(trade)
    
    if not trades_with_greeks:
        return go.Figure().add_annotation(text="No Greeks data available", showarrow=False)
    
    # Plot each trade's Greeks evolution
    for trade in trades_with_greeks[:10]:  # Limit to 10 trades for clarity
        greeks_history = trade['greeks_history']
        if not greeks_history:
            continue
            
        dates = [entry['date'] for entry in greeks_history]
        dates = pd.to_datetime(dates)
        
        color = 'green' if trade.get('pnl', 0) > 0 else 'red'
        name = f"Trade {trade['trade_id']}"
        
        # Delta
        deltas = [entry.get('delta', 0) for entry in greeks_history]
        if any(d for d in deltas if d is not None):
            fig.add_trace(go.Scatter(
                x=dates, y=deltas,
                mode='lines+markers',
                name=name,
                line=dict(color=color),
                showlegend=True
            ), row=1, col=1)
        
        # Gamma
        gammas = [entry.get('gamma', 0) for entry in greeks_history]
        if any(g for g in gammas if g is not None):
            fig.add_trace(go.Scatter(
                x=dates, y=gammas,
                mode='lines+markers',
                name=name,
                line=dict(color=color),
                showlegend=False
            ), row=1, col=2)
        
        # Theta
        thetas = [entry.get('theta', 0) for entry in greeks_history]
        if any(t for t in thetas if t is not None):
            fig.add_trace(go.Scatter(
                x=dates, y=thetas,
                mode='lines+markers',
                name=name,
                line=dict(color=color),
                showlegend=False
            ), row=2, col=1)
        
        # Vega
        vegas = [entry.get('vega', 0) for entry in greeks_history]
        if any(v for v in vegas if v is not None):
            fig.add_trace(go.Scatter(
                x=dates, y=vegas,
                mode='lines+markers',
                name=name,
                line=dict(color=color),
                showlegend=False
            ), row=2, col=2)
    
    # Update axes labels
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=2)
    
    fig.update_layout(
        title='Greeks Evolution Over Time',
        template='plotly_white',
        height=700,
        hovermode='x unified'
    )
    
    return fig


def plot_win_loss_distribution(trades: List[Dict]) -> go.Figure:
    """Plot distribution of wins and losses"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    df = pd.DataFrame(trades)
    completed_trades = df[df['exit_date'].notna()].copy()
    
    if completed_trades.empty:
        return go.Figure().add_annotation(text="No completed trades to display", showarrow=False)
    
    # Separate wins and losses
    wins = completed_trades[completed_trades['pnl'] > 0]['pnl_pct']
    losses = completed_trades[completed_trades['pnl'] <= 0]['pnl_pct']
    
    # Create figure
    fig = go.Figure()
    
    # Add histogram for wins
    if not wins.empty:
        fig.add_trace(go.Histogram(
            x=wins,
            name='Wins',
            marker_color='green',
            opacity=0.7,
            nbinsx=20
        ))
    
    # Add histogram for losses
    if not losses.empty:
        fig.add_trace(go.Histogram(
            x=losses,
            name='Losses',
            marker_color='red',
            opacity=0.7,
            nbinsx=20
        ))
    
    # Add statistics box
    total_trades = len(completed_trades)
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    avg_win = wins.mean() if not wins.empty else 0
    avg_loss = losses.mean() if not losses.empty else 0
    
    stats_text = f"""<b>Statistics:</b><br>
    Total Trades: {total_trades}<br>
    Win Rate: {win_rate:.1f}%<br>
    Avg Win: {avg_win:.1f}%<br>
    Avg Loss: {avg_loss:.1f}%<br>
    Best Trade: {completed_trades['pnl_pct'].max():.1f}%<br>
    Worst Trade: {completed_trades['pnl_pct'].min():.1f}%
    """
    
    fig.add_annotation(
        text=stats_text,
        xref="paper", yref="paper",
        x=0.95, y=0.95,
        showarrow=False,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1,
        font=dict(size=12),
        align="left"
    )
    
    # Update layout
    fig.update_layout(
        title='Win/Loss Distribution',
        xaxis_title='Return (%)',
        yaxis_title='Frequency',
        barmode='overlay',
        template='plotly_white',
        showlegend=True
    )
    
    return fig


def plot_strategy_heatmap(trades: List[Dict]) -> go.Figure:
    """Plot monthly returns heatmap"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    df = pd.DataFrame(trades)
    completed_trades = df[df['exit_date'].notna()].copy()
    
    if completed_trades.empty:
        return go.Figure().add_annotation(text="No completed trades to display", showarrow=False)
    
    # Convert dates and extract month/year
    completed_trades['exit_date'] = pd.to_datetime(completed_trades['exit_date'])
    completed_trades['year'] = completed_trades['exit_date'].dt.year
    completed_trades['month'] = completed_trades['exit_date'].dt.month
    completed_trades['month_name'] = completed_trades['exit_date'].dt.strftime('%b')
    
    # Calculate monthly returns
    monthly_returns = completed_trades.groupby(['year', 'month', 'month_name'])['pnl'].sum().reset_index()
    
    # Pivot for heatmap
    pivot_table = monthly_returns.pivot(index='year', columns='month_name', values='pnl')
    
    # Ensure all months are present
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    pivot_table = pivot_table.reindex(columns=month_order)
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=pivot_table.columns,
        y=pivot_table.index,
        colorscale='RdYlGn',
        zmid=0,
        text=[[f'${val:.0f}' if pd.notna(val) else '' for val in row] for row in pivot_table.values],
        texttemplate='%{text}',
        textfont={"size": 10},
        hoverongaps=False,
        hovertemplate='%{y} %{x}<br>P&L: $%{z:.2f}<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title='Monthly P&L Heatmap',
        xaxis_title='Month',
        yaxis_title='Year',
        template='plotly_white',
        height=400
    )
    
    return fig


def plot_delta_histogram(trades: List[Dict]) -> go.Figure:
    """Plot enhanced histogram of actual delta values vs target bands"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Extract delta data
    deltas = []
    targets = []
    compliant_deltas = []
    non_compliant_deltas = []
    
    for trade in trades:
        if 'delta_actual' in trade and trade['delta_actual'] is not None:
            delta = abs(trade['delta_actual'])  # Use absolute value
            deltas.append(delta)
            
            if trade.get('delta_compliant', False):
                compliant_deltas.append(delta)
            else:
                non_compliant_deltas.append(delta)
                
            if 'delta_target' in trade:
                targets.append(trade['delta_target'])
    
    if not deltas:
        return go.Figure().add_annotation(text="No delta data available", showarrow=False)
    
    # Create figure
    fig = go.Figure()
    
    # Get target and tolerance
    target = targets[0] if targets else 0.30
    tolerance = trades[0].get('delta_tolerance', 0.05) if trades else 0.05
    
    # Add shaded target zone
    fig.add_vrect(
        x0=target - tolerance,
        x1=target + tolerance,
        fillcolor="green",
        opacity=0.2,
        annotation_text="Target Zone",
        annotation_position="top",
        annotation=dict(font=dict(size=12, color="green"))
    )
    
    # Add histogram with custom bins to align with target zone
    bin_size = 0.025
    bins = [i * bin_size for i in range(int(1/bin_size) + 1)]
    
    # Color bars based on compliance
    colors = []
    for i in range(len(bins) - 1):
        bin_center = (bins[i] + bins[i+1]) / 2
        if target - tolerance <= bin_center <= target + tolerance:
            colors.append('green')
        else:
            colors.append('red')
    
    fig.add_trace(go.Histogram(
        x=deltas,
        name='Actual Delta',
        xbins=dict(start=0, end=1, size=bin_size),
        marker_color='blue',
        opacity=0.7
    ))
    
    # Add mean and median lines
    mean_delta = np.mean(deltas)
    median_delta = np.median(deltas)
    
    fig.add_vline(x=mean_delta, line_dash="dash", line_color="purple", 
                  annotation_text=f"Mean: {mean_delta:.3f}")
    fig.add_vline(x=median_delta, line_dash="dot", line_color="orange", 
                  annotation_text=f"Median: {median_delta:.3f}")
    
    # Calculate statistics
    std_delta = np.std(deltas)
    compliance_pct = (len(compliant_deltas) / len(deltas) * 100) if deltas else 0
    
    # Add statistics box
    stats_text = f"""<b>Statistics:</b>
    Mean: {mean_delta:.3f}
    Median: {median_delta:.3f}
    Std Dev: {std_delta:.3f}
    Target: {target:.2f} ± {tolerance:.2f}
    Compliance: {compliance_pct:.1f}%
    Total Trades: {len(deltas)}"""
    
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.98, y=0.98,
        text=stats_text,
        showarrow=False,
        bordercolor="black",
        borderwidth=1,
        bgcolor="white",
        align="left",
        xanchor="right",
        yanchor="top"
    )
    
    fig.update_layout(
        title=f'Delta Distribution - {compliance_pct:.1f}% Compliant<br><sub>Green zone = Target range</sub>',
        xaxis_title='Delta',
        yaxis_title='Count',
        showlegend=True,
        template='plotly_white',
        height=500
    )
    
    return fig


def plot_dte_histogram(trades: List[Dict]) -> go.Figure:
    """Plot enhanced histogram of actual DTE values vs target bands"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Extract DTE data
    dtes = []
    compliant_dtes = []
    non_compliant_dtes = []
    
    for trade in trades:
        if 'dte_actual' in trade:
            dte = trade['dte_actual']
            dtes.append(dte)
            
            if trade.get('dte_compliant', False):
                compliant_dtes.append(dte)
            else:
                non_compliant_dtes.append(dte)
    
    if not dtes:
        return go.Figure().add_annotation(text="No DTE data available", showarrow=False)
    
    # Create figure
    fig = go.Figure()
    
    # Get target range
    dte_min = trades[0].get('dte_min', 30) if trades else 30
    dte_max = trades[0].get('dte_max', 60) if trades else 60
    dte_target = trades[0].get('dte_target', 45) if trades else 45
    
    # Add shaded target zone
    fig.add_vrect(
        x0=dte_min,
        x1=dte_max,
        fillcolor="blue",
        opacity=0.2,
        annotation_text="Target Zone",
        annotation_position="top",
        annotation=dict(font=dict(size=12, color="blue"))
    )
    
    # Add histogram with appropriate bins
    bin_size = 5  # 5-day bins
    min_dte = min(dtes + [0])
    max_dte = max(dtes + [90])
    bins = list(range(0, int(max_dte) + bin_size, bin_size))
    
    fig.add_trace(go.Histogram(
        x=dtes,
        name='Actual DTE',
        xbins=dict(start=0, end=max_dte, size=bin_size),
        marker_color='purple',
        opacity=0.7
    ))
    
    # Add mean and median lines
    mean_dte = np.mean(dtes)
    median_dte = np.median(dtes)
    
    fig.add_vline(x=mean_dte, line_dash="dash", line_color="purple", 
                  annotation_text=f"Mean: {mean_dte:.1f}")
    fig.add_vline(x=median_dte, line_dash="dot", line_color="orange", 
                  annotation_text=f"Median: {median_dte:.0f}")
    fig.add_vline(x=dte_target, line_dash="solid", line_color="green", 
                  annotation_text=f"Target: {dte_target}")
    
    # Calculate statistics
    std_dte = np.std(dtes)
    compliance_pct = (len(compliant_dtes) / len(dtes) * 100) if dtes else 0
    
    # Add statistics box
    stats_text = f"""<b>Statistics:</b>
    Mean: {mean_dte:.1f}
    Median: {median_dte:.0f}
    Std Dev: {std_dte:.1f}
    Target: {dte_min}-{dte_max} days
    Compliance: {compliance_pct:.1f}%
    Total Trades: {len(dtes)}"""
    
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.98, y=0.98,
        text=stats_text,
        showarrow=False,
        bordercolor="black",
        borderwidth=1,
        bgcolor="white",
        align="left",
        xanchor="right",
        yanchor="top"
    )
    
    fig.update_layout(
        title=f'DTE Distribution - {compliance_pct:.1f}% Compliant<br><sub>Blue zone = Target range</sub>',
        xaxis_title='Days to Expiration',
        yaxis_title='Count',
        showlegend=True,
        template='plotly_white',
        height=500,
        xaxis=dict(range=[0, max(90, max_dte + 10)])
    )
    
    return fig


def plot_compliance_scorecard(compliance_data: Dict) -> go.Figure:
    """Create visual compliance scorecard"""
    fig = go.Figure()
    
    # Create scorecard data
    categories = ['Overall', 'Delta', 'DTE', 'Entry', 'Exit']
    scores = [
        compliance_data.get('overall_score', 0),
        compliance_data.get('delta_compliance', 0),
        compliance_data.get('dte_compliance', 0),
        compliance_data.get('entry_compliance', 0),
        compliance_data.get('exit_compliance', 0)
    ]
    
    # Color based on score
    colors = ['green' if s >= 90 else 'yellow' if s >= 70 else 'red' for s in scores]
    
    # Create bar chart
    fig.add_trace(go.Bar(
        x=categories,
        y=scores,
        text=[f'{s:.1f}%' for s in scores],
        textposition='auto',
        marker_color=colors,
        name='Compliance Score'
    ))
    
    # Add threshold lines
    fig.add_hline(y=90, line_dash="dash", line_color="green", 
                  annotation_text="Excellent (90%)")
    fig.add_hline(y=70, line_dash="dash", line_color="orange", 
                  annotation_text="Acceptable (70%)")
    
    # Add summary stats
    total_trades = compliance_data.get('total_trades', 0)
    compliant_trades = compliance_data.get('compliant_trades', 0)
    
    fig.update_layout(
        title=f'Compliance Scorecard - {compliant_trades}/{total_trades} Fully Compliant Trades',
        xaxis_title='Category',
        yaxis_title='Compliance %',
        yaxis_range=[0, 105],
        showlegend=False,
        template='plotly_white'
    )
    
    return fig


def plot_option_coverage_heatmap(trades: List[Dict]) -> go.Figure:
    """Create heatmap showing option selection coverage across delta and DTE ranges"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Extract delta and DTE data
    deltas = []
    dtes = []
    
    for trade in trades:
        if 'delta_actual' in trade and trade['delta_actual'] is not None:
            deltas.append(abs(trade['delta_actual']))  # Use absolute value for puts
        if 'dte_actual' in trade and trade['dte_actual'] is not None:
            dtes.append(trade['dte_actual'])
    
    if not deltas or not dtes:
        return go.Figure().add_annotation(text="No delta/DTE data available", showarrow=False)
    
    # Create bins
    delta_bins = [0, 0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 1.0]
    dte_bins = [0, 7, 14, 21, 30, 45, 60, 90, 180]
    
    # Create 2D histogram data
    import numpy as np
    hist, delta_edges, dte_edges = np.histogram2d(deltas, dtes, bins=[delta_bins, dte_bins])
    
    # Create labels for bins
    delta_labels = [f"{delta_bins[i]:.2f}-{delta_bins[i+1]:.2f}" for i in range(len(delta_bins)-1)]
    dte_labels = [f"{dte_bins[i]}-{dte_bins[i+1]}" for i in range(len(dte_bins)-1)]
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=hist.T,  # Transpose to match x/y orientation
        x=delta_labels,
        y=dte_labels,
        colorscale='Viridis',
        text=hist.T.astype(int),
        texttemplate='%{text}',
        textfont={"size": 10},
        hoverongaps=False,
        hovertemplate='Delta: %{x}<br>DTE: %{y}<br>Trades: %{z}<extra></extra>'
    ))
    
    # Add target zone rectangle (assuming 0.25-0.35 delta, 30-60 DTE)
    # Find indices for target zones
    target_delta_start = next(i for i, label in enumerate(delta_labels) if "0.25" in label)
    target_delta_end = next(i for i, label in enumerate(delta_labels) if "0.35" in label) + 1
    target_dte_start = next(i for i, label in enumerate(dte_labels) if "30-" in label or "-30" in label)
    target_dte_end = next(i for i, label in enumerate(dte_labels) if "60-" in label or "-60" in label) + 1
    
    # Add rectangle for target zone
    fig.add_shape(
        type="rect",
        x0=target_delta_start - 0.5, x1=target_delta_end - 0.5,
        y0=target_dte_start - 0.5, y1=target_dte_end - 0.5,
        line=dict(color="red", width=3, dash="dash"),
    )
    
    # Add annotation for target zone
    fig.add_annotation(
        x=(target_delta_start + target_delta_end - 1) / 2,
        y=(target_dte_start + target_dte_end - 1) / 2,
        text="Target<br>Zone",
        showarrow=False,
        font=dict(color="red", size=12, family="Arial Black"),
        bgcolor="rgba(255,255,255,0.8)"
    )
    
    # Update layout
    fig.update_layout(
        title='Option Selection Coverage Heatmap<br><sub>Number of trades by Delta and DTE ranges</sub>',
        xaxis_title='Delta Range',
        yaxis_title='DTE Range (Days)',
        template='plotly_white',
        height=600
    )
    
    return fig


def plot_delta_coverage_time_series(trades: List[Dict]) -> go.Figure:
    """Plot delta values over time with target bands"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Extract data
    dates = []
    deltas = []
    compliant = []
    
    for trade in trades:
        if 'entry_date' in trade and 'delta_actual' in trade and trade['delta_actual'] is not None:
            dates.append(pd.to_datetime(trade['entry_date']))
            deltas.append(abs(trade['delta_actual']))
            compliant.append(trade.get('delta_compliant', False))
    
    if not dates:
        return go.Figure().add_annotation(text="No delta time series data available", showarrow=False)
    
    # Sort by date
    sorted_data = sorted(zip(dates, deltas, compliant))
    dates, deltas, compliant = zip(*sorted_data)
    
    # Create figure
    fig = go.Figure()
    
    # Add scatter plot with color coding
    colors = ['green' if c else 'red' for c in compliant]
    fig.add_trace(go.Scatter(
        x=dates,
        y=deltas,
        mode='markers+lines',
        name='Actual Delta',
        marker=dict(color=colors, size=8),
        line=dict(color='gray', width=1),
        hovertemplate='Date: %{x}<br>Delta: %{y:.3f}<extra></extra>'
    ))
    
    # Add target band (assuming 0.25-0.35 from config)
    target_delta = 0.30
    tolerance = 0.05
    
    # Add shaded target area
    fig.add_shape(
        type="rect",
        x0=dates[0], x1=dates[-1],
        y0=target_delta - tolerance, y1=target_delta + tolerance,
        fillcolor="green", opacity=0.2,
        line=dict(width=0),
    )
    
    # Add target lines
    fig.add_hline(y=target_delta, line_dash="dash", line_color="green", 
                  annotation_text=f"Target: {target_delta:.2f}")
    fig.add_hline(y=target_delta - tolerance, line_dash="dot", line_color="orange", 
                  annotation_text=f"Min: {target_delta-tolerance:.2f}")
    fig.add_hline(y=target_delta + tolerance, line_dash="dot", line_color="orange", 
                  annotation_text=f"Max: {target_delta+tolerance:.2f}")
    
    # Calculate statistics
    mean_delta = np.mean(deltas)
    std_delta = np.std(deltas)
    compliance_rate = sum(compliant) / len(compliant) * 100
    
    # Add statistics box
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        text=f"Mean: {mean_delta:.3f}<br>Std: {std_delta:.3f}<br>Compliance: {compliance_rate:.1f}%",
        showarrow=False,
        bordercolor="black",
        borderwidth=1,
        bgcolor="white",
        align="left"
    )
    
    fig.update_layout(
        title='Delta Coverage Over Time<br><sub>Green = Compliant, Red = Non-compliant</sub>',
        xaxis_title='Date',
        yaxis_title='Delta',
        template='plotly_white',
        hovermode='x unified',
        height=500
    )
    
    return fig


def plot_dte_coverage_time_series(trades: List[Dict]) -> go.Figure:
    """Plot DTE values over time with target bands"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Extract data
    dates = []
    dtes = []
    compliant = []
    
    for trade in trades:
        if 'entry_date' in trade and 'dte_actual' in trade:
            dates.append(pd.to_datetime(trade['entry_date']))
            dtes.append(trade['dte_actual'])
            compliant.append(trade.get('dte_compliant', False))
    
    if not dates:
        return go.Figure().add_annotation(text="No DTE time series data available", showarrow=False)
    
    # Sort by date
    sorted_data = sorted(zip(dates, dtes, compliant))
    dates, dtes, compliant = zip(*sorted_data)
    
    # Create figure
    fig = go.Figure()
    
    # Add scatter plot with color coding
    colors = ['green' if c else 'red' for c in compliant]
    fig.add_trace(go.Scatter(
        x=dates,
        y=dtes,
        mode='markers+lines',
        name='Actual DTE',
        marker=dict(color=colors, size=8),
        line=dict(color='gray', width=1),
        hovertemplate='Date: %{x}<br>DTE: %{y}<extra></extra>'
    ))
    
    # Add target band (assuming 30-60 from config)
    min_dte = 30
    max_dte = 60
    target_dte = 45
    
    # Add shaded target area
    fig.add_shape(
        type="rect",
        x0=dates[0], x1=dates[-1],
        y0=min_dte, y1=max_dte,
        fillcolor="blue", opacity=0.2,
        line=dict(width=0),
    )
    
    # Add target lines
    fig.add_hline(y=target_dte, line_dash="dash", line_color="blue", 
                  annotation_text=f"Target: {target_dte}")
    fig.add_hline(y=min_dte, line_dash="dot", line_color="orange", 
                  annotation_text=f"Min: {min_dte}")
    fig.add_hline(y=max_dte, line_dash="dot", line_color="orange", 
                  annotation_text=f"Max: {max_dte}")
    
    # Calculate statistics
    mean_dte = np.mean(dtes)
    std_dte = np.std(dtes)
    compliance_rate = sum(compliant) / len(compliant) * 100
    
    # Add statistics box
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        text=f"Mean: {mean_dte:.1f}<br>Std: {std_dte:.1f}<br>Compliance: {compliance_rate:.1f}%",
        showarrow=False,
        bordercolor="black",
        borderwidth=1,
        bgcolor="white",
        align="left"
    )
    
    fig.update_layout(
        title='DTE Coverage Over Time<br><sub>Green = Compliant, Red = Non-compliant</sub>',
        xaxis_title='Date',
        yaxis_title='Days to Expiration',
        template='plotly_white',
        hovermode='x unified',
        height=500
    )
    
    return fig


def plot_exit_reason_distribution(trades: List[Dict]) -> go.Figure:
    """Create pie chart of exit reasons"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Count exit reasons
    exit_reasons = {}
    for trade in trades:
        if 'exit_reason' in trade and trade['exit_reason']:
            reason = trade['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
    
    if not exit_reasons:
        return go.Figure().add_annotation(text="No exit data available", showarrow=False)
    
    # Create pie chart
    fig = go.Figure(data=[go.Pie(
        labels=list(exit_reasons.keys()),
        values=list(exit_reasons.values()),
        hole=0.3,
        textinfo='label+percent',
        marker=dict(
            colors=px.colors.qualitative.Set3[:len(exit_reasons)]
        )
    )])
    
    # Add total trades in center
    total_exits = sum(exit_reasons.values())
    fig.add_annotation(
        text=f"{total_exits}<br>Exits",
        showarrow=False,
        font=dict(size=20)
    )
    
    fig.update_layout(
        title='Exit Reason Distribution<br><sub>How trades are exited</sub>',
        template='plotly_white',
        height=500
    )
    
    return fig


def plot_exit_efficiency_heatmap(trades: List[Dict]) -> go.Figure:
    """Create heatmap showing exit efficiency by reason and days held"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Prepare data
    exit_data = []
    for trade in trades:
        if all(key in trade for key in ['exit_reason', 'days_held', 'pnl_pct']):
            exit_data.append({
                'exit_reason': trade['exit_reason'],
                'days_held_bin': min(trade['days_held'] // 5 * 5, 30),  # 5-day bins, cap at 30+
                'return': trade['pnl_pct'] * 100  # Convert to percentage
            })
    
    if not exit_data:
        return go.Figure().add_annotation(text="No exit efficiency data available", showarrow=False)
    
    # Create DataFrame and pivot
    df = pd.DataFrame(exit_data)
    pivot = df.pivot_table(
        values='return',
        index='exit_reason',
        columns='days_held_bin',
        aggfunc='mean'
    )
    
    # Ensure all day bins are present
    all_bins = list(range(0, 35, 5))
    bin_labels = [f"{b}-{b+4}" if b < 30 else "30+" for b in all_bins]
    pivot = pivot.reindex(columns=all_bins, fill_value=np.nan)
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=bin_labels,
        y=pivot.index.tolist(),
        colorscale='RdYlGn',
        zmid=0,
        text=np.round(pivot.values, 1),
        texttemplate='%{text}%',
        textfont={"size": 10},
        hoverongaps=False,
        hovertemplate='Exit: %{y}<br>Days: %{x}<br>Avg Return: %{z:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title='Exit Efficiency Heatmap<br><sub>Average returns by exit type and holding period</sub>',
        xaxis_title='Days Held',
        yaxis_title='Exit Reason',
        template='plotly_white',
        height=400
    )
    
    return fig


def plot_available_vs_selected_options(selection_data: List[Dict]) -> go.Figure:
    """Plot all available options vs selected ones to show coverage"""
    if not selection_data:
        return go.Figure().add_annotation(text="No selection data available", showarrow=False)
    
    # Extract data for all options and selected options
    all_deltas = []
    all_dtes = []
    selected_deltas = []
    selected_dtes = []
    
    for entry in selection_data:
        if 'available_options' in entry:
            for opt in entry['available_options']:
                all_deltas.append(abs(opt.get('delta', 0)))
                all_dtes.append(opt.get('dte', 0))
        
        if 'selected_option' in entry and entry['selected_option']:
            selected_deltas.append(abs(entry['selected_option'].get('delta', 0)))
            selected_dtes.append(entry['selected_option'].get('dte', 0))
    
    if not all_deltas:
        return go.Figure().add_annotation(text="No options data available", showarrow=False)
    
    # Create figure
    fig = go.Figure()
    
    # Plot all available options as gray dots
    fig.add_trace(go.Scatter(
        x=all_deltas,
        y=all_dtes,
        mode='markers',
        name='Available Options',
        marker=dict(
            color='lightgray',
            size=3,
            opacity=0.3
        ),
        hovertemplate='Delta: %{x:.3f}<br>DTE: %{y}<extra></extra>'
    ))
    
    # Plot selected options as colored dots
    if selected_deltas:
        fig.add_trace(go.Scatter(
            x=selected_deltas,
            y=selected_dtes,
            mode='markers',
            name='Selected Options',
            marker=dict(
                color='red',
                size=10,
                symbol='star'
            ),
            hovertemplate='Selected<br>Delta: %{x:.3f}<br>DTE: %{y}<extra></extra>'
        ))
    
    # Add target zone rectangle
    fig.add_shape(
        type="rect",
        x0=0.25, x1=0.35,  # Delta range
        y0=30, y1=60,      # DTE range
        fillcolor="green",
        opacity=0.1,
        line=dict(color="green", width=2, dash="dash"),
    )
    
    # Add annotation for target zone
    fig.add_annotation(
        x=0.30, y=45,
        text="Target Zone",
        showarrow=False,
        font=dict(color="green", size=14),
        bgcolor="rgba(255,255,255,0.8)"
    )
    
    # Update layout
    fig.update_layout(
        title='Available vs Selected Options<br><sub>Gray dots: All available options | Red stars: Selected options</sub>',
        xaxis_title='Delta',
        yaxis_title='Days to Expiration (DTE)',
        template='plotly_white',
        height=600,
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, 120])
    )
    
    return fig


def create_summary_dashboard(trades: List[Dict], initial_capital: float = 10000) -> go.Figure:
    """Create a comprehensive dashboard with multiple charts"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('P&L Curve', 'Win/Loss Distribution', 'Trade Sizes', 'Exit Reasons'),
        specs=[[{"type": "scatter"}, {"type": "histogram"}],
               [{"type": "bar"}, {"type": "pie"}]],
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    df = pd.DataFrame(trades)
    completed_trades = df[df['exit_date'].notna()].copy()
    
    if not completed_trades.empty:
        try:
            # 1. P&L Curve (simplified)
            if 'exit_date' in completed_trades.columns and 'pnl' in completed_trades.columns:
                completed_trades['exit_date'] = pd.to_datetime(completed_trades['exit_date'])
                completed_trades = completed_trades.sort_values('exit_date')
                completed_trades['cumulative_pnl'] = completed_trades['pnl'].cumsum()
                
                fig.add_trace(go.Scatter(
                    x=completed_trades['exit_date'],
                    y=initial_capital + completed_trades['cumulative_pnl'],
                    mode='lines+markers',
                    name='Portfolio Value',
                    line=dict(color='blue', width=2)
                ), row=1, col=1)
        except Exception as e:
            print(f"Warning: Could not create P&L curve: {e}")
        
        try:
            # 2. Win/Loss Distribution
            if 'pnl_pct' in completed_trades.columns:
                fig.add_trace(go.Histogram(
                    x=completed_trades['pnl_pct'],
                    marker_color=['green' if x > 0 else 'red' for x in completed_trades['pnl_pct']],
                    name='Returns',
                    nbinsx=20
                ), row=1, col=2)
        except Exception as e:
            print(f"Warning: Could not create win/loss distribution: {e}")
        
        try:
            # 3. Trade Sizes (cost)
            # Handle both 'cost' and 'entry_cost' column names
            cost_col = None
            if 'cost' in completed_trades.columns:
                cost_col = 'cost'
            elif 'entry_cost' in completed_trades.columns:
                cost_col = 'entry_cost'
            
            if cost_col and 'trade_id' in completed_trades.columns:
                trade_sizes = completed_trades.groupby('trade_id')[cost_col].first().sort_values(ascending=False).head(10)
                fig.add_trace(go.Bar(
                    x=[f"Trade {tid}" for tid in trade_sizes.index],
                    y=trade_sizes.values,
                    name='Trade Size',
                    marker_color='lightblue'
                ), row=2, col=1)
        except Exception as e:
            print(f"Warning: Could not create trade sizes chart: {e}")
        
        try:
            # 4. Exit Reasons
            if 'exit_reason' in completed_trades.columns:
                exit_reasons = completed_trades['exit_reason'].value_counts()
                fig.add_trace(go.Pie(
                    labels=exit_reasons.index,
                    values=exit_reasons.values,
                    name='Exit Reasons'
                ), row=2, col=2)
        except Exception as e:
            print(f"Warning: Could not create exit reasons chart: {e}")
    
    # Update layout
    fig.update_layout(
        title='Trading Dashboard Summary',
        showlegend=False,
        template='plotly_white',
        height=800
    )
    
    # Update axes
    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
    fig.update_xaxes(title_text="Return (%)", row=1, col=2)
    fig.update_yaxes(title_text="Frequency", row=1, col=2)
    fig.update_xaxes(title_text="Trade", row=2, col=1)
    fig.update_yaxes(title_text="Cost ($)", row=2, col=1)
    
    return fig


# ===== ENHANCED TECHNICAL ANALYSIS VISUALIZATIONS =====

def plot_technical_indicators_dashboard(trades: List[Dict]) -> go.Figure:
    """Create comprehensive technical indicators dashboard"""
    if not trades:
        return go.Figure().add_annotation(text="No trades to display", showarrow=False)
    
    # Filter trades with Greeks history
    trades_with_history = [t for t in trades if 'greeks_history' in t and t['greeks_history']]
    if not trades_with_history:
        return go.Figure().add_annotation(text="No technical data available", showarrow=False)
    
    # Create subplots
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=('RSI Evolution', 'Bollinger Bands Position', 
                       'EMA Alignment Over Time', 'MACD Signals',
                       'Maximum Excursion Analysis', 'Volatility Regime'),
        specs=[[{"secondary_y": True}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )