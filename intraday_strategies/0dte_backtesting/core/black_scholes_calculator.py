#!/usr/bin/env python3
"""Black-Scholes calculator for correcting delta values"""

import numpy as np
from scipy.stats import norm
import pandas as pd
from typing import Dict, Tuple, Optional

class BlackScholesCalculator:
    """Calculate option Greeks using Black-Scholes model"""
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize calculator
        
        Args:
            risk_free_rate: Annual risk-free rate (default 5%)
        """
        self.r = risk_free_rate
    
    def calculate_greeks(self, 
                        spot: float, 
                        strike: float, 
                        time_to_expiry: float,
                        volatility: float,
                        option_type: str) -> Dict[str, float]:
        """
        Calculate all Greeks for an option
        
        Args:
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            volatility: Implied volatility (annualized)
            option_type: 'CALL' or 'PUT'
            
        Returns:
            Dictionary with delta, gamma, theta, vega, rho
        """
        # Handle edge cases
        if time_to_expiry <= 0:
            # At expiration
            if option_type == 'CALL':
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
        
        # Ensure volatility is reasonable
        if volatility <= 0 or np.isnan(volatility):
            volatility = 0.15  # Default 15% vol if missing/invalid
        
        # Calculate d1 and d2
        d1 = (np.log(spot / strike) + (self.r + 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
        d2 = d1 - volatility * np.sqrt(time_to_expiry)
        
        # Common calculations
        sqrt_t = np.sqrt(time_to_expiry)
        exp_rt = np.exp(-self.r * time_to_expiry)
        
        # Calculate Greeks
        if option_type == 'CALL':
            delta = norm.cdf(d1)
            theta = (-spot * norm.pdf(d1) * volatility / (2 * sqrt_t) 
                     - self.r * strike * exp_rt * norm.cdf(d2)) / 365
            rho = strike * time_to_expiry * exp_rt * norm.cdf(d2) / 100
        else:  # PUT
            delta = norm.cdf(d1) - 1
            theta = (-spot * norm.pdf(d1) * volatility / (2 * sqrt_t) 
                     + self.r * strike * exp_rt * norm.cdf(-d2)) / 365
            rho = -strike * time_to_expiry * exp_rt * norm.cdf(-d2) / 100
        
        # Common Greeks (same for calls and puts)
        gamma = norm.pdf(d1) / (spot * volatility * sqrt_t)
        vega = spot * norm.pdf(d1) * sqrt_t / 100  # Divided by 100 for 1% vol move
        
        # Note: Removed incorrect 0DTE theta scaling that was multiplying by 24x
        # Standard Black-Scholes theta is already correct for all timeframes
        
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho
        }
    
    def calculate_iv_from_price(self,
                               spot: float,
                               strike: float,
                               time_to_expiry: float,
                               option_price: float,
                               option_type: str,
                               initial_guess: float = 0.20) -> Optional[float]:
        """
        Calculate implied volatility from option price using Newton-Raphson
        
        Args:
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            option_price: Market price of option
            option_type: 'CALL' or 'PUT'
            initial_guess: Starting IV guess
            
        Returns:
            Implied volatility or None if cannot converge
        """
        max_iterations = 100
        precision = 1e-5
        
        # Use midpoint if we have bid/ask
        vol = initial_guess
        
        for i in range(max_iterations):
            # Calculate theoretical price and vega
            greeks = self.calculate_greeks(spot, strike, time_to_expiry, vol, option_type)
            theoretical_price = self._black_scholes_price(spot, strike, time_to_expiry, vol, option_type)
            
            # Check convergence
            price_diff = theoretical_price - option_price
            if abs(price_diff) < precision:
                return vol
            
            # Newton-Raphson update
            vega = greeks['vega'] * 100  # Vega per 100% vol move
            if abs(vega) < 1e-10:
                return None  # Vega too small
            
            vol = vol - price_diff / vega
            
            # Keep vol in reasonable range
            vol = max(0.01, min(5.0, vol))
        
        return None  # Failed to converge
    
    def _black_scholes_price(self, spot: float, strike: float, time_to_expiry: float, 
                            volatility: float, option_type: str) -> float:
        """Calculate Black-Scholes theoretical price"""
        if time_to_expiry <= 0:
            if option_type == 'CALL':
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)
        
        d1 = (np.log(spot / strike) + (self.r + 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
        d2 = d1 - volatility * np.sqrt(time_to_expiry)
        
        if option_type == 'CALL':
            return spot * norm.cdf(d1) - strike * np.exp(-self.r * time_to_expiry) * norm.cdf(d2)
        else:
            return strike * np.exp(-self.r * time_to_expiry) * norm.cdf(-d2) - spot * norm.cdf(-d1)
    
    def correct_options_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Correct delta values in options data
        
        Args:
            df: DataFrame with options data
            
        Returns:
            DataFrame with corrected Greeks
        """
        df = df.copy()
        calculator = BlackScholesCalculator()
        
        # Add helper columns
        if 'underlying_price_dollar' not in df.columns:
            df['underlying_price_dollar'] = df['underlying_price'] / 100
        
        # Calculate time to expiry for each row
        df['expiry_datetime'] = pd.to_datetime(df['expiration']) + pd.Timedelta(hours=16)  # 4 PM close
        df['current_datetime'] = pd.to_datetime(df['timestamp'])
        df['hours_to_expiry'] = (df['expiry_datetime'] - df['current_datetime']).dt.total_seconds() / 3600
        df['years_to_expiry'] = df['hours_to_expiry'] / (365.25 * 24)
        
        # Store original values
        df['delta_original'] = df['delta']
        if 'gamma' in df.columns:
            df['gamma_original'] = df['gamma']
        else:
            # Add gamma column if missing
            df['gamma'] = np.nan
        if 'theta' in df.columns:
            df['theta_original'] = df['theta']
        else:
            df['theta'] = np.nan
        if 'vega' in df.columns:
            df['vega_original'] = df['vega']
        else:
            df['vega'] = np.nan
        if 'rho' in df.columns:
            df['rho_original'] = df['rho']
        else:
            df['rho'] = np.nan
        
        # Correct Greeks for each row
        for idx, row in df.iterrows():
            # Skip if already expired
            if row['years_to_expiry'] <= 0:
                continue
            
            # Use midpoint for theoretical pricing
            mid_price = (row['bid'] + row['ask']) / 2
            
            # First try to calculate IV from market price
            iv = calculator.calculate_iv_from_price(
                row['underlying_price_dollar'],
                row['strike'],
                row['years_to_expiry'],
                mid_price,
                row['right'],
                initial_guess=row.get('implied_vol', 0.15)
            )
            
            # If IV calculation fails, use existing or default
            if iv is None:
                iv = row.get('implied_vol', 0.15)
            
            # Calculate corrected Greeks
            greeks = calculator.calculate_greeks(
                row['underlying_price_dollar'],
                row['strike'],
                row['years_to_expiry'],
                iv,
                row['right']
            )
            
            # Update all Greeks
            df.at[idx, 'delta'] = greeks['delta']
            df.at[idx, 'gamma'] = greeks['gamma']
            df.at[idx, 'theta'] = greeks['theta']
            df.at[idx, 'vega'] = greeks['vega']
            df.at[idx, 'rho'] = greeks['rho']
            df.at[idx, 'implied_vol'] = iv
        
        # Add quality flag
        df['delta_corrected'] = (df['delta'] != df['delta_original'])
        
        return df


