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

from abc import abstractmethod
from llama_stack.apis.agents import AgentConfig
from typing import AsyncGenerator, List
from llama_stack.apis.inference import (
    ToolResponseMessage,
    UserMessage,
)

class MultiFrameworkAgent:
    """
    Abstract base class for running agents.
    """
    def __init__(self, agent_config: AgentConfig) -> None:
        """
        Initializes the MultiFrameworkAgent with the given agent AgentConfig.
        """

        agent_metadata = self.extract_agent_metadata(agent_config)

        self.name = agent_metadata["name"]
        self.description = agent_metadata["description"]
        self.framework = agent_metadata["framework"]
        self.impl_class = agent_metadata["impl_class"]
        self.instructions = agent_config.instructions
        self.model = agent_config.model
        
    @staticmethod
    def extract_agent_metadata(agent_config):
        for tool in agent_config.client_tools:
            if tool.name == "AgentMetadata":
                return tool.metadata
        return None

    @abstractmethod
    def run(self, messages: List[UserMessage | ToolResponseMessage]) -> str:
        """
        Runs the agent with the input messages.
        """

    @abstractmethod
    async def run_streaming(self, messages: List[UserMessage | ToolResponseMessage]) -> AsyncGenerator:
        """
        Runs the agent in streaming mode with the given messages.
        """
