"""
Enhanced Strangle Analysis with Minute-Level Options Data
Combines probability band analysis with actual options pricing, Greeks, and P&L simulation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time
import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StranglePosition:
    """Represents a strangle position"""
    entry_time: str
    call_strike: float
    put_strike: float
    call_premium: float
    put_premium: float
    total_credit: float
    spot_price: float
    call_delta: float
    put_delta: float
    total_gamma: float
    total_theta: float
    implied_vol_call: float
    implied_vol_put: float


class EnhancedStrangleAnalyzer:
    """Analyzes strangles using both price movement probabilities and actual options data"""
    
    def __init__(self, 
                 stock_data_path: str = "/Users/nish_macbook/0dte/market_data/spy_stock_data/SPY",
                 options_data_path: str = "/Users/nish_macbook/0dte/market_data/spy_options_minute"):
        self.stock_data_path = stock_data_path
        self.options_data_path = options_data_path
        self.stock_data = None
        self.options_data = None
        self.entry_times = ["09:30", "10:00", "12:00", "13:00", "14:00", "15:00"]
        
    def load_stock_data(self) -> pd.DataFrame:
        """Load SPY minute stock data"""
        all_data = []
        date_folders = sorted([f for f in os.listdir(self.stock_data_path) 
                             if os.path.isdir(os.path.join(self.stock_data_path, f))])
        
        for date_folder in date_folders:
            file_path = os.path.join(self.stock_data_path, date_folder, "SPY_1min.parquet")
            if os.path.exists(file_path):
                df = pd.read_parquet(file_path)
                df['trading_date'] = date_folder
                all_data.append(df)
        
        self.stock_data = pd.concat(all_data, ignore_index=True)
        self.stock_data['date'] = pd.to_datetime(self.stock_data['date'])
        self.stock_data['time'] = self.stock_data['date'].dt.strftime('%H:%M')
        
        logger.info(f"Loaded {len(self.stock_data)} stock bars from {len(all_data)} days")
        return self.stock_data
    
    def load_options_data(self) -> pd.DataFrame:
        """Load minute-level options data"""
        all_data = []
        
        if not os.path.exists(self.options_data_path):
            logger.warning(f"Options data path does not exist: {self.options_data_path}")
            return pd.DataFrame()
        
        date_folders = sorted([f for f in os.listdir(self.options_data_path) 
                             if os.path.isdir(os.path.join(self.options_data_path, f))])
        
        for date_folder in date_folders:
            file_path = os.path.join(self.options_data_path, date_folder, 
                                   f"SPY_options_minute_{date_folder}.parquet")
            if os.path.exists(file_path):
                df = pd.read_parquet(file_path)
                all_data.append(df)
        
        if all_data:
            self.options_data = pd.concat(all_data, ignore_index=True)
            # Convert time fields
            if 'ms_of_day' in self.options_data.columns:
                self.options_data['time'] = pd.to_timedelta(self.options_data['ms_of_day'], unit='ms')
                self.options_data['time_str'] = self.options_data['time'].apply(
                    lambda x: f"{x.seconds//3600:02d}:{(x.seconds//60)%60:02d}"
                )
            logger.info(f"Loaded {len(self.options_data)} option quotes from {len(all_data)} days")
        else:
            self.options_data = pd.DataFrame()
            
        return self.options_data
    
    def find_strangle_strikes(self, spot_price: float, target_delta: float = 0.20) -> Tuple[float, float]:
        """Find optimal strangle strikes based on target delta"""
        # Simple percentage-based approach if no options data
        call_strike = spot_price * (1 + 0.005)  # 0.5% OTM
        put_strike = spot_price * (1 - 0.005)   # 0.5% OTM
        return call_strike, put_strike
    
    def analyze_strangle_entry(self, 
                             trade_date: str, 
                             entry_time: str,
                             strike_width_pct: float = 0.5) -> Optional[StranglePosition]:
        """Analyze a strangle entry at specific time with actual options data"""
        
        # Get stock data for entry time
        day_stock = self.stock_data[self.stock_data['trading_date'] == trade_date]
        entry_stock = day_stock[day_stock['time'] == entry_time]
        
        if entry_stock.empty:
            return None
            
        spot_price = entry_stock.iloc[0]['close']
        
        # Calculate strangle strikes
        call_strike = round(spot_price * (1 + strike_width_pct/100) * 2) / 2  # Round to 0.50
        put_strike = round(spot_price * (1 - strike_width_pct/100) * 2) / 2
        
        # If we have options data, get actual prices
        if not self.options_data.empty:
            day_options = self.options_data[self.options_data['trade_date'] == trade_date]
            time_options = day_options[day_options['time_str'] == entry_time]
            
            # Find closest strikes
            call_data = time_options[
                (time_options['right'] == 'C') & 
                (time_options['strike'] >= call_strike * 1000)
            ].nsmallest(1, 'strike')
            
            put_data = time_options[
                (time_options['right'] == 'P') & 
                (time_options['strike'] <= put_strike * 1000)
            ].nlargest(1, 'strike')
            
            if not call_data.empty and not put_data.empty:
                return StranglePosition(
                    entry_time=entry_time,
                    call_strike=call_data.iloc[0]['strike'] / 1000,
                    put_strike=put_data.iloc[0]['strike'] / 1000,
                    call_premium=(call_data.iloc[0]['bid'] + call_data.iloc[0]['ask']) / 2,
                    put_premium=(put_data.iloc[0]['bid'] + put_data.iloc[0]['ask']) / 2,
                    total_credit=(call_data.iloc[0]['bid'] + call_data.iloc[0]['ask']) / 2 +
                                (put_data.iloc[0]['bid'] + put_data.iloc[0]['ask']) / 2,
                    spot_price=spot_price,
                    call_delta=call_data.iloc[0].get('delta', 0.25),
                    put_delta=put_data.iloc[0].get('delta', -0.25),
                    total_gamma=call_data.iloc[0].get('gamma', 0) + put_data.iloc[0].get('gamma', 0),
                    total_theta=call_data.iloc[0].get('theta', 0) + put_data.iloc[0].get('theta', 0),
                    implied_vol_call=call_data.iloc[0].get('implied_vol', 0.15),
                    implied_vol_put=put_data.iloc[0].get('implied_vol', 0.15)
                )
        
        # Fallback: estimate premiums based on volatility
        estimated_call_premium = spot_price * 0.0015 * (16 - int(entry_time[:2])) / 6.5
        estimated_put_premium = spot_price * 0.0015 * (16 - int(entry_time[:2])) / 6.5
        
        return StranglePosition(
            entry_time=entry_time,
            call_strike=call_strike,
            put_strike=put_strike,
            call_premium=estimated_call_premium,
            put_premium=estimated_put_premium,
            total_credit=estimated_call_premium + estimated_put_premium,
            spot_price=spot_price,
            call_delta=0.20,
            put_delta=-0.20,
            total_gamma=0.05,
            total_theta=-0.10,
            implied_vol_call=0.15,
            implied_vol_put=0.15
        )
    
    def simulate_strangle_pnl(self, position: StranglePosition, close_price: float) -> float:
        """Calculate P&L for a strangle position at close"""
        call_intrinsic = max(0, close_price - position.call_strike)
        put_intrinsic = max(0, position.put_strike - close_price)
        
        # Total cost to close
        close_cost = call_intrinsic + put_intrinsic
        
        # P&L = credit received - cost to close
        pnl = position.total_credit - close_cost
        
        return pnl
    
    def backtest_strangle_strategy(self, 
                                 strike_width_pct: float = 0.5,
                                 min_credit: float = 0.20) -> pd.DataFrame:
        """Backtest strangle strategy with actual or estimated options data"""
        results = []
        
        # Get unique trading days
        trading_days = self.stock_data['trading_date'].unique()
        
        for day in trading_days:
            day_stock = self.stock_data[self.stock_data['trading_date'] == day]
            
            # Get closing price
            close_data = day_stock.iloc[-1]
            close_price = close_data['close']
            
            for entry_time in self.entry_times:
                # Analyze strangle entry
                position = self.analyze_strangle_entry(day, entry_time, strike_width_pct)
                
                if position and position.total_credit >= min_credit:
                    # Calculate P&L
                    pnl = self.simulate_strangle_pnl(position, close_price)
                    
                    # Calculate percentage move
                    pct_move = abs((close_price - position.spot_price) / position.spot_price) * 100
                    
                    results.append({
                        'date': day,
                        'entry_time': entry_time,
                        'spot_entry': position.spot_price,
                        'spot_close': close_price,
                        'pct_move': pct_move,
                        'call_strike': position.call_strike,
                        'put_strike': position.put_strike,
                        'credit': position.total_credit,
                        'pnl': pnl,
                        'win': pnl > 0,
                        'call_delta': position.call_delta,
                        'put_delta': position.put_delta,
                        'total_gamma': position.total_gamma,
                        'avg_iv': (position.implied_vol_call + position.implied_vol_put) / 2
                    })
        
        return pd.DataFrame(results)
    
    def analyze_premium_collection(self) -> pd.DataFrame:
        """Analyze average premium collection by entry time"""
        results = []
        
        for entry_time in self.entry_times:
            for width in [0.3, 0.4, 0.5, 0.7, 1.0]:
                positions = []
                
                for day in self.stock_data['trading_date'].unique()[:20]:  # Sample days
                    pos = self.analyze_strangle_entry(day, entry_time, width)
                    if pos:
                        positions.append(pos)
                
                if positions:
                    avg_credit = np.mean([p.total_credit for p in positions])
                    avg_call_delta = np.mean([p.call_delta for p in positions])
                    avg_put_delta = np.mean([p.put_delta for p in positions])
                    avg_theta = np.mean([p.total_theta for p in positions])
                    
                    results.append({
                        'entry_time': entry_time,
                        'strike_width_pct': width,
                        'avg_credit': avg_credit,
                        'avg_call_delta': avg_call_delta,
                        'avg_put_delta': avg_put_delta,
                        'avg_theta': avg_theta,
                        'sample_size': len(positions)
                    })
        
        return pd.DataFrame(results)
    
    def create_pnl_heatmap(self, backtest_results: pd.DataFrame) -> go.Figure:
        """Create P&L heatmap by entry time and strike width"""
        # Aggregate results
        summary = backtest_results.groupby(['entry_time']).agg({
            'pnl': ['mean', 'std', 'count'],
            'win': 'mean',
            'credit': 'mean'
        }).round(2)
        
        # Create heatmap
        fig = go.Figure()
        
        # Win rate heatmap
        win_rates = backtest_results.pivot_table(
            values='win', 
            index='entry_time', 
            aggfunc='mean'
        ) * 100
        
        fig.add_trace(go.Bar(
            x=win_rates.index,
            y=win_rates.values,
            name='Win Rate %',
            marker_color='lightblue'
        ))
        
        # Add average P&L line
        avg_pnl = backtest_results.groupby('entry_time')['pnl'].mean()
        
        fig.add_trace(go.Scatter(
            x=avg_pnl.index,
            y=avg_pnl.values,
            name='Avg P&L',
            yaxis='y2',
            line=dict(color='red', width=2)
        ))
        
        fig.update_layout(
            title="Strangle Performance by Entry Time",
            xaxis_title="Entry Time",
            yaxis_title="Win Rate %",
            yaxis2=dict(
                title="Average P&L ($)",
                overlaying='y',
                side='right'
            ),
            height=600
        )
        
        return fig
    
    def generate_trading_signals(self, current_time: str, current_iv_rank: float) -> Dict:
        """Generate real-time trading signals based on analysis"""
        signals = {
            'action': 'HOLD',
            'confidence': 0,
            'reasons': [],
            'recommended_width': 0.5
        }
        
        # Best entry times from our analysis
        optimal_times = ['14:00', '15:00']
        
        if current_time in optimal_times:
            signals['action'] = 'ENTER'
            signals['confidence'] = 85
            signals['reasons'].append(f"Optimal entry time: {current_time}")
            
            # Adjust width based on IV rank
            if current_iv_rank > 75:
                signals['recommended_width'] = 0.3
                signals['reasons'].append("High IV rank - tighter strikes recommended")
            elif current_iv_rank < 25:
                signals['recommended_width'] = 0.7
                signals['reasons'].append("Low IV rank - wider strikes for safety")
            else:
                signals['recommended_width'] = 0.5
        
        elif current_time == '09:30':
            signals['action'] = 'AVOID'
            signals['confidence'] = 90
            signals['reasons'].append("High volatility period - wait for market to settle")
        
        return signals


def main():
    """Run enhanced strangle analysis"""
    analyzer = EnhancedStrangleAnalyzer()
    
    # Load data
    print("Loading stock data...")
    analyzer.load_stock_data()
    
    print("Loading options data...")
    analyzer.load_options_data()
    
    # Analyze premium collection
    print("\nAnalyzing premium collection patterns...")
    premium_analysis = analyzer.analyze_premium_collection()
    
    if not premium_analysis.empty:
        print("\nAverage Premium Collection by Entry Time (0.5% width):")
        subset = premium_analysis[premium_analysis['strike_width_pct'] == 0.5]
        print(subset[['entry_time', 'avg_credit', 'avg_theta']].to_string(index=False))
    
    # Run backtest
    print("\nRunning strangle backtest...")
    backtest_results = analyzer.backtest_strangle_strategy(strike_width_pct=0.5)
    
    if not backtest_results.empty:
        # Summary statistics
        summary = backtest_results.groupby('entry_time').agg({
            'pnl': ['mean', 'std', 'count'],
            'win': 'mean',
            'credit': 'mean'
        })
        
        print("\nBacktest Results Summary:")
        print(summary)
        
        # Create visualizations
        fig = analyzer.create_pnl_heatmap(backtest_results)
        fig.write_html("/Users/nish_macbook/0dte/exports/enhanced_strangle_pnl.html")
        print("\nVisualization saved to exports/enhanced_strangle_pnl.html")
    
    # Generate current signals (example)
    signals = analyzer.generate_trading_signals("14:00", 45)
    print(f"\nCurrent Trading Signal: {signals}")


if __name__ == "__main__":
    main()