"""
Risk management utilities for options backtesting
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from strategy_base import Position, Trade
from portfolio_manager import PortfolioManager


@dataclass
class RiskMetrics:
    """Risk metrics for a portfolio"""
    portfolio_delta: float
    portfolio_gamma: float
    portfolio_theta: float
    portfolio_vega: float
    portfolio_rho: float
    var_95: float  # Value at Risk 95%
    max_position_value: float
    concentration_risk: float
    days_to_largest_expiration: int


class RiskManager:
    """Portfolio risk management and position sizing"""
    
    def __init__(self, max_portfolio_delta: float = 100,
                 max_position_size: float = 0.10,
                 max_single_position: float = 0.05,
                 var_limit: float = 0.02):
        """
        Initialize risk manager
        
        Args:
            max_portfolio_delta: Maximum net delta exposure
            max_position_size: Maximum position size as fraction of portfolio
            max_single_position: Maximum single position as fraction of portfolio  
            var_limit: Maximum VaR as fraction of portfolio
        """
        self.max_portfolio_delta = max_portfolio_delta
        self.max_position_size = max_position_size
        self.max_single_position = max_single_position
        self.var_limit = var_limit
        
    def calculate_portfolio_greeks(self, positions: List[Position], 
                                 current_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate portfolio-level Greeks"""
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        total_rho = 0.0
        
        for position in positions:
            if not position.is_open:
                continue
                
            last_trade = position.trades[-1]
            
            # Find current option data
            option_matches = current_data[
                (current_data['strike'] == last_trade.strike) &
                (current_data['right'] == last_trade.option_type) &
                (current_data['expiration'] == last_trade.expiration)
            ]
            
            if not option_matches.empty:
                option_data = option_matches.iloc[0]
                quantity = position.net_quantity
                
                # Aggregate Greeks
                total_delta += quantity * option_data.get('delta', 0)
                total_gamma += quantity * option_data.get('gamma', 0)
                total_theta += quantity * option_data.get('theta', 0)
                total_vega += quantity * option_data.get('vega', 0) / 100  # Vega per 1% vol
                total_rho += quantity * option_data.get('rho', 0) / 100    # Rho per 1% rate
        
        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'theta': total_theta,
            'vega': total_vega,
            'rho': total_rho
        }
    
    def calculate_var(self, portfolio_value: float, 
                     portfolio_delta: float,
                     underlying_price: float,
                     implied_vol: float = 0.20,
                     confidence: float = 0.95,
                     holding_period: int = 1) -> float:
        """
        Calculate Value at Risk using delta-normal method
        
        Args:
            portfolio_value: Current portfolio value
            portfolio_delta: Net portfolio delta
            underlying_price: Current underlying price
            implied_vol: Implied volatility for VaR calculation
            confidence: Confidence level (0.95 for 95% VaR)
            holding_period: Holding period in days
            
        Returns:
            VaR as dollar amount (positive number represents potential loss)
        """
        from scipy.stats import norm
        
        # Daily volatility
        daily_vol = implied_vol / np.sqrt(252)
        
        # Portfolio volatility (simplified - only considering delta risk)
        portfolio_vol = abs(portfolio_delta) * underlying_price * daily_vol * np.sqrt(holding_period)
        
        # VaR calculation
        z_score = norm.ppf(confidence)
        var_dollar = z_score * portfolio_vol
        
        return var_dollar
    
    def check_position_limits(self, portfolio_manager: PortfolioManager,
                            proposed_trade_value: float,
                            current_data: pd.DataFrame) -> Dict[str, bool]:
        """Check if proposed trade violates position limits"""
        portfolio_value = portfolio_manager.calculate_portfolio_value(current_data)
        
        checks = {}
        
        # Single position size check
        checks['single_position_ok'] = (
            proposed_trade_value <= portfolio_value * self.max_single_position
        )
        
        # Total position size check (sum of all open positions)
        positions_value, _ = portfolio_manager.calculate_positions_value(current_data)
        total_exposure = positions_value + proposed_trade_value
        checks['total_position_ok'] = (
            total_exposure <= portfolio_value * self.max_position_size
        )
        
        # Portfolio delta check
        current_greeks = self.calculate_portfolio_greeks(
            portfolio_manager.get_open_positions(), current_data
        )
        checks['delta_ok'] = abs(current_greeks['delta']) <= self.max_portfolio_delta
        
        # VaR check
        underlying_price = current_data['underlying_price'].iloc[0]
        var_estimate = self.calculate_var(
            portfolio_value, current_greeks['delta'], underlying_price
        )
        checks['var_ok'] = var_estimate <= portfolio_value * self.var_limit
        
        return checks
    
    def calculate_optimal_position_size(self, portfolio_value: float,
                                      option_price: float,
                                      option_delta: float,
                                      target_delta_exposure: float = 10) -> int:
        """
        Calculate optimal position size based on delta exposure
        
        Args:
            portfolio_value: Current portfolio value
            option_price: Price of the option
            option_delta: Delta of the option
            target_delta_exposure: Target delta exposure per position
            
        Returns:
            Optimal number of contracts
        """
        if abs(option_delta) < 0.01:  # Avoid division by very small deltas
            return 0
        
        # Calculate contracts needed for target delta exposure
        contracts_for_delta = int(target_delta_exposure / abs(option_delta))
        
        # Calculate contracts based on position size limit
        max_position_value = portfolio_value * self.max_single_position
        contracts_for_size = int(max_position_value / (option_price * 100))
        
        # Take minimum of both constraints
        optimal_contracts = min(contracts_for_delta, contracts_for_size)
        
        return max(1, optimal_contracts)  # At least 1 contract
    
    def assess_portfolio_risk(self, portfolio_manager: PortfolioManager,
                            current_data: pd.DataFrame) -> RiskMetrics:
        """Comprehensive portfolio risk assessment"""
        portfolio_value = portfolio_manager.calculate_portfolio_value(current_data)
        positions = portfolio_manager.get_open_positions()
        
        # Calculate Greeks
        greeks = self.calculate_portfolio_greeks(positions, current_data)
        
        # Calculate VaR
        underlying_price = current_data['underlying_price'].iloc[0]
        var_95 = self.calculate_var(portfolio_value, greeks['delta'], underlying_price)
        
        # Position concentration analysis
        position_values = []
        max_dte = 0
        
        for position in positions:
            last_trade = position.trades[-1]
            
            # Find current option data
            option_matches = current_data[
                (current_data['strike'] == last_trade.strike) &
                (current_data['right'] == last_trade.option_type) &
                (current_data['expiration'] == last_trade.expiration)
            ]
            
            if not option_matches.empty:
                option_data = option_matches.iloc[0]
                position_value = abs(position.net_quantity * option_data['mid_price'] * 100)
                position_values.append(position_value)
                max_dte = max(max_dte, option_data.get('dte', 0))
        
        # Concentration risk (largest position as % of portfolio)
        max_position_value = max(position_values) if position_values else 0
        concentration_risk = max_position_value / portfolio_value if portfolio_value > 0 else 0
        
        return RiskMetrics(
            portfolio_delta=greeks['delta'],
            portfolio_gamma=greeks['gamma'],
            portfolio_theta=greeks['theta'],
            portfolio_vega=greeks['vega'],
            portfolio_rho=greeks['rho'],
            var_95=var_95,
            max_position_value=max_position_value,
            concentration_risk=concentration_risk,
            days_to_largest_expiration=max_dte
        )
    
    def generate_risk_alerts(self, risk_metrics: RiskMetrics,
                           portfolio_value: float) -> List[str]:
        """Generate risk alerts based on current portfolio state"""
        alerts = []
        
        # Delta exposure alert
        if abs(risk_metrics.portfolio_delta) > self.max_portfolio_delta:
            alerts.append(f"HIGH DELTA EXPOSURE: {risk_metrics.portfolio_delta:.1f} "
                         f"(limit: {self.max_portfolio_delta})")
        
        # VaR alert
        var_pct = risk_metrics.var_95 / portfolio_value if portfolio_value > 0 else 0
        if var_pct > self.var_limit:
            alerts.append(f"VaR LIMIT EXCEEDED: {var_pct:.2%} "
                         f"(limit: {self.var_limit:.2%})")
        
        # Concentration alert
        if risk_metrics.concentration_risk > self.max_single_position:
            alerts.append(f"HIGH CONCENTRATION: {risk_metrics.concentration_risk:.2%} "
                         f"(limit: {self.max_single_position:.2%})")
        
        # Theta decay alert
        if risk_metrics.portfolio_theta < -50:  # Arbitrary threshold
            alerts.append(f"HIGH THETA DECAY: ${risk_metrics.portfolio_theta:.2f}/day")
        
        # Near expiration alert
        if risk_metrics.days_to_largest_expiration <= 5:
            alerts.append(f"POSITIONS NEAR EXPIRATION: {risk_metrics.days_to_largest_expiration} DTE")
        
        return alerts
    
    def suggest_hedge_trades(self, risk_metrics: RiskMetrics,
                           current_data: pd.DataFrame,
                           portfolio_value: float) -> List[Dict]:
        """Suggest hedge trades to reduce portfolio risk"""
        suggestions = []
        
        # Delta hedging suggestion
        if abs(risk_metrics.portfolio_delta) > self.max_portfolio_delta:
            hedge_delta_needed = -risk_metrics.portfolio_delta * 0.5  # Hedge 50% of excess
            
            # Find ATM option for hedging
            underlying_price = current_data['underlying_price'].iloc[0]
            atm_options = current_data[
                (abs(current_data['strike'] - underlying_price) <= 5) &
                (current_data['dte'] >= 20) &
                (current_data['dte'] <= 45)
            ]
            
            if not atm_options.empty:
                # Choose call or put based on hedge direction
                if hedge_delta_needed > 0:
                    hedge_option = atm_options[atm_options['right'] == 'C'].iloc[0]
                else:
                    hedge_option = atm_options[atm_options['right'] == 'P'].iloc[0]
                
                contracts_needed = int(abs(hedge_delta_needed / hedge_option['delta']))
                
                suggestions.append({
                    'type': 'delta_hedge',
                    'action': 'buy' if hedge_delta_needed > 0 else 'sell',
                    'option_type': hedge_option['right'],
                    'strike': hedge_option['strike'],
                    'expiration': hedge_option['expiration'],
                    'quantity': contracts_needed,
                    'reason': f"Hedge excess delta exposure of {risk_metrics.portfolio_delta:.1f}"
                })
        
        return suggestions


