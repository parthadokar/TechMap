#!/usr/bin/env bash
# Start backend + frontend in parallel
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Starting FastAPI backend on :8000"
cd "$ROOT/backend"
pip install -r requirements.txt -q
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

echo "==> Installing frontend deps"
cd "$ROOT/frontend"
npm install --silent

echo "==> Starting SvelteKit dev server on :5173"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "TechMap is running:"
echo "  Frontend → http://localhost:5173"
echo "  Backend  → http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
