# 🎯 0DTE Strangle Dashboard - Running Instructions

## ✅ Dashboard Status: RUNNING

Based on the logs, your dashboard is successfully running!

## 📍 Access the Dashboard

**Open your web browser and navigate to:**

### http://localhost:7860

## 🚀 Quick Start

1. **To launch the dashboard** (if not already running):
   ```bash
   cd /Users/nish_macbook/0dte/market_data
   python dashboards/comprehensive_strangle_dashboard.py
   ```

2. **Alternative launch methods**:
   ```bash
   ./launch_dashboard.sh
   # or
   python run_dashboard.py
   ```

## 📊 Dashboard Features

Once you open http://localhost:7860 in your browser, you'll see:

### 1. **Parameter Sweep Tab** 🎯
- Test multiple delta targets (0.15-0.40)
- Try different entry times (9:45, 10:00, 10:30, 11:00)
- Compare execution modes (conservative, midpoint, aggressive)
- View heatmaps and 3D performance surfaces
- Export results to CSV

### 2. **Trade Inspector Tab** 🔍
- Load any historical trade by date (e.g., 20241202)
- See minute-by-minute P&L evolution
- View complete Greek profiles
- Analyze execution quality
- Run what-if scenarios

### 3. **Greek Visualizer Tab** 📈
- Interactive 3D Greek surfaces
- Greek profiles by strike
- Compare original vs corrected Greeks
- Risk scenario analysis
- Real-time Greek calculations

### 4. **Education Center Tab** 🎓
- Interactive tutorials for each Greek
- Strangle strategy guide
- P&L calculator
- Quiz mode to test your knowledge
- Searchable glossary

### 5. **Settings Tab** ⚙️
- Configure data paths
- Adjust risk-free rate
- Export preferences
- Session notes

## 🛠️ Troubleshooting

If you can't access the dashboard:

1. **Check if it's running**:
   ```bash
   curl http://localhost:7860
   ```
   Should return HTML content.

2. **Check if port 7860 is in use**:
   ```bash
   lsof -i :7860
   ```

3. **Kill any existing processes**:
   ```bash
   pkill -f "python.*comprehensive_strangle_dashboard"
   ```

4. **Try a different port**:
   Edit line 475 in `comprehensive_strangle_dashboard.py`:
   ```python
   server_port=7861,  # Change to different port
   ```

## 💡 Tips

- The dashboard uses the corrected Greeks (Black-Scholes calculations)
- All data is from the SPY 0DTE options database
- Parameter sweeps may take a few minutes for large date ranges
- Use the Education Center to understand the Greeks better

## 🎉 Enjoy exploring your 0DTE strategies!

The dashboard provides complete transparency and auditability for all calculations.