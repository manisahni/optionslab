#!/bin/bash

# Alpaca Trading System Startup Script
# Manages live trading and monitoring for 0DTE options

echo "========================================"
echo "    ALPACA 0DTE TRADING SYSTEM"
echo "========================================"
echo ""

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Python executable
PYTHON="/opt/homebrew/bin/python3.11"

# Check Python
if [ ! -f "$PYTHON" ]; then
    echo "Error: Python 3.11 not found at $PYTHON"
    exit 1
fi

# Menu
echo "Select an option:"
echo "1) Test Alpaca Connection"
echo "2) Test VegaAware Strategy Components"
echo "3) Start Live Monitor (view positions/P&L)"
echo "4) Start Basic Trading Bot (simple $3 strikes)"
echo "5) Start VegaAware Bot (full strategy with Greeks)"
echo "6) Start LIVE VegaAware (requires confirmation)"
echo "7) View Historical Trades"
echo "8) Run Dashboard"
echo "9) Exit"
echo ""
read -p "Enter choice [1-9]: " choice

case $choice in
    1)
        echo "Testing Alpaca connection..."
        $PYTHON test_alpaca.py
        ;;
    2)
        echo "Testing VegaAware Strategy Components..."
        $PYTHON test_vegaware.py
        ;;
    3)
        echo "Starting position monitor..."
        echo "Press Ctrl+C to stop"
        $PYTHON alpaca_monitor.py
        ;;
    4)
        echo "Starting basic paper trading bot..."
        echo "Simple $3 strikes | Entry: 3:00 PM ET | Exit: 3:58 PM ET"
        echo "Press Ctrl+C to stop"
        $PYTHON alpaca_live_trader.py
        ;;
    5)
        echo "Starting VegaAware paper trading bot..."
        echo "Full strategy with Greeks, stop losses, and profit targets"
        echo "Entry: 2:30-3:30 PM ET | 13 criteria checks | 80% score required"
        echo "Press Ctrl+C to stop"
        $PYTHON alpaca_vegaware_trader.py
        ;;
    6)
        echo "⚠️  WARNING: This will start LIVE VEGAWARE TRADING with real money!"
        echo "The bot will:"
        echo "  - Check 13 entry criteria"
        echo "  - Use 0.15 delta strikes"
        echo "  - Apply 2x stop loss"
        echo "  - Exit at 50% profit or 3:55 PM"
        read -p "Are you absolutely sure? (type 'yes' to confirm): " confirm
        if [ "$confirm" = "yes" ]; then
            $PYTHON alpaca_vegaware_trader.py --live
        else
            echo "Cancelled."
        fi
        ;;
    7)
        echo "Viewing historical trades..."
        $PYTHON -c "
import sqlite3
conn = sqlite3.connect('database/market_data.db')
cur = conn.cursor()

# Try VegaAware trades first
cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"alpaca_vegaware_trades\"')
if cur.fetchone():
    cur.execute('SELECT * FROM alpaca_vegaware_trades ORDER BY trade_date DESC LIMIT 10')
    trades = cur.fetchall()
    if trades:
        print('\nRecent VegaAware Trades:')
        print('-' * 80)
        for trade in trades:
            print(f\"Date: {trade[1]}, Score: {trade[18]}%, P&L: \${trade[26]:.2f} ({trade[27]:.1f}%), Reason: {trade[29]}\")
    else:
        print('No VegaAware trades found.')
        
# Also check basic trades
cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"alpaca_trades\"')
if cur.fetchone():
    cur.execute('SELECT * FROM alpaca_trades ORDER BY trade_date DESC LIMIT 5')
    trades = cur.fetchall()
    if trades:
        print('\nRecent Basic Trades:')
        print('-' * 80)
        for trade in trades:
            print(f\"Date: {trade[1]}, P&L: \${trade[14]:.2f} ({trade[15]:.1f}%), Status: {trade[16]}\")
            
conn.close()
"
        ;;
    8)
        echo "Starting TradingView dashboard..."
        echo "Opening http://localhost:7870"
        $PYTHON dashboard/tradingview_dashboard.py
        ;;
    9)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo ""
echo "Press any key to continue..."
read -n 1