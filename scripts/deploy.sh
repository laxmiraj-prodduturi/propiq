#!/usr/bin/env bash
# =============================================================================
# PropIQ — Code Deployment
#
# Syncs local code to the EC2 instance, installs any new dependencies,
# builds the frontend, and restarts services. Run after every code change.
#
# Usage:
#   ./scripts/deploy.sh                    # deploy all three services
#   ./scripts/deploy.sh --frontend-only
#   ./scripts/deploy.sh --backend-only
#   ./scripts/deploy.sh --ai-only
#
# Requires: ./scripts/setup-instance.sh to have been run first.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[deploy]${RESET} $*"; }
success() { echo -e "${GREEN}[ok]${RESET}     $*"; }
die()     { echo -e "${RED}[error]${RESET}  $*" >&2; exit 1; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="$PROJECT_ROOT/scripts/.ec2-state"

[[ -f "$STATE_FILE" ]] || die "No instance state found. Run ./scripts/setup-instance.sh first."
source "$STATE_FILE"

# ── Start instance if stopped ─────────────────────────────────────────────────
STATUS=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" --region "$REGION" \
  --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)

if [[ "$STATUS" != "running" ]]; then
  echo -e "${YELLOW}Instance is '$STATUS'. Starting...${RESET}"
  aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$REGION" >/dev/null
  aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

  PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" --region "$REGION" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
  sed -i.bak "s/^PUBLIC_IP=.*/PUBLIC_IP=$PUBLIC_IP/" "$STATE_FILE"
  source "$STATE_FILE"
  success "Instance started — IP: $PUBLIC_IP"

  info "Waiting for SSH..."
  for i in $(seq 1 20); do
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
      "ubuntu@$PUBLIC_IP" "exit" 2>/dev/null && break
    [[ $i -eq 20 ]] && die "SSH unavailable"
    printf '.'; sleep 5
  done
  echo
fi

SSH="ssh -i $KEY_FILE -o StrictHostKeyChecking=no ubuntu@$PUBLIC_IP"

# ── Parse flags ───────────────────────────────────────────────────────────────
DEPLOY_BACKEND=true
DEPLOY_AI=true
DEPLOY_FRONTEND=true

while [[ $# -gt 0 ]]; do
  case $1 in
    --backend-only)  DEPLOY_AI=false;       DEPLOY_FRONTEND=false; shift ;;
    --ai-only)       DEPLOY_BACKEND=false;  DEPLOY_FRONTEND=false; shift ;;
    --frontend-only) DEPLOY_BACKEND=false;  DEPLOY_AI=false;       shift ;;
    *) die "Unknown flag: $1 (valid: --backend-only | --ai-only | --frontend-only)" ;;
  esac
done

echo -e "\n${BOLD}PropIQ — Deploy${RESET}  →  $PUBLIC_IP\n"

# ── Backend ───────────────────────────────────────────────────────────────────
if $DEPLOY_BACKEND; then
  info "Syncing backend..."
  rsync -az --progress \
    --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
    -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
    "$PROJECT_ROOT/backend/" \
    "ubuntu@$PUBLIC_IP:/home/ubuntu/propiq/backend/"

  $SSH bash -s <<'REMOTE'
    cd /home/ubuntu/propiq/backend
    venv/bin/pip install --quiet -r requirements.txt
REMOTE

  $SSH "sudo systemctl restart propiq-backend"
  success "Backend deployed and restarted"
fi

# ── AI service ────────────────────────────────────────────────────────────────
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
  success "AI service deployed and restarted"
fi

# ── Frontend ──────────────────────────────────────────────────────────────────
if $DEPLOY_FRONTEND; then
  info "Building frontend..."
  (cd "$PROJECT_ROOT/frontend" && npm run build --silent)
  success "Build complete"

  info "Syncing frontend..."
  rsync -az --delete --progress \
    -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
    "$PROJECT_ROOT/frontend/dist/" \
    "ubuntu@$PUBLIC_IP:/home/ubuntu/propiq/frontend/dist/"

  $SSH "sudo cp -r /home/ubuntu/propiq/frontend/dist/* /var/www/propiq/ \
    && sudo chown -R www-data:www-data /var/www/propiq \
    && sudo systemctl reload nginx"
  success "Frontend deployed and Nginx reloaded"
fi

# ── Health check ──────────────────────────────────────────────────────────────
sleep 2
info "Health check..."
$SSH bash -s <<'REMOTE'
  for svc in propiq-backend propiq-ai nginx; do
    if systemctl is-active --quiet "$svc"; then
      echo "  [ok]  $svc"
    else
      echo "  [!!]  $svc is NOT running — sudo journalctl -u $svc -n 20"
    fi
  done
REMOTE

echo
success "Deploy complete  →  http://$PUBLIC_IP"
echo
