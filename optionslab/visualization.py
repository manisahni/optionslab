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
        fig.add_trace(go.Scatter(
            x=[trade['entry_date'], trade['exit_date']],
            y=[trade['option_price'], trade['exit_price']],
            mode='lines+markers',
            name=f"Trade {trade['trade_id']}",
            line=dict(color=color, width=2),
            marker=dict(size=10),
            text=[f"Entry: ${trade['option_price']:.2f}<br>Strike: ${trade['strike']:.0f}",
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
        # 1. P&L Curve (simplified)
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
        
        # 2. Win/Loss Distribution
        fig.add_trace(go.Histogram(
            x=completed_trades['pnl_pct'],
            marker_color=['green' if x > 0 else 'red' for x in completed_trades['pnl_pct']],
            name='Returns',
            nbinsx=20
        ), row=1, col=2)
        
        # 3. Trade Sizes (cost)
        trade_sizes = completed_trades.groupby('trade_id')['cost'].first().sort_values(ascending=False).head(10)
        fig.add_trace(go.Bar(
            x=[f"Trade {tid}" for tid in trade_sizes.index],
            y=trade_sizes.values,
            name='Trade Size',
            marker_color='lightblue'
        ), row=2, col=1)
        
        # 4. Exit Reasons
        exit_reasons = completed_trades['exit_reason'].value_counts()
        fig.add_trace(go.Pie(
            labels=exit_reasons.index,
            values=exit_reasons.values,
            name='Exit Reasons'
        ), row=2, col=2)
    
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