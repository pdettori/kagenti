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

from typing import Dict
from pydantic import BaseModel

from llama_stack.distribution.datatypes import Api, ProviderSpec

from .config import MultiFrameworkAgentImplConfig


async def get_provider_impl(
    config: MultiFrameworkAgentImplConfig, deps: Dict[Api, ProviderSpec]
):
    from .agents import MultiFrameworkAgentImpl

    impl = MultiFrameworkAgentImpl(
        config,
        deps[Api.inference],
        deps[Api.vector_io],
        deps[Api.safety],
        deps[Api.tool_runtime],
        deps[Api.tool_groups],
    )
    await impl.initialize()
    return impl


class MultiFrameworkAgentImplDataValidator(BaseModel):
    framework: str
    implementation_class: str