"""
Strangle Band Analysis Module
Analyzes the probability of SPY closing within percentage bands from various entry times
Used for optimizing strangle trading strategies and risk/reward ratios
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)


class StrangleBandAnalyzer:
    """Analyzes percentage bands for strangle trading strategies"""
    
    def __init__(self, data_path: str = "/Users/nish_macbook/0dte/market_data/spy_stock_data/SPY"):
        self.data_path = data_path
        self.entry_times = ["09:30", "10:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
        self.percentage_bands = [0.1, 0.2, 0.3, 0.4, 0.5]  # Percentage bands
        self.data = None
        self.band_results = None
        
    def load_data(self) -> pd.DataFrame:
        """Load all SPY 1-minute data from parquet files"""
        all_data = []
        
        # Get all date folders
        date_folders = sorted([f for f in os.listdir(self.data_path) 
                             if os.path.isdir(os.path.join(self.data_path, f))])
        
        logger.info(f"Loading data from {len(date_folders)} days")
        
        for date_folder in date_folders:
            file_path = os.path.join(self.data_path, date_folder, "SPY_1min.parquet")
            if os.path.exists(file_path):
                try:
                    df = pd.read_parquet(file_path)
                    df['trading_date'] = date_folder
                    all_data.append(df)
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
        
        # Combine all data
        self.data = pd.concat(all_data, ignore_index=True)
        self.data['date'] = pd.to_datetime(self.data['date'])
        self.data['time'] = self.data['date'].dt.strftime('%H:%M')
        
        logger.info(f"Loaded {len(self.data)} total bars from {len(all_data)} days")
        return self.data
    
    def calculate_band_probabilities(self) -> pd.DataFrame:
        """Calculate probability of closing within each percentage band from each entry time"""
        results = []
        
        for entry_time in self.entry_times:
            for band in self.percentage_bands:
                prob = self._calculate_single_band_probability(entry_time, band)
                results.append({
                    'entry_time': entry_time,
                    'band_percentage': band,
                    'probability': prob['probability'],
                    'days_in_band': prob['days_in_band'],
                    'total_days': prob['total_days'],
                    'avg_move': prob['avg_move'],
                    'max_move': prob['max_move'],
                    'min_move': prob['min_move']
                })
        
        self.band_results = pd.DataFrame(results)
        return self.band_results
    
    def _calculate_single_band_probability(self, entry_time: str, band_pct: float) -> Dict:
        """Calculate probability for a single entry time and band combination"""
        # Get unique trading days
        trading_days = self.data['trading_date'].unique()
        days_in_band = 0
        moves = []
        
        for day in trading_days:
            day_data = self.data[self.data['trading_date'] == day].copy()
            day_data = day_data.sort_values('date')
            
            # Find entry price at specified time
            entry_data = day_data[day_data['time'] == entry_time]
            if entry_data.empty:
                continue
                
            entry_price = entry_data.iloc[0]['close']
            
            # Get closing price (last bar of the day)
            close_price = day_data.iloc[-1]['close']
            
            # Calculate percentage move
            pct_move = abs((close_price - entry_price) / entry_price) * 100
            moves.append(pct_move)
            
            # Check if within band
            if pct_move <= band_pct:
                days_in_band += 1
        
        total_days = len(moves)
        probability = (days_in_band / total_days * 100) if total_days > 0 else 0
        
        return {
            'probability': probability,
            'days_in_band': days_in_band,
            'total_days': total_days,
            'avg_move': np.mean(moves) if moves else 0,
            'max_move': np.max(moves) if moves else 0,
            'min_move': np.min(moves) if moves else 0
        }
    
    def calculate_risk_reward_ratios(self) -> pd.DataFrame:
        """Calculate risk/reward ratios for different band combinations"""
        if self.band_results is None:
            self.calculate_band_probabilities()
        
        rr_results = []
        
        # For each entry time, calculate R/R for selling strangles at different bands
        for entry_time in self.entry_times:
            time_data = self.band_results[self.band_results['entry_time'] == entry_time]
            
            for i, inner_band in enumerate(self.percentage_bands[:-1]):
                for outer_band in self.percentage_bands[i+1:]:
                    inner_prob = time_data[time_data['band_percentage'] == inner_band]['probability'].values[0]
                    outer_prob = time_data[time_data['band_percentage'] == outer_band]['probability'].values[0]
                    
                    # Probability of staying within inner band (max profit)
                    prob_max_profit = inner_prob / 100
                    
                    # Probability of breaching outer band (max loss)
                    prob_max_loss = (100 - outer_prob) / 100
                    
                    # Expected value calculation (simplified)
                    # Assuming credit received is proportional to band width
                    credit_ratio = inner_band / outer_band
                    expected_value = (prob_max_profit * credit_ratio) - (prob_max_loss * (1 - credit_ratio))
                    
                    rr_results.append({
                        'entry_time': entry_time,
                        'inner_band': inner_band,
                        'outer_band': outer_band,
                        'prob_profit': prob_max_profit * 100,
                        'prob_loss': prob_max_loss * 100,
                        'expected_value': expected_value,
                        'risk_reward_ratio': credit_ratio / (1 - credit_ratio) if credit_ratio < 1 else np.inf
                    })
        
        return pd.DataFrame(rr_results)
    
    def create_probability_heatmap(self) -> go.Figure:
        """Create heatmap visualization of band probabilities"""
        if self.band_results is None:
            self.calculate_band_probabilities()
        
        # Pivot data for heatmap
        heatmap_data = self.band_results.pivot(
            index='entry_time',
            columns='band_percentage',
            values='probability'
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=[f"{b}%" for b in heatmap_data.columns],
            y=heatmap_data.index,
            colorscale='RdYlGn',
            text=np.round(heatmap_data.values, 1),
            texttemplate='%{text}%',
            textfont={"size": 12},
            colorbar=dict(title="Probability %")
        ))
        
        fig.update_layout(
            title="SPY Close Within Percentage Bands - Probability Matrix",
            xaxis_title="Percentage Band from Entry",
            yaxis_title="Entry Time",
            height=500,
            width=800
        )
        
        return fig
    
    def create_risk_reward_chart(self) -> go.Figure:
        """Create visualization of risk/reward ratios"""
        rr_data = self.calculate_risk_reward_ratios()
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Expected Value by Entry Time", "Risk/Reward Ratios"),
            vertical_spacing=0.15
        )
        
        # Expected value chart
        for inner in self.percentage_bands[:-1]:
            for outer in self.percentage_bands[1:]:
                if outer > inner:
                    subset = rr_data[(rr_data['inner_band'] == inner) & 
                                   (rr_data['outer_band'] == outer)]
                    if not subset.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=subset['entry_time'],
                                y=subset['expected_value'],
                                name=f"{inner}%/{outer}%",
                                mode='lines+markers'
                            ),
                            row=1, col=1
                        )
        
        # Risk/Reward ratio chart
        best_combos = rr_data.nlargest(10, 'expected_value')
        fig.add_trace(
            go.Bar(
                x=[f"{row['entry_time']} ({row['inner_band']}%/{row['outer_band']}%)" 
                   for _, row in best_combos.iterrows()],
                y=best_combos['expected_value'],
                name="Expected Value"
            ),
            row=2, col=1
        )
        
        fig.update_layout(height=800, showlegend=True)
        fig.update_xaxes(title_text="Entry Time", row=1, col=1)
        fig.update_xaxes(title_text="Entry Time (Inner/Outer Band)", row=2, col=1, tickangle=-45)
        fig.update_yaxes(title_text="Expected Value", row=1, col=1)
        fig.update_yaxes(title_text="Expected Value", row=2, col=1)
        
        return fig
    
    def generate_summary_report(self) -> Dict:
        """Generate comprehensive summary report"""
        if self.band_results is None:
            self.calculate_band_probabilities()
        
        rr_data = self.calculate_risk_reward_ratios()
        
        # Find optimal configurations
        best_overall = rr_data.nlargest(5, 'expected_value')
        best_by_time = rr_data.loc[rr_data.groupby('entry_time')['expected_value'].idxmax()]
        
        summary = {
            'data_summary': {
                'total_days': len(self.data['trading_date'].unique()),
                'date_range': f"{self.data['trading_date'].min()} to {self.data['trading_date'].max()}",
                'total_bars': len(self.data)
            },
            'best_configurations': best_overall.to_dict('records'),
            'best_by_entry_time': best_by_time.to_dict('records'),
            'band_probabilities': self.band_results.to_dict('records'),
            'insights': self._generate_insights()
        }
        
        return summary
    
    def _generate_insights(self) -> List[str]:
        """Generate key insights from the analysis"""
        insights = []
        
        # Insight 1: Best entry time overall
        avg_probs = self.band_results.groupby('entry_time')['probability'].mean()
        best_time = avg_probs.idxmax()
        insights.append(f"Best entry time on average: {best_time} with {avg_probs[best_time]:.1f}% average probability")
        
        # Insight 2: Tightest profitable band
        tight_bands = self.band_results[self.band_results['band_percentage'] == 0.1]
        best_tight = tight_bands.nlargest(1, 'probability').iloc[0]
        insights.append(f"Highest probability for 0.1% band: {best_tight['entry_time']} at {best_tight['probability']:.1f}%")
        
        # Insight 3: Volatility pattern
        early_vol = self.band_results[self.band_results['entry_time'].isin(['09:30', '10:00'])]['avg_move'].mean()
        late_vol = self.band_results[self.band_results['entry_time'].isin(['15:00', '16:00'])]['avg_move'].mean()
        insights.append(f"Average move early day: {early_vol:.3f}%, late day: {late_vol:.3f}%")
        
        return insights


def main():
    """Run standalone analysis"""
    analyzer = StrangleBandAnalyzer()
    
    # Load data
    print("Loading SPY minute data...")
    analyzer.load_data()
    
    # Calculate probabilities
    print("Calculating band probabilities...")
    band_results = analyzer.calculate_band_probabilities()
    
    # Display results
    print("\nBand Probability Results:")
    print(band_results.pivot(index='entry_time', columns='band_percentage', values='probability'))
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    heatmap = analyzer.create_probability_heatmap()
    rr_chart = analyzer.create_risk_reward_chart()
    
    # Save visualizations
    heatmap.write_html("/Users/nish_macbook/0dte/exports/strangle_probability_heatmap.html")
    rr_chart.write_html("/Users/nish_macbook/0dte/exports/strangle_risk_reward.html")
    
    # Generate summary
    summary = analyzer.generate_summary_report()
    print("\nKey Insights:")
    for insight in summary['insights']:
        print(f"- {insight}")
    
    print("\nAnalysis complete! Check exports folder for visualizations.")


if __name__ == "__main__":
    main()