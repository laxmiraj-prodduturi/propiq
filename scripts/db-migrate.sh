#!/usr/bin/env bash
# =============================================================================
# PropIQ — Database Migrations
#
# Runs Alembic migrations and optional demo data seeding on the EC2 instance.
# Run after setup-instance.sh + deploy.sh, or any time the schema changes.
#
# Usage:
#   ./scripts/db-migrate.sh              # apply pending migrations
#   ./scripts/db-migrate.sh --seed       # migrate + load demo seed data
#   ./scripts/db-migrate.sh --status     # show current migration revision
#   ./scripts/db-migrate.sh --rollback   # downgrade one revision
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[db]${RESET}     $*"; }
success() { echo -e "${GREEN}[ok]${RESET}     $*"; }
warn()    { echo -e "${YELLOW}[warn]${RESET}   $*"; }
die()     { echo -e "${RED}[error]${RESET}  $*" >&2; exit 1; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="$PROJECT_ROOT/scripts/.ec2-state"

[[ -f "$STATE_FILE" ]] || die "No instance state found. Run ./scripts/setup-instance.sh first."
source "$STATE_FILE"

# ── Check instance is running ─────────────────────────────────────────────────
STATUS=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" --region "$REGION" \
  --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)

[[ "$STATUS" == "running" ]] || die "Instance is '$STATUS'. Start it with ./scripts/deploy.sh first."

SSH="ssh -i $KEY_FILE -o StrictHostKeyChecking=no ubuntu@$PUBLIC_IP"

# ── Parse flags ───────────────────────────────────────────────────────────────
DO_MIGRATE=true
DO_SEED=false
DO_STATUS=false
DO_ROLLBACK=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --seed)     DO_SEED=true;     shift ;;
    --status)   DO_STATUS=true;   DO_MIGRATE=false; shift ;;
    --rollback) DO_ROLLBACK=true; DO_MIGRATE=false; shift ;;
    *) die "Unknown flag: $1 (valid: --seed | --status | --rollback)" ;;
  esac
done

echo -e "\n${BOLD}PropIQ — Database Migrations${RESET}  →  $PUBLIC_IP\n"

# ── Status ────────────────────────────────────────────────────────────────────
if $DO_STATUS; then
  info "Current migration revision:"
  $SSH bash -s <<'REMOTE'
    cd /home/ubuntu/propiq/backend
    echo
    venv/bin/alembic current 2>&1
    echo
    echo "Migration history:"
    venv/bin/alembic history --verbose 2>&1 | head -40
REMOTE
  exit 0
fi

# ── Rollback ──────────────────────────────────────────────────────────────────
if $DO_ROLLBACK; then
  warn "Rolling back one migration revision..."
  read -rp "  Confirm rollback? This may cause data loss. [y/N] " ans
  [[ "${ans:-N}" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
  $SSH bash -s <<'REMOTE'
    cd /home/ubuntu/propiq/backend
    echo "Before:"
    venv/bin/alembic current
    venv/bin/alembic downgrade -1
    echo "After:"
    venv/bin/alembic current
REMOTE
  success "Rollback complete"
  exit 0
fi

# ── Migrate ───────────────────────────────────────────────────────────────────
if $DO_MIGRATE; then
  info "Running Alembic migrations (upgrade head)..."
  $SSH bash -s <<'REMOTE'
    set -euo pipefail
    cd /home/ubuntu/propiq/backend
    echo "  Current revision:"
    venv/bin/alembic current 2>&1
    echo
    echo "  Applying pending migrations..."
    venv/bin/alembic upgrade head 2>&1
    echo
    echo "  Final revision:"
    venv/bin/alembic current 2>&1
REMOTE
  success "Migrations applied"
fi

# ── Seed ──────────────────────────────────────────────────────────────────────
if $DO_SEED; then
  info "Seeding demo data..."
  $SSH bash -s <<'REMOTE'
    set -euo pipefail
    cd /home/ubuntu/propiq/backend
    source .env 2>/dev/null || true

    # Parse DB credentials from DATABASE_URL
    # Format: mysql+pymysql://user:password@host/dbname
    DB_USER=$(echo "$DATABASE_URL" | sed 's|.*://||; s|:.*||')
    DB_PASS=$(echo "$DATABASE_URL" | sed 's|.*://[^:]*:||; s|@.*||')
    DB_NAME=$(echo "$DATABASE_URL" | sed 's|.*/||')

    if [[ -f "master_seed.sql" ]]; then
      mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" < master_seed.sql
      echo "  Seed data loaded from master_seed.sql"
    else
      echo "  [warn] master_seed.sql not found — using SQLAlchemy seed instead"
      venv/bin/python - <<'PYEOF'
import sys
sys.path.insert(0, ".")
from app.database import SessionLocal
from app.seed import seed_db
db = SessionLocal()
try:
    seed_db(db)
    print("  Demo data seeded via seed_db()")
finally:
    db.close()
PYEOF
    fi
REMOTE
  success "Seed data loaded"
fi

echo
success "Database operations complete"
echo
