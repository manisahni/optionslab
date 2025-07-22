"""
Greek tracking utilities for options positions
Handles entry, current, and exit Greeks with history tracking
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class GreekSnapshot:
    """Represents Greeks at a specific point in time"""
    date: str
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    iv: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'date': self.date,
            'delta': self.delta,
            'gamma': self.gamma,
            'theta': self.theta,
            'vega': self.vega,
            'rho': self.rho,
            'iv': self.iv
        }


@dataclass
class GreekTracker:
    """Tracks Greeks throughout the lifecycle of a position"""
    entry_greeks: GreekSnapshot
    current_greeks: GreekSnapshot = None
    exit_greeks: GreekSnapshot = None
    history: List[GreekSnapshot] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize with entry Greeks in history"""
        self.history.append(self.entry_greeks)
        self.current_greeks = self.entry_greeks
    
    def update_current(self, option_data: Dict, current_date: str):
        """Update current Greeks from option data"""
        self.current_greeks = GreekSnapshot(
            date=current_date,
            delta=option_data.get('delta'),
            gamma=option_data.get('gamma'),
            theta=option_data.get('theta'),
            vega=option_data.get('vega'),
            rho=option_data.get('rho'),
            iv=option_data.get('implied_vol')
        )
        self.history.append(self.current_greeks)
    
    def set_exit_greeks(self, option_data: Dict, exit_date: str):
        """Set exit Greeks"""
        self.exit_greeks = GreekSnapshot(
            date=exit_date,
            delta=option_data.get('delta'),
            gamma=option_data.get('gamma'),
            theta=option_data.get('theta'),
            vega=option_data.get('vega'),
            rho=option_data.get('rho'),
            iv=option_data.get('implied_vol')
        )
        # Don't duplicate if we already have this date in history
        if not self.history or self.history[-1].date != exit_date:
            self.history.append(self.exit_greeks)
    
    def get_entry_dict(self) -> Dict:
        """Get entry Greeks as dictionary with 'entry_' prefix"""
        return {
            'entry_delta': self.entry_greeks.delta,
            'entry_gamma': self.entry_greeks.gamma,
            'entry_theta': self.entry_greeks.theta,
            'entry_vega': self.entry_greeks.vega,
            'entry_rho': self.entry_greeks.rho,
            'entry_iv': self.entry_greeks.iv
        }
    
    def get_exit_dict(self) -> Dict:
        """Get exit Greeks as dictionary with 'exit_' prefix"""
        if not self.exit_greeks:
            return {}
        return {
            'exit_delta': self.exit_greeks.delta,
            'exit_gamma': self.exit_greeks.gamma,
            'exit_theta': self.exit_greeks.theta,
            'exit_vega': self.exit_greeks.vega,
            'exit_rho': self.exit_greeks.rho,
            'exit_iv': self.exit_greeks.iv
        }
    
    def get_history_list(self) -> List[Dict]:
        """Get history as list of dictionaries"""
        return [snapshot.to_dict() for snapshot in self.history]
    
    def log_entry_greeks(self) -> str:
        """Format entry Greeks for logging"""
        lines = ["Entry Greeks:"]
        if self.entry_greeks.delta is not None:
            lines.append(f"   Delta: {self.entry_greeks.delta:.3f}")
        if self.entry_greeks.gamma is not None:
            lines.append(f"   Gamma: {self.entry_greeks.gamma:.3f}")
        if self.entry_greeks.theta is not None:
            lines.append(f"   Theta: {self.entry_greeks.theta:.3f}")
        if self.entry_greeks.vega is not None:
            lines.append(f"   Vega: {self.entry_greeks.vega:.3f}")
        if self.entry_greeks.iv is not None:
            lines.append(f"   IV: {self.entry_greeks.iv:.3f}")
        return "\n".join(lines) if len(lines) > 1 else ""
    
    def log_exit_greeks(self) -> str:
        """Format exit Greeks for logging with comparison to entry"""
        if not self.exit_greeks or not self.current_greeks:
            return ""
            
        lines = ["Exit Greeks:"]
        if self.current_greeks.delta is not None and self.entry_greeks.delta is not None:
            lines.append(f"   Delta: {self.current_greeks.delta:.3f} (entry: {self.entry_greeks.delta:.3f})")
        if self.current_greeks.gamma is not None and self.entry_greeks.gamma is not None:
            lines.append(f"   Gamma: {self.current_greeks.gamma:.3f} (entry: {self.entry_greeks.gamma:.3f})")
        if self.current_greeks.theta is not None and self.entry_greeks.theta is not None:
            lines.append(f"   Theta: {self.current_greeks.theta:.3f} (entry: {self.entry_greeks.theta:.3f})")
        if self.current_greeks.vega is not None and self.entry_greeks.vega is not None:
            lines.append(f"   Vega: {self.current_greeks.vega:.3f} (entry: {self.entry_greeks.vega:.3f})")
        if self.current_greeks.iv is not None and self.entry_greeks.iv is not None:
            lines.append(f"   IV: {self.current_greeks.iv:.3f} (entry: {self.entry_greeks.iv:.3f})")
        return "\n".join(lines) if len(lines) > 1 else ""
    
    @classmethod
    def from_option_data(cls, option_data: Dict, current_date: str) -> 'GreekTracker':
        """Create GreekTracker from option data"""
        entry_greeks = GreekSnapshot(
            date=current_date,
            delta=option_data.get('delta'),
            gamma=option_data.get('gamma'),
            theta=option_data.get('theta'),
            vega=option_data.get('vega'),
            rho=option_data.get('rho'),
            iv=option_data.get('implied_vol')
        )
        return cls(entry_greeks=entry_greeks)