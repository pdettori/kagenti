#!/usr/bin/env bash

# Copyright 2025 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

ROOT_LIB=lib/python3.10/site-packages

# Get the path to the Conda environment
CONDA_ENV_PATH=$(conda env list | grep ".*\*" | awk '{print $3}')

if [ -z "$CONDA_ENV_PATH" ]; then
    echo "Current conda env not found."
    exit 1
fi


# List of source paths relative to SCRIPT_DIR
SOURCE_PATHS=(
    "${SCRIPT_DIR}/../providers/registry/agents.py"
    "${SCRIPT_DIR}/../providers/registry/tool_runtime.py"
    "${SCRIPT_DIR}/../providers/remote/tool_runtime/model_context_protocol/model_context_protocol.py"
    "${SCRIPT_DIR}/../distribution/routers/routing_tables.py"
)

# List of target paths
TARGET_PATHS=(
    "$CONDA_ENV_PATH/${ROOT_LIB}/llama_stack/providers/registry/agents.py"
    "$CONDA_ENV_PATH/${ROOT_LIB}/llama_stack/providers/registry/tool_runtime.py"
    "$CONDA_ENV_PATH/${ROOT_LIB}/llama_stack/providers/remote/tool_runtime/model_context_protocol/model_context_protocol.py"
    "$CONDA_ENV_PATH/${ROOT_LIB}/llama_stack/distribution/routers/routing_tables.py"
)


# Ensure the lists are the same length
if [ ${#SOURCE_PATHS[@]} -ne ${#TARGET_PATHS[@]} ]; then
    echo "The number of source paths must match the number of target paths."
    exit 1
fi

# Iterate over the paths and perform operations
for i in "${!SOURCE_PATHS[@]}"; do
    SOURCE_PATH="${SOURCE_PATHS[$i]}"
    TARGET_PATH="${TARGET_PATHS[$i]}"
  
    if [ ! -f "$SOURCE_PATH" ]; then
        echo "Source file does not exist at: $SOURCE_PATH"
        continue
    fi
  
    if [ ! -f "$TARGET_PATH" ]; then
        echo "Target file does not exist at: $TARGET_PATH"
        continue
    fi
    
    mv "${TARGET_PATH}" "${TARGET_PATH}.bk"
    cp "${SOURCE_PATH}" "${TARGET_PATH}"
    echo "Successfully replaced '$(basename "$SOURCE_PATH")' in the current Conda environment at '$TARGET_PATH'"
done
