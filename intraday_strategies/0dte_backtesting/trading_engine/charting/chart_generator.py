import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time


class Visualizer:
    """
    Create interactive visualizations for trading analysis
    """
    
    def __init__(self):
        self.default_template = "plotly_white"
        self.color_scheme = {
            'bullish': '#00CC88',
            'bearish': '#FF3737',
            'neutral': '#888888',
            'orb_high': '#2E86AB',
            'orb_low': '#A23B72',
            'entry': '#F18F01',
            'target': '#00CC88',
            'stop': '#FF3737'
        }
        
    def plot_orb_day(self, df_day: pd.DataFrame, orb: Dict, 
                     breakout: Optional[Dict] = None, 
                     trade_result: Optional[Dict] = None) -> go.Figure:
        """
        Plot a single day's ORB setup with breakout and trade results
        """
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=('Price Action', 'Volume')
        )
        
        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df_day['date'],
                open=df_day['open'],
                high=df_day['high'],
                low=df_day['low'],
                close=df_day['close'],
                name='SPY',
                increasing_line_color=self.color_scheme['bullish'],
                decreasing_line_color=self.color_scheme['bearish']
            ),
            row=1, col=1
        )
        
        # ORB High line
        fig.add_trace(
            go.Scatter(
                x=[orb['start_time'], df_day['date'].iloc[-1]],
                y=[orb['high'], orb['high']],
                mode='lines',
                line=dict(color=self.color_scheme['orb_high'], width=2, dash='dash'),
                name=f"ORB High ({orb['high']:.2f})"
            ),
            row=1, col=1
        )
        
        # ORB Low line
        fig.add_trace(
            go.Scatter(
                x=[orb['start_time'], df_day['date'].iloc[-1]],
                y=[orb['low'], orb['low']],
                mode='lines',
                line=dict(color=self.color_scheme['orb_low'], width=2, dash='dash'),
                name=f"ORB Low ({orb['low']:.2f})"
            ),
            row=1, col=1
        )
        
        # Shade ORB period
        fig.add_vrect(
            x0=orb['start_time'], x1=orb['end_time'],
            fillcolor="LightGray", opacity=0.3,
            layer="below", line_width=0,
            row=1, col=1
        )
        
        # Add breakout marker if present
        if breakout:
            fig.add_trace(
                go.Scatter(
                    x=[breakout['time']],
                    y=[breakout['price']],
                    mode='markers',
                    marker=dict(
                        size=12,
                        color=self.color_scheme['entry'],
                        symbol='triangle-up' if breakout['type'] == 'long' else 'triangle-down'
                    ),
                    name=f"{breakout['type'].title()} Entry"
                ),
                row=1, col=1
            )
            
        # Add trade exit if present
        if trade_result:
            # Target and stop lines
            fig.add_hline(
                y=trade_result['target'],
                line_dash="dot",
                line_color=self.color_scheme['target'],
                annotation_text="Target",
                row=1, col=1
            )
            fig.add_hline(
                y=trade_result['stop_loss'],
                line_dash="dot",
                line_color=self.color_scheme['stop'],
                annotation_text="Stop",
                row=1, col=1
            )
            
            # Exit marker
            exit_color = self.color_scheme['target'] if trade_result['outcome'] == 'target' else self.color_scheme['stop']
            fig.add_trace(
                go.Scatter(
                    x=[trade_result['exit_time']],
                    y=[trade_result['exit_price']],
                    mode='markers',
                    marker=dict(size=12, color=exit_color, symbol='square'),
                    name=f"Exit ({trade_result['outcome']})"
                ),
                row=1, col=1
            )
        
        # Volume bars
        colors = ['green' if df_day.iloc[i]['close'] >= df_day.iloc[i]['open'] else 'red' 
                  for i in range(len(df_day))]
        fig.add_trace(
            go.Bar(
                x=df_day['date'],
                y=df_day['volume'],
                marker_color=colors,
                name='Volume',
                showlegend=False
            ),
            row=2, col=1
        )
        
        # Update layout
        title_date = df_day['date'].iloc[0].strftime('%Y-%m-%d')
        title_text = f"ORB Analysis - {title_date}"
        if trade_result:
            title_text += f" | P&L: ${trade_result['pnl']:.2f} ({trade_result['pnl_pct']:.2f}%)"
            
        fig.update_layout(
            title=title_text,
            template=self.default_template,
            xaxis_rangeslider_visible=False,
            height=600
        )
        
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        
        return fig
    
    def plot_backtest_summary(self, results_df: pd.DataFrame, stats: Dict) -> go.Figure:
        """
        Plot backtest summary with equity curve and statistics
        """
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Cumulative P&L', 'Win Rate by Month',
                'P&L Distribution', 'Outcome Distribution',
                'Daily P&L', 'ORB Range Analysis'
            ),
            specs=[[{"type": "xy"}, {"type": "xy"}],
                   [{"type": "xy"}, {"type": "domain"}],
                   [{"type": "xy"}, {"type": "xy"}]],
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        # Filter to only trades
        trades = results_df[results_df['breakout'] == True].copy()
        
        if not trades.empty:
            # 1. Cumulative P&L
            trades['cumulative_pnl'] = trades['pnl'].cumsum()
            fig.add_trace(
                go.Scatter(
                    x=trades['date'],
                    y=trades['cumulative_pnl'],
                    mode='lines',
                    line=dict(color=self.color_scheme['bullish'], width=2),
                    name='Cumulative P&L'
                ),
                row=1, col=1
            )
            
            # 2. Win rate by month
            trades['month'] = pd.to_datetime(trades['date']).dt.to_period('M')
            monthly_stats = trades.groupby('month').agg({
                'outcome': lambda x: (x == 'target').sum() / len(x) * 100
            }).reset_index()
            monthly_stats['month'] = monthly_stats['month'].astype(str)
            
            fig.add_trace(
                go.Bar(
                    x=monthly_stats['month'],
                    y=monthly_stats['outcome'],
                    marker_color=self.color_scheme['bullish'],
                    name='Win Rate %'
                ),
                row=1, col=2
            )
            
            # 3. P&L Distribution
            fig.add_trace(
                go.Histogram(
                    x=trades['pnl'],
                    nbinsx=20,
                    marker_color=self.color_scheme['neutral'],
                    name='P&L Distribution'
                ),
                row=2, col=1
            )
            
            # 4. Outcome Distribution
            outcome_counts = trades['outcome'].value_counts()
            fig.add_trace(
                go.Pie(
                    labels=outcome_counts.index,
                    values=outcome_counts.values,
                    marker_colors=[
                        self.color_scheme['target'] if x == 'target' else self.color_scheme['stop'] 
                        for x in outcome_counts.index
                    ],
                    name='Outcomes'
                ),
                row=2, col=2
            )
            
            # 5. Daily P&L
            fig.add_trace(
                go.Bar(
                    x=trades['date'],
                    y=trades['pnl'],
                    marker_color=[self.color_scheme['bullish'] if x > 0 else self.color_scheme['bearish'] 
                                 for x in trades['pnl']],
                    name='Daily P&L'
                ),
                row=3, col=1
            )
            
            # 6. ORB Range vs Success
            successful_trades = trades[trades['outcome'] == 'target']
            failed_trades = trades[trades['outcome'] == 'stop_loss']
            
            fig.add_trace(
                go.Box(
                    y=successful_trades['orb_range'],
                    name='Winners',
                    marker_color=self.color_scheme['bullish']
                ),
                row=3, col=2
            )
            fig.add_trace(
                go.Box(
                    y=failed_trades['orb_range'],
                    name='Losers',
                    marker_color=self.color_scheme['bearish']
                ),
                row=3, col=2
            )
        
        # Update layout with statistics
        title_text = f"ORB Backtest Results | Win Rate: {stats['win_rate']:.1%} | Total P&L: ${stats['total_pnl']:.2f}"
        fig.update_layout(
            title=title_text,
            template=self.default_template,
            height=900,
            showlegend=False
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="Date", row=1, col=1)
        fig.update_yaxes(title_text="Cumulative P&L ($)", row=1, col=1)
        fig.update_xaxes(title_text="Month", row=1, col=2)
        fig.update_yaxes(title_text="Win Rate (%)", row=1, col=2)
        fig.update_xaxes(title_text="P&L ($)", row=2, col=1)
        fig.update_yaxes(title_text="Count", row=2, col=1)
        fig.update_xaxes(title_text="Date", row=3, col=1)
        fig.update_yaxes(title_text="P&L ($)", row=3, col=1)
        fig.update_yaxes(title_text="ORB Range ($)", row=3, col=2)
        
        return fig
    
    def plot_volatility_analysis(self, df: pd.DataFrame, period_days: int = 30) -> go.Figure:
        """
        Create volatility analysis visualization
        """
        # Calculate volatility metrics
        df = df.copy()
        df['returns'] = df['close'].pct_change()
        df['hour'] = df['date'].dt.hour
        df['minute'] = df['date'].dt.minute
        df['time_of_day'] = df['hour'] + df['minute'] / 60
        
        # Rolling volatility
        df['volatility'] = df['returns'].rolling(window=390).std() * np.sqrt(252 * 390)
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Intraday Volatility Pattern', 'Rolling Volatility',
                'Volatility by Day of Week', 'High-Low Range Distribution'
            )
        )
        
        # 1. Intraday volatility pattern
        intraday_vol = df.groupby(['hour', 'minute'])['returns'].agg(['mean', 'std']).reset_index()
        intraday_vol['time'] = intraday_vol['hour'] + intraday_vol['minute'] / 60
        
        fig.add_trace(
            go.Scatter(
                x=intraday_vol['time'],
                y=intraday_vol['std'] * np.sqrt(252 * 390),
                mode='lines',
                line=dict(color=self.color_scheme['neutral'], width=2),
                name='Intraday Vol'
            ),
            row=1, col=1
        )
        
        # 2. Rolling volatility
        recent_df = df.iloc[-period_days*390:]  # Approximate
        fig.add_trace(
            go.Scatter(
                x=recent_df['date'],
                y=recent_df['volatility'],
                mode='lines',
                line=dict(color=self.color_scheme['bearish'], width=2),
                name='Rolling Vol'
            ),
            row=1, col=2
        )
        
        # 3. Volatility by day of week
        df['dayofweek'] = df['date'].dt.day_name()
        dow_vol = df.groupby('dayofweek')['returns'].std() * np.sqrt(252 * 390)
        dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        dow_vol = dow_vol.reindex(dow_order)
        
        fig.add_trace(
            go.Bar(
                x=dow_vol.index,
                y=dow_vol.values,
                marker_color=self.color_scheme['neutral'],
                name='DoW Vol'
            ),
            row=2, col=1
        )
        
        # 4. High-Low range distribution
        df['range'] = df['high'] - df['low']
        fig.add_trace(
            go.Histogram(
                x=df['range'],
                nbinsx=50,
                marker_color=self.color_scheme['neutral'],
                name='Range Dist'
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title="Volatility Analysis",
            template=self.default_template,
            height=700,
            showlegend=False
        )
        
        # Update axes
        fig.update_xaxes(title_text="Hour of Day", row=1, col=1)
        fig.update_yaxes(title_text="Annualized Vol", row=1, col=1)
        fig.update_xaxes(title_text="Date", row=1, col=2)
        fig.update_yaxes(title_text="Volatility", row=1, col=2)
        fig.update_xaxes(title_text="Day of Week", row=2, col=1)
        fig.update_yaxes(title_text="Volatility", row=2, col=1)
        fig.update_xaxes(title_text="Range ($)", row=2, col=2)
        fig.update_yaxes(title_text="Count", row=2, col=2)
        
        return fig
    
    def plot_pattern_analysis(self, df: pd.DataFrame, patterns: List[Dict]) -> go.Figure:
        """
        Visualize detected patterns
        """
        fig = go.Figure()
        
        # Add candlestick
        fig.add_trace(
            go.Candlestick(
                x=df['date'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='SPY'
            )
        )
        
        # Add pattern markers
        for pattern in patterns:
            color = self.color_scheme['bullish'] if pattern['type'] == 'bullish' else self.color_scheme['bearish']
            fig.add_trace(
                go.Scatter(
                    x=[pattern['date']],
                    y=[pattern['price']],
                    mode='markers+text',
                    marker=dict(size=15, color=color),
                    text=pattern['name'],
                    textposition='top center',
                    name=pattern['name']
                )
            )
            
        fig.update_layout(
            title="Pattern Detection Analysis",
            template=self.default_template,
            xaxis_rangeslider_visible=False,
            height=600
        )
        
        return fig