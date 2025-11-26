#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/env-detect.sh"
source "$SCRIPT_DIR/../lib/logging.sh"

log_step "50" "Installing Ollama"

if command -v ollama >/dev/null 2>&1; then
    log_info "Ollama already installed"
    exit 0
fi

curl -fsSL https://ollama.com/install.sh | sh
log_success "Ollama installed"
