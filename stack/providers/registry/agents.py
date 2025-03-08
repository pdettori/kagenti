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

from typing import List

from llama_stack.providers.datatypes import (
    AdapterSpec,
    Api,
    InlineProviderSpec,
    ProviderSpec,
    remote_provider_spec,
)
from llama_stack.providers.utils.kvstore import kvstore_dependencies


def available_providers() -> List[ProviderSpec]:
    return [
        InlineProviderSpec(
            api=Api.agents,
            provider_type="inline::meta-reference",
            pip_packages=[
                "matplotlib",
                "pillow",
                "pandas",
                "scikit-learn",
            ]
            + kvstore_dependencies(),
            module="llama_stack.providers.inline.agents.meta_reference",
            config_class="llama_stack.providers.inline.agents.meta_reference.MetaReferenceAgentsImplConfig",
            api_dependencies=[
                Api.inference,
                Api.safety,
                Api.vector_io,
                Api.vector_dbs,
                Api.tool_runtime,
                Api.tool_groups,
            ],
        ),
        InlineProviderSpec(
            api=Api.agents,
            provider_type="inline::multi-framework",
            pip_packages=[
                "matplotlib",
                "pillow",
                "pandas",
                "scikit-learn",
                "langchain_core",
                "langchain_community",
                "langgraph",
                "langchain_ollama",
                "crewai"
            ]
            + kvstore_dependencies(),
            module="stack.providers.inline.agents.multi_framework",
            config_class="stack.providers.inline.agents.multi_framework.MultiFrameworkAgentImplConfig",
            api_dependencies=[
                Api.inference,
                Api.safety,
                Api.vector_io,
                Api.vector_dbs,
                Api.tool_runtime,
                Api.tool_groups,
            ],
        ),
        remote_provider_spec(
            api=Api.agents,
            adapter=AdapterSpec(
                adapter_type="sample",
                pip_packages=[],
                module="llama_stack.providers.remote.agents.sample",
                config_class="llama_stack.providers.remote.agents.sample.SampleConfig",
            ),
        ),
    ]
