#!/usr/bin/env bash
# =============================================================================
# PropIQ — Redeploy Script
# Syncs local code changes to the running EC2 instance and restarts services.
# Runs in ~30 seconds. Use this after every code change.
#
# Usage: ./scripts/deploy.sh [--frontend-only | --backend-only | --ai-only]
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[deploy]${RESET} $*"; }
success() { echo -e "${GREEN}[ok]${RESET}     $*"; }
die()     { echo -e "${RED}[error]${RESET}  $*" >&2; exit 1; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="$PROJECT_ROOT/scripts/.ec2-state"

[[ -f "$STATE_FILE" ]] || die "No instance state found. Run ./scripts/launch.sh first."
source "$STATE_FILE"

# Verify instance is running
STATUS=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --region "$REGION" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text 2>/dev/null)

if [[ "$STATUS" != "running" ]]; then
  echo -e "${YELLOW}Instance is '$STATUS'. Starting it...${RESET}"
  aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$REGION" >/dev/null
  aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

  # IP may change on restart (Elastic IP not assigned)
  PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

  # Update state file with new IP
  sed -i.bak "s/^PUBLIC_IP=.*/PUBLIC_IP=$PUBLIC_IP/" "$STATE_FILE"
  success "Instance started — new IP: $PUBLIC_IP"

  # Wait for SSH
  info "Waiting for SSH..."
  for i in $(seq 1 20); do
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
      "ubuntu@$PUBLIC_IP" "exit" 2>/dev/null && break
    [[ $i -eq 20 ]] && die "SSH unavailable after instance start"
    printf '.'
    sleep 5
  done
  echo
fi

SSH="ssh -i $KEY_FILE -o StrictHostKeyChecking=no ubuntu@$PUBLIC_IP"
RSYNC_BASE="rsync -az --progress -e 'ssh -i $KEY_FILE -o StrictHostKeyChecking=no'"

# Parse flags
DEPLOY_FRONTEND=true
DEPLOY_BACKEND=true
DEPLOY_AI=true

while [[ $# -gt 0 ]]; do
  case $1 in
    --frontend-only) DEPLOY_BACKEND=false; DEPLOY_AI=false; shift ;;
    --backend-only)  DEPLOY_FRONTEND=false; DEPLOY_AI=false; shift ;;
    --ai-only)       DEPLOY_FRONTEND=false; DEPLOY_BACKEND=false; shift ;;
    *) die "Unknown flag: $1 (valid: --frontend-only | --backend-only | --ai-only)" ;;
  esac
done

echo -e "\n${BOLD}PropIQ — Deploy${RESET}  →  $PUBLIC_IP\n"

# ── Sync backend ──────────────────────────────────────────────────────────────
if $DEPLOY_BACKEND; then
  info "Syncing backend..."
  rsync -az --progress \
    --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.env' --exclude='alembic/versions/__pycache__' \
    -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
    "$PROJECT_ROOT/backend/" \
    "ubuntu@$PUBLIC_IP:/home/ubuntu/propiq/backend/"

  # Install any new packages and run migrations
  $SSH bash -s <<'REMOTE'
    cd /home/ubuntu/propiq/backend
    venv/bin/pip install --quiet -r requirements.txt
    venv/bin/alembic upgrade head
REMOTE

  $SSH "sudo systemctl restart propiq-backend"
  success "Backend restarted"
fi

# ── Sync AI service ───────────────────────────────────────────────────────────
if $DEPLOY_AI; then
  info "Syncing AI service..."
  rsync -az --progress \
    --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.env' --exclude='chroma_db' \
    -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
    "$PROJECT_ROOT/ai_service/" \
    "ubuntu@$PUBLIC_IP:/home/ubuntu/propiq/ai_service/"

  $SSH bash -s <<'REMOTE'
    cd /home/ubuntu/propiq/ai_service
    venv/bin/pip install --quiet -r requirements.txt
REMOTE

  $SSH "sudo systemctl restart propiq-ai"
  success "AI service restarted"
fi

# ── Build and sync frontend ───────────────────────────────────────────────────
if $DEPLOY_FRONTEND; then
  info "Building frontend locally..."
  (cd "$PROJECT_ROOT/frontend" && npm run build --silent)
  success "Build complete"

  info "Syncing frontend dist..."
  rsync -az --delete --progress \
    -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
    "$PROJECT_ROOT/frontend/dist/" \
    "ubuntu@$PUBLIC_IP:/home/ubuntu/propiq/frontend/dist/"

  $SSH "sudo cp -r /home/ubuntu/propiq/frontend/dist/* /var/www/propiq/ && sudo chown -R www-data:www-data /var/www/propiq"
  $SSH "sudo systemctl reload nginx"
  success "Frontend deployed and Nginx reloaded"
fi

# ── Health check ──────────────────────────────────────────────────────────────
sleep 2
info "Checking service health..."
$SSH bash -s <<'REMOTE'
  for svc in propiq-backend propiq-ai nginx; do
    if systemctl is-active --quiet "$svc"; then
      echo "[ok]  $svc"
    else
      echo "[!!]  $svc is NOT running — check: sudo journalctl -u $svc -n 20"
    fi
  done
REMOTE

echo
success "Deploy complete → http://$PUBLIC_IP"
echo
