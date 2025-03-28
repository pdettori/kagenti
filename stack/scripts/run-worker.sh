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

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <run config file path>"
    exit 1
fi

config_file=$1

# Get the path to the Conda environment
CONDA_ENV_PATH=$(conda env list | grep ".*\*" | awk '{print $3}')

if [ -z "$CONDA_ENV_PATH" ]; then
    echo "Current conda env not found."
    exit 1
fi

export ROLE=consumer
${CONDA_ENV_PATH}/bin/python -m stack.worker.main --config ${config_file}



