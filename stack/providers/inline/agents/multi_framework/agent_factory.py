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

class AgentFramework(Enum):
    """Enumeration of supported frameworks"""
    CREWAI = "crewai"
    LANGGRAPH = "langgraph"

class AgentFactory:
    """Factory class for handling agent frameworks"""

    @staticmethod
    def create_agent(framework: Union[str, AgentFramework]) -> Callable[..., LangGraphAgent]:
        """Create an instance of the specified agent framework.

        Args:
            framework (Union[str, AgentFramework]): The framework to create. Must be a valid enum value.

        Returns:
            A new instance of the corresponding agent class.
        """
        # If the input is a string, convert it to an AgentFramework
        if isinstance(framework, str):
            try:
                framework = AgentFramework(framework.lower())
            except ValueError:
                raise ValueError(f"Unknown framework: {framework}")

        factories = {
            # AgentFramework.CREWAI: CrewAIAgent,
            AgentFramework.LANGGRAPH: LangGraphAgent,
        }

        if framework not in factories:
            raise ValueError(f"Unknown framework: {framework}")
        
        return factories[framework]

    @classmethod
    def get_factory(cls, framework: str) -> Callable[..., LangGraphAgent]:
        """Get a factory function for the specified agent type."""
        return cls.create_agent(framework)

