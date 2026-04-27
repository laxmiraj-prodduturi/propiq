#!/usr/bin/env bash
# =============================================================================
# PropIQ — Instance Setup
#
# Provisions a fresh EC2 t4g.medium, installs all system dependencies,
# configures MySQL / Redis / Nginx / systemd, and leaves the server ready
# to receive code via deploy.sh.
#
# Run once when you need a new server. After this:
#   1. ./scripts/deploy.sh        — push code and start services
#   2. ./scripts/db-migrate.sh    — apply schema migrations and seed data
#
# Usage:
#   ./scripts/setup-instance.sh               # interactive
#   ./scripts/setup-instance.sh --region us-west-2
#
# Requirements: aws-cli (configured), ssh, rsync
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[setup]${RESET}  $*"; }
success() { echo -e "${GREEN}[ok]${RESET}     $*"; }
warn()    { echo -e "${YELLOW}[warn]${RESET}   $*"; }
die()     { echo -e "${RED}[error]${RESET}  $*" >&2; exit 1; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="$PROJECT_ROOT/scripts/.ec2-state"
REGION="${AWS_REGION:-us-east-1}"
INSTANCE_TYPE="t4g.medium"
KEY_NAME="propiq-key"
SG_NAME="propiq-sg"

while [[ $# -gt 0 ]]; do
  case $1 in
    --region) REGION="$2"; shift 2 ;;
    *) die "Unknown flag: $1" ;;
  esac
done

# ── Pre-flight ────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}PropIQ — Instance Setup${RESET}\n"

command -v aws   >/dev/null || die "aws-cli not found"
command -v ssh   >/dev/null || die "ssh not found"
command -v rsync >/dev/null || die "rsync not found"
aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1 \
  || die "AWS credentials not configured. Run: aws configure"
success "AWS credentials OK (region: $REGION)"

if [[ -f "$STATE_FILE" ]]; then
  source "$STATE_FILE"
  warn "Existing instance found: $INSTANCE_ID ($PUBLIC_IP)"
  read -rp "  Re-use it and skip provisioning? [Y/n] " ans
  if [[ "${ans:-Y}" =~ ^[Yy]$ ]]; then
    info "Skipping EC2 provisioning — running server setup on existing instance..."
    SKIP_PROVISION=true
  else
    SKIP_PROVISION=false
  fi
else
  SKIP_PROVISION=false
fi

# ── Collect secrets ───────────────────────────────────────────────────────────
echo
echo -e "${BOLD}Secrets (written to .env on server — never committed)${RESET}"
echo

read -rsp "  MySQL password     (required, input hidden)        : " DB_PASSWORD
echo
[[ -n "$DB_PASSWORD" ]] || die "MySQL password is required"

read -rp "  JWT secret key     [press Enter to auto-generate] : " JWT_SECRET
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"

read -rp "  OpenAI API key     [press Enter to skip]          : " OPENAI_KEY
OPENAI_KEY="${OPENAI_KEY:-}"
echo

# ── EC2 provisioning ──────────────────────────────────────────────────────────
if [[ "$SKIP_PROVISION" == false ]]; then

  KEY_FILE="$HOME/.ssh/${KEY_NAME}.pem"
  if aws ec2 describe-key-pairs --key-names "$KEY_NAME" --region "$REGION" \
       --query 'KeyPairs[0].KeyName' --output text 2>/dev/null | grep -q "$KEY_NAME"; then
    info "Key pair '$KEY_NAME' already exists"
    [[ -f "$KEY_FILE" ]] || die "Key pair exists in AWS but $KEY_FILE is missing locally. Delete the key pair in AWS and re-run."
  else
    info "Creating SSH key pair '$KEY_NAME'..."
    aws ec2 create-key-pair \
      --key-name "$KEY_NAME" --region "$REGION" \
      --query 'KeyMaterial' --output text > "$KEY_FILE"
    chmod 400 "$KEY_FILE"
    success "Key saved to $KEY_FILE"
  fi

  SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" \
    --region "$REGION" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "None")

  if [[ "$SG_ID" == "None" || -z "$SG_ID" ]]; then
    info "Creating security group '$SG_NAME'..."
    SG_ID=$(aws ec2 create-security-group \
      --group-name "$SG_NAME" \
      --description "PropIQ server" \
      --region "$REGION" \
      --query 'GroupId' --output text)

    MY_IP=$(curl -s https://checkip.amazonaws.com)/32
    info "Detected your IP: $MY_IP — locking SSH and HTTP to it"

    aws ec2 authorize-security-group-ingress \
      --group-id "$SG_ID" --region "$REGION" \
      --protocol tcp --port 22 --cidr "$MY_IP"
    aws ec2 authorize-security-group-ingress \
      --group-id "$SG_ID" --region "$REGION" \
      --protocol tcp --port 80 --cidr "$MY_IP"

    success "Security group created: $SG_ID (locked to $MY_IP)"
  else
    success "Reusing security group: $SG_ID"
  fi

  info "Resolving latest Ubuntu 24.04 ARM AMI..."
  AMI_ID=$(aws ssm get-parameter \
    --name /aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id \
    --region "$REGION" --query 'Parameter.Value' --output text 2>/dev/null) || \
  AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*" \
              "Name=state,Values=available" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --region "$REGION" --output text)
  success "AMI: $AMI_ID"

  info "Launching instance ($INSTANCE_TYPE)..."
  INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3","DeleteOnTermination":false}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=propiq}]" \
    --region "$REGION" \
    --query 'Instances[0].InstanceId' --output text)
  success "Instance launched: $INSTANCE_ID"

  info "Waiting for running state..."
  aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

  PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" --region "$REGION" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
  success "Instance running — IP: $PUBLIC_IP"

  KEY_FILE="$HOME/.ssh/${KEY_NAME}.pem"
  cat > "$STATE_FILE" <<EOF
INSTANCE_ID=$INSTANCE_ID
PUBLIC_IP=$PUBLIC_IP
REGION=$REGION
KEY_FILE=$KEY_FILE
KEY_NAME=$KEY_NAME
SG_ID=$SG_ID
EOF

  info "Waiting for SSH (~60s)..."
  for i in $(seq 1 30); do
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
      "ubuntu@$PUBLIC_IP" "exit" 2>/dev/null && break
    [[ $i -eq 30 ]] && die "SSH never became available"
    printf '.'; sleep 5
  done
  echo
  success "SSH ready"

fi

# ── Load state ────────────────────────────────────────────────────────────────
source "$STATE_FILE"
SSH="ssh -i $KEY_FILE -o StrictHostKeyChecking=no ubuntu@$PUBLIC_IP"

# ── Server configuration (runs on the remote instance) ───────────────────────
info "Configuring server..."

$SSH bash -s -- "$DB_PASSWORD" "$JWT_SECRET" "$OPENAI_KEY" <<'REMOTE'
set -euo pipefail
DB_PASSWORD="$1"
JWT_SECRET="$2"
OPENAI_KEY="$3"
PROJECT_DIR="/home/ubuntu/propiq"
DB_NAME="quantum_quest_properties"
DB_USER="propiq"

log() { echo -e "\n  \033[0;36m[setup]\033[0m $*"; }
ok()  { echo -e "  \033[0;32m[ok]\033[0m    $*"; }

# ── System packages ───────────────────────────────────────────────────────────
log "Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq \
  python3 python3-venv python3-dev python3-pip \
  mysql-server redis-server nginx curl git rsync at \
  build-essential libssl-dev libffi-dev >/dev/null
ok "System packages ready (Python $(python3 --version))"

# ── Node.js 20 ────────────────────────────────────────────────────────────────
if ! node --version 2>/dev/null | grep -q "v20"; then
  log "Installing Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - >/dev/null 2>&1
  sudo apt-get install -y -qq nodejs >/dev/null
fi
ok "Node.js $(node --version)"

# ── MySQL ─────────────────────────────────────────────────────────────────────
log "Configuring MySQL..."
sudo systemctl start mysql && sudo systemctl enable mysql
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
sudo systemctl start redis-server && sudo systemctl enable redis-server
ok "Redis running"

# ── Python virtual environments ───────────────────────────────────────────────
log "Creating Python virtual environments..."
mkdir -p "$PROJECT_DIR/backend" "$PROJECT_DIR/ai_service"
python3 -m venv "$PROJECT_DIR/backend/venv"
python3 -m venv "$PROJECT_DIR/ai_service/venv"
"$PROJECT_DIR/backend/venv/bin/pip" install --quiet --upgrade pip
"$PROJECT_DIR/ai_service/venv/bin/pip" install --quiet --upgrade pip
ok "Python venvs created"

# ── .env files ────────────────────────────────────────────────────────────────
log "Writing .env files..."
cat > "$PROJECT_DIR/backend/.env" <<ENV
DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASSWORD}@localhost/${DB_NAME}
SECRET_KEY=${JWT_SECRET}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
AI_SERVICE_URL=http://localhost:8100
AI_SERVICE_TIMEOUT_SECONDS=60.0
ENV

