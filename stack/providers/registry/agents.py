# MIT License

# Copyright (c) Meta Platforms, Inc. and affiliates

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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
                "faiss-cpu",
                "pillow",
                "pandas",
                "scikit-learn",
                "langchain_core",
                "langchain_community",
                "langgraph",
                "langchain_ollama",
                "crewai",
                "llama_models",
                "bullmq",
                "redis",
                "opentelemetry-instrumentation-redis",
                "opentelemetry.instrumentation.asyncpg",
                "asyncpg",
                "psycopg2",
                "nest-asyncio",
                "sentence_transformers"
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
