# 📊 DATA MANAGEMENT & SPY OPTIONS DATASET

## ⚠️ CRITICAL: We Already Have 5+ Years of SPY Options Data!

**Stop! Before downloading ANY SPY options data, know that we have:**
- **1,265 daily EOD parquet files** already downloaded
- **Date Range**: July 2020 through July 2025
- **Location**: `/Users/nish_macbook/trading/daily-optionslab/data/spy_options/`
- **Format**: `spy_options_eod_YYYYMMDD.parquet`
- **Content**: Full option chains with prices, Greeks, volume, OI

**This dataset took significant time and effort to download. DO NOT duplicate this work!**

## Data Usage Hierarchy (MANDATORY ORDER)

### 1️⃣ FIRST - Check if Data Already Exists
```bash
# Check available date range
ls /Users/nish_macbook/trading/daily-optionslab/data/spy_options/*.parquet | wc -l
# Output: 1265 files

# Check specific date (example: 2024-01-15)
ls /Users/nish_macbook/trading/daily-optionslab/data/spy_options/*20240115*.parquet
# If file exists, USE IT!

# Quick date range check
ls data/spy_options/*.parquet | head -1  # First file
ls data/spy_options/*.parquet | tail -1  # Last file
```

### 2️⃣ SECOND - Use optionslab.data_loader (Handles Everything)
```python
# CORRECT WAY - Use existing infrastructure
from optionslab.data_loader import load_data

# This automatically:
# - Finds all files in date range
# - Loads and combines them
# - Handles strike conversion
# - Validates data quality
data = load_data('data/spy_options/', '2023-01-01', '2024-12-31')

# For research notebooks - still use data_loader!
import sys
sys.path.append('/Users/nish_macbook/trading/daily-optionslab')
from optionslab.data_loader import load_data

# Load existing data
data = load_data('data/spy_options/', start_date, end_date)
```

### 3️⃣ LAST RESORT - Download ONLY Missing Dates
```python
# ONLY if data doesn't exist for your dates
from datetime import datetime, timedelta

def check_missing_dates(start_date, end_date):
    """Check which dates are missing from local data"""
    import pandas as pd
    from pathlib import Path
    
    data_dir = Path('data/spy_options')
    date_range = pd.date_range(start_date, end_date, freq='B')  # Business days
    
    missing = []
    for date in date_range:
        date_str = date.strftime('%Y%m%d')
        pattern = f'*{date_str}*.parquet'
        if not list(data_dir.glob(pattern)):
            missing.append(date)
    
    return missing

# Check before downloading
missing = check_missing_dates('2024-01-01', '2024-12-31')
if missing:
    print(f"Missing {len(missing)} dates: {missing[:5]}...")
    # ONLY download these specific dates
else:
    print("✅ All data already exists! Use load_data()")
```

## ⛔ Data Protection Rules

**NEVER DO THIS:**
```python
# ❌ DON'T overwrite existing files
df.to_parquet('data/spy_options/spy_options_eod_20240115.parquet')  # NO!

# ❌ DON'T delete the data directory
shutil.rmtree('data/spy_options/')  # ABSOLUTELY NOT!

# ❌ DON'T download data that already exists
download_spy_data('2023-01-01', '2024-12-31')  # We have this already!

# ❌ DON'T modify existing parquet files
os.remove('data/spy_options/*.parquet')  # NEVER!
```

**ALWAYS DO THIS:**
```python
# ✅ READ existing data
from optionslab.data_loader import load_data
data = load_data('data/spy_options/', start_date, end_date)

# ✅ Check before downloading
if not Path(f'data/spy_options/spy_options_eod_{date_str}.parquet').exists():
    # Only then consider downloading

# ✅ Save new data with different names if needed
df.to_parquet(f'data/research/my_analysis_{date}.parquet')  # Different directory

# ✅ Use existing infrastructure
from optionslab.backtest_engine import run_auditable_backtest
results = run_auditable_backtest(
    data_file='data/spy_options/',  # Points to existing data
    config_file='config/strategy.yaml',
    start_date='2023-01-01',
    end_date='2024-12-31'
)
```

