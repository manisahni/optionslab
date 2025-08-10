#!/usr/bin/env python3
"""
Final consistency check between all Greeks calculators
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.black_scholes_calculator import BlackScholesCalculator
from tradier.core.greeks_calculator import GreeksCalculator

print('Testing Greeks consistency between calculators...')
print('=' * 60)

calc1 = BlackScholesCalculator()
calc2 = GreeksCalculator()

# Test cases: (spot, strike, time_to_expiry, volatility)
test_cases = [
    (580, 585, 1/24/365, 0.15),   # OTM call, 1 hour
    (580, 575, 1/24/365, 0.15),   # OTM put, 1 hour
    (580, 580, 2/24/365, 0.20),   # ATM, 2 hours
    (580, 590, 0.5/24/365, 0.25),  # Far OTM, 30 min
]

all_match = True

for spot, strike, t, vol in test_cases:
    for opt in ['CALL', 'PUT']:
        g1 = calc1.calculate_greeks(spot, strike, t, vol, opt)
        g2 = calc2.calculate_greeks(spot, strike, t, vol, opt.lower())
        
        for greek in ['delta', 'gamma', 'theta', 'vega', 'rho']:
            diff = abs(g1[greek] - g2[greek])
            if diff > 1e-6:
                all_match = False
                print(f'❌ Mismatch in {greek} for {opt} S={spot} K={strike}')
                print(f'   BlackScholes: {g1[greek]:.8f}')
                print(f'   GreeksCalc: {g2[greek]:.8f}')
                print(f'   Difference: {diff:.8e}')

if all_match:
    print('✅ SUCCESS: All Greeks match perfectly between both calculators!')
    print('\nBoth calculators produce identical results for:')
    print('- Delta')
    print('- Gamma')
    print('- Theta (now fixed - no more 24x scaling)')
    print('- Vega')
    print('- Rho')
else:
    print('\n❌ Some Greeks differ between calculators')