# Market Data Dictionary

## Overview
This project contains TWO distinct types of minute-level data:

1. **OPTIONS DATA** - Intraday options chains
2. **STOCK DATA** - Intraday stock price bars

Both are minute-level data, NOT daily vs minute.

---

## 1. OPTIONS DATA
**Location**: `/options_data/spy_0dte_minute/`

### Description
- Minute-by-minute snapshots of all 0DTE SPY option contracts
- Captured every minute from 9:30 AM to 4:00 PM ET
- Approximately 50 contracts × 391 minutes = ~19,550 records per day

### File Format
- **Pattern**: `zero_dte_spy_YYYYMMDD.parquet`
- **Example**: `zero_dte_spy_20250801.parquet`

### Data Columns
| Column | Description | Example |
|--------|-------------|---------|
| symbol | Option symbol | SPY |
| expiration | Expiration date | 2025-08-01 |
| strike | Strike price | 440.0 |
| right | Option type | CALL or PUT |
| timestamp | Minute timestamp | 2025-08-01T10:00:00 |
| bid | Bid price | 1.25 |
| ask | Ask price | 1.30 |
| bid_size | Bid size | 100 |
| ask_size | Ask size | 150 |
| delta | Option delta | 0.35 |
| gamma | Option gamma | 0.02 |
| theta | Option theta | -0.15 |
| vega | Option vega | 0.08 |
| rho | Option rho | 0.01 |
| implied_vol | Implied volatility | 0.18 |
| underlying_price | SPY price (cents) | 44050 |
| underlying_price_dollar | SPY price ($) | 440.50 |

### Usage Example
```python
from core.zero_dte_spy_options_database import MinuteLevelOptionsDatabase

db = MinuteLevelOptionsDatabase()
options_data = db.load_zero_dte_data('20250801')
# Returns ~19,550 records for all options throughout the day
```

---

## 2. STOCK DATA
**Location**: `/stock_data/spy_minute/`

### Description
- One-minute OHLCV bars for SPY stock
- 391 bars per trading day (9:30 AM to 4:00 PM ET)
- Standard stock market data

### File Format
- **Pattern**: `YYYY-MM-DD/SPY_1min.parquet`
- **Example**: `2025-08-01/SPY_1min.parquet`

### Data Columns
| Column | Description | Example |
|--------|-------------|---------|
| date | Timestamp with timezone | 2025-08-01 09:30:00-04:00 |
| open | Opening price | 440.25 |
| high | High price | 440.50 |
| low | Low price | 440.10 |
| close | Closing price | 440.35 |
| volume | Volume traded | 125000.0 |

### Usage Example
```python
import pandas as pd

stock_data = pd.read_parquet('stock_data/spy_minute/2025-08-01/SPY_1min.parquet')
# Returns 391 records (one per minute)
```

---

## Key Differences

| Aspect | Options Data | Stock Data |
|--------|--------------|------------|
| **Type** | Option chains | Stock bars |
| **Granularity** | Minute-level | Minute-level |
| **Records/Day** | ~19,550 | 391 |
| **Contracts** | ~50 different strikes | 1 (SPY) |
| **Pricing** | Bid/Ask spreads | OHLC |
| **Greeks** | Yes (delta, gamma, etc.) | No |
| **Directory** | options_data/ | stock_data/ |

## Relationship Between Datasets

### SPY Price Data Overlap
Both datasets contain SPY price information, but with different detail levels:

| Feature | Options Data | Stock Data |
|---------|-------------|------------|
| **SPY Price** | Single snapshot per minute | Full OHLC bar |
| **What price?** | Price when options were quoted | Open, High, Low, Close |
| **Volume** | ❌ Not included | ✅ Included |
| **Coverage** | 249 days | 66 days |

### When to Use Which Dataset

**Use Options Data underlying_price when:**
- Running options backtests (already included)
- Need data for all 249 days
- Don't need volume or high/low information

**Use Stock Data when:**
- Need volume information
- Need intraday high/low (for stops, support/resistance)
- Calculating VWAP or volume-based indicators
- Only need the 66 days available

## Important Notes

1. **Both datasets are minute-level** - There is no "daily" data
2. **Options data is much larger** - ~50x more records due to multiple contracts
3. **Time alignment** - Both datasets cover the same trading hours
4. **Data quality issues** - Options data has some delta calculation problems (many show 1.0)
5. **Redundancy is intentional** - Different detail levels serve different purposes

## Common Confusion Points

❌ **Wrong**: "One is daily data, the other is minute data"
✅ **Right**: "Both are minute-level data - one for options, one for stocks"

❌ **Wrong**: "zero_dte_spy_database contains daily summaries"
✅ **Right**: "It contains minute-by-minute option chain snapshots"