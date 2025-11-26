#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/env-detect.sh"
source "$SCRIPT_DIR/../lib/logging.sh"

log_step "60" "Pulling Ollama model"

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    log_info "Starting Ollama in background"
    ollama serve > /tmp/ollama.log 2>&1 &
    
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            break
        fi
        sleep 2
    done
fi

# Verify Ollama is responsive
curl -s http://localhost:11434/api/tags || {
    log_error "Ollama failed to start"
    cat /tmp/ollama.log
    exit 1
}

# Pull model if not present
if ! ollama list | grep -q qwen2.5:0.5b; then
    log_info "Pulling qwen2.5:0.5b model"
    timeout 300 ollama pull qwen2.5:0.5b || {
        log_error "Model pull failed"
        exit 1
    }
fi

ollama list | grep qwen2.5 || {
    log_error "Model not found after pull"
    exit 1
}

log_success "Model ready"
