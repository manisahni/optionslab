"""
Quick Analysis Tool for SPY Options Database
Demonstrates key analyses possible with minute-level options data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from options_database_manager import OptionsDatabase, DownloadConfig
import logging

logger = logging.getLogger(__name__)


class OptionsQuickAnalysis:
    """Quick analysis tools for options database"""
    
    def __init__(self):
        self.db = OptionsDatabase()
        
    def analyze_iv_patterns(self, date: str) -> pd.DataFrame:
        """Analyze IV patterns throughout the day"""
        # Load single day data
        df = self.db.load_date_range(date, date)
        
        if df.empty:
            logger.warning(f"No data found for {date}")
            return pd.DataFrame()
        
        # Focus on 0DTE ATM options
        atm_df = df[
            (df['dte'] == 0) & 
            (abs(df['strike'] - df['spot_price']) / df['spot_price'] < 0.005)
        ].copy()
        
        if atm_df.empty:
            return pd.DataFrame()
        
        # Calculate IV statistics by time
        iv_stats = atm_df.groupby('time')['implied_vol'].agg([
            'mean', 'std', 'min', 'max'
        ]).reset_index()
        
        # Add time labels
        iv_stats['hour'] = pd.to_timedelta(iv_stats['time']).dt.total_seconds() / 3600
        
        return iv_stats
    
    def analyze_strangle_premiums(self, date: str, width_pct: float = 0.5) -> pd.DataFrame:
        """Analyze actual strangle premiums throughout the day"""
        df = self.db.load_date_range(date, date)
        
        if df.empty:
            return pd.DataFrame()
        
        # Focus on 0DTE
        dte0_df = df[df['dte'] == 0].copy()
        
        results = []
        
        # Group by time
        for time_val, time_group in dte0_df.groupby('time'):
            spot = time_group['spot_price'].iloc[0]
            
            # Find strangle strikes
            call_strike_target = spot * (1 + width_pct/100)
            put_strike_target = spot * (1 - width_pct/100)
            
            # Find closest available strikes
            calls = time_group[time_group['right'] == 'C']
            puts = time_group[time_group['right'] == 'P']
            
            if not calls.empty and not puts.empty:
                # Find closest call
                call_idx = (calls['strike'] - call_strike_target).abs().idxmin()
                call_data = calls.loc[call_idx]
                
                # Find closest put
                put_idx = (puts['strike'] - put_strike_target).abs().idxmin()
                put_data = puts.loc[put_idx]
                
                # Calculate strangle metrics
                total_credit = call_data['mid'] + put_data['mid']
                total_spread = call_data['spread'] + put_data['spread']
                
                results.append({
                    'time': time_val,
                    'spot': spot,
                    'call_strike': call_data['strike'],
                    'put_strike': put_data['strike'],
                    'call_mid': call_data['mid'],
                    'put_mid': put_data['mid'],
                    'total_credit': total_credit,
                    'total_spread': total_spread,
                    'call_delta': call_data.get('delta', np.nan),
                    'put_delta': put_data.get('delta', np.nan),
                    'avg_iv': (call_data['implied_vol'] + put_data['implied_vol']) / 2,
                    'call_volume': call_data['volume'],
                    'put_volume': put_data['volume']
                })
        
        return pd.DataFrame(results)
    
    def analyze_bid_ask_spreads(self, date: str) -> pd.DataFrame:
        """Analyze bid-ask spreads by time of day"""
        df = self.db.load_date_range(date, date)
        
        if df.empty:
            return pd.DataFrame()
        
        # Focus on liquid strikes (near ATM)
        liquid_df = df[
            (df['dte'] == 0) &
            (abs(df['strike'] - df['spot_price']) / df['spot_price'] < 0.02)
        ].copy()
        
        # Analyze spreads by time
        spread_analysis = liquid_df.groupby('time').agg({
            'spread': ['mean', 'median', 'std'],
            'spread_pct': ['mean', 'median'],
            'volume': 'sum',
            'mid': 'mean'
        }).reset_index()
        
        # Flatten column names
        spread_analysis.columns = ['_'.join(col).strip('_') for col in spread_analysis.columns]
        
        return spread_analysis
    
    def create_analysis_dashboard(self, date: str) -> go.Figure:
        """Create comprehensive analysis dashboard"""
        # Run analyses
        iv_patterns = self.analyze_iv_patterns(date)
        strangle_premiums = self.analyze_strangle_premiums(date)
        spreads = self.analyze_bid_ask_spreads(date)
        
        if iv_patterns.empty or strangle_premiums.empty:
            logger.warning("Insufficient data for dashboard")
            return go.Figure()
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "IV Throughout the Day",
                "Strangle Premium Collection",
                "Bid-Ask Spreads",
                "Delta Distribution"
            ),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Convert time to hours for plotting
        strangle_premiums['hours'] = pd.to_timedelta(strangle_premiums['time']).dt.total_seconds() / 3600
        
        # 1. IV Pattern
        fig.add_trace(
            go.Scatter(
                x=iv_patterns['hour'],
                y=iv_patterns['mean'] * 100,
                name="IV %",
                line=dict(color='blue', width=2)
            ),
            row=1, col=1
        )
        
        # 2. Strangle Premium
        fig.add_trace(
            go.Scatter(
                x=strangle_premiums['hours'],
                y=strangle_premiums['total_credit'],
                name="Total Credit",
                line=dict(color='green', width=2)
            ),
            row=1, col=2
        )
        
        # 3. Bid-Ask Spreads
        if not spreads.empty:
            spreads['hours'] = pd.to_timedelta(spreads['time']).dt.total_seconds() / 3600
            fig.add_trace(
                go.Scatter(
                    x=spreads['hours'],
                    y=spreads['spread_pct_mean'],
                    name="Spread %",
                    line=dict(color='red', width=2)
                ),
                row=2, col=1
            )
        
        # 4. Delta Distribution
        fig.add_trace(
            go.Scatter(
                x=strangle_premiums['hours'],
                y=strangle_premiums['call_delta'],
                name="Call Delta",
                line=dict(color='orange')
            ),
            row=2, col=2
        )
        
        fig.add_trace(
            go.Scatter(
                x=strangle_premiums['hours'],
                y=strangle_premiums['put_delta'],
                name="Put Delta",
                line=dict(color='purple')
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title=f"SPY Options Analysis - {date}",
            height=800,
            showlegend=True
        )
        
        # Update axes
        fig.update_xaxes(title_text="Hours from Open", row=1, col=1)
        fig.update_xaxes(title_text="Hours from Open", row=1, col=2)
        fig.update_xaxes(title_text="Hours from Open", row=2, col=1)
        fig.update_xaxes(title_text="Hours from Open", row=2, col=2)
        
        fig.update_yaxes(title_text="IV %", row=1, col=1)
        fig.update_yaxes(title_text="Premium ($)", row=1, col=2)
        fig.update_yaxes(title_text="Spread %", row=2, col=1)
        fig.update_yaxes(title_text="Delta", row=2, col=2)
        
        return fig
    
    def generate_trading_insights(self, start_date: str, end_date: str) -> Dict:
        """Generate trading insights from historical data"""
        df = self.db.load_date_range(start_date, end_date)
        
        if df.empty:
            return {"error": "No data available"}
        
        insights = {}
        
        # 1. Best times for entry (lowest spreads, good liquidity)
        time_quality = df.groupby('time').agg({
            'spread_pct': 'mean',
            'volume': 'sum',
            'implied_vol': 'mean'
        }).reset_index()
        
        time_quality['quality_score'] = (
            (1 / time_quality['spread_pct']) * 
            np.log1p(time_quality['volume']) *
            time_quality['implied_vol']
        )
        
        best_times = time_quality.nlargest(5, 'quality_score')
        insights['best_entry_times'] = best_times['time'].tolist()
        
        # 2. IV patterns
        iv_by_dte = df.groupby(['dte', 'time'])['implied_vol'].mean().reset_index()
        insights['iv_patterns'] = {
            '0dte_morning_iv': iv_by_dte[(iv_by_dte['dte'] == 0) & 
                                        (pd.to_timedelta(iv_by_dte['time']).dt.total_seconds() < 12600)]['implied_vol'].mean(),
            '0dte_afternoon_iv': iv_by_dte[(iv_by_dte['dte'] == 0) & 
                                          (pd.to_timedelta(iv_by_dte['time']).dt.total_seconds() > 18000)]['implied_vol'].mean()
        }
        
        # 3. Optimal strikes
        atm_efficiency = df[
            abs(df['strike'] - df['spot_price']) / df['spot_price'] < 0.02
        ].groupby(
            (df['strike'] - df['spot_price']) / df['spot_price'] * 100
        ).agg({
            'spread_pct': 'mean',
            'volume': 'sum'
        })
        
        insights['optimal_strike_distance'] = atm_efficiency.idxmin()['spread_pct']
        
        return insights


def main():
    """Run quick analysis demonstration"""
    analyzer = OptionsQuickAnalysis()
    
    # Check if we have any data
    stats = analyzer.db.get_database_stats()
    
    if stats['total_days'] == 0:
        print("No data in database. Please run options_database_manager.py first to download data.")
        return
    
    # Use most recent date
    latest_date = stats['date_range']['end']
    
    print(f"Running analysis for {latest_date}")
    print("=" * 60)
    
    # 1. IV Analysis
    print("\n1. IMPLIED VOLATILITY PATTERNS:")
    iv_data = analyzer.analyze_iv_patterns(latest_date)
    if not iv_data.empty:
        print(f"   Morning IV (9:30-10:30): {iv_data[iv_data['hour'] < 1]['mean'].mean():.3f}")
        print(f"   Afternoon IV (14:30-16:00): {iv_data[iv_data['hour'] > 5]['mean'].mean():.3f}")
    
    # 2. Strangle Analysis
    print("\n2. STRANGLE PREMIUM ANALYSIS (0.5% width):")
    strangle_data = analyzer.analyze_strangle_premiums(latest_date)
    if not strangle_data.empty:
        # Find specific times
        times_to_check = ['09:30', '10:00', '14:00', '15:00']
        for time_str in times_to_check:
            time_data = strangle_data[
                pd.to_timedelta(strangle_data['time']).dt.total_seconds() == 
                (int(time_str[:2]) - 9) * 3600 + int(time_str[3:]) * 60
            ]
            if not time_data.empty:
                row = time_data.iloc[0]
                print(f"   {time_str}: Credit=${row['total_credit']:.2f}, "
                      f"Spread=${row['total_spread']:.2f}, IV={row['avg_iv']:.3f}")
    
    # 3. Create visualization
    print("\n3. Creating analysis dashboard...")
    fig = analyzer.create_analysis_dashboard(latest_date)
    if fig.data:
        output_path = f"/Users/nish_macbook/0dte/exports/options_analysis_{latest_date}.html"
        fig.write_html(output_path)
        print(f"   Dashboard saved to: {output_path}")
    
    # 4. Multi-day insights
    if stats['total_days'] > 1:
        print("\n4. MULTI-DAY INSIGHTS:")
        start = stats['date_range']['start']
        end = stats['date_range']['end']
        insights = analyzer.generate_trading_insights(start, end)
        
        if 'best_entry_times' in insights:
            print(f"   Best entry times: {insights['best_entry_times'][:3]}")
            print(f"   Morning vs Afternoon IV: {insights['iv_patterns']['0dte_morning_iv']:.3f} vs "
                  f"{insights['iv_patterns']['0dte_afternoon_iv']:.3f}")
    
    print("\n" + "=" * 60)
    print("Analysis complete!")


if __name__ == "__main__":
    main()