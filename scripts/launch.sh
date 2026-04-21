#!/usr/bin/env bash
# =============================================================================
# PropIQ — EC2 Spot Launch & Deploy Script
# Provisions a t4g.medium Spot instance, uploads the project, and runs setup.
#
# Usage:
#   ./scripts/launch.sh                    # interactive (prompts for secrets)
#   ./scripts/launch.sh --region us-west-2 # override region
#
# Requirements: aws-cli (configured), ssh, rsync
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[info]${RESET}  $*"; }
success() { echo -e "${GREEN}[ok]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[warn]${RESET}  $*"; }
die()     { echo -e "${RED}[error]${RESET} $*" >&2; exit 1; }

# ── Defaults (override with env vars or flags) ────────────────────────────────
REGION="${AWS_REGION:-us-east-1}"
INSTANCE_TYPE="t4g.medium"         # 2 vCPU, 4 GB RAM, ARM
KEY_NAME="propiq-key"
SG_NAME="propiq-sg"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="$PROJECT_ROOT/scripts/.ec2-state"

# Parse flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --region) REGION="$2"; shift 2 ;;
    *) die "Unknown flag: $1" ;;
  esac
done

# ── Pre-flight checks ─────────────────────────────────────────────────────────
echo -e "\n${BOLD}PropIQ — EC2 Launch${RESET}\n"

command -v aws   >/dev/null || die "aws-cli not found. Install: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
command -v ssh   >/dev/null || die "ssh not found"
command -v rsync >/dev/null || die "rsync not found"
aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1 \
  || die "AWS credentials not configured. Run: aws configure"

success "AWS credentials OK (region: $REGION)"

# Warn if an instance already exists
if [[ -f "$STATE_FILE" ]]; then
  source "$STATE_FILE"
  warn "Existing instance found: $INSTANCE_ID ($PUBLIC_IP)"
  read -rp "  Re-use it and just redeploy? [Y/n] " ans
  if [[ "${ans:-Y}" =~ ^[Yy]$ ]]; then
    info "Running deploy only..."
    exec "$PROJECT_ROOT/scripts/deploy.sh"
  fi
fi

# ── Collect secrets ───────────────────────────────────────────────────────────
echo
echo -e "${BOLD}Configuration${RESET}"
echo "  These are written to .env files on the server — never committed to git."
echo

read -rp  "  MySQL root password  [default: PropIQ2024!]         : " DB_PASSWORD
DB_PASSWORD="${DB_PASSWORD:-PropIQ2024!}"

read -rp  "  JWT secret key       [press Enter to auto-generate] : " JWT_SECRET
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"

read -rp  "  OpenAI API key       [press Enter to skip]          : " OPENAI_KEY
OPENAI_KEY="${OPENAI_KEY:-}"

echo

# ── SSH key pair ──────────────────────────────────────────────────────────────
KEY_FILE="$HOME/.ssh/${KEY_NAME}.pem"

if aws ec2 describe-key-pairs --key-names "$KEY_NAME" --region "$REGION" \
     --query 'KeyPairs[0].KeyName' --output text 2>/dev/null | grep -q "$KEY_NAME"; then
  info "Key pair '$KEY_NAME' already exists"
  [[ -f "$KEY_FILE" ]] || die "Key pair exists in AWS but $KEY_FILE is missing locally. Delete the key pair in AWS and re-run."
else
  info "Creating key pair '$KEY_NAME'..."
  aws ec2 create-key-pair \
    --key-name "$KEY_NAME" \
    --region "$REGION" \
    --query 'KeyMaterial' \
    --output text > "$KEY_FILE"
  chmod 400 "$KEY_FILE"
  success "Key saved to $KEY_FILE"
fi

# ── Security group ────────────────────────────────────────────────────────────
SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=$SG_NAME" \
  --region "$REGION" \
  --query 'SecurityGroups[0].GroupId' \
  --output text 2>/dev/null || echo "None")

