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

import importlib
from typing import AsyncGenerator, List, Union
from ..agent_base import MultiFrameworkAgent, AgentConfig
from llama_stack.apis.inference import ToolResponseMessage, UserMessage
from .converters import convert_messages, EventProcessor
from .converters import EventProcessor, convert_messages
import asyncio
from llama_stack.apis.agents import AgentTurnResponseTurnCompletePayload


class CrewAIAgent(MultiFrameworkAgent):
    """
    CrewAIAgent extends the MultiFrameworkAgent class to load and run a specific CrewAI agent.
    """

    def __init__(self, agent_config: AgentConfig) -> None:
        """
        Initializes the specified agent.
        The executable code must be within $PYTHONPATH.

        Args:
            agent_config (AgentConfig): Configuration dict for the agent.

        Raises:
            Exception: If the agent cannot be loaded, an exception is raised with an error message.
        """
        super().__init__(agent_config)
        self.instance = None
        self.method_name = ""
        self.event_processor = EventProcessor()

        try:
            partial_impl_class, method_name = self.impl_class.rsplit(".", 1)
            self.method_name = method_name
            module_name, class_name = partial_impl_class.rsplit(".", 1)
            my_module = importlib.import_module(module_name)

            # Get the class object and instantiate it
            self.crewai_agent_class = getattr(my_module, class_name)
            self.instance = self.crewai_agent_class(
                self.model,
                "http://localhost:11434",
                self.event_processor.enqueue_event_wrapper,
            )

        except Exception as e:
            print(f"Failed to load agent {self.name}: {e}")
            raise

    async def run_streaming(
        self, session_id: str, messages: List[Union[UserMessage, ToolResponseMessage]]
    ) -> AsyncGenerator:
        """
        Streams the execution of the CrewAI agent with the given messages.

        Args:
            session_id (str): The ID of the current session.
            messages (List[Union[UserMessage, ToolResponseMessage]]): Input messages.
        """
        print(f"Running CrewAI agent (streaming): {self.impl_class}")

        try:
            get_crew = getattr(self.instance, self.method_name)

            self.event_processor.set_session_id(session_id)
            inputs_array = convert_messages(messages)

            kickoff_task = asyncio.create_task(
                get_crew().kickoff_for_each_async(inputs=inputs_array)
            )

            async for chunk in self.event_processor.process_events():
                yield chunk
                if isinstance(
                    chunk.event.payload, AgentTurnResponseTurnCompletePayload
                ):
                    return

            # Ensure all tasks complete
            await kickoff_task

        except Exception as e:
            print(f"Error during streaming execution: {e}")
            raise

    def run(
        self, session_id: str, messages: List[Union[UserMessage, ToolResponseMessage]]
    ) -> str:
        """
        Executes the CrewAI agent with the given messages. Uses the 'invoke' method.

        Args:
            session_id (str): The ID of the current session.
            messages (List[Union[UserMessage, ToolResponseMessage]]): Input messages.

        Returns:
            str: Content from the last AIMessage in the response.

        Raises:
            Exception: If there is an error retrieving or executing the agent's method.
        """
        raise NotImplementedError("Non-streaming agent run not yet implemented")
