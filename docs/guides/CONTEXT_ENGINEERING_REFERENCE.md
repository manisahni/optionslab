# ThetaData Python Client - Context Engineering Reference

## Project Overview

A comprehensive Python client library for ThetaData Terminal API with specific, descriptive function names and both synchronous/asynchronous interfaces. This implementation follows a context engineering paradigm with systematic development through PRPs (Project Requirements Plans).

## Key Implementation Principles

### 1. Specific Function Names
All functions use highly descriptive names that clearly indicate their purpose:
- `list_option_expirations()` instead of generic `list_contracts()`
- `get_bulk_option_quotes()` instead of generic `get_bulk_data()`
- `get_option_quote_snapshot()` instead of generic `get_quote()`

### 2. Dual Interface Pattern
Every function provides both async and sync versions:
- Async: `await client.get_bulk_option_quotes("AAPL", "20250117")`
- Sync: `client.get_bulk_option_quotes_sync("AAPL", "20250117")`

### 3. Terminal-Based Architecture
- Connects to locally running ThetaData Terminal (localhost:25510)
- No API keys required for local Terminal connection
- Uses REST endpoints discovered through systematic testing

## Technical Architecture

### Core Components

1. **ThetaDataTerminalClient** (`client.py`)
   - Main unified client class
   - Combines REST and streaming functionality
   - Provides high-level helper methods

2. **ThetaDataRESTClient** (`rest.py`)
   - Low-level REST API implementation
   - Direct Terminal endpoint access
   - Handles rate limiting and retries

3. **StreamClient** (`stream.py`)
   - WebSocket streaming implementation
   - Real-time data subscriptions
   - Message handling and callbacks

### Data Models (`models.py`)
- Pydantic-based validation
- Strong typing for all responses
- Automatic data conversion (millidollars to dollars)

### Error Handling (`exceptions.py`)
- Specific exception types for different error conditions
- Graceful handling of Terminal responses
- Informative error messages

## API Endpoint Categories

### 📋 List Operations
- `list_option_expirations(root)` - Available expiration dates
- `list_option_strikes(root, exp)` - Available strike prices

### 📊 Current Market Data
- `get_option_quote_snapshot(root, exp, strike, right)` - Real-time quotes
- `get_option_ohlc_snapshot(root, exp, strike, right)` - Real-time OHLC

### 🚀 Bulk Operations (High Performance)
- `get_bulk_option_quotes(root, exp=None)` - Entire option chain quotes
- `get_bulk_option_ohlc(root, exp=None)` - Entire option chain OHLC
- `get_bulk_option_greeks(root, exp=None)` - First-order Greeks
- `get_bulk_option_greeks_second_order(root, exp=None)` - Second-order Greeks
- `get_bulk_option_greeks_third_order(root, exp=None)` - Third-order Greeks
- `get_bulk_option_all_greeks(root, exp=None)` - Complete Greeks data
- `get_bulk_option_open_interest(root, exp=None)` - Open interest data

### 📈 Historical Data
- `get_option_ohlc_history(root, exp, strike, right, start, end, interval)` - Historical bars
- `get_option_trade_history(root, exp, strike, right, start, end)` - Trade history

### 🔗 High-Level Helpers
- `get_option_chain(root, exp)` - Complete calls/puts for expiration

### 📡 Real-Time Streaming
- `subscribe_option_quotes(root, exp, strike, right, handler)` - Quote updates
- `subscribe_option_trades(root, exp, strike, right, handler)` - Trade updates
- `connect_stream()`, `start_streaming()`, etc. - Connection management

## Key Features

### Performance Optimizations
- **Bulk Operations**: Retrieve entire option chains in single API calls
- **Concurrent Requests**: Async support for parallel data fetching
- **Rate Limiting**: Built-in respect for Terminal limits
- **Connection Pooling**: Efficient HTTP client management

### Data Quality
- **Automatic Conversions**: Millidollar strikes → dollar amounts
- **Type Safety**: Pydantic models with validation
- **Error Handling**: Graceful degradation for missing data
- **Consistent Formats**: Standardized date/time handling

### Developer Experience
- **Context Managers**: Automatic resource cleanup
- **Comprehensive Documentation**: Full API reference with examples
- **Testing Framework**: 190+ tests covering all functionality
- **Examples**: Real-world usage patterns and demos

## Usage Patterns

