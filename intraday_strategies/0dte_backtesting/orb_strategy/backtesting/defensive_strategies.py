"""
Defensive Strategies Analysis Module
Analyzes loss patterns and tests defensive strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DefensiveAnalyzer:
    """
    Analyze defensive strategies for ORB trading
    """
    
    def __init__(self, trades_df: pd.DataFrame):
        """
        Initialize with trade results
        
        Args:
            trades_df: DataFrame with trade results
        """
        self.trades = trades_df.copy()
        self.trades['date'] = pd.to_datetime(self.trades['date'])
        
        # Identify losses
        self.trades['is_loss'] = self.trades['net_pnl'] < 0
        self.losses = self.trades[self.trades['is_loss']].copy()
        self.wins = self.trades[~self.trades['is_loss']].copy()
        
        # Calculate basic metrics
        self.win_rate = len(self.wins) / len(self.trades) if len(self.trades) > 0 else 0
        self.avg_win = self.wins['net_pnl'].mean() if len(self.wins) > 0 else 0
        self.avg_loss = self.losses['net_pnl'].mean() if len(self.losses) > 0 else 0
        
        logger.info(f"Defensive Analyzer initialized with {len(self.trades)} trades")
    
    def analyze_loss_clustering(self) -> Dict:
        """
        Analyze if losses are clustered or random
        
        Returns:
            Dict with clustering analysis
        """
        clustering = {
            'total_losses': len(self.losses),
            'loss_rate': len(self.losses) / len(self.trades) * 100 if len(self.trades) > 0 else 0,
            'consecutive_streaks': [],
            'max_streak': 0,
            'days_between_losses': [],
            'clustering_score': 0  # 0 = random, 1 = highly clustered
        }
        
        # Find consecutive loss streaks
        current_streak = 0
        streak_start = None
        
        for idx, row in self.trades.iterrows():
            if row['is_loss']:
                if current_streak == 0:
                    streak_start = idx
                current_streak += 1
            else:
                if current_streak > 1:
                    clustering['consecutive_streaks'].append({
                        'length': current_streak,
                        'start_idx': streak_start,
                        'end_idx': idx - 1,
                        'total_loss': self.trades.loc[streak_start:idx-1, 'net_pnl'].sum(),
                        'start_date': self.trades.loc[streak_start, 'date'],
                        'end_date': self.trades.loc[idx-1, 'date']
                    })
                current_streak = 0
        
        # Handle if last trades were losses
        if current_streak > 1:
            clustering['consecutive_streaks'].append({
                'length': current_streak,
                'start_idx': streak_start,
                'end_idx': len(self.trades) - 1,
                'total_loss': self.trades.loc[streak_start:, 'net_pnl'].sum(),
                'start_date': self.trades.loc[streak_start, 'date'],
                'end_date': self.trades.iloc[-1]['date']
            })
        
        # Calculate max streak
        if clustering['consecutive_streaks']:
            clustering['max_streak'] = max(s['length'] for s in clustering['consecutive_streaks'])
        
        # Calculate days between losses
        if len(self.losses) > 1:
            losses_sorted = self.losses.sort_values('date')
            days_between = losses_sorted['date'].diff().dt.days.dropna().tolist()
            clustering['days_between_losses'] = days_between
            clustering['avg_days_between'] = np.mean(days_between) if days_between else 0
            clustering['median_days_between'] = np.median(days_between) if days_between else 0
        
        # Calculate clustering score (0-1)
        # Higher score means more clustered
        if len(self.losses) > 0:
            expected_random_streak = 1 / (1 - self.win_rate) if self.win_rate < 1 else 1
            actual_max_streak = clustering['max_streak'] if clustering['max_streak'] > 0 else 1
            clustering['clustering_score'] = min(1, actual_max_streak / (expected_random_streak * 3))
        
        return clustering
    
    def test_stop_loss_effectiveness(self) -> Dict:
        """
        Test if stop losses would improve performance
        
        Returns:
            Dict with stop loss analysis
        """
        stop_loss_results = {}
        
        for stop_pct in [0.25, 0.50, 0.75, 1.00]:
            helped_trades = 0
            hurt_trades = 0
            total_impact = 0
            
            for idx, trade in self.trades.iterrows():
                # Calculate max possible loss
                if 'short_strike' in trade and 'long_strike' in trade:
                    max_loss = (abs(trade['short_strike'] - trade['long_strike']) * 100) - trade['entry_credit']
                    stop_level = -max_loss * stop_pct
                    
                    # Only check losing trades for stop loss
                    if trade['net_pnl'] < 0:
                        # This is a losing trade
                        if trade['net_pnl'] < stop_level:
                            # Loss exceeded stop level - stop would have helped
                            helped_trades += 1
                            # We would have lost stop_level instead of actual loss
                            saved_amount = abs(trade['net_pnl']) - abs(stop_level)
                            total_impact += saved_amount
                        else:
                            # Loss was smaller than stop - no impact
                            pass
            
            stop_loss_results[f'{int(stop_pct*100)}%'] = {
                'stop_level': stop_pct,
                'trades_helped': helped_trades,
                'trades_hurt': hurt_trades,
                'net_impact': total_impact,
                'recommendation': 'Use' if total_impact > 50 else "Don't Use"  # Only use if saves >$50
            }
        
        return stop_loss_results
    
    def calculate_kelly_criterion(self) -> Dict:
        """
        Calculate optimal position sizing using Kelly Criterion
        
        Returns:
            Dict with Kelly calculations
        """
        if self.win_rate == 0 or self.avg_win == 0:
            return {'kelly_pct': 0, 'half_kelly': 0, 'quarter_kelly': 0}
        
        # Kelly formula: (p*b - q) / b
        # where p = win rate, q = loss rate, b = win/loss ratio
        p = self.win_rate
        q = 1 - p
        b = abs(self.avg_win / self.avg_loss) if self.avg_loss != 0 else 0
        
        kelly_fraction = (p * b - q) / b if b > 0 else 0
        
        # Convert to percentage and cap at reasonable levels
        kelly_pct = min(100, max(0, kelly_fraction * 100))
        
        return {
            'win_rate': p * 100,
            'loss_rate': q * 100,
            'win_loss_ratio': b,
            'kelly_pct': kelly_pct,
            'half_kelly': kelly_pct / 2,
            'quarter_kelly': kelly_pct / 4,
            'recommended': min(kelly_pct / 2, 10)  # Cap at 10% for safety
        }
    
    def analyze_time_patterns(self) -> Dict:
        """
        Analyze time-based patterns in losses
        
        Returns:
            Dict with time analysis
        """
        time_analysis = {
            'losses_by_hour': {},
            'losses_by_day': {},
            'best_hours': [],
            'worst_hours': [],
            'recommendations': []
        }
        
        if 'entry_time' in self.losses.columns:
            # Convert entry_time to datetime if needed
            if not pd.api.types.is_datetime64_any_dtype(self.losses['entry_time']):
                self.losses['entry_time'] = pd.to_datetime(self.losses['entry_time'])
            
            # Losses by hour
            self.losses['entry_hour'] = self.losses['entry_time'].dt.hour
            hour_counts = self.losses['entry_hour'].value_counts().sort_index()
            
            # Also get total trades by hour for win rate
            if 'entry_time' in self.trades.columns:
                if not pd.api.types.is_datetime64_any_dtype(self.trades['entry_time']):
                    self.trades['entry_time'] = pd.to_datetime(self.trades['entry_time'])
                
                self.trades['entry_hour'] = self.trades['entry_time'].dt.hour
                total_by_hour = self.trades['entry_hour'].value_counts()
                
                for hour in range(10, 16):  # Market hours
                    losses = hour_counts.get(hour, 0)
                    total = total_by_hour.get(hour, 0)
                    win_rate = ((total - losses) / total * 100) if total > 0 else 0
                    
                    time_analysis['losses_by_hour'][f'{hour}:00'] = {
                        'losses': losses,
                        'total': total,
                        'win_rate': win_rate
                    }
                
                # Find best and worst hours
                hour_data = [(h, d['win_rate']) for h, d in time_analysis['losses_by_hour'].items()]
                hour_data.sort(key=lambda x: x[1], reverse=True)
                
                if hour_data:
                    time_analysis['best_hours'] = [h[0] for h in hour_data[:3]]
                    time_analysis['worst_hours'] = [h[0] for h in hour_data[-3:]]
                
                # Recommendations
                if hour_data and hour_data[-1][1] < 70:  # Worst hour has <70% win rate
                    time_analysis['recommendations'].append(
                        f"Consider avoiding trades at {hour_data[-1][0]}"
                    )
        
        # Day of week analysis
        if 'date' in self.losses.columns:
            self.losses['day_of_week'] = self.losses['date'].dt.day_name()
            day_counts = self.losses['day_of_week'].value_counts()
            
            for day in day_counts.index:
                time_analysis['losses_by_day'][day] = day_counts[day]
        
        return time_analysis
    
    def calculate_recovery_metrics(self) -> Dict:
        """
        Calculate how quickly losses are recovered
        
        Returns:
            Dict with recovery metrics
        """
        recovery_metrics = {
            'recovery_times': [],
            'avg_trades_to_recover': 0,
            'median_trades_to_recover': 0,
            'max_trades_to_recover': 0,
            'unrecovered_losses': 0
        }
        
        for idx in self.losses.index:
            loss_amount = abs(self.losses.loc[idx, 'net_pnl'])
            
            # Get trades after this loss
            next_trades = self.trades[self.trades.index > idx]
            
            if len(next_trades) > 0:
                cumsum_after = next_trades['net_pnl'].cumsum()
                
                # Find when cumulative P&L exceeds the loss
                recovery_mask = cumsum_after >= loss_amount
                
                if recovery_mask.any():
                    recovery_idx = recovery_mask.idxmax()
                    trades_to_recover = recovery_idx - idx
                    recovery_metrics['recovery_times'].append(trades_to_recover)
                else:
                    recovery_metrics['unrecovered_losses'] += 1
        
        if recovery_metrics['recovery_times']:
            recovery_metrics['avg_trades_to_recover'] = np.mean(recovery_metrics['recovery_times'])
            recovery_metrics['median_trades_to_recover'] = np.median(recovery_metrics['recovery_times'])
            recovery_metrics['max_trades_to_recover'] = max(recovery_metrics['recovery_times'])
        
        return recovery_metrics
    
    def test_position_reduction_strategy(self) -> Dict:
        """
        Test reducing position size after consecutive losses
        
        Returns:
            Dict with position reduction analysis
        """
        # Simulate trading with position reduction
        capital = 100000
        position_size = 1  # contracts
        reduced_size = 0.5  # 50% reduction
        
        # Track results
        original_pnl = self.trades['net_pnl'].sum()
        modified_pnl = 0
        current_position_multiplier = 1.0
        consecutive_losses = 0
        
        for idx, trade in self.trades.iterrows():
            # Apply position multiplier
            trade_pnl = trade['net_pnl'] * current_position_multiplier
            modified_pnl += trade_pnl
            
            # Update consecutive loss counter
            if trade['is_loss']:
                consecutive_losses += 1
                if consecutive_losses >= 2:
                    current_position_multiplier = reduced_size
            else:
                # Reset on win
                consecutive_losses = 0
                current_position_multiplier = 1.0
        
        return {
            'original_pnl': original_pnl,
            'modified_pnl': modified_pnl,
            'improvement': modified_pnl - original_pnl,
            'improvement_pct': ((modified_pnl - original_pnl) / abs(original_pnl) * 100) if original_pnl != 0 else 0,
            'recommendation': 'Use' if modified_pnl > original_pnl else 'Optional'
        }
    
    def generate_defensive_report(self) -> Dict:
        """
        Generate comprehensive defensive strategy report
        
        Returns:
            Dict with all defensive analyses
        """
        report = {
            'summary': {
                'total_trades': len(self.trades),
                'total_losses': len(self.losses),
                'loss_rate': len(self.losses) / len(self.trades) * 100 if len(self.trades) > 0 else 0,
                'win_rate': self.win_rate * 100,
                'avg_win': self.avg_win,
                'avg_loss': self.avg_loss
            },
            'clustering': self.analyze_loss_clustering(),
            'stop_loss': self.test_stop_loss_effectiveness(),
            'kelly': self.calculate_kelly_criterion(),
            'time_patterns': self.analyze_time_patterns(),
            'recovery': self.calculate_recovery_metrics(),
            'position_reduction': self.test_position_reduction_strategy()
        }
        
        # Generate recommendations
        recommendations = []
        
        # 1. Stop loss recommendation
        stop_losses_help = any(v['net_impact'] > 100 for v in report['stop_loss'].values())
        if not stop_losses_help:
            recommendations.append("✓ NO STOP LOSS NEEDED - Would reduce profits")
        
        # 2. Position sizing
        kelly = report['kelly']
        recommendations.append(f"✓ POSITION SIZE: Use {kelly['recommended']:.1f}% of capital per trade")
        
        # 3. Clustering
        if report['clustering']['max_streak'] > 3:
            recommendations.append("⚠ CONSECUTIVE LOSSES: Reduce size after 2 losses in a row")
        else:
            recommendations.append("✓ LOSSES ARE RANDOM - No clustering detected")
        
        # 4. Recovery
        if report['recovery']['median_trades_to_recover'] < 5:
            recommendations.append("✓ FAST RECOVERY - Losses recovered within 5 trades")
        
        # 5. Time patterns
        if report['time_patterns']['recommendations']:
            for rec in report['time_patterns']['recommendations']:
                recommendations.append(f"⚠ TIME FILTER: {rec}")
        
        report['recommendations'] = recommendations
        
        return report