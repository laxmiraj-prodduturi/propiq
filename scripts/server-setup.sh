#!/usr/bin/env bash
# =============================================================================
# PropIQ — Server Setup Script
# Runs on the EC2 instance. Installs all dependencies, configures MySQL,
# builds the frontend, and registers systemd services.
#
# Called by launch.sh via SSH. Not intended to be run directly.
# Env vars injected by launch.sh: DB_PASSWORD, JWT_SECRET, OPENAI_KEY
# =============================================================================

set -euo pipefail

PROJECT_DIR="/home/ubuntu/propiq"
DB_NAME="quantum_quest_properties"
DB_USER="propiq"
DB_PASSWORD="${DB_PASSWORD:-PropIQ2024!}"
JWT_SECRET="${JWT_SECRET:-changeme}"
OPENAI_KEY="${OPENAI_KEY:-}"

log() { echo -e "\n\033[0;36m[setup]\033[0m $*"; }
ok()  { echo -e "\033[0;32m[ok]\033[0m    $*"; }

# ── System packages ───────────────────────────────────────────────────────────
log "Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq \
  python3 python3-venv python3-dev python3-pip \
  mysql-server \
  redis-server \
  nginx \
  curl git rsync \
  at \
  build-essential libssl-dev libffi-dev \
  >/dev/null
ok "System packages installed (Python $(python3 --version))"

# ── Node.js 20 ────────────────────────────────────────────────────────────────
log "Installing Node.js 20..."
if ! node --version 2>/dev/null | grep -q "v20"; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - >/dev/null 2>&1
  sudo apt-get install -y -qq nodejs >/dev/null
fi
ok "Node.js $(node --version)"

# ── MySQL ─────────────────────────────────────────────────────────────────────
log "Configuring MySQL..."
sudo systemctl start mysql
sudo systemctl enable mysql

# Set root password and create app database + user
sudo mysql --user=root <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL
ok "MySQL configured (db: $DB_NAME, user: $DB_USER)"

# ── Redis ─────────────────────────────────────────────────────────────────────
log "Starting Redis..."
sudo systemctl start redis-server
sudo systemctl enable redis-server
ok "Redis running"

# ── Backend ───────────────────────────────────────────────────────────────────
log "Setting up FastAPI backend..."
cd "$PROJECT_DIR/backend"

python3 -m venv venv
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r requirements.txt

# Write .env
cat > .env <<EOF
DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASSWORD}@localhost/${DB_NAME}
SECRET_KEY=${JWT_SECRET}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
AI_SERVICE_URL=http://localhost:8100
AI_SERVICE_TIMEOUT_SECONDS=8.0
EOF

# Step 1: create_all() to build the base schema (migration 0001 is a no-op baseline)
log "Creating base schema via SQLAlchemy create_all..."
venv/bin/python - <<'PYEOF'
import sys
sys.path.insert(0, ".")
from app.database import engine, Base
from app import models  # registers all ORM models
Base.metadata.create_all(bind=engine)
print("  Base tables created")
PYEOF

# Step 2: create_all already applied the full schema, so stamp head directly.
# (0001 is a no-op baseline; 0002-0004 add tables that create_all already created.)
log "Stamping Alembic at head (schema already created by create_all)..."
venv/bin/alembic stamp head

# Seed demo data
log "Seeding demo data..."
if [[ -f "master_seed.sql" ]]; then
  mysql -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < master_seed.sql
  ok "Demo data seeded"
fi

ok "Backend ready"

# ── AI Service ────────────────────────────────────────────────────────────────
log "Setting up AI service..."
cd "$PROJECT_DIR/ai_service"

python3 -m venv venv
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r requirements.txt

cat > .env <<EOF
OPENAI_API_KEY=${OPENAI_KEY}
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
DEMO_MODE=${OPENAI_KEY:+false}${OPENAI_KEY:-true}
CHROMA_DB_PATH=${PROJECT_DIR}/ai_service/chroma_db
EOF