cat > "$PROJECT_DIR/ai_service/.env" <<ENV
OPENAI_API_KEY=${OPENAI_KEY}
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
DEMO_MODE=${OPENAI_KEY:+false}${OPENAI_KEY:-true}
CHROMA_DB_PATH=${PROJECT_DIR}/ai_service/chroma_db
ENV
ok ".env files written"

# ── Nginx ─────────────────────────────────────────────────────────────────────
log "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/propiq > /dev/null <<'NGINX'
server {
    listen 80;
    server_name _;

    root /var/www/propiq;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    location /ai/ {
        proxy_pass         http://127.0.0.1:8100/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }

    location /ws/ {
        proxy_pass         http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_read_timeout 86400s;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;
}
NGINX
sudo ln -sf /etc/nginx/sites-available/propiq /etc/nginx/sites-enabled/propiq
sudo rm -f /etc/nginx/sites-enabled/default
sudo mkdir -p /var/www/propiq
sudo nginx -t
sudo systemctl enable nginx
ok "Nginx configured"

# ── systemd services ──────────────────────────────────────────────────────────
log "Registering systemd services..."

sudo tee /etc/systemd/system/propiq-backend.service > /dev/null <<SVC
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
SVC

sudo tee /etc/systemd/system/propiq-ai.service > /dev/null <<SVC
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
SVC

# ── Idle auto-shutdown (60 min of no HTTP activity) ───────────────────────────
sudo tee /usr/local/bin/propiq-idle-shutdown.sh > /dev/null <<'IDLE'
#!/usr/bin/env bash
IDLE_MINUTES=60
NGINX_LOG="/var/log/nginx/access.log"
LOG_FILE="/var/log/propiq-idle-shutdown.log"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
[[ -f "$NGINX_LOG" ]] || { log "Nginx log not found — skipping."; exit 0; }
LAST_LINE=$(tail -1 "$NGINX_LOG" 2>/dev/null)
if [[ -n "$LAST_LINE" ]]; then
  TS=$(echo "$LAST_LINE" | grep -oP '\[\K[^\]]+' | head -1)
  [[ -z "$TS" ]] && { log "Could not parse timestamp — skipping."; exit 0; }
  PARSED=$(echo "$TS" | sed 's|/| |g; s|:| |')
  LAST_EPOCH=$(date -d "$PARSED" '+%s' 2>/dev/null || echo 0)
  [[ "$LAST_EPOCH" -eq 0 ]] && { log "Bad timestamp '$TS' — skipping."; exit 0; }
  IDLE=$(( $(date '+%s') - LAST_EPOCH ))
  if [[ $IDLE -lt $(( IDLE_MINUTES * 60 )) ]]; then
    log "Active — last request $((IDLE/60))m ago."; exit 0
  fi
  log "IDLE $((IDLE/60))m — shutting down."
else
  UP=$(awk '{print int($1/60)}' /proc/uptime)
  [[ $UP -lt $IDLE_MINUTES ]] && { log "No requests yet, up ${UP}m."; exit 0; }
  log "No requests in ${UP}m — shutting down."
fi
systemctl stop propiq-backend propiq-ai 2>/dev/null || true
shutdown -h now "PropIQ idle auto-shutdown"
IDLE
sudo chmod +x /usr/local/bin/propiq-idle-shutdown.sh

sudo tee /etc/systemd/system/propiq-idle-shutdown.service > /dev/null <<'SVC'
[Unit]
Description=PropIQ Idle Auto-Shutdown Check
[Service]
Type=oneshot
ExecStart=/usr/local/bin/propiq-idle-shutdown.sh
SVC

sudo tee /etc/systemd/system/propiq-idle-shutdown.timer > /dev/null <<'TMR'
[Unit]
Description=PropIQ Idle Auto-Shutdown Timer
[Timer]
OnBootSec=10min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
TMR

sudo systemctl daemon-reload
sudo systemctl enable propiq-backend propiq-ai propiq-idle-shutdown.timer
ok "systemd services registered (not started — run deploy.sh next)"

REMOTE

success "Server configured"

# ── Done ──────────────────────────────────────────────────────────────────────
echo
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  Instance ready${RESET}   →  $PUBLIC_IP"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo
echo -e "  SSH:  ${YELLOW}ssh -i $KEY_FILE ubuntu@$PUBLIC_IP${RESET}"
echo
echo -e "  Next steps:"
echo -e "    1. ${CYAN}./scripts/deploy.sh${RESET}      — push code and start services"
echo -e "    2. ${CYAN}./scripts/db-migrate.sh${RESET}  — apply schema and seed demo data"
echo
