import pandas as pd
import glob

# Get the most recent file
files = sorted(glob.glob('spy_options_parquet/*.parquet'))
latest_file = files[-1]
print(f'Latest file: {latest_file}')

# Read the latest file
df = pd.read_parquet(latest_file)

print('\n=== DATA SUMMARY ===')
print(f'Date range: {df["date"].min()} to {df["date"].max()}')
print(f'Total rows: {len(df):,}')
print(f'Underlying price: ${df["underlying_price"].iloc[0]:.2f}')

# Show data types for key columns
print('\n=== DATA TYPES FOR GREEKS & IV ===')
greek_cols = ['delta', 'gamma', 'theta', 'vega', 'rho', 'vanna', 'charm', 'vomma', 
              'veta', 'vera', 'speed', 'zomma', 'color', 'ultima', 'epsilon', 
              'lambda', 'implied_vol', 'iv_error']

for col in greek_cols:
    print(f'{col:12s} : {df[col].dtype}')

# Show value ranges
print('\n=== VALUE RANGES FOR KEY GREEKS & IV ===')
for col in ['delta', 'gamma', 'theta', 'vega', 'implied_vol']:
    non_zero = df[df[col] != 0][col]
    if len(non_zero) > 0:
        print(f'{col:12s} : min={non_zero.min():.6f}, max={non_zero.max():.6f}, mean={non_zero.mean():.6f}')
    else:
        print(f'{col:12s} : all values are zero')

# Show a sample of at-the-money options
print('\n=== SAMPLE ATM OPTIONS WITH GREEKS ===')
underlying = df['underlying_price'].iloc[0]
atm_strike = round(underlying) * 1000  # Convert to thousandths
tolerance = 5000  # $5 tolerance

atm_options = df[
    (df['strike'] >= atm_strike - tolerance) & 
    (df['strike'] <= atm_strike + tolerance) &
    (df['delta'].abs() > 0.01)
].head(6)

if len(atm_options) > 0:
    display_cols = ['strike', 'right', 'expiration', 'bid', 'ask', 'volume', 
                    'delta', 'gamma', 'theta', 'vega', 'implied_vol']
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(atm_options[display_cols])
else:
    print("No ATM options with significant Greeks found")

# Show column availability summary
print('\n=== GREEKS AND IV COLUMNS AVAILABLE ===')
print('First-Order Greeks:')
print('  ✓ delta - Option price sensitivity to underlying price changes')
print('  ✓ gamma - Rate of change of delta')
print('  ✓ theta - Time decay')
print('  ✓ vega - Sensitivity to volatility changes')
print('  ✓ rho - Sensitivity to interest rate changes')

print('\nSecond-Order Greeks:')
print('  ✓ vanna - Sensitivity of delta to volatility changes')
print('  ✓ charm - Rate of change of delta over time')
print('  ✓ vomma/volga - Sensitivity of vega to volatility changes')
print('  ✓ veta - Sensitivity of vega to time')
print('  ✓ vera - Sensitivity of rho to volatility')

print('\nThird-Order Greeks:')
print('  ✓ speed - Rate of change of gamma')
print('  ✓ zomma - Rate of change of gamma with respect to volatility')
print('  ✓ color - Rate of change of gamma over time')
print('  ✓ ultima - Sensitivity of vomma to volatility')

print('\nOther Greeks and Calculations:')
print('  ✓ epsilon - Dividend yield sensitivity')
print('  ✓ lambda - Leverage ratio')
print('  ✓ d1, d2 - Black-Scholes parameters')

print('\nImplied Volatility:')
print('  ✓ implied_vol - Implied volatility')
print('  ✓ iv_error - Error in implied volatility calculation')