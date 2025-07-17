# ThetaData Python Client

A comprehensive Python client library for ThetaData Terminal API with **specific, descriptive function names** for clear data access.

**✅ Real API Tested** - All functions validated against live ThetaData Terminal  
**🎯 Specific Names** - Every function clearly indicates its purpose  
**⚡ Fast & Reliable** - Local Terminal connection, no authentication required  
**🔄 Sync & Async** - Both synchronous and asynchronous interfaces  

## Quick Start

```python
from thetadata import ThetaDataTerminalClient

# Synchronous usage
client = ThetaDataTerminalClient()
expirations = client.list_option_expirations_sync("AAPL")
strikes = client.list_option_strikes_sync("AAPL", "20250117")
quote = client.get_option_quote_snapshot_sync("AAPL", "20250117", 200.0, "C")

# Asynchronous usage
async with ThetaDataTerminalClient() as client:
    expirations = await client.list_option_expirations("AAPL")
    chain = await client.get_option_chain("AAPL", "20250117")
```

## Specific Function Names

### 📋 List Operations
- `list_option_expirations()` - Get available expiration dates for a symbol
- `list_option_strikes()` - Get available strike prices for symbol/expiration

### 📊 Current Market Data  
- `get_option_quote_snapshot()` - Current bid/ask quotes for specific option
- `get_option_ohlc_snapshot()` - Current OHLC data for specific option

### 📈 Historical Data
- `get_option_ohlc_history()` - Historical OHLC bars with custom intervals
- `get_option_trade_history()` - Historical tick-by-tick trade data

### 🚀 Bulk Operations (NEW)
- `get_bulk_option_quotes()` - Get quotes for entire option chain
- `get_bulk_option_ohlc()` - Get OHLC for entire option chain
- `get_bulk_option_greeks()` - Get Greeks for entire option chain
- `get_bulk_option_greeks_second_order()` - Get 2nd order Greeks
- `get_bulk_option_greeks_third_order()` - Get 3rd order Greeks
- `get_bulk_option_all_greeks()` - Get all Greeks combined
- `get_bulk_option_open_interest()` - Get open interest for entire chain

### 🔗 High-Level Helpers
- `get_option_chain()` - Complete calls/puts chain for expiration

### 📡 Streaming (WebSocket)
- `subscribe_option_quotes()` - Real-time quote updates
- `subscribe_option_trades()` - Real-time trade updates

## Installation

```bash
# Install from source
pip install -e .

# Requires ThetaData Terminal running on localhost:25510
```

## Function Examples

### List Available Data
```python
# Get all AAPL option expirations
expirations = await client.list_option_expirations("AAPL")
print(f"Next expiration: {expirations[0]}")  # 20250117

# Get all strikes for specific expiration
strikes = await client.list_option_strikes("AAPL", "20250117") 
print(f"Available strikes: {strikes[:5]}")  # [50.0, 100.0, 150.0, ...]
```

### Get Current Market Data
```python
# Current quote for AAPL $200 Call
quote = await client.get_option_quote_snapshot("AAPL", "20250117", 200.0, "C")
if quote:
    print(f"Bid: {quote['bid']}, Ask: {quote['ask']}")

# Current OHLC for AAPL $200 Put  
ohlc = await client.get_option_ohlc_snapshot("AAPL", "20250117", 200.0, "P")
if ohlc:
    print(f"Last: {ohlc['close']}, Volume: {ohlc['volume']}")
```

### Get Historical Data
```python
# 5-minute OHLC bars for specific option
history = await client.get_option_ohlc_history(
    "AAPL", "20250117", 200.0, "C",
    "20240101", "20240102", 
    interval_size=300000  # 5 minutes
)

# Tick-by-tick trade history
trades = await client.get_option_trade_history(
    "AAPL", "20250117", 200.0, "C", "20240101", "20240102"
)
```

### Get Bulk Data for Entire Option Chain
```python
# Get all quotes for a specific expiration at once
bulk_quotes = await client.get_bulk_option_quotes("AAPL", "20250117")
print(f"Retrieved {len(bulk_quotes)} option quotes in one call")

# Get all Greeks for entire chain
bulk_greeks = await client.get_bulk_option_greeks("AAPL", "20250117")
for option in bulk_greeks:
    print(f"Strike: {option['strike']}, Delta: {option.get('delta')}")

# Get open interest for all options
bulk_oi = await client.get_bulk_option_open_interest("AAPL", "20250117")
total_oi = sum(option.get('open_interest', 0) for option in bulk_oi)
print(f"Total open interest: {total_oi}")
```

### Get Complete Option Chain
```python
# Get calls and puts for entire expiration
chain = await client.get_option_chain("AAPL", "20250117")
calls = chain['calls']
puts = chain['puts']

print(f"Found {len(calls)} calls and {len(puts)} puts")
```

## Real-Time Streaming
```python
async def quote_handler(quote_data):
    print(f"New quote: Bid {quote_data['bid']}, Ask {quote_data['ask']}")

# Subscribe to real-time quotes
await client.connect_stream()
await client.subscribe_option_quotes("AAPL", "20250117", 200.0, "C", quote_handler)
await client.start_streaming()
```

## Project Structure
```text
thetadata-api/
├── thetadata/                 # Main package
│   ├── client.py             # ThetaDataTerminalClient
│   ├── rest.py               # ThetaDataRESTClient
│   ├── stream.py             # StreamClient
│   ├── models.py             # Data models
│   ├── exceptions.py         # Custom exceptions
│   └── utils.py              # Utility functions
├── docs/                     # Documentation
│   ├── API_REFERENCE.md      # Complete API reference
│   └── ThetaData_API_Summary.txt
├── examples/                 # Usage examples
├── tests/                    # Test suite (190+ tests)
└── README.md                 # This file
```

## Features

- ✅ **190+ Comprehensive Tests** - All functions tested against real API
- 🎯 **Specific Function Names** - `get_option_quote_snapshot()` vs generic `get_data()`
- ⚡ **Local Terminal Access** - No API keys, no rate limits, fast response
- 🔄 **Sync & Async APIs** - Use `_sync` suffix for synchronous versions
- 📊 **Rich Data Models** - Pydantic validation for all responses
- 🛡️ **Error Handling** - Specific exceptions for different error types
- 📈 **Historical Data** - Customizable intervals (1min, 5min, 1hour, 1day)
- 📡 **Real-Time Streaming** - WebSocket subscriptions for live data
- 🔗 **High-Level Helpers** - `get_option_chain()` for complete market view

## Requirements

- Python 3.8+
- ThetaData Terminal running on localhost:25510
- Dependencies: `httpx`, `websockets`, `pydantic`

## Error Handling

```python
from thetadata import ValidationError, ConnectionError

try:
    quote = await client.get_option_quote_snapshot("AAPL", "20250117", 200.0, "C")
except ValidationError as e:
    print(f"Invalid parameters: {e}")
except ConnectionError as e:
    print(f"Terminal not running: {e}")
```

## Documentation

- **[Complete API Reference](docs/API_REFERENCE.md)** - All functions with examples
- **Function signatures** - Type hints and docstrings for all methods  
- **Error handling** - Specific exceptions for different scenarios
- **Data formats** - Response structures and field definitions

## Backwards Compatibility

```python
# New specific names (recommended)
from thetadata import ThetaDataTerminalClient

# Legacy aliases still work
from thetadata import ThetaDataClient, RESTClient
```

---

**🎯 All function names are intentionally specific and descriptive for maximum clarity in your trading applications!**