"""
Greeks Calculator for Tradier Options
Real-time Greeks calculation for options positions
"""

import numpy as np
from scipy.stats import norm
from typing import Dict, Optional, Tuple
from datetime import datetime, time
import math
import pytz

class GreeksCalculator:
    """Calculate option Greeks using Black-Scholes model"""
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize Greeks calculator
        
        Args:
            risk_free_rate: Annual risk-free rate (default 5%)
        """
        self.r = risk_free_rate
        # Market operates in Eastern Time
        self.ET = pytz.timezone('US/Eastern')
    
    def calculate_time_to_expiry(self, expiry_date: str) -> float:
        """
        Calculate time to expiry in years (fraction of day for 0DTE)
        
        Args:
            expiry_date: Expiry date string (YYYY-MM-DD)
            
        Returns:
            Time to expiry in years
        """
        # Get current time in ET (market timezone)
        now_et = datetime.now(self.ET)
        
        # Parse expiry date
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        
        # For 0DTE, calculate fraction of trading day remaining
        if expiry.date() == now_et.date():
            # Market closes at 4:00 PM ET
            close_time_et = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
            
            # If after close in ET, return 0
            if now_et >= close_time_et:
                return 0.0
            
            # Calculate fraction of day remaining (in years)
            seconds_remaining = (close_time_et - now_et).total_seconds()
            # Trading day is 6.5 hours (390 minutes)
            trading_seconds = 6.5 * 3600
            
            # Fraction of year = fraction of day / 252 trading days
            return max((seconds_remaining / trading_seconds) / 252, 1e-6)
        
        # For future dates
        # Set expiry to 4:00 PM ET on expiry date
        expiry_et = self.ET.localize(expiry.replace(hour=16, minute=0, second=0, microsecond=0))
        time_diff = (expiry_et - now_et).total_seconds()
        
        # Convert to years (365 days per year for consistency)
        days_to_expiry = time_diff / (24 * 3600)
        return max(days_to_expiry / 365, 1e-6)
    
    def calculate_iv_from_price(self, option_price: float, spot: float, 
                               strike: float, time_to_expiry: float, 
                               option_type: str) -> float:
        """
        Calculate implied volatility from option price using Newton-Raphson
        
        Args:
            option_price: Current option price
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiry in years
            option_type: 'call' or 'put'
            
        Returns:
            Implied volatility (annualized)
        """
        # Initial guess based on rule of thumb
        # Avoid divide by zero when time_to_expiry is very small
        if time_to_expiry <= 1e-6:
            iv_guess = 0.15  # Default to 15% for expired/near-expired options
        else:
            iv_guess = option_price / (spot * np.sqrt(time_to_expiry)) * 2.5
        
        # Bounds
        iv_min = 0.01
        iv_max = 5.0
        
        # Newton-Raphson iterations
        for _ in range(50):
            iv_guess = max(iv_min, min(iv_max, iv_guess))
            
            # Calculate option price with current IV guess
            greeks = self.calculate_greeks(spot, strike, time_to_expiry, 
                                          iv_guess, option_type)
            theoretical_price = self.calculate_option_price(spot, strike, 
                                                           time_to_expiry, 
                                                           iv_guess, option_type)
            
            # Check convergence
            diff = theoretical_price - option_price
            if abs(diff) < 0.001:
                return iv_guess
            
            # Update guess using vega
            vega = greeks['vega']
            if vega > 0.0001:
                iv_guess = iv_guess - diff / (vega * 100)
            else:
                # Fallback to bisection if vega too small
                if diff > 0:
                    iv_max = iv_guess
                else:
                    iv_min = iv_guess
                iv_guess = (iv_min + iv_max) / 2
        
        return iv_guess
    
    def calculate_option_price(self, spot: float, strike: float, 
                              time_to_expiry: float, volatility: float, 
                              option_type: str) -> float:
        """
        Calculate theoretical option price using Black-Scholes
        
        Args:
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility
            option_type: 'call' or 'put'
            
        Returns:
            Theoretical option price
        """
        if time_to_expiry <= 0:
            # At expiry
            if option_type.lower() == 'call':
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)
        
        # Calculate d1 and d2 with protection against divide by zero
        sqrt_time = np.sqrt(max(time_to_expiry, 1e-6))
        d1 = (np.log(spot / strike) + (self.r + 0.5 * volatility ** 2) * time_to_expiry) / \
             (volatility * sqrt_time)
        d2 = d1 - volatility * sqrt_time
        
        if option_type.lower() == 'call':
            price = spot * norm.cdf(d1) - strike * np.exp(-self.r * time_to_expiry) * norm.cdf(d2)
        else:
            price = strike * np.exp(-self.r * time_to_expiry) * norm.cdf(-d2) - spot * norm.cdf(-d1)
        
        return price
    
    def calculate_greeks(self, spot: float, strike: float, time_to_expiry: float,
                        volatility: float, option_type: str) -> Dict[str, float]:
        """
        Calculate all Greeks for an option
        
        Args:
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (annualized)
            option_type: 'call' or 'put'
            
        Returns:
            Dictionary with delta, gamma, theta, vega, rho
        """
        # Handle edge cases
        if time_to_expiry <= 0:
            # At expiration
            if option_type.lower() == 'call':
                delta = 1.0 if spot > strike else 0.0
            else:
                delta = -1.0 if spot < strike else 0.0
            return {
                'delta': delta,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0
            }
        
        # Ensure volatility is positive
        if volatility <= 0:
            volatility = 0.01
        
        # Calculate d1 and d2 with protection against divide by zero
        sqrt_time = np.sqrt(max(time_to_expiry, 1e-6))
        d1 = (np.log(spot / strike) + (self.r + 0.5 * volatility ** 2) * time_to_expiry) / \
             (volatility * sqrt_time)
        d2 = d1 - volatility * sqrt_time
        
        # Common calculations
        n_d1 = norm.pdf(d1)
        N_d1 = norm.cdf(d1)
        N_d2 = norm.cdf(d2)
        
        # Delta
        if option_type.lower() == 'call':
            delta = N_d1
        else:
            delta = N_d1 - 1
        
        # Gamma (same for calls and puts)
        gamma = n_d1 / (spot * volatility * sqrt_time)
        
        # Theta (per day, not per year)
        # Standard Black-Scholes theta formula
        if option_type.lower() == 'call':
            theta = (-spot * n_d1 * volatility / (2 * sqrt_time) 
                     - self.r * strike * np.exp(-self.r * time_to_expiry) * N_d2) / 365
        else:  # put
            theta = (-spot * n_d1 * volatility / (2 * sqrt_time) 
                     + self.r * strike * np.exp(-self.r * time_to_expiry) * norm.cdf(-d2)) / 365
        
        # Vega (per 1% change in volatility)
        vega = spot * n_d1 * sqrt_time / 100
        
        # Rho (per 1% change in interest rate)
        if option_type.lower() == 'call':
            rho = strike * time_to_expiry * np.exp(-self.r * time_to_expiry) * N_d2 / 100
        else:
            rho = -strike * time_to_expiry * np.exp(-self.r * time_to_expiry) * norm.cdf(-d2) / 100
        
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho
        }
    
    def calculate_strangle_greeks(self, spot: float, call_strike: float, 
                                 put_strike: float, time_to_expiry: float,
                                 call_iv: float, put_iv: float,
                                 call_qty: int = -1, put_qty: int = -1) -> Dict[str, float]:
        """
        Calculate combined Greeks for a strangle position
        
        Args:
            spot: Current underlying price
            call_strike: Call strike price
            put_strike: Put strike price
            time_to_expiry: Time to expiry in years
            call_iv: Call implied volatility
            put_iv: Put implied volatility
            call_qty: Call position quantity (negative for short)
            put_qty: Put position quantity (negative for short)
            
        Returns:
            Dictionary with combined Greeks
        """
        # Calculate individual Greeks
        call_greeks = self.calculate_greeks(spot, call_strike, time_to_expiry, 
                                           call_iv, 'call')
        put_greeks = self.calculate_greeks(spot, put_strike, time_to_expiry, 
                                          put_iv, 'put')
        
        # Combine based on position quantities
        combined = {
            'delta': call_qty * call_greeks['delta'] + put_qty * put_greeks['delta'],
            'gamma': call_qty * call_greeks['gamma'] + put_qty * put_greeks['gamma'],
            'theta': call_qty * call_greeks['theta'] + put_qty * put_greeks['theta'],
            'vega': call_qty * call_greeks['vega'] + put_qty * put_greeks['vega'],
            'rho': call_qty * call_greeks['rho'] + put_qty * put_greeks['rho'],
            
            # Individual Greeks for reference
            'call_delta': call_greeks['delta'],
            'put_delta': put_greeks['delta'],
            'call_vega': call_greeks['vega'],
            'put_vega': put_greeks['vega']
        }
        
        return combined