## Quick Data Inventory Commands

```bash
# Count total files
ls data/spy_options/*.parquet | wc -l

# Get date range
ls data/spy_options/*.parquet | head -1 | grep -oE '[0-9]{8}'  # First date
ls data/spy_options/*.parquet | tail -1 | grep -oE '[0-9]{8}'  # Last date

# Check specific month (e.g., Jan 2024)
ls data/spy_options/*202401*.parquet | wc -l

# Get file sizes (check data completeness)
ls -lh data/spy_options/*.parquet | head

# Find gaps in data
for i in {20230101..20231231}; do
  if ! ls data/spy_options/*$i*.parquet 2>/dev/null; then
    echo "Missing: $i"
  fi
done
```

## Data Coverage Summary

| Year | Coverage | Files | Notes |
|------|----------|-------|-------|
| 2020 | Jul-Dec | ~120 | Partial year |
| 2021 | Full | ~252 | Complete |
| 2022 | Full | ~252 | Complete |
| 2023 | Full | ~252 | Complete |
| 2024 | Full | ~252 | Complete |
| 2025 | Jan-Jul | ~137 | Through July 11 |

**Total: 1,265 files covering 5+ years of daily SPY options data**

## Why This Matters

1. **Time Saved**: Each file took time to download from ThetaData
2. **Cost**: ThetaData has rate limits and potential costs
3. **Consistency**: All research uses the same validated dataset
4. **Reproducibility**: Results can be replicated with same data
5. **Storage**: These files represent GB of valuable market data

## If You Need Different Data

For non-SPY symbols or different data types:
1. First check if we have it: `ls data/*/` 
2. Consider if SPY can proxy your research
3. Only then download new data to a NEW directory
4. Document what you downloaded and why

**Remember: The existing SPY dataset is a valuable resource. Protect it and use it!**

## Data Pipeline
```
ThetaData Terminal (port 11000)
        ↓
spy_options_downloader/downloader.py
        ↓
spy_options_parquet/ (raw storage)
        ↓
daily_strategies/data/spy_options/ (processed)
        ↓
OptionsLab backtesting engine
```

## Data Format
- **Type**: Daily EOD snapshots
- **Storage**: Parquet files
- **Fields**: Open, High, Low, Close, Volume, Greeks
- **History**: 2020-2025 SPY options

## ⚠️ IMPORTANT: Options Data Quality - Zero Prices (VALIDATED IN TESTING)
**EXACTLY 50% of options have close price = $0.00** - This is NORMAL and EXPECTED:

### Testing Findings (Phase 2 Integration Tests):
- **Tested Dataset**: SPY options 2024-03-01 to 2024-03-05 (170,810 records)
- **Zero Close Prices**: 85,405 options (exactly 50% of dataset)  
- **Perfect Correlation**: Every close=0 option also has volume=0
- **Distribution**: More common in far OTM strikes (>10% from current price)
- **Verification**: Cross-checked with bid/ask data - all zero-close options have valid markets

### Why Zero Prices Exist:
1. **Close = Last traded price** - If option didn't trade today, close = 0
2. **Bid/Ask still valid** - Market makers provide quotes even without trades
3. **Perfect correlation** - Every close=0 option also has volume=0 (validated in tests)
4. **Common for illiquid strikes** - Most OTM options don't trade daily
5. **Market Structure** - Options markets are quote-driven, not trade-driven

### How the System Handles It (TESTED AND VERIFIED):
1. **Option Selection** (`option_selector.py`) filters out illiquid options:
   - Requires minimum volume (default 100) 
   - Requires valid bid > 0
   - Requires tight spreads (<15% or <$0.50)
   - Has fallback logic if filters too strict
   - **Guard Clause**: Returns (0,0) for zero-price options with audit log

2. **Position Sizing** (`calculate_position_size()`):
   ```python
   if max_loss_per_contract <= 0:
       print(f"⚠️ AUDIT: Zero/negative option price ${option_price:.2f} - skipping")
       return 0, 0
   ```

3. **For Pricing** - Uses bid/ask midpoint when close=0:
   ```python
   mid_price = (bid + ask) / 2
   ```

