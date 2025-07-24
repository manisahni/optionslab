#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}🚀 Starting OptionsLab Trading Platform${NC}"
echo -e "${BLUE}============================================================${NC}"

# Check if we're in the right directory
if [ ! -f "optionslab/app.py" ]; then
    echo -e "${RED}❌ Error: Not in the correct directory!${NC}"
    echo "Please run this script from the thetadata-api directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Error: Virtual environment not found!${NC}"
    echo "Please create a virtual environment first"
    exit 1
fi

# Activate virtual environment
echo -e "\n${YELLOW}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Kill any existing processes
echo -e "${YELLOW}🔍 Checking for existing processes...${NC}"
if pgrep -f "python.*optionslab" > /dev/null; then
    echo -e "${YELLOW}   Stopping existing OptionsLab processes...${NC}"
    pkill -f "python.*optionslab"
    sleep 1
    echo -e "${GREEN}   ✅ Existing processes stopped${NC}"
else
    echo -e "${GREEN}   ✅ No existing processes found${NC}"
fi

# Check if port is free
if lsof -i :7862 > /dev/null 2>&1; then
    echo -e "${YELLOW}   Port 7862 is in use, clearing...${NC}"
    lsof -ti:7862 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Start the app
echo -e "\n${GREEN}🌐 Launching OptionsLab...${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}✅ Server starting on:${NC}"
echo -e "   ${BLUE}• Local:    http://localhost:7862${NC}"
echo -e "   ${BLUE}• Network:  http://0.0.0.0:7862${NC}"
echo -e "\n${YELLOW}⏳ Please wait a few seconds for the server to start...${NC}"
echo -e "${YELLOW}⌨️  Press Ctrl+C to stop${NC}"
echo -e "${BLUE}============================================================${NC}\n"

# Run the app
exec python -m optionslab.app