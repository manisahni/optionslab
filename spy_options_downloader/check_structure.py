import pandas as pd

# Read the parquet file
df = pd.read_parquet('spy_options_parquet/spy_options_eod_20230717.parquet')

# Display key columns with sample data
print('=== FILE STRUCTURE OVERVIEW ===\n')
print(f'Total rows: {len(df):,}')
print(f'Total columns: {len(df.columns)}\n')

print('=== KEY OPTION FIELDS ===')
key_cols = ['root', 'expiration', 'strike', 'right', 'date', 'underlying_price']
print(df[key_cols].head())

print('\n=== PRICE & VOLUME DATA ===')
price_cols = ['open', 'high', 'low', 'close', 'volume', 'bid', 'ask']
print(df[price_cols].head())

print('\n=== GREEKS ===')
greeks_cols = ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_vol']
print(df[greeks_cols].head())

print('\n=== UNIQUE VALUES ===')
print(f"Unique expiration dates: {df['expiration'].nunique()}")
print(f"Unique strikes: {df['strike'].nunique()}")
print(f"Option types: {df['right'].unique()}")

# Convert strike prices from thousandths to dollars for display
print('\n=== STRIKE PRICE RANGE ===')
print(f"Min strike: ${df['strike'].min()/1000:.2f}")
print(f"Max strike: ${df['strike'].max()/1000:.2f}")
print(f"Underlying price: ${df['underlying_price'].iloc[0]:.2f}")

# Show all column groups
print('\n=== ALL COLUMN GROUPS ===')
print('\n1. Basic Option Info:')
print('   - root, expiration, strike, right, date, underlying_price')

print('\n2. EOD Price Data:')
print('   - open, high, low, close, volume, count')

print('\n3. Bid/Ask Data:')
print('   - bid, bid_size, bid_exchange, bid_condition')
print('   - ask, ask_size, ask_exchange, ask_condition')

print('\n4. First-Order Greeks:')
print('   - delta, gamma, theta, vega, rho')

print('\n5. Second-Order Greeks:')
print('   - vanna, charm, vomma, veta, vera')

print('\n6. Third-Order Greeks:')
print('   - speed, zomma, color, ultima')

print('\n7. Other Greeks/Calculations:')
print('   - epsilon, lambda, d1, d2, implied_vol, iv_error')

print('\n8. Timestamp Fields:')
print('   - ms_of_day, ms_of_day2, ms_of_day_greeks, ms_of_day2_greeks')