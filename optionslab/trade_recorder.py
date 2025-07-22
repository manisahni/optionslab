"""
Trade recording and management for backtesting
Handles trade entry, exit, and compliance tracking
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class Trade:
    """Represents a complete trade with entry and exit data"""
    trade_id: int
    entry_date: str
    option_type: str  # 'C' or 'P'
    strike: float
    expiration: str
    contracts: int
    
    # Entry data
    entry_price: float
    entry_underlying: float
    entry_cost: float
    cash_before: float
    cash_after: float
    
    # Exit data (optional until trade is closed)
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_underlying: Optional[float] = None
    proceeds: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_reason: Optional[str] = None
    days_held: Optional[int] = None
    
    # Spreads
    entry_bid: Optional[float] = None
    entry_ask: Optional[float] = None
    entry_spread: Optional[float] = None
    entry_spread_pct: Optional[float] = None
    exit_bid: Optional[float] = None
    exit_ask: Optional[float] = None
    exit_spread: Optional[float] = None
    exit_spread_pct: Optional[float] = None
    
    # Market data
    entry_volume: Optional[int] = None
    entry_open_interest: Optional[int] = None
    exit_volume: Optional[int] = None
    exit_open_interest: Optional[int] = None
    
    # Compliance tracking
    delta_target: Optional[float] = None
    delta_tolerance: Optional[float] = None
    delta_actual: Optional[float] = None
    delta_compliant: bool = False
    dte_target: Optional[int] = None
    dte_min: Optional[int] = None
    dte_max: Optional[int] = None
    dte_actual: Optional[int] = None
    dte_compliant: bool = False
    compliance_score: float = 0.0
    
    # Selection process data
    selection_process: Dict = field(default_factory=dict)
    
    # Greeks are handled by GreekTracker
    greeks_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class TradeRecorder:
    """Manages trade recording and compliance tracking"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.trades: List[Trade] = []
        self._extract_compliance_targets()
    
    def _extract_compliance_targets(self):
        """Extract compliance targets from config"""
        option_selection = self.config.get('option_selection', {})
        delta_criteria = option_selection.get('delta_criteria', {})
        dte_criteria = option_selection.get('dte_criteria', {})
        
        self.delta_target = delta_criteria.get('target', 0.30)
        self.delta_tolerance = delta_criteria.get('tolerance', 0.05)
        self.dte_target = dte_criteria.get('target', 45)
        self.dte_min = dte_criteria.get('minimum', 30)
        self.dte_max = dte_criteria.get('maximum', 60)
    
    def record_entry(self, selected_option: Dict, current_date: str, current_price: float,
                    contracts: int, cash: float, cost: float) -> Trade:
        """Record a new trade entry"""
        # Calculate DTE
        dte = (pd.to_datetime(selected_option['expiration']) - pd.to_datetime(current_date)).days
        
        # Create trade object
        trade = Trade(
            trade_id=len(self.trades) + 1,
            entry_date=current_date,
            option_type=selected_option['right'],
            strike=selected_option['strike_dollars'],
            expiration=selected_option['expiration'],
            contracts=contracts,
            entry_price=selected_option['close'],
            entry_underlying=current_price,
            entry_cost=cost,
            cash_before=cash,
            cash_after=cash - cost,
            entry_bid=selected_option.get('bid'),
            entry_ask=selected_option.get('ask'),
            entry_spread=selected_option.get('ask', 0) - selected_option.get('bid', 0),
            entry_volume=selected_option.get('volume'),
            entry_open_interest=selected_option.get('open_interest'),
            delta_target=self.delta_target,
            delta_tolerance=self.delta_tolerance,
            delta_actual=selected_option.get('delta'),
            dte_target=self.dte_target,
            dte_min=self.dte_min,
            dte_max=self.dte_max,
            dte_actual=dte,
            selection_process=selected_option.get('selection_process', {})
        )
        
        # Calculate spread percentage
        if trade.entry_price > 0 and trade.entry_spread is not None:
            trade.entry_spread_pct = (trade.entry_spread / trade.entry_price) * 100
        
        # Calculate compliance
        self._calculate_compliance(trade)
        
        # Add to trades list
        self.trades.append(trade)
        
        return trade
    
    def record_exit(self, trade: Trade, exit_option: Dict, current_date: str,
                   current_price: float, exit_reason: str, days_held: int,
                   proceeds: float) -> Trade:
        """Record trade exit"""
        trade.exit_date = current_date
        trade.exit_price = exit_option['close']
        trade.exit_underlying = current_price
        trade.proceeds = proceeds
        trade.exit_reason = exit_reason
        trade.days_held = days_held
        
        # Calculate P&L
        trade.pnl = proceeds - trade.entry_cost
        trade.pnl_pct = (trade.pnl / trade.entry_cost) * 100
        
        # Calculate underlying move
        trade.underlying_move = current_price - trade.entry_underlying
        trade.underlying_move_pct = (trade.underlying_move / trade.entry_underlying) * 100
        
        # Record exit market data
        trade.exit_bid = exit_option.get('bid')
        trade.exit_ask = exit_option.get('ask')
        trade.exit_spread = exit_option.get('ask', 0) - exit_option.get('bid', 0)
        trade.exit_volume = exit_option.get('volume')
        trade.exit_open_interest = exit_option.get('open_interest')
        
        # Calculate exit spread percentage
        if trade.exit_price > 0 and trade.exit_spread is not None:
            trade.exit_spread_pct = (trade.exit_spread / trade.exit_price) * 100
        
        # Calculate annualized return
        if trade.days_held > 0:
            trade.annualized_return = (trade.pnl_pct / trade.days_held) * 365
        else:
            trade.annualized_return = trade.pnl_pct * 365
        
        return trade
    
    def _calculate_compliance(self, trade: Trade):
        """Calculate compliance score for a trade"""
        compliance_checks = []
        
        # Delta compliance
        if trade.delta_actual is not None:
            delta_min = trade.delta_target - trade.delta_tolerance
            delta_max = trade.delta_target + trade.delta_tolerance
            trade.delta_compliant = delta_min <= abs(trade.delta_actual) <= delta_max
            compliance_checks.append(trade.delta_compliant)
        
        # DTE compliance
        trade.dte_compliant = trade.dte_min <= trade.dte_actual <= trade.dte_max
        compliance_checks.append(trade.dte_compliant)
        
        # Overall compliance score
        trade.compliance_score = (sum(compliance_checks) / len(compliance_checks) * 100) if compliance_checks else 0
    
    def get_trade_by_position(self, entry_date: str, strike: float, expiration: str) -> Optional[Trade]:
        """Find trade matching position details"""
        for trade in self.trades:
            if (trade.entry_date == entry_date and 
                trade.strike == strike and
                trade.expiration == expiration and
                trade.exit_date is None):
                return trade
        return None
    
    def get_completed_trades(self) -> List[Trade]:
        """Get all completed trades"""
        return [t for t in self.trades if t.exit_date is not None]
    
    def get_open_trades(self) -> List[Trade]:
        """Get all open trades"""
        return [t for t in self.trades if t.exit_date is None]
    
    def get_trades_as_dicts(self) -> List[Dict]:
        """Get all trades as dictionaries for JSON export"""
        return [trade.to_dict() for trade in self.trades]
    
    def update_trade_greeks(self, trade: Trade, greeks_history: List[Dict]):
        """Update trade with Greeks history"""
        trade.greeks_history = greeks_history