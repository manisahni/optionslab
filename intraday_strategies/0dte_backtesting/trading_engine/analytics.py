"""
Advanced Analytics for Trading Strategies
Provides regime analysis, clustering, and ML insights
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.ensemble import RandomForestClassifier
from sklearn.manifold import TSNE
import logging

logger = logging.getLogger(__name__)


class TradingAnalytics:
    """Advanced analytics for trading strategy analysis"""
    
    def __init__(self, daily_df: pd.DataFrame, trades_df: pd.DataFrame):
        self.daily_df = daily_df
        self.trades_df = trades_df
    
    def _create_basic_analysis(self) -> pd.DataFrame:
        """Create basic analysis when advanced features aren't available"""
        if self.trades_df.empty:
            return pd.DataFrame()
        
        # Basic statistics using available columns
        basic_stats = pd.DataFrame({
            'metric': ['Total Trades', 'Win Rate', 'Avg P&L', 'Total P&L', 'Best Trade', 'Worst Trade'],
            'value': [
                len(self.trades_df),
                f"{float((self.trades_df['pnl'] > 0).mean() * 100):.1f}%" if 'pnl' in self.trades_df.columns else 'N/A',
                f"${float(self.trades_df['pnl'].mean()):.2f}" if 'pnl' in self.trades_df.columns else 'N/A',
                f"${float(self.trades_df['pnl'].sum()):.2f}" if 'pnl' in self.trades_df.columns else 'N/A',
                f"${float(self.trades_df['pnl'].max()):.2f}" if 'pnl' in self.trades_df.columns else 'N/A',
                f"${float(self.trades_df['pnl'].min()):.2f}" if 'pnl' in self.trades_df.columns else 'N/A'
            ]
        })
        
        return basic_stats
        
    def analyze_regime_performance(self) -> Tuple[pd.DataFrame, go.Figure]:
        """Analyze performance across different market regimes"""
        
        # Ensure we have regime columns
        if 'volatility_regime' not in self.daily_df.columns:
            logger.warning("No volatility regime data found")
            return pd.DataFrame(), go.Figure()
        
        # Aggregate performance by regime
        regime_stats = self.daily_df.groupby('volatility_regime').agg({
            'daily_pnl': ['mean', 'sum', 'std', 'count'],
            'trades_taken': 'sum',
            'winning_trades': 'sum',
            'losing_trades': 'sum'
        }).round(2)
        
        # Calculate win rate per regime
        regime_stats['win_rate'] = (regime_stats['winning_trades']['sum'] / 
                                    regime_stats['trades_taken']['sum'] * 100).round(1)
        
        # Create visualization
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Average Daily P&L by Regime', 'Total P&L by Regime',
                          'Win Rate by Regime', 'Trade Count by Regime'),
            specs=[[{'type': 'bar'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'bar'}]]
        )
        
        regimes = regime_stats.index.tolist()
        
        # Average daily P&L
        fig.add_trace(
            go.Bar(x=regimes, y=regime_stats['daily_pnl']['mean'].values,
                   name='Avg Daily P&L',
                   marker_color=['red' if x < 0 else 'green' for x in regime_stats['daily_pnl']['mean']]),
            row=1, col=1
        )
        
        # Total P&L
        fig.add_trace(
            go.Bar(x=regimes, y=regime_stats['daily_pnl']['sum'].values,
                   name='Total P&L',
                   marker_color=['red' if x < 0 else 'green' for x in regime_stats['daily_pnl']['sum']]),
            row=1, col=2
        )
        
        # Win rate
        fig.add_trace(
            go.Bar(x=regimes, y=regime_stats['win_rate'].values,
                   name='Win Rate %',
                   marker_color='blue'),
            row=2, col=1
        )
        
        # Trade count
        fig.add_trace(
            go.Bar(x=regimes, y=regime_stats['trades_taken']['sum'].values,
                   name='Trades',
                   marker_color='purple'),
            row=2, col=2
        )
        
        fig.update_layout(height=600, title="Performance by Market Regime", showlegend=False)
        fig.update_yaxes(title_text="P&L ($)", row=1, col=1)
        fig.update_yaxes(title_text="P&L ($)", row=1, col=2)
        fig.update_yaxes(title_text="Win Rate (%)", row=2, col=1)
        fig.update_yaxes(title_text="Count", row=2, col=2)
        
        return regime_stats, fig
    
    def cluster_trades(self, n_clusters: int = 4) -> Tuple[pd.DataFrame, go.Figure]:
        """Cluster trades based on market conditions"""
        
        if self.trades_df.empty:
            return pd.DataFrame(), go.Figure()
        
        # Select features for clustering - try enhanced first, then fallback
        feature_cols = ['entry_volatility', 'entry_rsi', 'entry_volume_ratio', 'entry_time_from_open']
        fallback_cols = ['pnl', 'duration_minutes', 'entry_price', 'orb_range']
        
        # Check which features are available
        available_features = [col for col in feature_cols if col in self.trades_df.columns]
        
        if len(available_features) < 2:
            # Try fallback features
            available_features = [col for col in fallback_cols if col in self.trades_df.columns]
            if len(available_features) < 2:
                logger.warning("Not enough features for clustering")
                basic_stats = self._create_basic_analysis()
                # Create a simple figure showing basic stats
                fig = go.Figure()
                fig.add_annotation(
                    text="Insufficient features for clustering analysis.<br>Basic statistics shown in summary.",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=14)
                )
                fig.update_layout(
                    title="Clustering Analysis Not Available",
                    height=400
                )
                return basic_stats, fig
        
        # Prepare data
        X = self.trades_df[available_features].dropna()
        
        if len(X) < n_clusters:
            logger.warning("Not enough data points for clustering")
            fig = go.Figure()
            fig.add_annotation(
                text=f"Need at least {n_clusters} trades for clustering.<br>Found only {len(X)} trades with valid features.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14)
            )
            fig.update_layout(
                title="Insufficient Data for Clustering",
                height=400
            )
            return pd.DataFrame(), fig
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(X_scaled)
        
        # Add cluster labels to trades
        self.trades_df.loc[X.index, 'cluster'] = clusters
        
        # Analyze cluster performance
        cluster_stats = self.trades_df.groupby('cluster').agg({
            'pnl': ['mean', 'sum', 'std', 'count'],
            'duration_minutes': 'mean' if 'duration_minutes' in self.trades_df.columns else lambda x: 0
        }).round(2)
        
        # Calculate win rate per cluster
        win_rates = self.trades_df.groupby('cluster')['pnl'].apply(lambda x: (x > 0).mean() * 100)
        cluster_stats['win_rate'] = win_rates
        
        # Create visualization
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Average P&L by Cluster', 'Win Rate by Cluster',
                          'Trade Count by Cluster', 'Cluster Characteristics'),
            specs=[[{'type': 'bar'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'scatter'}]]
        )
        
        clusters_list = cluster_stats.index.tolist()
        
        # Average P&L
        fig.add_trace(
            go.Bar(x=[f'Cluster {i}' for i in clusters_list], 
                   y=cluster_stats['pnl']['mean'].values,
                   marker_color=['red' if x < 0 else 'green' for x in cluster_stats['pnl']['mean']]),
            row=1, col=1
        )
        
        # Win rate
        fig.add_trace(
            go.Bar(x=[f'Cluster {i}' for i in clusters_list], 
                   y=cluster_stats['win_rate'].values,
                   marker_color='blue'),
            row=1, col=2
        )
        
        # Trade count
        fig.add_trace(
            go.Bar(x=[f'Cluster {i}' for i in clusters_list], 
                   y=cluster_stats['pnl']['count'].values,
                   marker_color='purple'),
            row=2, col=1
        )
        
        # Scatter plot of first two features colored by cluster
        if len(available_features) >= 2:
            fig.add_trace(
                go.Scatter(
                    x=X[available_features[0]],
                    y=X[available_features[1]],
                    mode='markers',
                    marker=dict(
                        color=clusters,
                        colorscale='Viridis',
                        size=8,
                        colorbar=dict(title="Cluster")
                    ),
                    text=[f'P&L: ${p:.2f}' for p in self.trades_df.loc[X.index, 'pnl']],
                    hovertemplate='%{text}<br>%{xaxis.title.text}: %{x}<br>%{yaxis.title.text}: %{y}'
                ),
                row=2, col=2
            )
            fig.update_xaxes(title_text=available_features[0], row=2, col=2)
            fig.update_yaxes(title_text=available_features[1], row=2, col=2)
        
        fig.update_layout(height=600, title="Trade Clustering Analysis", showlegend=False)
        
        # Update y-axis labels with proper formatting
        fig.update_yaxes(title_text="P&L ($)", row=1, col=1)
        fig.update_yaxes(title_text="Win Rate (%)", row=1, col=2)
        fig.update_yaxes(title_text="Count", row=2, col=1)
        
        return cluster_stats, fig
    
    def feature_importance_analysis(self) -> Tuple[pd.DataFrame, go.Figure]:
        """Analyze which features are most important for winning trades"""
        
        if self.trades_df.empty:
            return pd.DataFrame(), go.Figure()
        
        # Features to analyze - enhanced first, then fallback
        feature_cols = [
            'entry_volatility', 'entry_rsi', 'entry_volume_ratio', 
            'entry_time_from_open', 'entry_bb_position', 'entry_macd_histogram',
            'gap_size', 'orb_width_pct'
        ]
        fallback_cols = ['orb_range', 'duration_minutes', 'entry_price', 'position_size']
        
        # Get available features
        available_features = [col for col in feature_cols if col in self.trades_df.columns]
        
        if len(available_features) < 3:
            # Try fallback features
            available_features = [col for col in fallback_cols if col in self.trades_df.columns]
            if len(available_features) < 2:
                logger.warning("Not enough features for importance analysis")
                return self._create_basic_analysis(), go.Figure()
        
        # Prepare data
        X = self.trades_df[available_features].dropna()
        y = (self.trades_df.loc[X.index, 'pnl'] > 0).astype(int)  # 1 for wins, 0 for losses
        
        if len(X) < 10 or y.sum() < 3:
            logger.warning("Not enough data for feature importance")
            return pd.DataFrame(), go.Figure()
        
        # Train Random Forest
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X, y)
        
        # Get feature importance
        importance_df = pd.DataFrame({
            'feature': available_features,
            'importance': rf.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Create visualization
        fig = go.Figure()
        
        fig.add_trace(
            go.Bar(
                x=importance_df['importance'],
                y=importance_df['feature'],
                orientation='h',
                marker_color='lightblue'
            )
        )
        
        fig.update_layout(
            title="Feature Importance for Winning Trades",
            xaxis_title="Importance Score",
            yaxis_title="Feature",
            height=400,
            margin=dict(l=150)
        )
        
        return importance_df, fig
    
    def create_performance_heatmap(self) -> go.Figure:
        """Create P&L heatmap by hour and volatility"""
        if self.trades_df.empty:
            return go.Figure()
        
        try:
            # Add hour and volatility features if not present
            if 'hour' not in self.trades_df.columns:
                self.trades_df['hour'] = pd.to_datetime(self.trades_df['date']).dt.hour
            
            if 'volatility' not in self.trades_df.columns:
                # Calculate simple volatility as price range
                self.trades_df['volatility'] = self.trades_df['orb_range']
            
            # Create pivot table
            heatmap_data = self.trades_df.pivot_table(
                values='pnl',
                index='hour',
                columns='volatility',
                aggfunc='mean',
                observed=False  # Fix FutureWarning
            )
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale='RdYlGn',
                zmid=0,
                text=np.round(heatmap_data.values, 2),
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            # Update layout - REMOVE height parameter
            fig.update_layout(
                title="P&L Heatmap: Hour vs Volatility",
                xaxis_title="Volatility (ORB Range)",
                yaxis_title="Hour of Day",
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Heatmap creation failed: {e}")
            return go.Figure()
    
    def calculate_risk_metrics(self) -> Dict:
        """Calculate comprehensive risk metrics"""
        
        metrics = {}
        
        if not self.daily_df.empty:
            # Sharpe Ratio
            daily_returns = self.daily_df['daily_pnl'] / 10000  # Assuming $10k capital
            if float(daily_returns.std()) > 0:
                metrics['sharpe_ratio'] = float(np.sqrt(252) * daily_returns.mean() / daily_returns.std())
            else:
                metrics['sharpe_ratio'] = 0.0
            
            # Maximum Drawdown
            cumulative = self.daily_df['cumulative_pnl']
            running_max = cumulative.expanding().max()
            drawdown = cumulative - running_max
            metrics['max_drawdown'] = float(drawdown.min())
            metrics['max_drawdown_pct'] = float((drawdown / running_max * 100).min())
            
            # Drawdown duration
            underwater = drawdown < 0
            underwater_periods = underwater.astype(int).groupby(underwater.ne(underwater.shift()).cumsum())
            if any(underwater):
                metrics['max_dd_duration'] = int(underwater_periods.sum().max())
            else:
                metrics['max_dd_duration'] = 0
            
            # Value at Risk (95%)
            metrics['var_95'] = float(np.percentile(self.daily_df['daily_pnl'], 5))
            
            # Calmar Ratio
            annual_return = float(self.daily_df['daily_pnl'].sum()) / len(self.daily_df) * 252
            metrics['calmar_ratio'] = annual_return / abs(metrics['max_drawdown']) if metrics['max_drawdown'] != 0 else 0.0
        
        if not self.trades_df.empty:
            # Win/Loss metrics
            wins = self.trades_df[self.trades_df['pnl'] > 0]
            losses = self.trades_df[self.trades_df['pnl'] <= 0]
            
            metrics['win_rate'] = float(len(wins) / len(self.trades_df) * 100)
            metrics['avg_win'] = float(wins['pnl'].mean()) if len(wins) > 0 else 0.0
            metrics['avg_loss'] = float(losses['pnl'].mean()) if len(losses) > 0 else 0.0
            losses_sum = float(losses['pnl'].sum()) if len(losses) > 0 else 0.0
            wins_sum = float(wins['pnl'].sum()) if len(wins) > 0 else 0.0
            metrics['profit_factor'] = abs(wins_sum / losses_sum) if losses_sum != 0 else float('inf')
            
            # Risk-reward ratio
            if metrics['avg_loss'] != 0:
                metrics['avg_rr_ratio'] = abs(metrics['avg_win'] / metrics['avg_loss'])
            else:
                metrics['avg_rr_ratio'] = float('inf')
        
        return metrics
    
    def comprehensive_clustering_analysis(self) -> Dict[str, Tuple[pd.DataFrame, go.Figure]]:
        """Run clustering analysis for insights"""
        
        results = {}
        
        # K-means clustering only
        kmeans_stats, kmeans_fig = self.cluster_trades(n_clusters=4)
        results['kmeans'] = (kmeans_stats, kmeans_fig)
        
        # Combined insights
        insights = self._generate_clustering_insights(kmeans_stats, pd.DataFrame())
        results['insights'] = insights
        
        return results
    
    def _generate_clustering_insights(self, kmeans_stats: pd.DataFrame, dbscan_stats: pd.DataFrame) -> str:
        """Generate actionable insights from clustering analysis"""
        
        insights = []
        
        # K-means insights only (removed DBSCAN)
        if not kmeans_stats.empty:
            best_idx = kmeans_stats['pnl']['mean'].idxmax()
            worst_idx = kmeans_stats['pnl']['mean'].idxmin()
            
            # Fix Series access - handle both Series and scalar values
            best_pnl_val = kmeans_stats.loc[best_idx, ('pnl', 'mean')]
            best_pnl = float(best_pnl_val.iloc[0] if hasattr(best_pnl_val, 'iloc') else best_pnl_val)
            
            best_win_rate_val = kmeans_stats.loc[best_idx, 'win_rate']
            best_win_rate = float(best_win_rate_val.iloc[0] if hasattr(best_win_rate_val, 'iloc') else best_win_rate_val)
            
            best_count_val = kmeans_stats.loc[best_idx, ('pnl', 'count')]
            best_count = int(best_count_val.iloc[0] if hasattr(best_count_val, 'iloc') else best_count_val)
            
            worst_pnl_val = kmeans_stats.loc[worst_idx, ('pnl', 'mean')]
            worst_pnl = float(worst_pnl_val.iloc[0] if hasattr(worst_pnl_val, 'iloc') else worst_pnl_val)
            
            insights.append(f"**K-means Best Performing Cluster:**")
            insights.append(f"- Cluster {best_idx}: ${best_pnl:.2f} avg P&L")
            insights.append(f"- Win rate: {best_win_rate:.1f}%")
            insights.append(f"- {best_count} trades")
            insights.append("")
            
            insights.append(f"**K-means Worst Performing Cluster:**")
            insights.append(f"- Cluster {worst_idx}: ${worst_pnl:.2f} avg P&L")
            insights.append(f"- Consider avoiding these market conditions")
            insights.append("")
        
        return "\n".join(insights)