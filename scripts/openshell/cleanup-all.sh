#!/usr/bin/env bash
# ============================================================================
# OPENSHELL FULL CLEANUP
# ============================================================================
# Convenience wrapper that removes ALL OpenShell resources:
#   1. Discovers all tenants (by Helm releases or namespace labels)
#   2. Calls cleanup-tenant.sh for each tenant
#   3. Calls cleanup-shared.sh to remove shared infrastructure
#
# Usage:
#   scripts/openshell/cleanup-all.sh
#   scripts/openshell/cleanup-all.sh --delete-namespaces
#   scripts/openshell/cleanup-all.sh --dry-run
#   scripts/openshell/cleanup-all.sh --help
#
# Idempotent: safe to re-run if resources are already gone.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Defaults ────────────────────────────────────────────────────────────────
DRY_RUN=false
DELETE_NAMESPACES=false
KEYCLOAK_NS="${KEYCLOAK_NS:-keycloak}"
BACKEND_NS="${BACKEND_NS:-team1}"
EXTRA_SHARED_ARGS=()

# ── Colors & logging ────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}→${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warn()    { echo -e "${YELLOW}⚠${NC} $1"; }
log_error()   { echo -e "${RED}✗${NC} $1"; }

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Remove ALL OpenShell resources (tenants + shared infrastructure).

Options:
  --help               Show this help message
  --dry-run            Print commands without executing
  --delete-namespaces  Also delete tenant namespaces (DESTRUCTIVE)
  --keycloak-ns NS     Keycloak namespace (default: keycloak)
  --backend-ns NS      Backend namespace (default: team1)
  --skip-sandbox       Pass through to cleanup-shared.sh
  --skip-gateway-api   Pass through to cleanup-shared.sh
  --skip-tls           Pass through to cleanup-shared.sh
  --skip-keycloak      Pass through to cleanup-shared.sh
  --skip-litellm       Pass through to cleanup-shared.sh
  --skip-backend       Pass through to cleanup-shared.sh
  --skip-istio         Pass through to cleanup-shared.sh
EOF
  exit 0
}

# ── Argument parsing ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help)              usage ;;
    --dry-run)           DRY_RUN=true; shift ;;
    --delete-namespaces) DELETE_NAMESPACES=true; shift ;;
    --keycloak-ns)       KEYCLOAK_NS="$2"; shift 2 ;;
    --backend-ns)        BACKEND_NS="$2"; shift 2 ;;
    --skip-sandbox|--skip-gateway-api|--skip-tls|--skip-keycloak|--skip-litellm|--skip-backend|--skip-istio)
      EXTRA_SHARED_ARGS+=("$1"); shift ;;
    *)
      log_error "Unknown option: $1"
      usage
      ;;
  esac
done

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  OpenShell Full Cleanup                                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "  Delete namespaces: $DELETE_NAMESPACES"
echo "  Dry run:           $DRY_RUN"
echo ""

# ============================================================================
# Step 1: Discover tenants
# ============================================================================
log_info "Step 1: Discovering OpenShell tenants..."

TENANTS=()

# Method 1: Find Helm releases with openshell- prefix
HELM_TENANTS=$(helm list --all-namespaces --filter '^openshell-' -q 2>/dev/null | sed 's/^openshell-//' || true)
for t in $HELM_TENANTS; do
  TENANTS+=("$t")
done

# Method 2: Find namespaces with openshell.ai/tenant label
LABELED_TENANTS=$(kubectl get namespaces -l "openshell.ai/tenant" -o jsonpath='{.items[*].metadata.labels.openshell\.ai/tenant}' 2>/dev/null || true)
for t in $LABELED_TENANTS; do
  # Avoid duplicates
  if [[ ! " ${TENANTS[*]:-} " =~ " $t " ]]; then
    TENANTS+=("$t")
  fi
done

if [[ ${#TENANTS[@]} -eq 0 ]]; then
  log_warn "No OpenShell tenants found"
else
  log_info "Found tenants: ${TENANTS[*]}"
fi

# ============================================================================
# Step 2: Clean up each tenant
# ============================================================================
log_info "Step 2: Cleaning up tenants..."

TENANT_ARGS=()
if $DRY_RUN; then TENANT_ARGS+=(--dry-run); fi
if $DELETE_NAMESPACES; then TENANT_ARGS+=(--delete-namespace); fi

for tenant in "${TENANTS[@]}"; do
  log_info "── Cleaning tenant: $tenant ──"
  "$SCRIPT_DIR/cleanup-tenant.sh" "$tenant" "${TENANT_ARGS[@]}"
  echo ""
done

# ============================================================================
# Step 3: Clean up shared infrastructure
# ============================================================================
log_info "Step 3: Cleaning up shared infrastructure..."

SHARED_ARGS=(--keycloak-ns "$KEYCLOAK_NS" --backend-ns "$BACKEND_NS")
if $DRY_RUN; then SHARED_ARGS+=(--dry-run); fi
SHARED_ARGS+=("${EXTRA_SHARED_ARGS[@]}")

"$SCRIPT_DIR/cleanup-shared.sh" "${SHARED_ARGS[@]}"

echo ""
log_success "Full OpenShell cleanup complete"
