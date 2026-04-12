#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
AI_SERVICE_DIR="$ROOT_DIR/ai_service"

BACKEND_PID=""
FRONTEND_PID=""
AI_SERVICE_PID=""

cleanup() {
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${AI_SERVICE_PID}" ]] && kill -0 "${AI_SERVICE_PID}" 2>/dev/null; then
    kill "${AI_SERVICE_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "Checking MySQL database..."
mysql -uroot -p'REPLACE_WITH_DB_PASSWORD' --socket=/tmp/mysql.sock -e "CREATE DATABASE IF NOT EXISTS quantum_quest_properties;" >/dev/null

echo "Starting AI service on http://localhost:8100 ..."
(
  cd "$AI_SERVICE_DIR"
  venv/bin/python run.py
) &
AI_SERVICE_PID=$!

sleep 2

echo "Starting backend on http://localhost:8000 ..."
(
  cd "$BACKEND_DIR"
  source venv/bin/activate
  python run.py
) &
BACKEND_PID=$!

sleep 2

echo "Starting frontend on http://localhost:5173 ..."
(
  cd "$FRONTEND_DIR"
  npm run dev -- --host 0.0.0.0
) &
FRONTEND_PID=$!

echo
echo "Apps are starting:"
echo "  AI:       http://localhost:8100"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo
echo "Demo logins:"
echo "  Owner:   alex.thompson@example.com / demo1234"
echo "  Manager: sarah.chen@example.com / demo1234"
echo "  Tenant:  marcus.johnson@example.com / demo1234"
echo
echo "Press Ctrl+C to stop both services."

wait "$AI_SERVICE_PID" "$BACKEND_PID" "$FRONTEND_PID"
