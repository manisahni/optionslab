"""
Portfolio management for options backtesting
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass
import uuid

from strategy_base import Trade, Position, OrderType, PositionType
from config import COMMISSION_PER_CONTRACT, BID_ASK_SPREAD_FACTOR


@dataclass
class PortfolioSnapshot:
    """Portfolio state at a point in time"""
    date: datetime
    cash: float
    positions_value: float
    total_value: float
    num_positions: int
    daily_pnl: float
    total_pnl: float


class PortfolioManager:
    """Manages portfolio state and executes trades"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.snapshots: List[PortfolioSnapshot] = []
        self.trade_counter = 0
        
    def execute_trade(self, option_data: pd.Series, quantity: int, 
                     order_type: OrderType, date: datetime, 
                     selection_metadata: Dict[str, Any] = None) -> Optional[Trade]:
        """Execute a trade and update portfolio"""
        
        # Calculate execution price (mid + spread factor)
        if order_type in [OrderType.BUY_TO_OPEN, OrderType.BUY_TO_CLOSE]:
            # Buying - pay ask or mid + spread
            execution_price = option_data['ask'] if 'ask' in option_data else \
                            option_data['mid_price'] * (1 + BID_ASK_SPREAD_FACTOR)
        else:
            # Selling - receive bid or mid - spread
            execution_price = option_data['bid'] if 'bid' in option_data else \
                            option_data['mid_price'] * (1 - BID_ASK_SPREAD_FACTOR)
        
        # Calculate commission
        commission = abs(quantity) * COMMISSION_PER_CONTRACT
        
        # Create enhanced trade with complete data
        self.trade_counter += 1
        date_str = date.strftime('%Y%m%d')
        trade_id = f"{date_str}-{self.trade_counter:03d}"
        
        # Parse expiration date properly
        expiration_date = None
        if 'expiration' in option_data and pd.notna(option_data['expiration']):
            if isinstance(option_data['expiration'], str):
                expiration_date = pd.to_datetime(option_data['expiration'])
            else:
                expiration_date = option_data['expiration']
        
        trade = Trade(
            trade_id=trade_id,
            date=date,
            symbol="SPY",
            strike=float(option_data['strike']),
            expiration=expiration_date,
            option_type=option_data['right'],
            position_type=PositionType.LONG if order_type in [OrderType.BUY_TO_OPEN, OrderType.BUY_TO_CLOSE] else PositionType.SHORT,
            order_type=order_type,
            quantity=abs(quantity),
            price=execution_price,
            commission=commission,
            underlying_price=float(option_data.get('underlying_price', 0)),
            delta=float(option_data.get('delta', 0)),
            gamma=float(option_data.get('gamma', 0)),
            theta=float(option_data.get('theta', 0)),
            vega=float(option_data.get('vega', 0)),
            rho=float(option_data.get('rho', 0)),
            implied_vol=float(option_data.get('implied_volatility', option_data.get('implied_vol', 0))),
            dte=int(option_data.get('dte', 0)),
            strategy_name=getattr(self, 'current_strategy_name', 'unknown')
        )
        
        # Generate contract symbol
        trade.contract_symbol = trade.generate_contract_symbol()
        
        # Set selection accuracy if provided (for opening trades)
        if selection_metadata and order_type in [OrderType.BUY_TO_OPEN, OrderType.SELL_TO_OPEN]:
            trade.set_selection_accuracy(
                target_delta=selection_metadata.get('target_delta', 0),
                actual_delta=selection_metadata.get('actual_delta', trade.delta),
                tolerance=selection_metadata.get('tolerance', 0.05),
                available_options=selection_metadata.get('available_options', 0),
                best_candidates=selection_metadata.get('best_candidates', []),
                selection_method=selection_metadata.get('selection_method', 'unknown'),
                target_dte_min=selection_metadata.get('target_dte_min'),
                target_dte_max=selection_metadata.get('target_dte_max'),
                actual_dte=trade.dte
            )
        
        # Check if we have enough cash/margin
        if not self._can_execute_trade(trade):
            return None
        
        # Update cash
        self.cash -= trade.total_cost
        
        # Update positions
        self._update_positions(trade)
        
        # Add to trades list
        self.trades.append(trade)
        
        return trade
    
    def close_trade_with_exit_data(self, opening_trade: Trade, option_data: pd.Series, 
                                  quantity: int, order_type: OrderType, date: datetime, 
                                  exit_reason: str, strategy_params: Dict[str, Any] = None) -> Optional[Trade]:
        """Close a trade and record comprehensive exit data"""
        
        # Execute the closing trade
        closing_trade = self.execute_trade(option_data, quantity, order_type, date)
        
        if closing_trade:
            # Update the original opening trade with exit information
            opening_trade.update_exit_data(date, closing_trade.price, option_data, exit_reason)
            
            # Set exit accuracy metrics
            if strategy_params:
                stop_loss_percent = strategy_params.get('stop_loss_percent')
                profit_target_percent = strategy_params.get('profit_target_percent')
                time_decay_threshold = strategy_params.get('min_dte')
                min_dte_exit = strategy_params.get('min_dte')  # Optimal exit range min
                max_dte_exit = min(strategy_params.get('max_dte', 60), 21)  # Optimal exit range max (21 days or less)
                
                opening_trade.set_exit_accuracy(
                    exit_reason=exit_reason,
                    stop_loss_percent=stop_loss_percent,
                    profit_target_percent=profit_target_percent,
                    time_decay_threshold=time_decay_threshold,
                    min_dte_exit=5,  # Optimal to exit when > 5 DTE (avoid pin risk)
                    max_dte_exit=max_dte_exit
                )
            
            # Add detailed logging
            print(f"📋 {opening_trade.to_detailed_log_string()}")
            
        return closing_trade
    
    def set_strategy_name(self, strategy_name: str):
        """Set current strategy name for trade logging"""
        self.current_strategy_name = strategy_name
    
    def _can_execute_trade(self, trade: Trade) -> bool:
        """Check if trade can be executed (sufficient cash/margin)"""
        if trade.order_type in [OrderType.BUY_TO_OPEN, OrderType.BUY_TO_CLOSE]:
            # Buying requires cash
            return self.cash >= trade.total_cost
        else:
            # Selling - for now, assume always allowed (simplified margin)
            return True
    
    def _update_positions(self, trade: Trade):
        """Update position tracking"""
        position_key = f"{trade.option_type}_{trade.strike}_{trade.expiration.strftime('%Y%m%d')}"
        
        if position_key in self.positions:
            self.positions[position_key].trades.append(trade)
            
            # Check if position is closed
            if not self.positions[position_key].is_open:
                del self.positions[position_key]
        else:
            # New position
            if trade.is_opening:
                self.positions[position_key] = Position(position_key, [trade])
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        return list(self.positions.values())
    
    def calculate_positions_value(self, current_data: pd.DataFrame) -> Tuple[float, Dict[str, float]]:
        """Calculate current value of all positions"""
        total_value = 0.0
        position_values = {}
        
        for position_key, position in self.positions.items():
            last_trade = position.trades[-1]
            
            # Find current option price
            option_matches = current_data[
                (current_data['strike'] == last_trade.strike) &
                (current_data['right'] == last_trade.option_type) &
                (current_data['expiration'] == last_trade.expiration)
            ]
            
            if not option_matches.empty:
                current_price = option_matches.iloc[0]['mid_price']
                position_value = position.net_quantity * current_price * 100
                position_values[position_key] = position_value
                total_value += position_value
            else:
                # Option expired or not found - assume worthless
                position_values[position_key] = 0.0
        
        return total_value, position_values
    
    def calculate_portfolio_value(self, current_data: pd.DataFrame) -> float:
        """Calculate total portfolio value"""
        positions_value, _ = self.calculate_positions_value(current_data)
        return self.cash + positions_value
    
    def calculate_greeks(self, current_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate portfolio-level Greeks"""
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        total_rho = 0.0
        
        for position in self.positions.values():
            last_trade = position.trades[-1]
            
            # Find current option Greeks
            option_matches = current_data[
                (current_data['strike'] == last_trade.strike) &
                (current_data['right'] == last_trade.option_type) &
                (current_data['expiration'] == last_trade.expiration)
            ]
            
            if not option_matches.empty:
                option_data = option_matches.iloc[0]
                quantity = position.net_quantity
                
                total_delta += quantity * option_data.get('delta', 0)
                total_gamma += quantity * option_data.get('gamma', 0)
                total_theta += quantity * option_data.get('theta', 0)
                total_vega += quantity * option_data.get('vega', 0) / 100  # Vega per 1% vol change
                total_rho += quantity * option_data.get('rho', 0) / 100    # Rho per 1% rate change
        
        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'theta': total_theta,
            'vega': total_vega,
            'rho': total_rho
        }
    
    def generate_daily_performance_log(self, date: datetime, current_data: pd.DataFrame) -> str:
        """Generate comprehensive daily performance log"""
        
        # Calculate current portfolio metrics
        portfolio_value = self.calculate_portfolio_value(current_data)
        daily_pnl = portfolio_value - (self.snapshots[-1].total_value if self.snapshots else self.initial_capital)
        total_pnl = portfolio_value - self.initial_capital
        
        # Count trades for the day
        daily_trades = [t for t in self.trades if t.date.date() == date.date()]
        opening_trades = [t for t in daily_trades if t.is_opening]
        closing_trades = [t for t in daily_trades if t.is_closing]
        
        # Count open positions
        open_positions = len([p for p in self.positions.values() if p.is_open])
        
        # Calculate position values
        positions_value, _ = self.calculate_positions_value(current_data)
        
        # Calculate max drawdown for the period
        max_value = max([s.total_value for s in self.snapshots], default=self.initial_capital)
        max_drawdown = (max_value - portfolio_value) / max_value * 100 if max_value > 0 else 0
        
        # Generate log string
        log_parts = [
            f"📅 DAILY SUMMARY - {date.strftime('%Y-%m-%d')}",
            "=" * 50,
            f"Portfolio Value: ${portfolio_value:,.2f}",
            f"Cash: ${self.cash:,.2f}",
            f"Positions Value: ${positions_value:,.2f}",
            f"Daily P&L: ${daily_pnl:,.2f}",
            f"Total P&L: ${total_pnl:,.2f} ({(total_pnl/self.initial_capital)*100:.2f}%)",
            f"Open Positions: {open_positions}",
            f"Daily Trades: {len(opening_trades)} entries, {len(closing_trades)} exits",
            f"Max Drawdown: {max_drawdown:.2f}%"
        ]
        
        # Add Greeks if positions exist
        if open_positions > 0:
            greeks = self.calculate_greeks(current_data)
            log_parts.extend([
                "Portfolio Greeks:",
                f"  Delta: {greeks['delta']:+.2f}",
                f"  Gamma: {greeks['gamma']:+.4f}",
                f"  Theta: {greeks['theta']:+.2f}",
                f"  Vega: {greeks['vega']:+.2f}"
            ])
        
        return "\n".join(log_parts)
    
    def take_snapshot(self, date: datetime, current_data: pd.DataFrame):
        """Take a snapshot of portfolio state"""
        positions_value, _ = self.calculate_positions_value(current_data)
        total_value = self.cash + positions_value
        
        # Calculate daily P&L
        daily_pnl = 0.0
        if self.snapshots:
            daily_pnl = total_value - self.snapshots[-1].total_value
        
        snapshot = PortfolioSnapshot(
            date=date,
            cash=self.cash,
            positions_value=positions_value,
            total_value=total_value,
            num_positions=len(self.positions),
            daily_pnl=daily_pnl,
            total_pnl=total_value - self.initial_capital
        )
        
        self.snapshots.append(snapshot)
    
    def get_performance_summary(self) -> Dict[str, float]:
        """Get performance summary statistics"""
        if not self.snapshots:
            return {}
        
        # Extract values
        values = [s.total_value for s in self.snapshots]
        daily_returns = [s.daily_pnl / self.snapshots[i-1].total_value 
                        for i, s in enumerate(self.snapshots[1:], 1)]
        
        # Calculate metrics
        total_return = (values[-1] - self.initial_capital) / self.initial_capital
        
        if daily_returns:
            avg_daily_return = np.mean(daily_returns)
            daily_vol = np.std(daily_returns)
            sharpe_ratio = avg_daily_return / daily_vol * np.sqrt(252) if daily_vol > 0 else 0
            
            # Maximum drawdown
            peak = values[0]
            max_drawdown = 0
            for value in values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
        else:
            avg_daily_return = 0
            daily_vol = 0
            sharpe_ratio = 0
            max_drawdown = 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': values[-1],
            'total_return': total_return,
            'total_pnl': values[-1] - self.initial_capital,
            'num_trades': len(self.trades),
            'num_positions': len(self.positions),
            'avg_daily_return': avg_daily_return,
            'daily_volatility': daily_vol,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'current_cash': self.cash
        }
    
    def get_trades_df(self) -> pd.DataFrame:
        """Get trades as DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        
        trades_data = []
        for trade in self.trades:
            # Base trade data
            trade_dict = {
                'trade_id': trade.trade_id,
                'date': trade.date,
                'strike': trade.strike,
                'expiration': trade.expiration,
                'option_type': trade.option_type,
                'order_type': trade.order_type.value,
                'quantity': trade.quantity,
                'price': trade.price,
                'commission': trade.commission,
                'total_cost': trade.total_cost,
                'underlying_price': trade.underlying_price,
                'delta': trade.delta,
                'dte': trade.dte,
                'implied_vol': trade.implied_vol,
                'exit_reason': trade.exit_reason if hasattr(trade, 'exit_reason') and trade.is_opening else ''
            }
            
            # Add Selection Accuracy metrics if available
            if hasattr(trade, 'selection_accuracy') and trade.selection_accuracy:
                sa = trade.selection_accuracy
                trade_dict.update({
                    'Selection_Target_Delta': sa.get('target_delta', ''),
                    'Selection_Actual_Delta': sa.get('actual_delta', ''),
                    'Selection_Delta_Difference': sa.get('delta_difference', ''),
                    'Selection_Tolerance': sa.get('tolerance', ''),
                    'Selection_Is_Compliant': sa.get('is_compliant', ''),
                    'Selection_Accuracy_Percentage': sa.get('accuracy_percentage', ''),
                    'Selection_Available_Options': sa.get('available_options', ''),
                    'Selection_Method': sa.get('selection_method', ''),
                    'Selection_Compliance_Status': sa.get('compliance_status', ''),
                    # DTE Selection Accuracy
                    'Selection_Target_DTE_Min': sa.get('target_dte_min', ''),
                    'Selection_Target_DTE_Max': sa.get('target_dte_max', ''),
                    'Selection_Actual_DTE': sa.get('actual_dte', ''),
                    'Selection_Is_DTE_Compliant': sa.get('is_dte_compliant', ''),
                    'Selection_DTE_Accuracy_Percentage': sa.get('dte_accuracy_percentage', ''),
                    'Selection_DTE_Target_Range': sa.get('dte_target_range', ''),
                    'Selection_DTE_Compliance_Status': sa.get('dte_compliance_status', '')
                })
            else:
                # Add empty columns for consistency
                trade_dict.update({
                    'Selection_Target_Delta': '',
                    'Selection_Actual_Delta': '',
                    'Selection_Delta_Difference': '',
                    'Selection_Tolerance': '',
                    'Selection_Is_Compliant': '',
                    'Selection_Accuracy_Percentage': '',
                    'Selection_Available_Options': '',
                    'Selection_Method': '',
                    'Selection_Compliance_Status': '',
                    # DTE Selection Accuracy
                    'Selection_Target_DTE_Min': '',
                    'Selection_Target_DTE_Max': '',
                    'Selection_Actual_DTE': '',
                    'Selection_Is_DTE_Compliant': '',
                    'Selection_DTE_Accuracy_Percentage': '',
                    'Selection_DTE_Target_Range': '',
                    'Selection_DTE_Compliance_Status': ''
                })
            
            # Add Exit Accuracy metrics if available (only for opening trades)
            if hasattr(trade, 'exit_accuracy') and trade.exit_accuracy and trade.is_opening:
                ea = trade.exit_accuracy
                trade_dict.update({
                    'Exit_Reason': ea.get('exit_reason', ''),
                    'Exit_Actual_PnL_Percent': ea.get('actual_pnl_percent', ''),
                    'Exit_Days_Held': ea.get('days_held', ''),
                    'Exit_Method_Accuracy': ea.get('exit_method_accuracy', ''),
                    'Exit_Target_Stop_Loss': ea.get('target_stop_loss', ''),
                    'Exit_Target_Profit_Target': ea.get('target_profit_target', ''),
                    'Exit_Stop_Loss_Accuracy': ea.get('stop_loss_accuracy', ''),
                    'Exit_Profit_Target_Accuracy': ea.get('profit_target_accuracy', ''),
                    'Exit_DTE_Change': ea.get('dte_change', ''),
                    'Exit_Theta_Decay_Effect': ea.get('theta_decay_effect', ''),
                    # DTE Exit Accuracy
                    'Exit_Entry_DTE': ea.get('entry_dte', ''),
                    'Exit_Exit_DTE': ea.get('exit_dte', ''),
                    'Exit_DTE_Timing': ea.get('exit_dte_timing', ''),
                    'Exit_DTE_Accuracy': ea.get('exit_dte_accuracy', ''),
                    'Exit_Target_DTE_Min': ea.get('target_exit_dte_min', ''),
                    'Exit_Target_DTE_Max': ea.get('target_exit_dte_max', ''),
                    'Exit_DTE_Target_Range': ea.get('exit_dte_target_range', ''),
                    'Exit_Is_DTE_Optimal': ea.get('is_exit_dte_optimal', ''),
                    'Exit_Theta_Captured': ea.get('theta_captured', ''),
                    'Exit_Theta_Efficiency': ea.get('theta_efficiency', '')
                })
            else:
                # Add empty columns for consistency
                trade_dict.update({
                    'Exit_Reason': '',
                    'Exit_Actual_PnL_Percent': '',
                    'Exit_Days_Held': '',
                    'Exit_Method_Accuracy': '',
                    'Exit_Target_Stop_Loss': '',
                    'Exit_Target_Profit_Target': '',
                    'Exit_Stop_Loss_Accuracy': '',
                    'Exit_Profit_Target_Accuracy': '',
                    'Exit_DTE_Change': '',
                    'Exit_Theta_Decay_Effect': '',
                    # DTE Exit Accuracy
                    'Exit_Entry_DTE': '',
                    'Exit_Exit_DTE': '',
                    'Exit_DTE_Timing': '',
                    'Exit_DTE_Accuracy': '',
                    'Exit_Target_DTE_Min': '',
                    'Exit_Target_DTE_Max': '',
                    'Exit_DTE_Target_Range': '',
                    'Exit_Is_DTE_Optimal': '',
                    'Exit_Theta_Captured': '',
                    'Exit_Theta_Efficiency': ''
                })
            
            trades_data.append(trade_dict)
        
        return pd.DataFrame(trades_data)
    
    def get_snapshots_df(self) -> pd.DataFrame:
        """Get portfolio snapshots as DataFrame"""
        if not self.snapshots:
            return pd.DataFrame()
        
        snapshots_data = []
        for snapshot in self.snapshots:
            snapshots_data.append({
                'date': snapshot.date,
                'cash': snapshot.cash,
                'positions_value': snapshot.positions_value,
                'total_value': snapshot.total_value,
                'num_positions': snapshot.num_positions,
                'daily_pnl': snapshot.daily_pnl,
                'total_pnl': snapshot.total_pnl
            })
        
        return pd.DataFrame(snapshots_data)
    
    def reset(self):
        """Reset portfolio to initial state"""
        self.cash = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.snapshots.clear()
        self.trade_counter = 0