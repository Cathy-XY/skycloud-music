#!/bin/bash
# start.sh - Launch both backend and frontend for the Music Player demo

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Music Player Demo ==="
echo ""

# Start backend
echo "[1/2] Starting backend..."
cd "$SCRIPT_DIR/backend"
if [ ! -d "venv" ]; then
  echo "  Creating Python virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt -q
else
  source venv/bin/activate
fi
python app.py &
BACKEND_PID=$!
echo "  Backend running on http://localhost:5001 (PID: $BACKEND_PID)"

# Start frontend
echo "[2/2] Starting frontend..."
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  echo "  Installing npm dependencies..."
  npm install --silent
fi
npm run dev &
FRONTEND_PID=$!
echo "  Frontend running on http://localhost:5173 (PID: $FRONTEND_PID)"

echo ""
echo "Open http://localhost:5173 in your browser"
echo "Press Ctrl+C to stop both servers"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
