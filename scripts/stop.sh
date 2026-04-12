#!/usr/bin/env bash
# =============================================================================
# PropIQ — Stop / Terminate EC2
# Stops the instance (keeps EBS data, ~$1.60/mo storage cost).
# Pass --terminate to destroy everything (no data retained, $0 ongoing cost).
#
# Usage:
#   ./scripts/stop.sh              # stop (can restart later with deploy.sh)
#   ./scripts/stop.sh --terminate  # destroy instance and all data permanently
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[stop]${RESET}   $*"; }
success() { echo -e "${GREEN}[ok]${RESET}     $*"; }
warn()    { echo -e "${YELLOW}[warn]${RESET}   $*"; }
die()     { echo -e "${RED}[error]${RESET}  $*" >&2; exit 1; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="$PROJECT_ROOT/scripts/.ec2-state"

TERMINATE=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --terminate) TERMINATE=true; shift ;;
    *) die "Unknown flag: $1 (valid: --terminate)" ;;
  esac
done

[[ -f "$STATE_FILE" ]] || die "No instance state found at $STATE_FILE"
source "$STATE_FILE"

echo -e "\n${BOLD}PropIQ — Stop Instance${RESET}\n"
echo "  Instance : $INSTANCE_ID"
echo "  IP       : $PUBLIC_IP"
echo "  Region   : $REGION"
echo

if $TERMINATE; then
  echo -e "${RED}${BOLD}WARNING: --terminate will permanently destroy the instance and all data.${RESET}"
  echo -e "  MySQL data, ChromaDB, uploaded documents — all gone."
  echo
  read -rp "  Type the instance ID to confirm ($INSTANCE_ID): " confirm
  [[ "$confirm" == "$INSTANCE_ID" ]] || die "Confirmation did not match. Aborted."

  info "Terminating instance $INSTANCE_ID..."
  aws ec2 terminate-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --output text >/dev/null

  aws ec2 wait instance-terminated \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION"

  # Clean up security group (only if not shared)
  read -rp "  Delete security group '$SG_ID' too? [y/N] " del_sg
  if [[ "${del_sg:-N}" =~ ^[Yy]$ ]]; then
    aws ec2 delete-security-group --group-id "$SG_ID" --region "$REGION" 2>/dev/null \
      && success "Security group deleted" \
      || warn "Could not delete security group (may still have dependencies)"
  fi

  # Clean up key pair
  read -rp "  Delete key pair '$KEY_NAME' from AWS? [y/N] " del_key
  if [[ "${del_key:-N}" =~ ^[Yy]$ ]]; then
    aws ec2 delete-key-pair --key-name "$KEY_NAME" --region "$REGION"
    success "Key pair deleted from AWS (local file $KEY_FILE retained)"
  fi

  rm -f "$STATE_FILE"
  success "Instance terminated. State file removed."
  echo
  echo "  To start fresh: ./scripts/launch.sh"

else
  # ── Graceful stop ────────────────────────────────────────────────────────────
  STATUS=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text)

  if [[ "$STATUS" == "stopped" ]]; then
    warn "Instance is already stopped."
    echo
    echo "  To start it again: ./scripts/deploy.sh"
    echo "  To destroy it:     ./scripts/stop.sh --terminate"
    exit 0
  fi

  if [[ "$STATUS" == "terminated" ]]; then
    warn "Instance has already been terminated."
    rm -f "$STATE_FILE"
    exit 0
  fi

  info "Stopping instance $INSTANCE_ID (data retained on EBS)..."
  aws ec2 stop-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --output text >/dev/null

  aws ec2 wait instance-stopped \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION"

  success "Instance stopped."
  echo
  echo "  EBS volume retained — ongoing cost: ~\$1.60/mo (20GB gp3)"
  echo
  echo "  To restart:  ./scripts/deploy.sh  (auto-starts the instance)"
  echo "  To destroy:  ./scripts/stop.sh --terminate"
  echo
fi
