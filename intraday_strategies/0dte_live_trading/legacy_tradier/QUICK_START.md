# Quick Start Guide - Tradier Cache System

## 📍 Important: Run all commands from the `/Users/nish_macbook/0dte` directory

```bash
cd /Users/nish_macbook/0dte
```

## 1️⃣ Initialize Cache (First Time Setup)
```bash
# Download 20 days of historical data
python tradier/scripts/initialize_cache.py --days 20
```

## 2️⃣ Start Real-Time Updates (Keep Running)
```bash
# Start the updater (updates every 10 seconds)
python tradier/scripts/initialize_cache.py --start-updater
```
Press `Ctrl+C` to stop

## 3️⃣ Run Dashboard (In New Terminal)
```bash
cd /Users/nish_macbook/0dte
python tradier/dashboard/gradio_dashboard.py
```
Access at: http://localhost:7870

## 4️⃣ Monitor Positions (Optional)
```bash
cd /Users/nish_macbook/0dte
python tradier/scripts/live_monitor.py
```

## 5️⃣ Validate Cache
```bash
cd /Users/nish_macbook/0dte
python tradier/scripts/validate_cache.py
```

## 📊 Check Cache Status
```bash
cd /Users/nish_macbook/0dte
python -c "from tradier.core.cache_manager import TradierCacheManager; c = TradierCacheManager(); print(c.get_cache_statistics())"
```

## 🔍 Database Location
The SQLite database is stored at:
```
/Users/nish_macbook/0dte/tradier/database/market_data.db
```

## ✅ Current Status
- Cache initialized with 3,600+ records
- Real-time updates active (every 10 seconds)
- Dashboard will show full day's data from 9:30 AM
- All queries < 50ms response time

## 🚨 Troubleshooting

### If you get "No such file or directory":
Make sure you're in the `/Users/nish_macbook/0dte` directory:
```bash
pwd  # Should show: /Users/nish_macbook/0dte
```

### If real-time updates aren't working:
1. Check if market is open (9:30 AM - 4:00 PM ET)
2. Kill any existing processes:
   ```bash
   pkill -f "initialize_cache.py"
   ```
3. Restart the updater

### To stop all Tradier processes:
```bash
pkill -f "tradier"
```