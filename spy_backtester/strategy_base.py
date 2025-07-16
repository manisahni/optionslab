"""
Base classes for options trading strategies
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import field
import pandas as pd
import numpy as np
import logging
from enum import Enum


class PositionType(Enum):
    LONG = "long"
    SHORT = "short"


class OrderType(Enum):
    BUY_TO_OPEN = "buy_to_open"
    SELL_TO_OPEN = "sell_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_CLOSE = "sell_to_close"


@dataclass
class Trade:
    """Represents a single options trade with comprehensive tracking"""
    trade_id: str
    date: datetime
    symbol: str = "SPY"
    strike: float = 0.0
    expiration: datetime = None
    option_type: str = ""  # 'C' or 'P'
    position_type: PositionType = PositionType.LONG
    order_type: OrderType = OrderType.BUY_TO_OPEN
    quantity: int = 0
    price: float = 0.0
    commission: float = 0.0
    underlying_price: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    implied_vol: float = 0.0
    dte: int = 0
    
    # Enhanced exit tracking
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_underlying_price: Optional[float] = None
    exit_delta: Optional[float] = None
    exit_gamma: Optional[float] = None
    exit_theta: Optional[float] = None
    exit_vega: Optional[float] = None
    exit_implied_vol: Optional[float] = None
    exit_dte: Optional[int] = None
    exit_reason: str = ""  # 'stop_loss', 'profit_target', 'manual', 'expiration', 'time_decay'
    stop_loss_triggered: bool = False
    profit_target_triggered: bool = False
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    
    # Contract identification
    contract_symbol: str = ""  # e.g., "SPY210122P370"
    
    # Additional metadata
    strategy_name: str = ""
    notes: str = ""
    
    # Selection and Exit Accuracy Metrics
    selection_accuracy: Dict[str, Any] = field(default_factory=dict)  # Dict containing selection metrics
    exit_accuracy: Dict[str, Any] = field(default_factory=dict)       # Dict containing exit metrics
    
    @property
    def total_cost(self) -> float:
        """Total cost including commission"""
        cost = self.quantity * self.price * 100  # Options are per 100 shares
        if self.order_type in [OrderType.BUY_TO_OPEN, OrderType.BUY_TO_CLOSE]:
            return cost + self.commission
        else:
            return -cost + self.commission
    
    @property
    def is_opening(self) -> bool:
        """Check if this is an opening trade"""
        return self.order_type in [OrderType.BUY_TO_OPEN, OrderType.SELL_TO_OPEN]
    
    @property
    def is_closing(self) -> bool:
        """Check if this is a closing trade"""
        return self.order_type in [OrderType.BUY_TO_CLOSE, OrderType.SELL_TO_CLOSE]
    
    def generate_contract_symbol(self) -> str:
        """Generate standard option contract symbol"""
        if self.expiration and self.strike and self.option_type:
            exp_str = self.expiration.strftime('%y%m%d')
            return f"{self.symbol}{exp_str}{self.option_type}{int(self.strike)}"
        return ""
    
    def update_exit_data(self, exit_date: datetime, exit_price: float, 
                        exit_option_data: pd.Series, exit_reason: str):
        """Update trade with exit information"""
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_underlying_price = exit_option_data.get('underlying_price', 0.0)
        self.exit_delta = exit_option_data.get('delta', 0.0)
        self.exit_gamma = exit_option_data.get('gamma', 0.0)
        self.exit_theta = exit_option_data.get('theta', 0.0)
        self.exit_vega = exit_option_data.get('vega', 0.0)
        self.exit_implied_vol = exit_option_data.get('implied_volatility', 0.0)
        self.exit_dte = exit_option_data.get('dte', 0)
        self.exit_reason = exit_reason
        
        # Set exit trigger flags
        self.stop_loss_triggered = exit_reason == 'stop_loss'
        self.profit_target_triggered = exit_reason == 'profit_target'
        
        # Calculate P&L (account for both entry and exit commissions)
        if self.order_type in [OrderType.BUY_TO_OPEN, OrderType.BUY_TO_CLOSE]:
            # Long position: profit when exit price > entry price
            # Note: self.commission is entry commission, exit commission is same amount
            self.pnl = (exit_price - self.price) * self.quantity * 100 - (self.commission * 2)
        else:
            # Short position: profit when exit price < entry price  
            # Note: self.commission is entry commission, exit commission is same amount
            self.pnl = (self.price - exit_price) * self.quantity * 100 - (self.commission * 2)
            
        # Calculate percentage return
        if self.price > 0:
            self.pnl_percent = (self.pnl / (self.price * self.quantity * 100)) * 100
    
    def to_detailed_log_string(self) -> str:
        """Generate detailed log string for enhanced logging"""
        entry_greeks = f"Δ:{self.delta:.3f}, Θ:{self.theta:.3f}, Γ:{self.gamma:.3f}, ν:{self.vega:.3f}"
        
        if self.exit_date:
            exit_greeks = f"Δ:{self.exit_delta:.3f}, Θ:{self.exit_theta:.3f}, Γ:{self.exit_gamma:.3f}, ν:{self.exit_vega:.3f}"
            pnl_str = f"${self.pnl:.2f} ({self.pnl_percent:.1f}%)" if self.pnl is not None else "N/A"
            
            return (f"Trade {self.trade_id}: {self.date.strftime('%Y-%m-%d %H:%M')} → "
                   f"{self.exit_date.strftime('%Y-%m-%d %H:%M')} | "
                   f"{self.contract_symbol or self.generate_contract_symbol()} | "
                   f"Strike: ${self.strike} | DTE: {self.dte}→{self.exit_dte} | "
                   f"Qty: {self.quantity} | Entry: ${self.price:.2f} | Exit: ${self.exit_price:.2f} | "
                   f"P&L: {pnl_str} | Reason: {self.exit_reason} | "
                   f"Entry Greeks: [{entry_greeks}] | Exit Greeks: [{exit_greeks}]")
        else:
            return (f"Trade {self.trade_id}: {self.date.strftime('%Y-%m-%d %H:%M')} | "
                   f"{self.contract_symbol or self.generate_contract_symbol()} | "
                   f"Strike: ${self.strike} | DTE: {self.dte} | Qty: {self.quantity} | "
                   f"Entry: ${self.price:.2f} | Greeks: [{entry_greeks}] | Status: OPEN")
    
    def set_selection_accuracy(self, target_delta: float, actual_delta: float, 
                             tolerance: float, available_options: int, 
                             best_candidates: List[Dict], selection_method: str = "delta_targeting",
                             target_dte_min: Optional[int] = None, target_dte_max: Optional[int] = None,
                             actual_dte: Optional[int] = None):
        """Set selection accuracy metrics for this trade"""
        delta_diff = abs(actual_delta - target_delta)
        is_delta_compliant = delta_diff <= tolerance
        delta_accuracy_percentage = max(0, 100 * (1 - delta_diff / max(abs(target_delta), 0.01)))
        
        # DTE accuracy calculations
        dte_metrics = {}
        is_dte_compliant = True
        dte_accuracy_percentage = 100.0
        
        if target_dte_min is not None and target_dte_max is not None and actual_dte is not None:
            # Calculate DTE compliance
            is_dte_compliant = target_dte_min <= actual_dte <= target_dte_max
            
            # Calculate DTE accuracy percentage
            if is_dte_compliant:
                # If within range, accuracy is 100%
                dte_accuracy_percentage = 100.0
            else:
                # Calculate how far outside the range
                if actual_dte < target_dte_min:
                    dte_diff = target_dte_min - actual_dte
                    range_size = target_dte_max - target_dte_min
                else:
                    dte_diff = actual_dte - target_dte_max
                    range_size = target_dte_max - target_dte_min
                
                # Accuracy decreases based on how far outside the range
                dte_accuracy_percentage = max(0, 100 * (1 - dte_diff / max(range_size, 1)))
            
            dte_metrics = {
                'target_dte_min': target_dte_min,
                'target_dte_max': target_dte_max,
                'actual_dte': actual_dte,
                'is_dte_compliant': is_dte_compliant,
                'dte_accuracy_percentage': dte_accuracy_percentage,
                'dte_target_range': f"{target_dte_min}-{target_dte_max}",
                'dte_compliance_status': 'COMPLIANT' if is_dte_compliant else 'NON_COMPLIANT'
            }
        
        # Overall compliance requires both delta and DTE compliance
        overall_compliant = is_delta_compliant and is_dte_compliant
        overall_accuracy = (delta_accuracy_percentage + dte_accuracy_percentage) / 2
        
        self.selection_accuracy = {
            # Delta accuracy
            'target_delta': target_delta,
            'actual_delta': actual_delta,
            'delta_difference': delta_diff,
            'tolerance': tolerance,
            'is_delta_compliant': is_delta_compliant,
            'delta_accuracy_percentage': delta_accuracy_percentage,
            
            # DTE accuracy
            **dte_metrics,
            
            # Overall metrics
            'is_compliant': overall_compliant,
            'accuracy_percentage': overall_accuracy,
            'available_options': available_options,
            'best_candidates': best_candidates[:3] if best_candidates else [],
            'selection_method': selection_method,
            'compliance_status': 'COMPLIANT' if overall_compliant else 'NON_COMPLIANT'
        }
    
    def set_exit_accuracy(self, exit_reason: str, target_pnl_percent: Optional[float] = None,
                         stop_loss_percent: Optional[float] = None, 
                         profit_target_percent: Optional[float] = None,
                         time_decay_threshold: Optional[int] = None,
                         min_dte_exit: Optional[int] = None, max_dte_exit: Optional[int] = None):
        """Set exit accuracy metrics for this trade"""
        exit_metrics = {
            'exit_reason': exit_reason,
            'actual_pnl_percent': self.pnl_percent,
            'days_held': (self.exit_date - self.date).days if self.exit_date else None,
            'exit_method_accuracy': 'ACCURATE'  # Default, will be refined below
        }
        
        # Analyze exit accuracy based on reason and targets
        if exit_reason == 'stop_loss' and stop_loss_percent:
            target_loss = -stop_loss_percent
            actual_loss = self.pnl_percent or 0
            exit_metrics['target_stop_loss'] = target_loss
            exit_metrics['stop_loss_accuracy'] = abs(actual_loss - target_loss)
            exit_metrics['exit_method_accuracy'] = 'ACCURATE' if actual_loss <= target_loss * 1.1 else 'LATE'
            
        elif exit_reason == 'profit_target' and profit_target_percent:
            target_profit = profit_target_percent
            actual_profit = self.pnl_percent or 0
            exit_metrics['target_profit_target'] = target_profit
            exit_metrics['profit_target_accuracy'] = abs(actual_profit - target_profit)
            exit_metrics['exit_method_accuracy'] = 'ACCURATE' if actual_profit >= target_profit * 0.9 else 'EARLY'
            
        elif exit_reason == 'time_decay':
            exit_metrics['exit_method_accuracy'] = 'EXPECTED'  # Time decay is expected
            if time_decay_threshold:
                exit_metrics['time_decay_threshold'] = time_decay_threshold
                
        # Add DTE exit timing analysis
        if self.dte and self.exit_dte:
            exit_metrics['entry_dte'] = self.dte
            exit_metrics['exit_dte'] = self.exit_dte
            exit_metrics['dte_change'] = self.dte - self.exit_dte
            exit_metrics['theta_decay_effect'] = (self.theta * exit_metrics['dte_change']) if self.theta else None
            
            # DTE exit timing accuracy
            if min_dte_exit is not None and max_dte_exit is not None:
                exit_metrics['target_exit_dte_min'] = min_dte_exit
                exit_metrics['target_exit_dte_max'] = max_dte_exit
                exit_metrics['exit_dte_target_range'] = f"{min_dte_exit}-{max_dte_exit}"
                
                # Check if exit DTE was within optimal range
                is_exit_dte_optimal = min_dte_exit <= self.exit_dte <= max_dte_exit
                exit_metrics['is_exit_dte_optimal'] = is_exit_dte_optimal
                
                if is_exit_dte_optimal:
                    exit_metrics['exit_dte_accuracy'] = 100.0
                    exit_metrics['exit_dte_timing'] = 'OPTIMAL'
                elif self.exit_dte < min_dte_exit:
                    # Exited too early (before optimal DTE range)
                    dte_diff = min_dte_exit - self.exit_dte
                    range_size = max_dte_exit - min_dte_exit
                    exit_metrics['exit_dte_accuracy'] = max(0, 100 * (1 - dte_diff / max(range_size, 1)))
                    exit_metrics['exit_dte_timing'] = 'EARLY'
                else:
                    # Exited too late (after optimal DTE range)
                    dte_diff = self.exit_dte - max_dte_exit
                    range_size = max_dte_exit - min_dte_exit
                    exit_metrics['exit_dte_accuracy'] = max(0, 100 * (1 - dte_diff / max(range_size, 1)))
                    exit_metrics['exit_dte_timing'] = 'LATE'
            
            # Analyze theta efficiency (how much theta decay was captured)
            if self.theta and self.exit_theta:
                avg_theta = (abs(self.theta) + abs(self.exit_theta)) / 2
                theta_captured = avg_theta * exit_metrics['dte_change']
                exit_metrics['theta_captured'] = theta_captured
                
                # Theta efficiency as percentage of potential theta decay
                max_theta_potential = abs(self.theta) * exit_metrics['dte_change']
                if max_theta_potential > 0:
                    exit_metrics['theta_efficiency'] = (theta_captured / max_theta_potential) * 100
                else:
                    exit_metrics['theta_efficiency'] = 0.0
            
        self.exit_accuracy = exit_metrics


@dataclass
class Position:
    """Represents an open options position"""
    position_id: str
    trades: List[Trade]
    
    @property
    def is_open(self) -> bool:
        """Check if position is still open"""
        total_quantity = sum(
            t.quantity if t.is_opening else -t.quantity 
            for t in self.trades
        )
        return total_quantity != 0
    
    @property
    def net_quantity(self) -> int:
        """Net quantity (positive for long, negative for short)"""
        return sum(
            t.quantity if t.order_type in [OrderType.BUY_TO_OPEN, OrderType.BUY_TO_CLOSE] 
            else -t.quantity for t in self.trades
        )
    
    @property
    def total_cost(self) -> float:
        """Total cost of the position"""
        return sum(t.total_cost for t in self.trades)
    
    @property
    def average_entry_price(self) -> float:
        """Average entry price for the position"""
        opening_trades = [t for t in self.trades if t.is_opening]
        if not opening_trades:
            return 0.0
        
        total_cost = sum(t.price * t.quantity for t in opening_trades)
        total_quantity = sum(t.quantity for t in opening_trades)
        
        return total_cost / total_quantity if total_quantity > 0 else 0.0


@dataclass
class Signal:
    """Trading signal generated by strategy"""
    signal_type: str  # 'entry', 'exit', 'adjust'
    action: str  # 'buy', 'sell'
    option_criteria: Dict[str, Any]  # Search criteria for option
    quantity: int
    reason: str
    confidence: float = 1.0
    
    # Selection accuracy metadata (for entry signals)
    selection_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Exit accuracy metadata (for exit signals)
    exit_metadata: Dict[str, Any] = field(default_factory=dict)
    
    
class StrategyBase(ABC):
    """Abstract base class for all trading strategies"""
    
    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.signals: List[Signal] = []
        self.current_date = None
        self.portfolio_value = params.get('initial_capital', 100000)
        
        # Set up logger for the strategy
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
    @abstractmethod
    def generate_signals(self, current_data: pd.DataFrame, 
                        market_data: Dict[str, Any]) -> List[Signal]:
        """Generate trading signals based on current market data"""
        pass
    
    @abstractmethod
    def should_exit_position(self, position: Position, 
                           current_data: pd.DataFrame) -> bool:
        """Determine if a position should be closed"""
        pass
    
    def add_trade(self, trade: Trade):
        """Add a trade to the strategy"""
        self.trades.append(trade)
        
        # Update or create position
        if trade.is_opening:
            # Create new position
            position_id = f"{trade.option_type}_{trade.strike}_{trade.expiration.strftime('%Y%m%d')}"
            if position_id in self.positions:
                self.positions[position_id].trades.append(trade)
            else:
                self.positions[position_id] = Position(position_id, [trade])
        else:
            # Find matching position to close
            position_id = f"{trade.option_type}_{trade.strike}_{trade.expiration.strftime('%Y%m%d')}"
            if position_id in self.positions:
                self.positions[position_id].trades.append(trade)
                
                # Remove position if fully closed
                if not self.positions[position_id].is_open:
                    del self.positions[position_id]
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        return [pos for pos in self.positions.values() if pos.is_open]
    
    def calculate_portfolio_value(self, current_data: pd.DataFrame) -> float:
        """Calculate current portfolio value"""
        cash = self.portfolio_value - sum(t.total_cost for t in self.trades)
        
        # Add current value of open positions
        positions_value = 0.0
        for position in self.get_open_positions():
            # Find current option price
            last_trade = position.trades[-1]
            option_data = self._find_option_in_data(
                current_data, last_trade.strike, 
                last_trade.option_type, last_trade.expiration
            )
            
            if option_data is not None:
                current_price = option_data['mid_price']
                positions_value += position.net_quantity * current_price * 100
        
        return cash + positions_value
    
    def _find_option_in_data(self, data: pd.DataFrame, strike: float, 
                           option_type: str, expiration: datetime) -> Optional[pd.Series]:
        """Find specific option in current data"""
        matches = data[
            (data['strike'] == strike) & 
            (data['right'] == option_type) & 
            (data['expiration'] == expiration)
        ]
        
        return matches.iloc[0] if not matches.empty else None
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Calculate basic performance metrics"""
        if not self.trades:
            return {}
        
        # Calculate total P&L
        total_pnl = sum(t.total_cost for t in self.trades)
        
        # Count winning and losing trades
        trade_pnls = []
        current_pnl = 0
        
        for trade in self.trades:
            current_pnl += trade.total_cost
            if trade.is_closing:
                trade_pnls.append(current_pnl)
                current_pnl = 0
        
        if not trade_pnls:
            return {'total_pnl': total_pnl}
        
        winning_trades = [pnl for pnl in trade_pnls if pnl > 0]
        losing_trades = [pnl for pnl in trade_pnls if pnl <= 0]
        
        return {
            'total_pnl': total_pnl,
            'total_trades': len(trade_pnls),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trade_pnls) if trade_pnls else 0,
            'avg_win': np.mean(winning_trades) if winning_trades else 0,
            'avg_loss': np.mean(losing_trades) if losing_trades else 0,
            'profit_factor': abs(sum(winning_trades) / sum(losing_trades)) if losing_trades else float('inf')
        }
    
    def reset(self):
        """Reset strategy state"""
        self.positions.clear()
        self.trades.clear()
        self.signals.clear()
        self.current_date = None
        self.portfolio_value = self.params.get('initial_capital', 100000)


