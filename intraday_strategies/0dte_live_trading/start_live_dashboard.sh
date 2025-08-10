#!/bin/bash

# 0DTE Live Trading Dashboard (Tradier)
# For real-time trading with Tradier API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}     0DTE Live Trading Dashboard (Tradier API)        ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python is not installed${NC}"
    exit 1
fi

# Navigate to tradier directory
cd "$(dirname "$0")/tradier"

# Check for required files
if [ ! -f "dashboard/tradingview_dashboard.py" ]; then
    echo -e "${RED}❌ Dashboard file not found${NC}"
    echo -e "${YELLOW}Please ensure you're in the correct directory${NC}"
    exit 1
fi

# Check environment
if [ ! -f "config/.env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found${NC}"
    echo -e "${YELLOW}Creating from template...${NC}"
    if [ -f "../.env.example" ]; then
        cp ../.env.example config/.env
        echo -e "${GREEN}✅ Created config/.env - Please add your Tradier API credentials${NC}"
        exit 1
    fi
fi

# Launch dashboard
echo -e "${GREEN}🚀 Starting Live Trading Dashboard...${NC}"
echo -e "${YELLOW}📊 Opening at: http://localhost:7870${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Run the dashboard
python dashboard/tradingview_dashboard.py