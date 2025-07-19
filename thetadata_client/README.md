# ThetaData Client Library

⚠️ **CRITICAL: DO NOT DELETE THIS DIRECTORY** ⚠️

This directory contains the ThetaData API client integration, which is essential for:
- Connecting to ThetaData Terminal
- Fetching real-time and historical options data
- Option contract discovery
- Greek calculations and analysis

## Directory Contents

- `__init__.py` - Package initialization and exports
- `discovery.py` - Option contract discovery utilities
- `utils.py` - Comprehensive utility functions for data fetching and analysis

## Important Notes

1. **This is production-critical code** - The backtesting system depends on this for data access
2. **Keep separate from backtesting code** - This ensures clean separation of concerns
3. **Version control** - All changes should be carefully reviewed and tested

## Usage

```python
from thetadata_client import discover_option_contracts
from thetadata_client.utils import fetch_option_chain_at_time, get_spot_price

# Discover options
contracts = discover_option_contracts(
    symbol='SPY',
    target_dte=30,
    target_delta=0.30
)

# Fetch option chain
chain = fetch_option_chain_at_time(
    symbol='SPY',
    date='2023-01-15',
    time='15:30:00'
)
```

## Future Enhancements

- Complete the missing modules (client.py, models.py, etc.)
- Add comprehensive type hints
- Implement proper error handling
- Add unit tests