### Basic Data Retrieval
```python
# Synchronous - Simple scripts
client = ThetaDataTerminalClient()
expirations = client.list_option_expirations_sync("AAPL")
quotes = client.get_bulk_option_quotes_sync("AAPL", "20250117")

# Asynchronous - High performance
async with ThetaDataTerminalClient() as client:
    chains = await asyncio.gather(*[
        client.get_bulk_option_quotes("AAPL", exp),
        client.get_bulk_option_quotes("MSFT", exp),
        client.get_bulk_option_quotes("GOOGL", exp)
    ])
```

### Market Analysis
```python
# Option chain analysis
async with ThetaDataTerminalClient() as client:
    quotes = await client.get_bulk_option_quotes("SPY", "20250117")
    greeks = await client.get_bulk_option_greeks("SPY", "20250117")
    oi = await client.get_bulk_option_open_interest("SPY", "20250117")
    
    # Combine data for comprehensive analysis
    analysis = analyze_option_chain(quotes, greeks, oi)
```

### Real-Time Monitoring
```python
async def quote_handler(data):
    print(f"New quote: {data}")

async with ThetaDataTerminalClient() as client:
    await client.connect_stream()
    await client.subscribe_option_quotes("AAPL", "20250117", 200.0, "C", quote_handler)
    await client.start_streaming()
```

## Context Engineering Implementation

### Development Process
1. **Requirements Analysis** - Defined specific needs in INITIAL.md
2. **PRP Generation** - Created comprehensive Project Requirements Plan
3. **Systematic Implementation** - Built components following PRP phases
4. **Endpoint Discovery** - Tested Terminal to find working endpoints
5. **API Enhancement** - Added bulk operations based on documentation research
6. **Testing & Validation** - Comprehensive test suite development

### Code Organization
```
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
└── README.md                 # Project overview
```

## Terminal API Discovery

### Known Working Endpoints
- `/list/expirations` - ✅ Returns available expiration dates
- `/list/strikes` - ✅ Returns available strike prices  
- `/snapshot/option/quote` - ✅ Current option quotes
- `/snapshot/option/ohlc` - ✅ Current option OHLC
- `/hist/option/ohlc` - ✅ Historical OHLC data
- `/hist/option/trade` - ✅ Historical trade data

### Bulk Endpoints (Implemented but require market hours/subscription)
- `/bulk_snapshot/option/quote` - Bulk option quotes
- `/bulk_snapshot/option/ohlc` - Bulk option OHLC
- `/bulk_snapshot/option/greeks` - Bulk Greeks data
- `/bulk_snapshot/option/open_interest` - Bulk open interest

### Response Format
```json
{
  "header": {
    "id": 1,
    "latency_ms": 89,
    "error_type": "null",
    "error_msg": "null"
  },
  "response": [data_array]
}
```

## Best Practices

### Function Naming Convention
- Use verb + noun + specific descriptor pattern
- Examples: `get_bulk_option_quotes`, `list_option_expirations`
- Avoid generic terms like `get_data`, `fetch_info`

### Async/Sync Design
- Always provide both interfaces
- Implement async first, wrap with sync
- Use context managers for resource management

### Error Handling
- Specific exception types for different scenarios
- Graceful degradation for missing data
- Informative error messages with context

### Data Conversion
- Automatic conversion of API data to user-friendly formats
- Strike prices: millidollars → dollars
- Dates: Multiple format support (string, int, date objects)

## Testing Strategy

### Endpoint Testing
- Systematic testing of all Terminal endpoints
- Mock testing for offline development
- Real API testing during market hours

### Integration Testing
- Full client functionality testing
- Context manager behavior
- Error condition handling

### Performance Testing
- Bulk vs individual request comparisons
- Concurrent request handling
- Rate limiting validation

## Future Roadmap

### Phase 1: Stock Market Data (High Priority)
**Missing: 10 endpoints covering complete stock data access**

1. **Stock Snapshots**
   - `get_stock_quote_snapshot(symbol)` - Current stock bid/ask
   - `get_stock_trade_snapshot(symbol)` - Last trade data
   - `get_stock_ohlc_snapshot(symbol)` - Current day OHLC

2. **Stock Bulk Operations**
   - `get_bulk_stock_quotes(symbols)` - Multiple stock quotes at once
   - `get_bulk_stock_ohlc(symbols)` - Multiple stock OHLC data

3. **Stock Historical Data**
   - `get_stock_quote_history(symbol, start, end)` - Historical quotes
   - `get_stock_trade_history(symbol, start, end)` - Historical trades
   - `get_stock_ohlc_history(symbol, start, end)` - Historical bars
   - `get_stock_splits(symbol, start, end)` - Stock split events
   - `get_stock_dividends(symbol, start, end)` - Dividend history

**Impact**: Complete equity market data coverage for portfolio analysis