4. **Data Loading** - No preprocessing needed, handled at selection level

### Testing Protocol for Zero Prices:
```python
# Standard validation in all tests
zero_close = (data['close'] == 0).sum()
zero_volume = (data['volume'] == 0).sum()
print(f"Zero close prices: {zero_close:,} ({zero_close/len(data):.1%})")
print(f"Zero volume: {zero_volume:,} ({zero_volume/len(data):.1%})")
assert zero_close == zero_volume, "Close=0 should equal volume=0"
```

### Key Insights from Testing:
1. **NOT corrupted data** - it's how options markets work
2. **Consistent across all dates** - always ~50% for SPY options
3. **System handles correctly** - liquidity filters prevent selection
4. **No data cleaning needed** - handle at algorithm level
5. **Perfect for testing** - predictable pattern for validation

### Historical Context:
- **Before Testing**: Assumed this was data corruption, spent time investigating
- **After Testing**: Confirmed normal market behavior, documented in system  
- **Lesson**: Always validate data quality assumptions before "fixing" data

## Strike Price Format: The Deterministic Approach

**NO MORE GUESSING WITH THRESHOLDS!** We know exactly what format each source uses:

### ThetaData Format (Our Primary Source) - VALIDATED IN TESTING
- **ALWAYS uses 1/1000th dollars** (documented in their API)
- Strike 407000 = $407.00 (always divide by 1000)
- Strike 120000 = $120.00 (always divide by 1000)  
- **No threshold checking needed!**

### Testing Validation (Phase 1.1 Data Loader Tests):
- **Raw Strike Range**: 120000 - 910000 (cents format)
- **Converted Range**: $120.00 - $910.00 (dollar format) 
- **Conversion Factor**: Exactly 1000x (verified deterministically)
- **Auto-Detection**: Works reliably on 'spy_options' path pattern
- **No Failures**: 100% successful conversion across all test data

### How It's Handled Now (TESTED AND VERIFIED)
```python
# optionslab/data_loader.py automatically handles this based on source:

# For ThetaData sources (auto-detected from path):
data = load_data('data/spy_options/', start, end)  # Automatically converts!

# Test validation shows:
print("📊 AUDIT: Converting ThetaData strikes (1/1000th dollars → dollars)")
print(f"   Before: {df['strike'].min():.0f} - {df['strike'].max():.0f}")
df['strike'] = df['strike'] / 1000  # Deterministic conversion
print(f"   After: ${df['strike'].min():.2f} - ${df['strike'].max():.2f}")

# Or explicitly specify the format:
data = load_data('some/path', start, end, source_format='thetadata')  # Divides by 1000
data = load_data('other/path', start, end, source_format='dollars')   # No conversion

# The loader detects ThetaData sources by path patterns (TESTED):
# - Contains 'spy_options' ✅
# - Contains 'thetadata' ✅
# - Contains 'parquet' ✅
```

### Why Thresholds Were Wrong (Lesson from Testing)
- Arbitrary thresholds (>1000, >10000) are fragile and unreliable
- What if a stock trades at $15,000? We'd break valid data
- **We KNOW ThetaData's format** - use that knowledge deterministically
- **Testing proved**: Source-based detection is 100% accurate vs threshold guessing

## Data Source Format Reference

| Source | Strike Format | Date Format | Greeks | Conversion |
|--------|--------------|-------------|--------|------------|
| **ThetaData API** | ALWAYS 1/1000th dollars | Integer (20240115) | May be 0.0000 | Divide by 1000 |
| **spy_options/** | 1/1000th dollars (ThetaData) | datetime | Pre-calculated | Auto-converted by data_loader |
| **CSV Exports** | Varies - check header | String or datetime | May be missing | Specify source_format |
| **Other Sources** | Usually dollars | Varies | Varies | No conversion needed |

## Downloading New Data
```bash
cd /Users/nish_macbook/trading/daily-optionslab
source venv/bin/activate
python spy_options_downloader/downloader.py --date 20250819
```

**Note**: Downloaded data will have ~50% zero close prices. This is expected (see Data Quality section above).