class SimpleStrategy(StrategyBase):
    """Base class for simple strategies with common functionality"""
    
    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        
        # Common parameters
        self.delta_threshold = params.get('delta_threshold', 0.30)
        self.min_dte = params.get('min_dte', 10)
        self.max_dte = params.get('max_dte', 60)
        self.stop_loss_pct = params.get('stop_loss_pct', 0.50)
        self.profit_target_pct = params.get('profit_target_pct', 1.00)
        self.max_position_size = params.get('max_position_size', 0.05)
    
    def should_exit_position(self, position: Position, 
                           current_data: pd.DataFrame) -> Tuple[bool, str]:
        """Check if position should be closed based on P&L or time"""
        last_trade = position.trades[-1]
        
        # Find current option price
        option_data = self._find_option_in_data(
            current_data, last_trade.strike, 
            last_trade.option_type, last_trade.expiration
        )
        
        if option_data is None:
            return True, "option_not_found"  # Close if option not found
        
        # Check if approaching expiration (close if < 5 DTE)
        if option_data['dte'] <= 5:
            return True, "expiration"
        
        # Calculate current P&L
        current_price = option_data['mid_price']
        entry_price = position.average_entry_price
        
        if position.net_quantity > 0:  # Long position
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # Short position
            pnl_pct = (entry_price - current_price) / entry_price
        
        # Check stop loss
        if pnl_pct <= -self.stop_loss_pct:
            return True, "stop_loss"
        
        # Check profit target
        if pnl_pct >= self.profit_target_pct:
            return True, "profit_target"
        
        # Check time decay (close if DTE < 10)
        if option_data['dte'] <= 10:
            return True, "time_decay"
        
        return False, "none"