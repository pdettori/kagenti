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


def available_providers() -> List[ProviderSpec]:
    return [
        InlineProviderSpec(
            api=Api.tool_runtime,
            provider_type="inline::rag-runtime",
            pip_packages=[
                "blobfile",
                "chardet",
                "pypdf",
                "tqdm",
                "numpy",
                "scikit-learn",
                "scipy",
                "nltk",
                "sentencepiece",
                "transformers",
            ],
            module="llama_stack.providers.inline.tool_runtime.rag",
            config_class="llama_stack.providers.inline.tool_runtime.rag.config.RagToolRuntimeConfig",
            api_dependencies=[Api.vector_io, Api.inference],
        ),
        InlineProviderSpec(
            api=Api.tool_runtime,
            provider_type="inline::code-interpreter",
            pip_packages=[],
            module="llama_stack.providers.inline.tool_runtime.code_interpreter",
            config_class="llama_stack.providers.inline.tool_runtime.code_interpreter.config.CodeInterpreterToolConfig",
        ),
        remote_provider_spec(
            api=Api.tool_runtime,
            adapter=AdapterSpec(
                adapter_type="brave-search",
                module="llama_stack.providers.remote.tool_runtime.brave_search",
                config_class="llama_stack.providers.remote.tool_runtime.brave_search.config.BraveSearchToolConfig",
                pip_packages=["requests"],
                provider_data_validator="llama_stack.providers.remote.tool_runtime.brave_search.BraveSearchToolProviderDataValidator",
            ),
        ),
        remote_provider_spec(
            api=Api.tool_runtime,
            adapter=AdapterSpec(
                adapter_type="bing-search",
                module="llama_stack.providers.remote.tool_runtime.bing_search",
                config_class="llama_stack.providers.remote.tool_runtime.bing_search.config.BingSearchToolConfig",
                pip_packages=["requests"],
                provider_data_validator="llama_stack.providers.remote.tool_runtime.bing_search.BingSearchToolProviderDataValidator",
            ),
        ),
        remote_provider_spec(
            api=Api.tool_runtime,
            adapter=AdapterSpec(
                adapter_type="tavily-search",
                module="llama_stack.providers.remote.tool_runtime.tavily_search",
                config_class="llama_stack.providers.remote.tool_runtime.tavily_search.config.TavilySearchToolConfig",
                pip_packages=["requests"],
                provider_data_validator="llama_stack.providers.remote.tool_runtime.tavily_search.TavilySearchToolProviderDataValidator",
            ),
        ),
        remote_provider_spec(
            api=Api.tool_runtime,
            adapter=AdapterSpec(
                adapter_type="wolfram-alpha",
                module="llama_stack.providers.remote.tool_runtime.wolfram_alpha",
                config_class="llama_stack.providers.remote.tool_runtime.wolfram_alpha.config.WolframAlphaToolConfig",
                pip_packages=["requests"],
                provider_data_validator="llama_stack.providers.remote.tool_runtime.wolfram_alpha.WolframAlphaToolProviderDataValidator",
            ),
        ),
        remote_provider_spec(
            api=Api.tool_runtime,
            adapter=AdapterSpec(
                adapter_type="model-context-protocol",
                module="llama_stack.providers.remote.tool_runtime.model_context_protocol",
                config_class="llama_stack.providers.remote.tool_runtime.model_context_protocol.config.ModelContextProtocolConfig",
                pip_packages=["mcp"],
                provider_data_validator="llama_stack.providers.remote.tool_runtime.model_context_protocol.ModelContextProtocolToolProviderDataValidator",
            ),
        ),
    ]
