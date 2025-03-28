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

from typing import Any, Dict

from pydantic import BaseModel

from llama_stack.providers.utils.kvstore import KVStoreConfig
from llama_stack.providers.utils.kvstore.config import SqliteKVStoreConfig


class MultiFrameworkAgentImplConfig(BaseModel):
    persistence_store: KVStoreConfig

    @classmethod
    def sample_run_config(cls, __distro_dir__: str) -> Dict[str, Any]:
        return {
            "persistence_store": SqliteKVStoreConfig.sample_run_config(
                __distro_dir__=__distro_dir__,
                db_name="agents_store.db",
            )
        }
