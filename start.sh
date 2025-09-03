#!/bin/bash

# Form & Function Calc Engine Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Form & Function Calc Engine...${NC}"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"; then
    echo -e "${GREEN}Python version ${python_version} is compatible${NC}"
else
    echo -e "${RED}Python version ${python_version} is too old. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Set environment variables
export API_BASE_URL=${API_BASE_URL:-"http://localhost:8080"}
export CALC_ENGINE_PORT=${CALC_ENGINE_PORT:-"8081"}

echo -e "${GREEN}Environment Configuration:${NC}"
echo -e "  API Base URL: ${API_BASE_URL}"
echo -e "  Calc Engine Port: ${CALC_ENGINE_PORT}"

# Check if Go API is running
echo -e "${YELLOW}Checking API connectivity...${NC}"
if curl -s "${API_BASE_URL}/beams" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Go API is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Go API at ${API_BASE_URL} is not accessible${NC}"
    echo -e "${YELLOW}  Make sure your Go API is running on port 8080${NC}"
fi

# Start the calc engine
echo -e "${GREEN}Starting calc engine on port ${CALC_ENGINE_PORT}...${NC}"
echo -e "${GREEN}Access the API documentation at: http://localhost:${CALC_ENGINE_PORT}/docs${NC}"
echo -e "${GREEN}Press Ctrl+C to stop the server${NC}"
echo ""

python main.py
