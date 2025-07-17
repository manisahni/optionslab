"""
Performance reporting and visualization for options backtesting
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path

from risk_manager import calculate_sharpe_ratio, calculate_maximum_drawdown


class PerformanceReporter:
    """Generate comprehensive performance reports and visualizations"""
    
    def __init__(self, results: Dict, output_dir: str = "results"):
        """
        Initialize reporter with backtest results
        
        Args:
            results: Backtest results dictionary
            output_dir: Directory to save reports and charts
        """
        self.results = results
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Extract data
        self.trades_df = results.get('trades_df', pd.DataFrame())
        self.snapshots_df = results.get('snapshots_df', pd.DataFrame())
        self.performance = results.get('performance', {})
        
    def generate_full_report(self, save_charts: bool = True) -> str:
        """Generate comprehensive HTML report"""
        
        # Create individual sections
        summary_html = self._generate_summary_section()
        trades_html = self._generate_trades_section()
        performance_html = self._generate_performance_section()
        risk_html = self._generate_risk_section()
        
        # Generate charts if requested
        chart_files = []
        if save_charts:
            chart_files = self._generate_all_charts()
        
        # Combine into full HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Options Backtest Report - {self.results.get('strategy', 'Unknown')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 30px 0; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; 
                          background-color: #e9e9e9; border-radius: 5px; min-width: 150px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
                .metric-label {{ font-size: 12px; color: #666; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .chart {{ text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Options Backtest Report</h1>
                <h2>{self.results.get('strategy', 'Unknown Strategy')}</h2>
                <p><strong>Period:</strong> {self.results.get('period', 'Unknown')}</p>
                <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            {summary_html}
            {performance_html}
            {trades_html}
            {risk_html}
            
        </body>
        </html>
        """
        
        # Save HTML report
        report_file = self.output_dir / f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        return str(report_file)
    
    def _generate_summary_section(self) -> str:
        """Generate performance summary section"""
        perf = self.performance
        
        # Format key metrics
        total_return = perf.get('total_return', 0) * 100
        total_pnl = perf.get('total_pnl', 0)
        sharpe = perf.get('sharpe_ratio', 0)
        max_dd = perf.get('max_drawdown', 0) * 100
        num_trades = perf.get('num_trades', 0)
        
        return f"""
        <div class="section">
            <h3>Performance Summary</h3>
            <div class="metric">
                <div class="metric-value {'positive' if total_return > 0 else 'negative'}">
                    {total_return:.2f}%
                </div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric">
                <div class="metric-value {'positive' if total_pnl > 0 else 'negative'}">
                    ${total_pnl:,.2f}
                </div>
                <div class="metric-label">Total P&L</div>
            </div>
            <div class="metric">
                <div class="metric-value">{sharpe:.2f}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
            <div class="metric">
                <div class="metric-value negative">{max_dd:.2f}%</div>
                <div class="metric-label">Max Drawdown</div>
            </div>
            <div class="metric">
                <div class="metric-value">{num_trades}</div>
                <div class="metric-label">Total Trades</div>
            </div>
        </div>
        """
    
    def _generate_trades_section(self) -> str:
        """Generate trades analysis section"""
        if self.trades_df.empty:
            return "<div class='section'><h3>Trades Analysis</h3><p>No trades executed.</p></div>"
        
        # Calculate trade statistics
        trade_stats = self._calculate_trade_statistics()
        
        # Recent trades table
        recent_trades = self.trades_df.tail(20)
        trades_table = recent_trades.to_html(classes='trades-table', index=False, 
                                           float_format='{:.2f}'.format)
        
        return f"""
        <div class="section">
            <h3>Trades Analysis</h3>
            <p><strong>Total Trades:</strong> {len(self.trades_df)}</p>
            <p><strong>Win Rate:</strong> {trade_stats.get('win_rate', 0):.1%}</p>
            <p><strong>Average Win:</strong> ${trade_stats.get('avg_win', 0):.2f}</p>
            <p><strong>Average Loss:</strong> ${trade_stats.get('avg_loss', 0):.2f}</p>
            <p><strong>Profit Factor:</strong> {trade_stats.get('profit_factor', 0):.2f}</p>
            
            <h4>Recent Trades (Last 20)</h4>
            {trades_table}
        </div>
        """
    
    def _generate_performance_section(self) -> str:
        """Generate detailed performance metrics section"""
        if self.snapshots_df.empty:
            return "<div class='section'><h3>Performance Details</h3><p>No performance data available.</p></div>"
        
        # Calculate additional metrics
        daily_returns = self.snapshots_df['daily_pnl'].pct_change().dropna()
        monthly_returns = self._calculate_monthly_returns()
        
        # Best and worst days
        best_day = self.snapshots_df.loc[self.snapshots_df['daily_pnl'].idxmax()]
        worst_day = self.snapshots_df.loc[self.snapshots_df['daily_pnl'].idxmin()]
        
        return f"""
        <div class="section">
            <h3>Performance Details</h3>
            <p><strong>Best Day:</strong> {best_day['date'].strftime('%Y-%m-%d')} 
               (+${best_day['daily_pnl']:.2f})</p>
            <p><strong>Worst Day:</strong> {worst_day['date'].strftime('%Y-%m-%d')} 
               (${worst_day['daily_pnl']:.2f})</p>
            <p><strong>Volatility (Daily):</strong> {daily_returns.std():.2%}</p>
            <p><strong>Average Daily Return:</strong> {daily_returns.mean():.2%}</p>
            
            <h4>Monthly Returns</h4>
            {monthly_returns.to_html(classes='monthly-returns')}
        </div>
        """
    
    def _generate_risk_section(self) -> str:
        """Generate risk analysis section"""
        if self.snapshots_df.empty:
            return "<div class='section'><h3>Risk Analysis</h3><p>No risk data available.</p></div>"
        
        # Calculate risk metrics
        portfolio_values = self.snapshots_df['total_value'].tolist()
        max_drawdown = calculate_maximum_drawdown(portfolio_values)
        
        # Drawdown periods
        drawdown_periods = self._calculate_drawdown_periods()
        
        return f"""
        <div class="section">
            <h3>Risk Analysis</h3>
            <p><strong>Maximum Drawdown:</strong> {max_drawdown:.2%}</p>
            <p><strong>Current Drawdown:</strong> {self._calculate_current_drawdown():.2%}</p>
            
            <h4>Major Drawdown Periods</h4>
            {drawdown_periods.to_html(classes='drawdown-table', index=False)}
        </div>
        """
    
    def _generate_all_charts(self) -> List[str]:
        """Generate all performance charts"""
        chart_files = []
        
        try:
            # Set style
            plt.style.use('seaborn-v0_8')
            
            # Portfolio value chart
            chart_files.append(self._create_portfolio_chart())
            
            # Returns distribution
            chart_files.append(self._create_returns_distribution())
            
            # Drawdown chart
            chart_files.append(self._create_drawdown_chart())
            
            # Trade analysis charts
            if not self.trades_df.empty:
                chart_files.append(self._create_trade_analysis_chart())
            
        except Exception as e:
            print(f"Warning: Could not generate charts: {e}")
        
        return chart_files
    
    def _create_portfolio_chart(self) -> str:
        """Create portfolio value over time chart"""
        if self.snapshots_df.empty:
            return ""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Portfolio value
        ax1.plot(self.snapshots_df['date'], self.snapshots_df['total_value'], 
                linewidth=2, color='blue')
        ax1.set_title('Portfolio Value Over Time')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.grid(True, alpha=0.3)
        
        # Daily P&L
        colors = ['green' if x > 0 else 'red' for x in self.snapshots_df['daily_pnl']]
        ax2.bar(self.snapshots_df['date'], self.snapshots_df['daily_pnl'], 
               color=colors, alpha=0.7)
        ax2.set_title('Daily P&L')
        ax2.set_ylabel('Daily P&L ($)')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        chart_file = self.output_dir / 'portfolio_performance.png'
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_file)
    
    def _create_returns_distribution(self) -> str:
        """Create returns distribution chart"""
        if self.snapshots_df.empty:
            return ""
        
        daily_returns = self.snapshots_df['daily_pnl'].pct_change().dropna()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Histogram
        ax1.hist(daily_returns, bins=50, alpha=0.7, color='blue', edgecolor='black')
        ax1.set_title('Daily Returns Distribution')
        ax1.set_xlabel('Daily Return')
        ax1.set_ylabel('Frequency')
        ax1.grid(True, alpha=0.3)
        
        # Q-Q plot (simplified)
        from scipy import stats
        stats.probplot(daily_returns, dist="norm", plot=ax2)
        ax2.set_title('Q-Q Plot (Normal Distribution)')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        chart_file = self.output_dir / 'returns_distribution.png'
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_file)
    
    def _create_drawdown_chart(self) -> str:
        """Create drawdown chart"""
        if self.snapshots_df.empty:
            return ""
        
        # Calculate running drawdown
        portfolio_values = self.snapshots_df['total_value']
        running_max = portfolio_values.expanding().max()
        drawdown = (portfolio_values - running_max) / running_max
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.fill_between(self.snapshots_df['date'], drawdown, 0, 
                       color='red', alpha=0.3, label='Drawdown')
        ax.plot(self.snapshots_df['date'], drawdown, color='red', linewidth=1)
        
        ax.set_title('Portfolio Drawdown Over Time')
        ax.set_ylabel('Drawdown (%)')
        ax.set_xlabel('Date')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        chart_file = self.output_dir / 'drawdown_chart.png'
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_file)
    
    def _create_trade_analysis_chart(self) -> str:
        """Create trade analysis charts"""
        if self.trades_df.empty:
            return ""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Trade P&L distribution
        trade_pnl = self.trades_df.groupby('trade_id')['total_cost'].sum()
        ax1.hist(trade_pnl, bins=30, alpha=0.7, color='blue', edgecolor='black')
        ax1.set_title('Trade P&L Distribution')
        ax1.set_xlabel('Trade P&L ($)')
        ax1.set_ylabel('Frequency')
        ax1.grid(True, alpha=0.3)
        
        # Trades by option type
        option_type_counts = self.trades_df['option_type'].value_counts()
        ax2.pie(option_type_counts.values, labels=option_type_counts.index, autopct='%1.1f%%')
        ax2.set_title('Trades by Option Type')
        
        # Trades over time
        trades_by_date = self.trades_df.groupby(self.trades_df['date'].dt.date).size()
        ax3.plot(trades_by_date.index, trades_by_date.values, marker='o')
        ax3.set_title('Number of Trades Over Time')
        ax3.set_xlabel('Date')
        ax3.set_ylabel('Number of Trades')
        ax3.grid(True, alpha=0.3)
        
        # Delta distribution at entry
        ax4.hist(self.trades_df['delta'], bins=30, alpha=0.7, color='green', edgecolor='black')
        ax4.set_title('Delta Distribution at Entry')
        ax4.set_xlabel('Delta')
        ax4.set_ylabel('Frequency')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        chart_file = self.output_dir / 'trade_analysis.png'
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_file)
    
    def _calculate_trade_statistics(self) -> Dict:
        """Calculate detailed trade statistics"""
        if self.trades_df.empty:
            return {}
        
        # Group trades by trade_id to get complete round-trip trades
        trade_groups = self.trades_df.groupby('trade_id')
        trade_pnls = trade_groups['total_cost'].sum()
        
        winning_trades = trade_pnls[trade_pnls > 0]
        losing_trades = trade_pnls[trade_pnls <= 0]
        
        return {
            'total_trades': len(trade_pnls),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trade_pnls) if len(trade_pnls) > 0 else 0,
            'avg_win': winning_trades.mean() if len(winning_trades) > 0 else 0,
            'avg_loss': abs(losing_trades.mean()) if len(losing_trades) > 0 else 0,
            'profit_factor': abs(winning_trades.sum() / losing_trades.sum()) if losing_trades.sum() != 0 else float('inf'),
            'largest_win': winning_trades.max() if len(winning_trades) > 0 else 0,
            'largest_loss': losing_trades.min() if len(losing_trades) > 0 else 0
        }
    
    def _calculate_monthly_returns(self) -> pd.DataFrame:
        """Calculate monthly returns"""
        if self.snapshots_df.empty:
            return pd.DataFrame()
        
        monthly_data = self.snapshots_df.set_index('date').resample('M')['total_value'].last()
        monthly_returns = monthly_data.pct_change().dropna()
        
        return pd.DataFrame({
            'Month': monthly_returns.index.strftime('%Y-%m'),
            'Return': monthly_returns.values
        })
    
    def _calculate_drawdown_periods(self) -> pd.DataFrame:
        """Calculate major drawdown periods"""
        if self.snapshots_df.empty:
            return pd.DataFrame()
        
        portfolio_values = self.snapshots_df['total_value']
        running_max = portfolio_values.expanding().max()
        drawdown = (portfolio_values - running_max) / running_max
        
        # Find drawdown periods > 5%
        major_drawdowns = []
        in_drawdown = False
        start_date = None
        
        for i, (date, dd) in enumerate(zip(self.snapshots_df['date'], drawdown)):
            if dd < -0.05 and not in_drawdown:
                in_drawdown = True
                start_date = date
                min_dd = dd
            elif dd < -0.05 and in_drawdown:
                min_dd = min(min_dd, dd)
            elif dd >= -0.01 and in_drawdown:
                in_drawdown = False
                major_drawdowns.append({
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': date.strftime('%Y-%m-%d'),
                    'Max Drawdown': f"{min_dd:.2%}",
                    'Days': (date - start_date).days
                })
        
        return pd.DataFrame(major_drawdowns)
    
    def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown"""
        if self.snapshots_df.empty:
            return 0.0
        
        current_value = self.snapshots_df['total_value'].iloc[-1]
        peak_value = self.snapshots_df['total_value'].max()
        
        return (current_value - peak_value) / peak_value
    
    def export_summary_json(self) -> str:
        """Export summary statistics as JSON"""
        summary = {
            'strategy': self.results.get('strategy', 'Unknown'),
            'period': self.results.get('period', 'Unknown'),
            'performance': self.performance,
            'trade_statistics': self._calculate_trade_statistics() if not self.trades_df.empty else {},
            'generated_at': datetime.now().isoformat()
        }
        
        json_file = self.output_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        return str(json_file)