def diagnose_and_fix_sample():
    """Quick diagnostic of delta issues and fix"""
    import sys
    sys.path.append('..')
    from zero_dte_spy_options_database import MinuteLevelOptionsDatabase
    
    # Load sample data
    db = MinuteLevelOptionsDatabase()
    df = db.load_zero_dte_data('20250728')
    
    # Get 10 AM snapshot
    time_10am = df[df['timestamp'] == '2025-07-28T10:00:00'].copy()
    spy_price = time_10am.iloc[0]['underlying_price_dollar']
    
    print(f"SPY Price at 10 AM: ${spy_price:.2f}")
    print("\nBEFORE CORRECTION:")
    print("-" * 60)
    
    # Show delta distribution
    calls = time_10am[time_10am['right'] == 'CALL'].sort_values('strike')
    delta_counts = calls['delta'].value_counts().sort_index()
    print(f"Delta distribution:\n{delta_counts}")
    
    # Apply corrections
    calculator = BlackScholesCalculator()
    corrected_df = calculator.correct_options_data(time_10am)
    
    print("\nAFTER CORRECTION:")
    print("-" * 60)
    
    # Show corrected delta distribution
    corrected_calls = corrected_df[corrected_df['right'] == 'CALL'].sort_values('strike')
    corrected_delta_counts = corrected_calls['delta'].value_counts(bins=10).sort_index()
    print(f"Delta distribution (binned):\n{corrected_delta_counts}")
    
    # Show specific examples
    print("\nEXAMPLE CORRECTIONS:")
    print("-" * 60)
    print(f"{'Strike':>7} | {'Moneyness':>10} | {'Original Δ':>10} | {'Corrected Δ':>12} | {'Change':>8}")
    print("-" * 60)
    
    for _, row in corrected_calls.iterrows():
        if row['delta_corrected']:
            moneyness = (row['strike'] / spy_price - 1) * 100
            change = row['delta'] - row['delta_original']
            print(f"{row['strike']:7.1f} | {moneyness:9.1f}% | {row['delta_original']:10.4f} | {row['delta']:12.4f} | {change:+8.4f}")
    
    # Find 0.30 delta options
    print("\n0.30 DELTA OPTIONS:")
    print("-" * 60)
    suitable = corrected_calls[(corrected_calls['delta'] >= 0.25) & (corrected_calls['delta'] <= 0.35)]
    if len(suitable) > 0:
        print(f"Found {len(suitable)} suitable calls:")
        for _, row in suitable.iterrows():
            print(f"  Strike ${row['strike']}: delta = {row['delta']:.4f}")
    else:
        print("No calls found with delta near 0.30")


if __name__ == "__main__":
    diagnose_and_fix_sample()