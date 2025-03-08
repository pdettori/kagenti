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

from enum import Enum
from typing import Callable, Type, Union
from .langgraph.agent import LangGraphAgent
from .crewai.agent import CrewAIAgent


class AgentFramework(Enum):
    """Enumeration of supported frameworks"""

    CREWAI = "crewai"
    LANGGRAPH = "langgraph"

    @classmethod
    def from_str(cls, framework_str: str):
        """Converts a string to an AgentFramework enum, if valid."""
        try:
            return cls[framework_str.upper()]
        except KeyError:
            raise ValueError(f"Unknown framework: {framework_str}")


class AgentFactory:
    """Factory class for handling agent frameworks."""

    _factories = {
        AgentFramework.CREWAI: CrewAIAgent,  
        AgentFramework.LANGGRAPH: LangGraphAgent,
    }

    @staticmethod
    def create_agent(
        framework: Union[str, AgentFramework, CrewAIAgent]
    ) -> Callable[..., Union[LangGraphAgent, CrewAIAgent]]:
        """Create an instance of the specified agent framework.

        Args:
            framework (Union[str, AgentFramework]): The framework to create. Must be a valid enum value.

        Returns:
            A new instance of the corresponding agent class.
        """
        if isinstance(framework, str):
            framework = AgentFramework.from_str(framework)

        if framework not in AgentFactory._factories:
            raise ValueError(f"Unsupported framework: {framework}")

        return AgentFactory._factories[framework]

    @classmethod
    def get_factory(cls, framework: str) -> Callable[..., Union[LangGraphAgent,CrewAIAgent]]:
        """Get a factory function for the specified agent type."""
        return cls.create_agent(framework)
