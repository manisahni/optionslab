"""
Greeks Tracker for Enhanced Options Backtesting
Tracks and analyzes Greeks evolution throughout the trade lifecycle
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class GreeksSnapshot:
    """Point-in-time Greeks data for a position or portfolio"""
    timestamp: datetime
    underlying_price: float
    dte: int
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    implied_vol: float
    option_price: float
    position_value: float
    pnl: float
    pnl_percent: float
    
    # Additional tracking metrics
    delta_change_from_entry: float = 0.0
    gamma_change_from_entry: float = 0.0
    theta_change_from_entry: float = 0.0
    vega_change_from_entry: float = 0.0
    iv_change_from_entry: float = 0.0
    
    # Greeks acceleration metrics
    delta_acceleration: float = 0.0
    gamma_acceleration: float = 0.0
    theta_acceleration: float = 0.0
    
    # Risk metrics
    delta_dollars: float = 0.0  # Delta exposure in dollars
    gamma_dollars: float = 0.0  # Gamma exposure in dollars
    vega_dollars: float = 0.0   # Vega exposure in dollars
    
    # Volatility metrics
    realized_vol: Optional[float] = None
    iv_rank: Optional[float] = None
    iv_percentile: Optional[float] = None


@dataclass
class PositionGreeksHistory:
    """Tracks Greeks evolution for a single position"""
    position_id: str
    entry_snapshot: GreeksSnapshot
    snapshots: List[GreeksSnapshot] = field(default_factory=list)
    exit_snapshot: Optional[GreeksSnapshot] = None
    
    def add_snapshot(self, snapshot: GreeksSnapshot):
        """Add a new Greeks snapshot"""
        # Calculate changes from entry
        snapshot.delta_change_from_entry = snapshot.delta - self.entry_snapshot.delta
        snapshot.gamma_change_from_entry = snapshot.gamma - self.entry_snapshot.gamma
        snapshot.theta_change_from_entry = snapshot.theta - self.entry_snapshot.theta
        snapshot.vega_change_from_entry = snapshot.vega - self.entry_snapshot.vega
        snapshot.iv_change_from_entry = snapshot.implied_vol - self.entry_snapshot.implied_vol
        
        # Calculate accelerations if we have history
        if len(self.snapshots) >= 2:
            prev_snapshot = self.snapshots[-1]
            time_diff = (snapshot.timestamp - prev_snapshot.timestamp).total_seconds() / 86400  # Days
            
            if time_diff > 0:
                snapshot.delta_acceleration = (snapshot.delta - prev_snapshot.delta) / time_diff
                snapshot.gamma_acceleration = (snapshot.gamma - prev_snapshot.gamma) / time_diff
                snapshot.theta_acceleration = (snapshot.theta - prev_snapshot.theta) / time_diff
        
        self.snapshots.append(snapshot)
    
    def get_greeks_summary(self) -> Dict[str, Any]:
        """Get summary statistics of Greeks evolution"""
        if not self.snapshots:
            return {}
        
        deltas = [s.delta for s in self.snapshots]
        gammas = [s.gamma for s in self.snapshots]
        thetas = [s.theta for s in self.snapshots]
        vegas = [s.vega for s in self.snapshots]
        ivs = [s.implied_vol for s in self.snapshots]
        
        return {
            'entry_greeks': {
                'delta': self.entry_snapshot.delta,
                'gamma': self.entry_snapshot.gamma,
                'theta': self.entry_snapshot.theta,
                'vega': self.entry_snapshot.vega,
                'iv': self.entry_snapshot.implied_vol
            },
            'exit_greeks': {
                'delta': self.exit_snapshot.delta if self.exit_snapshot else deltas[-1],
                'gamma': self.exit_snapshot.gamma if self.exit_snapshot else gammas[-1],
                'theta': self.exit_snapshot.theta if self.exit_snapshot else thetas[-1],
                'vega': self.exit_snapshot.vega if self.exit_snapshot else vegas[-1],
                'iv': self.exit_snapshot.implied_vol if self.exit_snapshot else ivs[-1]
            },
            'max_greeks': {
                'delta': max(deltas),
                'gamma': max(gammas),
                'theta': max(thetas),
                'vega': max(vegas),
                'iv': max(ivs)
            },
            'min_greeks': {
                'delta': min(deltas),
                'gamma': min(gammas),
                'theta': min(thetas),
                'vega': min(vegas),
                'iv': min(ivs)
            },
            'avg_greeks': {
                'delta': np.mean(deltas),
                'gamma': np.mean(gammas),
                'theta': np.mean(thetas),
                'vega': np.mean(vegas),
                'iv': np.mean(ivs)
            },
            'greeks_volatility': {
                'delta_std': np.std(deltas),
                'gamma_std': np.std(gammas),
                'theta_std': np.std(thetas),
                'vega_std': np.std(vegas),
                'iv_std': np.std(ivs)
            }
        }


class GreeksTracker:
    """Manages Greeks tracking for all positions in a portfolio"""
    
    def __init__(self):
        self.position_histories: Dict[str, PositionGreeksHistory] = {}
        self.portfolio_snapshots: List[Dict[str, Any]] = []
        
    def create_position_tracking(self, position_id: str, entry_data: Dict[str, Any], 
                               option_data: pd.Series, quantity: int):
        """Initialize Greeks tracking for a new position"""
        entry_snapshot = GreeksSnapshot(
            timestamp=entry_data['timestamp'],
            underlying_price=float(option_data.get('underlying_price', 0)),
            dte=int(option_data.get('dte', 0)),
            delta=float(option_data.get('delta', 0)),
            gamma=float(option_data.get('gamma', 0)),
            theta=float(option_data.get('theta', 0)),
            vega=float(option_data.get('vega', 0)),
            rho=float(option_data.get('rho', 0)),
            implied_vol=float(option_data.get('implied_volatility', 0)),
            option_price=float(option_data.get('mid_price', 0)),
            position_value=quantity * float(option_data.get('mid_price', 0)) * 100,
            pnl=0.0,
            pnl_percent=0.0,
            delta_dollars=quantity * float(option_data.get('delta', 0)) * float(option_data.get('underlying_price', 0)) * 100,
            gamma_dollars=quantity * float(option_data.get('gamma', 0)) * float(option_data.get('underlying_price', 0)) ** 2 * 100,
            vega_dollars=quantity * float(option_data.get('vega', 0)),
            iv_rank=float(option_data.get('iv_rank', 50)),
            iv_percentile=float(option_data.get('iv_percentile', 50))
        )
        
        self.position_histories[position_id] = PositionGreeksHistory(
            position_id=position_id,
            entry_snapshot=entry_snapshot
        )
        
        logger.info(f"Created Greeks tracking for position {position_id}")
    
    def update_position_greeks(self, position_id: str, current_data: pd.Series,
                             quantity: int, entry_price: float, timestamp: datetime):
        """Update Greeks for an existing position"""
        if position_id not in self.position_histories:
            logger.warning(f"Position {position_id} not found in Greeks tracker")
            return
        
        history = self.position_histories[position_id]
        
        # Calculate P&L
        current_price = float(current_data.get('mid_price', 0))
        if quantity > 0:  # Long position
            pnl = (current_price - entry_price) * quantity * 100
            pnl_percent = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        else:  # Short position
            pnl = (entry_price - current_price) * abs(quantity) * 100
            pnl_percent = ((entry_price - current_price) / entry_price) * 100 if entry_price > 0 else 0
        
        snapshot = GreeksSnapshot(
            timestamp=timestamp,
            underlying_price=float(current_data.get('underlying_price', 0)),
            dte=int(current_data.get('dte', 0)),
            delta=float(current_data.get('delta', 0)),
            gamma=float(current_data.get('gamma', 0)),
            theta=float(current_data.get('theta', 0)),
            vega=float(current_data.get('vega', 0)),
            rho=float(current_data.get('rho', 0)),
            implied_vol=float(current_data.get('implied_volatility', 0)),
            option_price=current_price,
            position_value=quantity * current_price * 100,
            pnl=pnl,
            pnl_percent=pnl_percent,
            delta_dollars=quantity * float(current_data.get('delta', 0)) * float(current_data.get('underlying_price', 0)) * 100,
            gamma_dollars=quantity * float(current_data.get('gamma', 0)) * float(current_data.get('underlying_price', 0)) ** 2 * 100,
            vega_dollars=quantity * float(current_data.get('vega', 0)),
            iv_rank=float(current_data.get('iv_rank', 50)),
            iv_percentile=float(current_data.get('iv_percentile', 50))
        )
        
        history.add_snapshot(snapshot)
    
    def close_position_tracking(self, position_id: str, exit_data: pd.Series,
                              quantity: int, entry_price: float, timestamp: datetime):
        """Mark position as closed and record final Greeks"""
        if position_id not in self.position_histories:
            logger.warning(f"Position {position_id} not found in Greeks tracker")
            return
        
        history = self.position_histories[position_id]
        
        # Calculate final P&L
        exit_price = float(exit_data.get('mid_price', 0))
        if quantity > 0:  # Long position
            pnl = (exit_price - entry_price) * quantity * 100
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        else:  # Short position
            pnl = (entry_price - exit_price) * abs(quantity) * 100
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100 if entry_price > 0 else 0
        
        history.exit_snapshot = GreeksSnapshot(
            timestamp=timestamp,
            underlying_price=float(exit_data.get('underlying_price', 0)),
            dte=int(exit_data.get('dte', 0)),
            delta=float(exit_data.get('delta', 0)),
            gamma=float(exit_data.get('gamma', 0)),
            theta=float(exit_data.get('theta', 0)),
            vega=float(exit_data.get('vega', 0)),
            rho=float(exit_data.get('rho', 0)),
            implied_vol=float(exit_data.get('implied_volatility', 0)),
            option_price=exit_price,
            position_value=0,  # Position is closed
            pnl=pnl,
            pnl_percent=pnl_percent,
            delta_change_from_entry=float(exit_data.get('delta', 0)) - history.entry_snapshot.delta,
            gamma_change_from_entry=float(exit_data.get('gamma', 0)) - history.entry_snapshot.gamma,
            theta_change_from_entry=float(exit_data.get('theta', 0)) - history.entry_snapshot.theta,
            vega_change_from_entry=float(exit_data.get('vega', 0)) - history.entry_snapshot.vega,
            iv_change_from_entry=float(exit_data.get('implied_volatility', 0)) - history.entry_snapshot.implied_vol
        )
        
        logger.info(f"Closed Greeks tracking for position {position_id}")
    
    def update_portfolio_greeks(self, timestamp: datetime, positions: List[Dict[str, Any]],
                              current_data: pd.DataFrame):
        """Calculate and store portfolio-level Greeks"""
        portfolio_greeks = {
            'timestamp': timestamp,
            'total_delta': 0.0,
            'total_gamma': 0.0,
            'total_theta': 0.0,
            'total_vega': 0.0,
            'total_delta_dollars': 0.0,
            'total_gamma_dollars': 0.0,
            'total_vega_dollars': 0.0,
            'num_positions': len(positions),
            'position_details': []
        }
        
        for position in positions:
            position_id = position['position_id']
            if position_id in self.position_histories:
                history = self.position_histories[position_id]
                if history.snapshots:
                    latest = history.snapshots[-1]
                    portfolio_greeks['total_delta'] += latest.delta * position['quantity']
                    portfolio_greeks['total_gamma'] += latest.gamma * position['quantity']
                    portfolio_greeks['total_theta'] += latest.theta * position['quantity']
                    portfolio_greeks['total_vega'] += latest.vega * position['quantity']
                    portfolio_greeks['total_delta_dollars'] += latest.delta_dollars
                    portfolio_greeks['total_gamma_dollars'] += latest.gamma_dollars
                    portfolio_greeks['total_vega_dollars'] += latest.vega_dollars
                    
                    portfolio_greeks['position_details'].append({
                        'position_id': position_id,
                        'delta': latest.delta * position['quantity'],
                        'gamma': latest.gamma * position['quantity'],
                        'theta': latest.theta * position['quantity'],
                        'vega': latest.vega * position['quantity'],
                        'pnl': latest.pnl,
                        'pnl_percent': latest.pnl_percent
                    })
        
        self.portfolio_snapshots.append(portfolio_greeks)
    
    def get_position_greeks_history(self, position_id: str) -> Optional[pd.DataFrame]:
        """Get Greeks history for a specific position as DataFrame"""
        if position_id not in self.position_histories:
            return None
        
        history = self.position_histories[position_id]
        if not history.snapshots:
            return None
        
        data = []
        for snapshot in history.snapshots:
            data.append({
                'timestamp': snapshot.timestamp,
                'underlying_price': snapshot.underlying_price,
                'dte': snapshot.dte,
                'delta': snapshot.delta,
                'gamma': snapshot.gamma,
                'theta': snapshot.theta,
                'vega': snapshot.vega,
                'iv': snapshot.implied_vol,
                'option_price': snapshot.option_price,
                'pnl': snapshot.pnl,
                'pnl_percent': snapshot.pnl_percent,
                'delta_change': snapshot.delta_change_from_entry,
                'gamma_change': snapshot.gamma_change_from_entry,
                'theta_change': snapshot.theta_change_from_entry,
                'vega_change': snapshot.vega_change_from_entry,
                'iv_change': snapshot.iv_change_from_entry
            })
        
        return pd.DataFrame(data)
    
    def get_portfolio_greeks_history(self) -> pd.DataFrame:
        """Get portfolio-level Greeks history as DataFrame"""
        if not self.portfolio_snapshots:
            return pd.DataFrame()
        
        return pd.DataFrame(self.portfolio_snapshots)
    
    def analyze_greeks_patterns(self, position_id: str) -> Dict[str, Any]:
        """Analyze Greeks patterns for exit signal generation"""
        if position_id not in self.position_histories:
            return {}
        
        history = self.position_histories[position_id]
        if len(history.snapshots) < 3:  # Need at least 3 snapshots for analysis
            return {}
        
        # Get recent snapshots
        recent_snapshots = history.snapshots[-5:]  # Last 5 snapshots
        
        # Calculate trends
        deltas = [s.delta for s in recent_snapshots]
        gammas = [s.gamma for s in recent_snapshots]
        thetas = [s.theta for s in recent_snapshots]
        vegas = [s.vega for s in recent_snapshots]
        ivs = [s.implied_vol for s in recent_snapshots]
        
        # Calculate acceleration patterns
        delta_trend = np.polyfit(range(len(deltas)), deltas, 1)[0] if len(deltas) > 1 else 0
        theta_trend = np.polyfit(range(len(thetas)), thetas, 1)[0] if len(thetas) > 1 else 0
        iv_trend = np.polyfit(range(len(ivs)), ivs, 1)[0] if len(ivs) > 1 else 0
        
        # Detect significant changes
        current_snapshot = history.snapshots[-1]
        entry_snapshot = history.entry_snapshot
        
        patterns = {
            'delta_decay': {
                'current': current_snapshot.delta,
                'entry': entry_snapshot.delta,
                'change_percent': abs((current_snapshot.delta - entry_snapshot.delta) / entry_snapshot.delta * 100) if entry_snapshot.delta != 0 else 0,
                'trend': delta_trend,
                'is_accelerating': delta_trend < -0.01  # Delta decay accelerating
            },
            'theta_acceleration': {
                'current': current_snapshot.theta,
                'entry': entry_snapshot.theta,
                'change_ratio': abs(current_snapshot.theta / entry_snapshot.theta) if entry_snapshot.theta != 0 else 1,
                'trend': theta_trend,
                'is_accelerating': theta_trend < -0.01  # Theta becoming more negative
            },
            'iv_crush': {
                'current': current_snapshot.implied_vol,
                'entry': entry_snapshot.implied_vol,
                'change_percent': (current_snapshot.implied_vol - entry_snapshot.implied_vol) / entry_snapshot.implied_vol * 100 if entry_snapshot.implied_vol != 0 else 0,
                'trend': iv_trend,
                'is_crushing': iv_trend < -0.01 and current_snapshot.implied_vol < entry_snapshot.implied_vol * 0.8
            },
            'gamma_risk': {
                'current': current_snapshot.gamma,
                'max_gamma': max(gammas),
                'current_vs_max_ratio': current_snapshot.gamma / max(gammas) if max(gammas) != 0 else 0,
                'is_high_gamma': current_snapshot.gamma > 0.05  # High gamma threshold
            }
        }
        
        return patterns
    
    def get_exit_signals_from_greeks(self, position_id: str, 
                                   thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate exit signals based on Greeks patterns"""
        patterns = self.analyze_greeks_patterns(position_id)
        if not patterns:
            return []
        
        signals = []
        
        # Delta decay signal
        if patterns['delta_decay']['change_percent'] > thresholds.get('delta_decay_threshold', 50):
            signals.append({
                'type': 'delta_decay',
                'strength': min(patterns['delta_decay']['change_percent'] / 50, 1.0),
                'message': f"Delta decayed {patterns['delta_decay']['change_percent']:.1f}% from entry",
                'current_delta': patterns['delta_decay']['current']
            })
        
        # Theta acceleration signal
        if patterns['theta_acceleration']['change_ratio'] > thresholds.get('theta_acceleration_threshold', 2.0):
            signals.append({
                'type': 'theta_acceleration',
                'strength': min(patterns['theta_acceleration']['change_ratio'] / 2.0, 1.0),
                'message': f"Theta accelerated {patterns['theta_acceleration']['change_ratio']:.1f}x from entry",
                'current_theta': patterns['theta_acceleration']['current']
            })
        
        # IV crush signal
        if patterns['iv_crush']['is_crushing'] and patterns['iv_crush']['change_percent'] < thresholds.get('iv_crush_threshold', -20):
            signals.append({
                'type': 'iv_crush',
                'strength': min(abs(patterns['iv_crush']['change_percent']) / 20, 1.0),
                'message': f"IV crushed {patterns['iv_crush']['change_percent']:.1f}% from entry",
                'current_iv': patterns['iv_crush']['current']
            })
        
        # Gamma risk signal
        if patterns['gamma_risk']['is_high_gamma'] and patterns['gamma_risk']['current'] > thresholds.get('gamma_risk_threshold', 0.10):
            signals.append({
                'type': 'gamma_risk',
                'strength': min(patterns['gamma_risk']['current'] / 0.10, 1.0),
                'message': f"High gamma risk at {patterns['gamma_risk']['current']:.3f}",
                'current_gamma': patterns['gamma_risk']['current']
            })
        
        return signals