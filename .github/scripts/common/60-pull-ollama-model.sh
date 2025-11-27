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

# Pull model if not present with retry logic
if ! ollama list | grep -q qwen2.5:0.5b; then
    MAX_RETRIES=3
    RETRY_COUNT=0
    BACKOFF_SECONDS=10

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        log_info "Pulling qwen2.5:0.5b model (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"

        if timeout 300 ollama pull qwen2.5:0.5b; then
            log_success "Model pull successful"
            break
        fi

        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            WAIT_TIME=$((BACKOFF_SECONDS * RETRY_COUNT))
            log_warn "Model pull failed - retrying in ${WAIT_TIME}s (attempt $RETRY_COUNT/$MAX_RETRIES)"
            sleep $WAIT_TIME
        else
            log_error "Model pull failed after $MAX_RETRIES attempts"
            exit 1
        fi
    done
fi

ollama list | grep qwen2.5 || {
    log_error "Model not found after pull"
    exit 1
}

log_success "Model ready"
