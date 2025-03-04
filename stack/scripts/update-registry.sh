#!/bin/bash


SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
AGENTS_FILE_PATH=${SCRIPT_DIR}/../providers/registry/agents.py

# Get the path to the Conda environment 
CONDA_ENV_PATH=$(conda env list | grep ".*\*" | awk '{print $3}')

if [ -z "$CONDA_ENV_PATH" ]; then
    echo "Current conda env not found."
    exit 1
fi

TARGET_PATH="$CONDA_ENV_PATH/lib/python3.10/site-packages/llama_stack/providers/registry/agents.py"

if [ ! -f "$TARGET_PATH" ]; then
    echo "Target file does not exist at: $TARGET_PATH"
    exit 1
fi

mv ${TARGET_PATH} ${TARGET_PATH}.bk

cp "$AGENTS_FILE_PATH" "$TARGET_PATH"

# Confirm completion
echo "Successfully replaced 'agents.py' in the current Conda environment at '$CONDA_ENV_PATH'"
