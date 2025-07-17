"""
Configuration settings for SPY Options Backtester
"""
from pathlib import Path

# Data paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR.parent / "spy_options_downloader" / "spy_options_parquet"
OUTPUT_DIR = BASE_DIR / "results"

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)

# Trading parameters
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.02  # 2% annual risk-free rate

# Commission structure (per contract)
COMMISSION_PER_CONTRACT = 0.65
BID_ASK_SPREAD_FACTOR = 0.5  # Use mid price + 50% of spread as execution price

# Default strategy parameters
DEFAULT_PARAMS = {
    'initial_capital': 100000,
    'max_position_size': 0.05,  # 5% of capital per position
    'stop_loss_pct': 0.50,      # 50% stop loss
    'profit_target_pct': 1.00,  # 100% profit target
    'min_dte': 10,              # Minimum days to expiration
    'max_dte': 60,              # Maximum days to expiration
    'delta_threshold': 0.30,    # Delta threshold for entry
}

# Data columns mapping
OPTION_COLUMNS = {
    'date': 'date',
    'expiration': 'expiration', 
    'strike': 'strike',
    'right': 'right',  # 'C' for call, 'P' for put
    'bid': 'bid',
    'ask': 'ask',
    'close': 'close',
    'volume': 'volume',
    'open_interest': 'count',
    'delta': 'delta',
    'gamma': 'gamma',
    'theta': 'theta',
    'vega': 'vega',
    'rho': 'rho',
    'implied_vol': 'implied_vol',
    'underlying_price': 'underlying_price'
}