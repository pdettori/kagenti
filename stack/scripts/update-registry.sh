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
