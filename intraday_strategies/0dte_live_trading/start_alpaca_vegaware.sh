#!/bin/bash

# VegaAware Alpaca Trading System Startup Script
# Launches the live trading system with monitoring

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/Users/nish_macbook/theta-options-suite"
SCRIPT_DIR="$PROJECT_ROOT/intraday_strategies/0dte_live_trading"
VENV_PATH="$PROJECT_ROOT/venv"

# Print header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   VegaAware Alpaca Trading System${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ "$PWD" != "$SCRIPT_DIR" ]; then
    echo -e "${YELLOW}Changing to trading directory...${NC}"
    cd "$SCRIPT_DIR"
fi

# Activate virtual environment
echo -e "${GREEN}Activating Python environment...${NC}"
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo -e "${RED}Virtual environment not found at $VENV_PATH${NC}"
    echo -e "${RED}Please run: python3 -m venv $VENV_PATH${NC}"
    exit 1
fi

# Check Python version
PYTHON_CMD="/opt/homebrew/bin/python3.11"
echo -e "${GREEN}Python version:${NC} $($PYTHON_CMD --version)"

# Menu
echo ""
echo -e "${BLUE}Select mode:${NC}"
echo "1) Test Connection - Verify Alpaca API"
echo "2) Test Strategy - Check entry criteria"
echo "3) Live Trading - Start VegaAware trader"
echo "4) Monitor Only - View positions and P&L"
echo "5) Paper Trading - Test with paper account"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo -e "\n${GREEN}Testing Alpaca connection...${NC}"
        $PYTHON_CMD -m alpaca_vegaware.test_connection
        ;;
    2)
        echo -e "\n${GREEN}Testing VegaAware strategy...${NC}"
        $PYTHON_CMD -m alpaca_vegaware.test_strategy
        ;;
    3)
        echo -e "\n${YELLOW}⚠️  WARNING: LIVE TRADING MODE${NC}"
        echo -e "${YELLOW}This will place REAL trades with REAL money${NC}"
        read -p "Are you sure? Type 'YES' to confirm: " confirm
        if [ "$confirm" = "YES" ]; then
            echo -e "\n${RED}Starting LIVE trading...${NC}"
            $PYTHON_CMD -m alpaca_vegaware.vegaware_trader --live
        else
            echo -e "${GREEN}Cancelled. No trades will be placed.${NC}"
        fi
        ;;
    4)
        echo -e "\n${GREEN}Starting position monitor...${NC}"
        $PYTHON_CMD -m alpaca_vegaware.monitor
        ;;
    5)
        echo -e "\n${GREEN}Starting paper trading...${NC}"
        $PYTHON_CMD -m alpaca_vegaware.vegaware_trader --paper
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "\n${GREEN}Process completed.${NC}"