if [[ "$SG_ID" == "None" || -z "$SG_ID" ]]; then
  info "Creating security group '$SG_NAME'..."
  SG_ID=$(aws ec2 create-security-group \
    --group-name "$SG_NAME" \
    --description "PropIQ internal instance" \
    --region "$REGION" \
    --query 'GroupId' \
    --output text)

  MY_IP=$(curl -s https://checkip.amazonaws.com)/32
  info "Detected your IP: $MY_IP — restricting SSH and HTTP to it only"

  # SSH only from your current IP
  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" --region "$REGION" \
    --protocol tcp --port 22 --cidr "$MY_IP"

  # HTTP (Nginx) only from your current IP
  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" --region "$REGION" \
    --protocol tcp --port 80 --cidr "$MY_IP"

  success "Security group created: $SG_ID (locked to $MY_IP)"
else
  success "Security group '$SG_NAME' already exists: $SG_ID"
fi

# ── Find latest Ubuntu 24.04 ARM AMI ─────────────────────────────────────────
info "Resolving latest Ubuntu 24.04 LTS ARM AMI..."
AMI_ID=$(aws ssm get-parameter \
  --name /aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id \
  --region "$REGION" \
  --query 'Parameter.Value' \
  --output text 2>/dev/null) || \
AMI_ID=$(aws ec2 describe-images \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*" \
            "Name=state,Values=available" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --region "$REGION" \
  --output text)
success "AMI: $AMI_ID"

# ── Launch Spot instance ──────────────────────────────────────────────────────
info "Requesting On-Demand instance ($INSTANCE_TYPE)..."

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --key-name "$KEY_NAME" \
  --security-group-ids "$SG_ID" \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3","DeleteOnTermination":false}}]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=propiq},{Key=Project,Value=propiq}]" \
  --region "$REGION" \
  --query 'Instances[0].InstanceId' \
  --output text)

success "Instance launched: $INSTANCE_ID"

# ── Wait for running state ────────────────────────────────────────────────────
info "Waiting for instance to enter 'running' state..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --region "$REGION" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

success "Instance running — Public IP: $PUBLIC_IP"

# Save state for stop.sh and deploy.sh
cat > "$STATE_FILE" <<EOF
INSTANCE_ID=$INSTANCE_ID
PUBLIC_IP=$PUBLIC_IP
REGION=$REGION
KEY_FILE=$KEY_FILE
KEY_NAME=$KEY_NAME
SG_ID=$SG_ID
EOF

# ── Wait for SSH ──────────────────────────────────────────────────────────────
info "Waiting for SSH to become available (this takes ~60s)..."
for i in $(seq 1 30); do
  ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "ubuntu@$PUBLIC_IP" "exit" 2>/dev/null && break
  [[ $i -eq 30 ]] && die "SSH never became available"
  printf '.'
  sleep 5
done
echo
success "SSH is ready"

# ── Set up auto-stop cron (EventBridge rule) ──────────────────────────────────
info "Setting up auto-stop after 5 hours via EventBridge..."

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create Lambda-less auto-stop using EC2 instance scheduled shutdown via SSM
aws ec2 create-tags \
  --resources "$INSTANCE_ID" \
  --tags "Key=AutoStop,Value=true" \
  --region "$REGION" 2>/dev/null || true

# Schedule auto-stop via SSM Run Command (runs in 5 hours)
# Clear any stale at jobs first — leftover jobs from a previous run fire immediately on reboot
aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[\"atq | awk '{print \$1}' | xargs -r atrm\", \"echo 'sudo shutdown -h now' | at now + 5 hours\"]" \
  --region "$REGION" \
  --output text >/dev/null 2>/dev/null || warn "SSM auto-stop scheduling skipped (SSM agent may not be ready yet; set manually if needed)"

# ── Upload project files ──────────────────────────────────────────────────────
info "Uploading project files (excluding node_modules, venv, __pycache__)..."
rsync -az --progress \
  --exclude='node_modules' \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='dist' \
  --exclude='chroma_db' \
  --exclude='*.pem' \
  --exclude='scripts/.ec2-state' \
  -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
  "$PROJECT_ROOT/" \
  "ubuntu@$PUBLIC_IP:/home/ubuntu/propiq/"

success "Files uploaded"

# ── Upload and run server setup ───────────────────────────────────────────────
info "Uploading server setup script..."
scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
  "$PROJECT_ROOT/scripts/server-setup.sh" \
  "ubuntu@$PUBLIC_IP:/home/ubuntu/server-setup.sh"

ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "ubuntu@$PUBLIC_IP" \
  "chmod +x /home/ubuntu/server-setup.sh"

info "Running server setup (takes ~5 min)..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "ubuntu@$PUBLIC_IP" \
  "DB_PASSWORD='$DB_PASSWORD' JWT_SECRET='$JWT_SECRET' OPENAI_KEY='$OPENAI_KEY' \
   bash /home/ubuntu/server-setup.sh 2>&1 | tee /home/ubuntu/setup.log"

# ── Done ──────────────────────────────────────────────────────────────────────
echo
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  PropIQ is live!${RESET}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo
echo -e "  App:        ${CYAN}http://$PUBLIC_IP${RESET}"
echo -e "  API:        ${CYAN}http://$PUBLIC_IP/api${RESET}"
echo -e "  AI Service: ${CYAN}http://$PUBLIC_IP/ai${RESET}"
echo
echo -e "  SSH:        ${YELLOW}ssh -i $KEY_FILE ubuntu@$PUBLIC_IP${RESET}"
echo
echo -e "  Demo logins:"
echo -e "    Owner:   alex.thompson@example.com / demo1234"
echo -e "    Manager: sarah.chen@example.com / demo1234"
echo -e "    Tenant:  marcus.johnson@example.com / demo1234"
echo
echo -e "  Auto-stops in 5 hours. To stop now:"
echo -e "    ${YELLOW}./scripts/stop.sh${RESET}"
echo -e "  To redeploy code changes:"
echo -e "    ${YELLOW}./scripts/deploy.sh${RESET}"
echo
