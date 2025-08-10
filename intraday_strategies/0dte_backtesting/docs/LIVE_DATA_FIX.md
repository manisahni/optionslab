# Live Data Loading Fix for Dashboard

## Problem
Dashboard was only showing yesterday's data when started in the morning, not loading today's pre-market or live data.

## Root Cause
1. Dashboard only looked for existing data in database
2. `load_today_data()` was only called if cache didn't exist
3. Pre-market hours (before 9:30 AM) weren't being captured
4. Today wasn't added to dropdown if no data existed yet

## Solutions Implemented

### 1. Force Load Today's Data on Initialize
**File**: `/Users/nish_macbook/0dte/tradier/dashboard/tradingview_dashboard.py`

```python
# Force load today's data explicitly
print("Loading today's market data...")
try:
    new_records = self.cache_mgr.loader.load_today_data()
    print(f"Loaded {new_records} new records for today")
except Exception as e:
    print(f"Note: Could not load today's data: {e}")
```

### 2. Enhanced Date Loading
**File**: `/Users/nish_macbook/0dte/tradier/dashboard/tradingview_dashboard.py`

- Always add "Today" to dropdown if it's a weekday
- Show "(Pre-market)" label before market open
- Show "(Live)" label when data is available
- Check for market days (Monday-Friday)

### 3. Pre-Market Data Collection
**File**: `/Users/nish_macbook/0dte/tradier/core/historical_loader.py`

```python
# Start from pre-market (4:00 AM ET) to capture all available data
start_str = today.strftime("%Y-%m-%d 04:00")
end_str = today.strftime("%Y-%m-%d %H:%M")

# Include pre-market and after-hours
session_filter="all"
```

### 4. Manual Refresh Script
**File**: `/Users/nish_macbook/0dte/tradier/scripts/refresh_today_data.py`

Created utility script to manually refresh today's data:
```bash
python tradier/scripts/refresh_today_data.py
```

## How It Works Now

### Dashboard Startup Sequence:
1. Initialize cache manager
2. Check for existing cache
3. **NEW**: Force load today's data
4. **NEW**: Add today to dropdown even if no data
5. Start real-time updates (every 10 seconds)

### Data Loading Timeline:
- **4:00 AM**: Pre-market data starts
- **8:00 AM**: Dashboard can load pre-market data
- **9:30 AM**: Regular market opens
- **4:00 PM**: Market closes
- **8:00 PM**: After-hours ends

## Testing Results

✅ Successfully loaded 207 pre-market records at 8:45 AM
✅ Dashboard shows "Today" in dropdown
✅ Real-time updates working (every 10 seconds)
✅ SPY price updating: $633.90 (pre-market)

## Usage

### Start Dashboard with Live Data:
```bash
cd /Users/nish_macbook/0dte/tradier
python dashboard/tradingview_dashboard.py
```

### Manual Data Refresh:
```bash
python scripts/refresh_today_data.py
```

### Verify Data:
```sql
SELECT COUNT(*), MIN(timestamp), MAX(timestamp) 
FROM spy_prices 
WHERE date(timestamp) = date('now');
```

## Benefits

1. **Pre-Market Visibility**: See SPY movement before market open
2. **Real-Time Updates**: Data refreshes every 10 seconds
3. **No Missing Days**: Today always appears in dropdown
4. **Reliable Loading**: Explicit data fetch on startup
5. **Debug Tools**: Manual refresh script for troubleshooting

## Notes

- Pre-market volume is typically lower
- Data starts at 4:00 AM ET
- Real-time updates continue throughout the day
- Dashboard auto-detects market vs non-market days
- Sandbox environment has same data as production for SPY