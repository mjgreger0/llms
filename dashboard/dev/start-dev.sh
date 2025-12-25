#!/bin/bash
# Development startup script for LLM Serve Dashboard
# Starts both backend and frontend with hot reload

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting LLM Serve Dashboard Development Servers${NC}"
echo "================================================"

# Check if required tools are available
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}Error: $1 is not installed${NC}"
        exit 1
    fi
}

check_command python3
check_command npm

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}Starting backend (FastAPI) on port 8080...${NC}"
cd "$PROJECT_ROOT"
python3 -m uvicorn dashboard.backend.main:app --host 0.0.0.0 --port 8080 --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend (Vite) on port 5173...${NC}"
cd "$PROJECT_ROOT/frontend"
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}Development servers started!${NC}"
echo "================================================"
echo -e "Backend API:  ${YELLOW}http://localhost:8080${NC}"
echo -e "Frontend Dev: ${YELLOW}http://localhost:5173${NC}"
echo -e "API Docs:     ${YELLOW}http://localhost:8080/docs${NC}"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