ok "AI service ready"

# ── Frontend ──────────────────────────────────────────────────────────────────
log "Building React frontend..."
cd "$PROJECT_DIR/frontend"
npm install --silent
npm run build

# Copy built files to web root
sudo mkdir -p /var/www/propiq
sudo cp -r dist/* /var/www/propiq/
sudo chown -R www-data:www-data /var/www/propiq
ok "Frontend built and deployed to /var/www/propiq"

# ── Nginx ─────────────────────────────────────────────────────────────────────
log "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/propiq > /dev/null <<'NGINX'
server {
    listen 80;
    server_name _;

    # Frontend — React SPA
    root /var/www/propiq;
    index index.html;

    # SPA fallback: all unmatched routes serve index.html (React Router handles it)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # AI Service
    location /ai/ {
        proxy_pass         http://127.0.0.1:8100/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # WebSocket support (Socket.IO / SSE)
    location /ws/ {
        proxy_pass         http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host       $host;
        proxy_read_timeout 86400s;
    }

    # Document downloads — increase timeout for large files
    location /api/documents/ {
        proxy_pass         http://127.0.0.1:8000/documents/;
        proxy_read_timeout 60s;
        client_max_body_size 50M;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;
}
NGINX

sudo ln -sf /etc/nginx/sites-available/propiq /etc/nginx/sites-enabled/propiq
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
ok "Nginx configured"

# ── Systemd: Backend ──────────────────────────────────────────────────────────
log "Registering systemd services..."

sudo tee /etc/systemd/system/propiq-backend.service > /dev/null <<EOF
[Unit]
Description=PropIQ FastAPI Backend
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=${PROJECT_DIR}/backend
ExecStart=${PROJECT_DIR}/backend/venv/bin/python run.py
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# ── Systemd: AI Service ───────────────────────────────────────────────────────
sudo tee /etc/systemd/system/propiq-ai.service > /dev/null <<EOF
[Unit]
Description=PropIQ AI Agent Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=${PROJECT_DIR}/ai_service
ExecStart=${PROJECT_DIR}/ai_service/venv/bin/python run.py
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# ── Systemd: Celery Worker ────────────────────────────────────────────────────
# Only register if backend has Celery configured
if grep -r "celery" "$PROJECT_DIR/backend/requirements.txt" >/dev/null 2>&1; then
sudo tee /etc/systemd/system/propiq-celery.service > /dev/null <<EOF
[Unit]
Description=PropIQ Celery Worker
After=network.target redis.service mysql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=${PROJECT_DIR}/backend
ExecStart=${PROJECT_DIR}/backend/venv/bin/celery -A app.celery worker --loglevel=info
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
fi

# ── Idle auto-shutdown (shuts down if no HTTP activity for 60 min) ────────────
log "Installing idle auto-shutdown timer..."
sudo tee /usr/local/bin/propiq-idle-shutdown.sh > /dev/null <<'IDLE_SCRIPT'
#!/usr/bin/env bash
IDLE_MINUTES=60
LOG_FILE="/var/log/propiq-idle-shutdown.log"
NGINX_LOG="/var/log/nginx/access.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }

if [[ -f "$NGINX_LOG" ]]; then
  LAST_LINE=$(tail -1 "$NGINX_LOG" 2>/dev/null)
  if [[ -n "$LAST_LINE" ]]; then
    TS=$(echo "$LAST_LINE" | grep -oP '\[\K[^\]]+' | head -1)
    if [[ -z "$TS" ]]; then
      log "Could not parse nginx log timestamp — skipping shutdown."; exit 0
    fi
    # Convert nginx format "21/Apr/2026:19:30:00 +0000" to GNU date-parseable
    # "21 Apr 2026 19:30:00 +0000" by replacing / with space and first : with space
    PARSED_TS=$(echo "$TS" | sed 's|/| |g; s|:| |')
    LAST_EPOCH=$(date -d "$PARSED_TS" '+%s' 2>/dev/null)
    if [[ -z "$LAST_EPOCH" || "$LAST_EPOCH" -eq 0 ]]; then
      log "Could not convert nginx timestamp '$TS' — skipping shutdown."; exit 0
    fi
    NOW_EPOCH=$(date '+%s')
    IDLE_SECONDS=$(( NOW_EPOCH - LAST_EPOCH ))
    IDLE_MINS=$(( IDLE_SECONDS / 60 ))
    if [[ $IDLE_SECONDS -lt $(( IDLE_MINUTES * 60 )) ]]; then
      log "Active — last request ${IDLE_MINS}m ago. No shutdown."
      exit 0
    fi
    log "IDLE for ${IDLE_MINS}m (threshold: ${IDLE_MINUTES}m). Shutting down."
  else
    # Use /proc/uptime (seconds since boot) to avoid unit mismatch with
    # ActiveEnterTimestampMonotonic (microseconds) vs date +%s (Unix epoch)
    UPTIME_SECS=$(awk '{print int($1)}' /proc/uptime)
    UP_MINS=$(( UPTIME_SECS / 60 ))
    if [[ $UP_MINS -lt $IDLE_MINUTES ]]; then
      log "No requests yet — nginx up ${UP_MINS}m. Waiting."; exit 0
    fi
    log "No requests in ${UP_MINS}m since startup. Shutting down."
  fi
else
  log "Nginx log not found — skipping."; exit 0
fi

systemctl stop propiq-backend propiq-ai 2>/dev/null || true
log "Shutting down instance."
shutdown -h now "PropIQ idle auto-shutdown (no activity for ${IDLE_MINUTES}m)"
IDLE_SCRIPT

sudo chmod +x /usr/local/bin/propiq-idle-shutdown.sh

sudo tee /etc/systemd/system/propiq-idle-shutdown.service > /dev/null <<'SVC'
[Unit]
Description=PropIQ Idle Auto-Shutdown Check
After=network.target nginx.service
[Service]
Type=oneshot
ExecStart=/usr/local/bin/propiq-idle-shutdown.sh
StandardOutput=journal
StandardError=journal
SVC

sudo tee /etc/systemd/system/propiq-idle-shutdown.timer > /dev/null <<'TMR'
[Unit]
Description=PropIQ Idle Auto-Shutdown — check every 5 minutes
Requires=propiq-idle-shutdown.service
[Timer]
OnBootSec=10min
OnUnitActiveSec=5min
AccuracySec=1min
[Install]
WantedBy=timers.target
TMR

# ── Enable and start ──────────────────────────────────────────────────────────
sudo systemctl daemon-reload
sudo systemctl enable propiq-backend propiq-ai propiq-idle-shutdown.timer
sudo systemctl start  propiq-backend propiq-ai propiq-idle-shutdown.timer

if [[ -f /etc/systemd/system/propiq-celery.service ]]; then
  sudo systemctl enable propiq-celery
  sudo systemctl start  propiq-celery
fi

ok "All services started"
ok "Idle auto-shutdown timer active (shuts down after 60min of no HTTP activity)"

# ── Verify services are running ───────────────────────────────────────────────
sleep 3
log "Service health check..."

check_service() {
  local name=$1
  if sudo systemctl is-active --quiet "$name"; then
    ok "$name is running"
  else
    echo "[warn] $name failed to start — check: sudo journalctl -u $name -n 50"
  fi
}

check_service propiq-backend
check_service propiq-ai
check_service nginx
check_service mysql
check_service redis-server

# Quick HTTP check
sleep 2
if curl -sf http://localhost/api/health >/dev/null 2>&1 || \
   curl -sf http://localhost:8000/health >/dev/null 2>&1; then
  ok "Backend HTTP responding"
else
  echo "[warn] Backend HTTP not yet responding (may still be starting up)"
fi

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Server setup complete"
echo "  Logs: sudo journalctl -u propiq-backend -f"
echo "        sudo journalctl -u propiq-ai -f"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