### Phase 2: At-Time Queries (Medium Priority)
**Missing: 4 endpoints for point-in-time historical data**

1. **Option At-Time**
   - `get_option_quote_at_time(root, exp, strike, right, timestamp)` - Historical point-in-time quote
   - `get_option_trade_at_time(root, exp, strike, right, timestamp)` - Historical point-in-time trade

2. **Stock At-Time**
   - `get_stock_quote_at_time(symbol, timestamp)` - Historical stock quote
   - `get_stock_trade_at_time(symbol, timestamp)` - Historical stock trade

**Impact**: Backtesting and historical analysis capabilities

### Phase 3: Additional Option Data (Medium Priority)
**Missing: 4 endpoints for comprehensive options coverage**

1. **Option Trade & Open Interest Snapshots**
   - `get_option_trade_snapshot(root, exp, strike, right)` - Current trade data
   - `get_option_open_interest_snapshot(root, exp, strike, right)` - Current OI

2. **Option Historical Extensions**
   - `get_option_open_interest_history(root, exp, strike, right, start, end)` - Historical OI
   - `get_option_eod_report(root, exp, start, end)` - End-of-day summaries

**Impact**: Complete options data ecosystem

### Phase 4: Enhanced Streaming (Medium Priority)
**Missing: Advanced real-time capabilities**

1. **Index Streaming**
   - `subscribe_index_prices(symbol, handler)` - Real-time index prices
   - Index symbols: SPX, NDX, RUT, etc.

2. **Full Market Streams**
   - `subscribe_full_option_stream(handler)` - All option trades/quotes
   - `subscribe_full_stock_stream(handler)` - All stock trades/quotes

3. **Advanced Stream Management**
   - `get_stream_statistics()` - Connection health metrics
   - `pause_streaming()` / `resume_streaming()` - Stream control
   - Automatic reconnection with backoff

**Impact**: Professional-grade real-time market monitoring

### Phase 5: Advanced Analytics (Low Priority)
**New: Value-added analytical functions**

1. **Options Analytics**
   - `calculate_implied_volatility_surface(root, exp)` - IV surface construction
   - `find_arbitrage_opportunities(root, exp)` - Price inconsistency detection
   - `get_options_flow_analysis(root, start, end)` - Large trade analysis

2. **Portfolio Tools**
   - `calculate_portfolio_greeks(positions)` - Portfolio risk metrics
   - `simulate_price_scenarios(positions, scenarios)` - What-if analysis
   - `optimize_hedge_ratios(positions)` - Risk management

**Impact**: Professional trading and risk management tools

### Phase 6: Data Export & Integration (Low Priority)
**New: Enhanced data management capabilities**

1. **Export Formats**
   - `export_to_csv(data, filename)` - CSV export functionality
   - `export_to_parquet(data, filename)` - Efficient columnar storage
   - `export_to_hdf5(data, filename)` - High-performance scientific format

2. **Database Integration**
   - `save_to_database(data, connection_string)` - Direct DB storage
   - `create_data_pipeline(symbols, schedule)` - Automated data collection

3. **Third-Party Integrations**
   - Pandas DataFrame optimization
   - NumPy array conversions
   - QuantLib integration for pricing

**Impact**: Seamless integration with existing quantitative workflows

### Implementation Strategy

#### Development Priorities
1. **Stock endpoints** (80% of remaining API coverage)
2. **At-time queries** (backtesting capabilities)
3. **Additional options data** (completeness)
4. **Advanced features** (differentiation)

#### Technical Approach
- **Maintain consistency**: Follow existing naming conventions
- **Dual interfaces**: Always provide async/sync versions
- **Comprehensive testing**: Real API validation during market hours
- **Documentation first**: Update docs before implementation
- **Backward compatibility**: Never break existing interfaces

#### Estimated Timeline
- **Phase 1 (Stock Data)**: 2-3 weeks - High business value
- **Phase 2 (At-Time)**: 1-2 weeks - Moderate complexity
- **Phase 3 (Options Complete)**: 1 week - Low complexity
- **Phase 4 (Advanced Streaming)**: 3-4 weeks - High complexity
- **Phase 5 (Analytics)**: 4-6 weeks - Research required
- **Phase 6 (Export/Integration)**: 2-3 weeks - Infrastructure work

### Success Metrics
- **API Coverage**: Target 95%+ of ThetaData REST endpoints
- **Performance**: Bulk operations 10x faster than individual calls
- **Adoption**: Support for both research (sync) and production (async) use cases
- **Reliability**: Comprehensive error handling and graceful degradation

This reference provides the essential context for understanding and extending the ThetaData Python client implementation.