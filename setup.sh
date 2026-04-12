#!/usr/bin/env bash
# First-time setup: creates venvs and installs all dependencies.
# Run once before starting the services with dev-up.sh.

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Setting up backend venv ==="
cd "$ROOT_DIR/backend"
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q
echo "Backend dependencies installed."

echo ""
echo "=== Setting up AI service venv ==="
cd "$ROOT_DIR/ai_service"
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q
echo "AI service dependencies installed."

echo ""
echo "=== Setting up frontend ==="
cd "$ROOT_DIR/frontend"
npm install --silent
echo "Frontend dependencies installed."

echo ""
echo "Setup complete. Run ./dev-up.sh to start all services."
