#!/bin/bash

# 0DTE Trading Dashboard Launcher
# Main entry point for the trading dashboard

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         0DTE SPY Strangle Trading Dashboard          ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python is not installed${NC}"
    exit 1
fi

# Navigate to live trading tradier directory
cd "$(dirname "$0")/../0dte_live_trading/tradier" 2>/dev/null || cd "$(dirname "$0")"

# Check for required files
if [ ! -f "dashboard/tradingview_dashboard.py" ]; then
    echo -e "${RED}❌ Dashboard file not found${NC}"
    echo "Please ensure you're in the correct directory"
    exit 1
fi

# Display features
echo -e "${GREEN}Features:${NC}"
echo "  📊 Trading View - Real-time charts and signals"
echo "  ✅ Strategy Checklist - 13-point criteria evaluation"
echo "  📈 Risk Analysis - Position and Greeks monitoring"
echo "  📚 Strategy Guide - Trading rules and tips"
echo ""
echo -e "${GREEN}Data:${NC}"
echo "  • Pre-market data from 4:00 AM ET"
echo "  • Real-time updates every 10 seconds"
echo "  • 21 days of historical data"
echo ""

# Check if we should refresh data
read -p "Refresh today's data first? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Refreshing market data...${NC}"
    python scripts/refresh_today_data.py --quick || true
    echo
fi

# Start dashboard
echo -e "${GREEN}Starting dashboard...${NC}"
echo ""
echo "Dashboard will open at: http://localhost:7870"
echo "Press Ctrl+C to stop"
echo ""

# Launch dashboard
python dashboard/tradingview_dashboard.py

# Cleanup on exit
echo -e "\n${YELLOW}Dashboard stopped${NC}"
echo "Thank you for using 0DTE Trading Dashboard!"