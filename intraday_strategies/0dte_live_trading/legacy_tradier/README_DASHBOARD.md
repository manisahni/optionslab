# 0DTE Strangle Dashboard - Quick Start Guide

## ✅ System Status
The dashboard is now fully functional with the following fixes implemented:
- **Chart Display**: Fixed empty chart issues by handling single data points and empty arrays
- **Data Persistence**: Dashboard now loads historical data from `tradier_risk_metrics.json` on startup
- **Greeks Visualization**: All Greeks (Delta, Gamma, Theta, Vega) now display properly with markers for single points

## 🚀 Starting the Dashboard

### Method 1: Direct Launch
```bash
cd /Users/nish_macbook/0dte
python tradier/dashboard/gradio_dashboard.py
```

### Method 2: Using Launch Script
```bash
cd /Users/nish_macbook/0dte
./tradier/start_dashboard.sh
```

The dashboard will be available at: **http://localhost:7870**

## 📊 Dashboard Features

### Real-Time Monitoring
- **SPY Price**: Live price tracking with chart
- **Position Details**: Call and put strikes, prices, and IVs
- **Greeks**: Delta, Gamma, Theta, Vega with evolution charts
- **Risk Assessment**: Color-coded risk levels for each metric

### Visual Components
1. **Price Chart**: Shows SPY price movement with strike lines
2. **Greeks Charts**: 2x2 grid showing evolution of each Greek
3. **Strike Map**: Visual representation of position relative to SPY price
4. **Risk Indicators**: Color-coded warnings and exit recommendations

### Data Persistence
- Automatically loads last 50 data points from previous sessions
- Continues building history as new data arrives
- Charts update from markers to lines as data accumulates

## 🔄 Generating Data

To populate the dashboard with data, run the live monitor:
```bash
python tradier/scripts/live_monitor.py
```

This will:
- Update every 30 seconds
- Calculate real-time Greeks
- Save metrics to `tradier_risk_metrics.json`
- Provide exit strategy recommendations

## 📝 Current Position (Sandbox)
- **Call**: SPY250807C00636000 (Strike: $636)
- **Put**: SPY250807P00629000 (Strike: $629)
- **Account**: VA56528795 (Sandbox)

## 🎯 Risk Thresholds
- **Vega Limit**: 2.0
- **Delta Limit**: 0.20
- **Strike Buffer**: 0.5%
- **Time Stop**: 1 minute to close

## 🛠️ Troubleshooting

### If charts are empty:
1. Run the monitor to generate data: `python tradier/scripts/live_monitor.py`
2. Wait for at least 2 data points (60 seconds)
3. Refresh the dashboard

### If connection fails:
1. Check that market is open (9:30 AM - 4:00 PM ET)
2. Verify sandbox credentials are correct
3. Check internet connection

## 📋 Next Steps
1. Continue testing in sandbox environment
2. Monitor position throughout the day
3. Test exit strategy execution
4. Prepare for live trading deployment