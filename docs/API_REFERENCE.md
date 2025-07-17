# ThetaData Python Client - API Reference

## Overview

The ThetaData Python Client provides comprehensive access to ThetaData Terminal's REST and WebSocket APIs. All function names are specific and descriptive to clearly indicate their purpose.

**Terminal Connection**: `http://localhost:25510` (no authentication required)

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from thetadata import ThetaDataTerminalClient

# Synchronous usage
client = ThetaDataTerminalClient()
expirations = client.list_option_expirations_sync("AAPL")
strikes = client.list_option_strikes_sync("AAPL", "20250117")

# Asynchronous usage
async with ThetaDataTerminalClient() as client:
    expirations = await client.list_option_expirations("AAPL")
    quote = await client.get_option_quote_snapshot("AAPL", "20250117", 200.0, "C")
```

## Main Client Classes

### ThetaDataTerminalClient

Primary client class that provides unified access to both REST and streaming APIs.

**Constructor Parameters:**
- `terminal_host` (str): ThetaData Terminal host (default: "localhost")
- `terminal_port` (int): ThetaData Terminal port (default: 25510)
- `rate_limit` (int): Maximum requests per second (default: 100)
- `timeout` (float): Request timeout in seconds (default: 30.0)

## List Operations

### list_option_expirations()
Get available option expiration dates for a symbol.

**Async:** `await client.list_option_expirations(root: str) -> List[int]`
**Sync:** `client.list_option_expirations_sync(root: str) -> List[int]`

**Parameters:**
- `root` (str): Underlying symbol (e.g., "AAPL", "SPY")

**Returns:** List of expiration dates in YYYYMMDD format (as integers)

**Example:**
```python
# Get all available AAPL option expirations
expirations = await client.list_option_expirations("AAPL")
print(f"Next expiration: {expirations[0]}")  # 20250117

# Synchronous version
expirations = client.list_option_expirations_sync("AAPL")
```

### list_option_strikes()
Get available strike prices for a symbol and expiration.

**Async:** `await client.list_option_strikes(root: str, exp: Union[str, int, date]) -> List[float]`
**Sync:** `client.list_option_strikes_sync(root: str, exp: Union[str, int, date]) -> List[float]`

**Parameters:**
- `root` (str): Underlying symbol (e.g., "AAPL", "SPY")
- `exp` (Union[str, int, date]): Expiration date in YYYYMMDD format or date object

**Returns:** List of strike prices (converted from millidollars to actual prices)

**Example:**
```python
# Get available strikes for AAPL Jan 17, 2025 expiration
strikes = await client.list_option_strikes("AAPL", "20250117")
print(f"Available strikes: {strikes[:5]}")  # [50.0, 100.0, 150.0, ...]

# Using date object
from datetime import date
strikes = await client.list_option_strikes("AAPL", date(2025, 1, 17))
```

## Current Market Data (Snapshots)

### get_option_quote_snapshot()
Get current quote snapshot for a specific option contract.

**Async:** `await client.get_option_quote_snapshot(root: str, exp: Union[str, int, date], strike: float, right: str) -> Dict[str, Any]`
**Sync:** `client.get_option_quote_snapshot_sync(root: str, exp: Union[str, int, date], strike: float, right: str) -> Dict[str, Any]`

**Parameters:**
- `root` (str): Underlying symbol (e.g., "AAPL", "SPY")
- `exp` (Union[str, int, date]): Expiration date in YYYYMMDD format
- `strike` (float): Strike price (e.g., 200.0)
- `right` (str): Option type - "C" for Call, "P" for Put

**Returns:** Current quote data dictionary (empty if no data available)

**Example:**
```python
# Get current quote for AAPL $200 Call expiring Jan 17, 2025
quote = await client.get_option_quote_snapshot("AAPL", "20250117", 200.0, "C")
if quote:
    print(f"Bid: {quote.get('bid')}, Ask: {quote.get('ask')}")
    print(f"Bid Size: {quote.get('bid_size')}, Ask Size: {quote.get('ask_size')}")