def calculate_kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Calculate Kelly Criterion for position sizing
    
    Args:
        win_rate: Historical win rate (0.0 to 1.0)
        avg_win: Average winning trade amount
        avg_loss: Average losing trade amount (positive number)
        
    Returns:
        Kelly percentage (fraction of capital to risk)
    """
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    
    # Kelly formula: f = (bp - q) / b
    # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - win_rate
    
    kelly_fraction = (b * p - q) / b
    
    # Cap at reasonable maximum (25%)
    return min(max(kelly_fraction, 0.0), 0.25)


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """Calculate Sharpe ratio from returns series"""
    if not returns or len(returns) < 2:
        return 0.0
    
    excess_returns = np.array(returns) - risk_free_rate / 252  # Daily risk-free rate
    
    if np.std(excess_returns) == 0:
        return 0.0
    
    return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)


def calculate_maximum_drawdown(portfolio_values: List[float]) -> float:
    """Calculate maximum drawdown from portfolio value series"""
    if not portfolio_values:
        return 0.0
    
    peak = portfolio_values[0]
    max_drawdown = 0.0
    
    for value in portfolio_values:
        if value > peak:
            peak = value
        
        drawdown = (peak - value) / peak
        max_drawdown = max(max_drawdown, drawdown)
    
    return max_drawdown