```

### get_option_ohlc_snapshot()
Get current OHLC snapshot for a specific option contract.

**Async:** `await client.get_option_ohlc_snapshot(root: str, exp: Union[str, int, date], strike: float, right: str) -> Dict[str, Any]`
**Sync:** `client.get_option_ohlc_snapshot_sync(root: str, exp: Union[str, int, date], strike: float, right: str) -> Dict[str, Any]`

**Parameters:**
- `root` (str): Underlying symbol (e.g., "AAPL", "SPY")
- `exp` (Union[str, int, date]): Expiration date in YYYYMMDD format
- `strike` (float): Strike price (e.g., 200.0)
- `right` (str): Option type - "C" for Call, "P" for Put

**Returns:** Current OHLC data dictionary (empty if no data available)

**Example:**
```python
# Get current OHLC for AAPL $200 Put expiring Jan 17, 2025
ohlc = await client.get_option_ohlc_snapshot("AAPL", "20250117", 200.0, "P")
if ohlc:
    print(f"Open: {ohlc.get('open')}, High: {ohlc.get('high')}")
    print(f"Low: {ohlc.get('low')}, Close: {ohlc.get('close')}")
    print(f"Volume: {ohlc.get('volume')}")
```

## Bulk Operations

### get_bulk_option_quotes()
Get bulk quote snapshots for entire option chain.

**Async:** `await client.get_bulk_option_quotes(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`
**Sync:** `client.get_bulk_option_quotes_sync(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`

**Parameters:**
- `root` (str): Underlying symbol (e.g., "AAPL", "SPY")
- `exp` (Union[str, int, date, None]): Optional expiration date. If None, gets all expirations

**Returns:** List of quote data for all options in the chain

**Example:**
```python
# Get all quotes for specific expiration
quotes = await client.get_bulk_option_quotes("AAPL", "20250117")

# Get all quotes for all expirations
all_quotes = await client.get_bulk_option_quotes("AAPL")

# Process the data
for quote in quotes:
    strike = quote['strike']
    bid = quote.get('bid')
    ask = quote.get('ask')
    print(f"Strike ${strike}: {bid} x {ask}")
```

### get_bulk_option_ohlc()
Get bulk OHLC snapshots for entire option chain.

**Async:** `await client.get_bulk_option_ohlc(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`
**Sync:** `client.get_bulk_option_ohlc_sync(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`

**Parameters:** Same as get_bulk_option_quotes()

**Returns:** List of OHLC data for all options in the chain

### get_bulk_option_greeks()
Get bulk first-order Greeks (delta, gamma, theta, vega, rho) for entire option chain.

**Async:** `await client.get_bulk_option_greeks(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`
**Sync:** `client.get_bulk_option_greeks_sync(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`

**Parameters:** Same as get_bulk_option_quotes()

**Returns:** List of Greeks data for all options

**Example:**
```python
greeks = await client.get_bulk_option_greeks("AAPL", "20250117")
for option in greeks:
    print(f"Strike: {option['strike']}")
    print(f"  Delta: {option.get('delta')}")
    print(f"  Gamma: {option.get('gamma')}")
    print(f"  Theta: {option.get('theta')}")
    print(f"  Vega: {option.get('vega')}")
    print(f"  Rho: {option.get('rho')}")
```

### get_bulk_option_greeks_second_order()
Get bulk second-order Greeks for entire option chain.

**Async:** `await client.get_bulk_option_greeks_second_order(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`
**Sync:** `client.get_bulk_option_greeks_second_order_sync(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`

### get_bulk_option_greeks_third_order()
Get bulk third-order Greeks for entire option chain.

**Async:** `await client.get_bulk_option_greeks_third_order(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`
**Sync:** `client.get_bulk_option_greeks_third_order_sync(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`

### get_bulk_option_all_greeks()
Get all Greeks (1st, 2nd, and 3rd order) for entire option chain in one call.

**Async:** `await client.get_bulk_option_all_greeks(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`
**Sync:** `client.get_bulk_option_all_greeks_sync(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`

### get_bulk_option_open_interest()
Get bulk open interest for entire option chain.

**Async:** `await client.get_bulk_option_open_interest(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`
**Sync:** `client.get_bulk_option_open_interest_sync(root: str, exp: Union[str, int, date, None] = None) -> List[Dict[str, Any]]`

**Example:**
```python
oi_data = await client.get_bulk_option_open_interest("AAPL", "20250117")

# Calculate total open interest
total_oi = sum(option.get('open_interest', 0) for option in oi_data)
print(f"Total open interest: {total_oi}")

# Find highest OI strikes
sorted_oi = sorted(oi_data, key=lambda x: x.get('open_interest', 0), reverse=True)
for option in sorted_oi[:5]:
    print(f"Strike ${option['strike']}: OI {option.get('open_interest')}")
```

## Historical Data

### get_option_ohlc_history()
Get historical OHLC data for a specific option contract.

**Async:** `await client.get_option_ohlc_history(root: str, exp: Union[str, int, date], strike: float, right: str, start_date: Union[str, int, date], end_date: Union[str, int, date], interval_size: int = 60000) -> List[Dict[str, Any]]`
**Sync:** `client.get_option_ohlc_history_sync(...) -> List[Dict[str, Any]]`

**Parameters:**
- `root` (str): Underlying symbol (e.g., "AAPL", "SPY")
- `exp` (Union[str, int, date]): Expiration date in YYYYMMDD format
- `strike` (float): Strike price (e.g., 200.0)
- `right` (str): Option type - "C" for Call, "P" for Put
- `start_date` (Union[str, int, date]): Start date in YYYYMMDD format
- `end_date` (Union[str, int, date]): End date in YYYYMMDD format
- `interval_size` (int): Interval in milliseconds (default: 60000 = 1 minute)

**Returns:** List of historical OHLC data dictionaries

**Common Interval Sizes:**
- 60000 = 1 minute
- 300000 = 5 minutes
- 900000 = 15 minutes
- 3600000 = 1 hour
- 86400000 = 1 day

**Example:**
```python
# Get 5-minute OHLC history for AAPL $200 Call
history = await client.get_option_ohlc_history(
    "AAPL", "20250117", 200.0, "C", 
    "20240101", "20240102", 
    interval_size=300000  # 5 minutes
)

for bar in history:
    print(f"Time: {bar.get('timestamp')}, Close: {bar.get('close')}")
```

### get_option_trade_history()
Get historical trade data for a specific option contract.

**Async:** `await client.get_option_trade_history(root: str, exp: Union[str, int, date], strike: float, right: str, start_date: Union[str, int, date], end_date: Union[str, int, date]) -> List[Dict[str, Any]]`
**Sync:** `client.get_option_trade_history_sync(...) -> List[Dict[str, Any]]`

**Parameters:**
- `root` (str): Underlying symbol (e.g., "AAPL", "SPY")
- `exp` (Union[str, int, date]): Expiration date in YYYYMMDD format
- `strike` (float): Strike price (e.g., 200.0)
- `right` (str): Option type - "C" for Call, "P" for Put
- `start_date` (Union[str, int, date]): Start date in YYYYMMDD format
- `end_date` (Union[str, int, date]): End date in YYYYMMDD format

**Returns:** List of historical trade data dictionaries

**Example:**
```python
# Get trade history for AAPL $200 Put
trades = await client.get_option_trade_history(
    "AAPL", "20250117", 200.0, "P", "20240101", "20240102"
)

for trade in trades:
    print(f"Price: {trade.get('price')}, Size: {trade.get('size')}")
```

## High-Level Helper Methods

### get_option_chain()
Get complete option chain for a symbol and expiration.

**Async:** `await client.get_option_chain(root: str, exp: Union[str, int, date]) -> Dict[str, List[Dict[str, Any]]]`
**Sync:** `client.get_option_chain_sync(root: str, exp: Union[str, int, date]) -> Dict[str, List[Dict[str, Any]]]`

**Parameters:**
- `root` (str): Underlying symbol
- `exp` (Union[str, int, date]): Expiration date

**Returns:** Dictionary with 'calls' and 'puts' lists containing quote data

**Example:**
```python
# Get complete option chain for AAPL Jan 17, 2025
chain = await client.get_option_chain("AAPL", "20250117")

calls = chain['calls']
puts = chain['puts']

print(f"Found {len(calls)} calls and {len(puts)} puts")

# Display call quotes
for call in calls[:5]:  # First 5 calls
    strike = call['strike']
    bid = call.get('bid', 'N/A')
    ask = call.get('ask', 'N/A')
    print(f"Call ${strike}: Bid {bid}, Ask {ask}")
```

## Streaming Operations

### connect_stream()
Connect to WebSocket stream.

**Async:** `await client.connect_stream()`

### disconnect_stream()
Disconnect from WebSocket stream.

**Async:** `await client.disconnect_stream()`

### subscribe_option_quotes()
Subscribe to real-time option quote updates.

**Async:** `await client.subscribe_option_quotes(root: str, exp: Union[str, int, date], strike: float, right: str, handler: Callable[[Dict[str, Any]], None])`

**Parameters:**
- `root` (str): Underlying symbol
- `exp` (Union[str, int, date]): Expiration date
- `strike` (float): Strike price
- `right` (str): Option type ("C" or "P")
- `handler` (Callable): Callback function for quote updates

**Example:**
```python
async def quote_handler(quote_data):
    print(f"New quote: {quote_data}")

await client.connect_stream()
await client.subscribe_option_quotes("AAPL", "20250117", 200.0, "C", quote_handler)
await client.start_streaming()
```

### subscribe_option_trades()
Subscribe to real-time option trade updates.

**Async:** `await client.subscribe_option_trades(root: str, exp: Union[str, int, date], strike: float, right: str, handler: Callable[[Dict[str, Any]], None])`

**Parameters:**
- `root` (str): Underlying symbol
- `exp` (Union[str, int, date]): Expiration date
- `strike` (float): Strike price
- `right` (str): Option type ("C" or "P")
- `handler` (Callable): Callback function for trade updates

## Error Handling

The client provides specific exception types for different error conditions:

- `ThetaDataError`: Base exception for all ThetaData-related errors
- `ConnectionError`: Connection issues with ThetaData Terminal
- `ValidationError`: Invalid parameters or data validation errors
- `ResponseError`: Invalid response format from API
- `RateLimitError`: Rate limiting errors
- `StreamError`: WebSocket streaming errors

**Example:**
```python
from thetadata import ThetaDataTerminalClient, ValidationError, ConnectionError

try:
    client = ThetaDataTerminalClient()
    expirations = client.list_option_expirations_sync("INVALID_SYMBOL")
except ValidationError as e:
    print(f"Invalid parameter: {e}")
except ConnectionError as e:
    print(f"Connection problem: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Data Format Notes

### Dates
- All dates are in YYYYMMDD format (e.g., "20250117" for January 17, 2025)
- Can be provided as strings, integers, or Python date objects
- The client automatically converts between formats

### Strike Prices
- Internally stored as millidollars in ThetaData (multiply by 1000)
- Client automatically converts to/from actual dollar amounts
- Use normal dollar values (e.g., 200.0 for $200 strike)

### Option Rights
- "C" or "CALL" for Call options
- "P" or "PUT" for Put options
- Case-insensitive

### Response Format
All ThetaData Terminal responses follow this format:
```json
{
  "header": {
    "id": 1,
    "latency_ms": 89,
    "error_type": "null",
    "error_msg": "null",
    "next_page": "null",
    "format": null
  },
  "response": [data_array]
}
```

The client automatically extracts the `response` array and handles errors from the `header`.

## Context Managers

Use context managers for automatic resource cleanup:

```python
# Synchronous
with ThetaDataTerminalClient() as client:
    data = client.list_option_expirations_sync("AAPL")

# Asynchronous  
async with ThetaDataTerminalClient() as client:
    data = await client.list_option_expirations("AAPL")
```

## Constants

For convenience, the package provides helpful constants:

```python
from thetadata import TERMINAL_DEFAULT_HOST, TERMINAL_DEFAULT_PORT, CALL, PUT

# Default connection settings
print(f"Default terminal: {TERMINAL_DEFAULT_HOST}:{TERMINAL_DEFAULT_PORT}")

# Option rights
call_quote = await client.get_option_quote_snapshot("AAPL", "20250117", 200.0, CALL)
put_quote = await client.get_option_quote_snapshot("AAPL", "20250117", 200.0, PUT)
```

# At-Time Endpoints (v2)

## Option Quote At Time
- **Endpoint:** `/v2/at_time/option/quote`
- **Parameters:**
  - `root`: Underlying symbol (e.g., "AAPL")
  - `exp`: Expiration date (YYYYMMDD)
  - `strike`: Strike price (1/10th of a cent)
  - `right`: "C" or "P"
  - `timestamp`: `YYYYMMDDHHMMSS` (converted to `ivl` internally)
- **Returns:**
  - Dictionary with fields:
    - `ms_of_day`, `bid_size`, `bid_exchange`, `bid`, `bid_condition`, `ask_size`, `ask_exchange`, `ask`, `ask_condition`, `date`
- **Example:**
```json
{
  "ms_of_day": 52200000,
  "bid_size": 0,
  "bid_exchange": 1,
  "bid": 0.0,
  "bid_condition": 50,
  "ask_size": 2858,
  "ask_exchange": 7,
  "ask": 0.01,
  "ask_condition": 50,
  "date": 20240119
}
```

## Option Trade At Time
- **Endpoint:** `/v2/at_time/option/trade`
- **Parameters:**
  - Same as above
- **Returns:**
  - Dictionary with fields:
    - `ms_of_day`, `sequence`, `ext_condition1`, `ext_condition2`, `ext_condition3`, `ext_condition4`, `condition`, `size`, `exchange`, `price`, `condition_flags`, `price_flags`, `volume_type`, `records_back`, `date`
- **Example:**
```json
{
  "ms_of_day": 52152464,
  "sequence": -226828104,
  "ext_condition1": 255,
  "ext_condition2": 255,
  "ext_condition3": 255,
  "ext_condition4": 255,
  "condition": 18,
  "size": 2,
  "exchange": 11,
  "price": 0.01,
  "condition_flags": 0,
  "price_flags": 1,
  "volume_type": 0,
  "records_back": 0,
  "date": 20240119
}
```

## Stock Quote At Time
- **Endpoint:** `/v2/at_time/stock/quote`
- **Parameters:**
  - `root`: Stock symbol (e.g., "AAPL")
  - `timestamp`: `YYYYMMDDHHMMSS` (converted to `ivl` internally)
- **Returns:**
  - Dictionary with fields:
    - `ms_of_day`, `bid_size`, `bid_exchange`, `bid`, `bid_condition`, `ask_size`, `ask_exchange`, `ask`, `ask_condition`, `date`
- **Example:**
```json
{
  "ms_of_day": 52200000,
  "bid_size": 4,
  "bid_exchange": 1,
  "bid": 191.47,
  "bid_condition": 0,
  "ask_size": 3,
  "ask_exchange": 1,
  "ask": 191.48,
  "ask_condition": 0,
  "date": 20240119
}
```

## Stock Trade At Time
- **Endpoint:** `/v2/at_time/stock/trade`
- **Parameters:**
  - Same as above
- **Returns:**
  - Dictionary with fields:
    - `ms_of_day`, `sequence`, `ext_condition1`, `ext_condition2`, `ext_condition3`, `ext_condition4`, `condition`, `size`, `exchange`, `price`, `condition_flags`, `price_flags`, `volume_type`, `records_back`, `date`
- **Example:**
```json
{
  "ms_of_day": 52199853,
  "sequence": 281233,
  "ext_condition1": 32,
  "ext_condition2": 255,
  "ext_condition3": 255,
  "ext_condition4": 115,
  "condition": 115,
  "size": 1,
  "exchange": 57,
  "price": 191.475,
  "condition_flags": 7,
  "price_flags": 0,
  "volume_type": 0,
  "records_back": 0,
  "date": 20240119
}
```

---

- All endpoints require `timestamp` in `YYYYMMDDHHMMSS` format, which is converted to `ivl` (milliseconds since midnight ET) internally.
- All endpoints return a dictionary with named fields, not a raw list.
- See the test file `test_at_time_endpoints.py` for usage examples.