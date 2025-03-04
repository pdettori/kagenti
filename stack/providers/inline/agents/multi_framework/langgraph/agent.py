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
from ..agent import MultiFrameworkAgent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage  # type: ignore
from llama_stack.apis.agents import AgentConfig, AgentTurnResponseTurnCompletePayload
from llama_stack.apis.inference import ToolResponseMessage, UserMessage
from .converters import convert_messages, EventProcessor


class LangGraphAgent(MultiFrameworkAgent):
    """
    LangGraphAgent extends the MultiFrameworkAgent class to load and run a specific LangGraph agent.
    """

    def __init__(self, agent_config: AgentConfig) -> None:
        """
        Initializes the workflow for the specified agent.
        The executable code must be within $PYTHONPATH.

        Args:
            agent_config (AgentConfig): Configuration dict for the agent.

        Raises:
            Exception: If the agent cannot be loaded, an exception is raised with an error message.
        """
        super().__init__(agent_config)
        self.instance = None
        self.method_name = ""

        try:
            partial_impl_class, method_name = self.impl_class.rsplit(".", 1)
            self.method_name = method_name
            module_name, class_name = partial_impl_class.rsplit(".", 1)
            my_module = importlib.import_module(module_name)

            # Get the class object and instantiate it
            self.langgraph_agent_class = getattr(my_module, class_name)
            self.instance = self.langgraph_agent_class()

        except Exception as e:
            print(f"Failed to load agent {self.name}: {e}")
            raise

    def run(
        self, session_id: str, messages: List[Union[UserMessage, ToolResponseMessage]]
    ) -> str:
        """
        Executes the LangGraph agent with the given messages. Uses the 'invoke' method.

        Args:
            session_id (str): The ID of the current session.
            messages (List[Union[UserMessage, ToolResponseMessage]]): Input messages.

        Returns:
            str: Content from the last AIMessage in the response.

        Raises:
            Exception: If there is an error retrieving or executing the agent's method.
        """
        print(f"Running LangGraph agent: {self.impl_class}")

        try:
            method = getattr(self.instance, self.method_name)
            config = {"configurable": {"thread_id": session_id}, "model": self.model}
            sys_msg = SystemMessage(content=self.instructions)
            lg_messages = [sys_msg] + convert_messages(messages)
            response = method().invoke({"messages": lg_messages}, config)

            last_ai_message_content = next(
                (
                    message.content
                    for message in response["messages"]
                    if isinstance(message, AIMessage)
                ),
                None,
            )
            return last_ai_message_content

        except Exception as e:
            print(f"Failed to kickoff LangGraph agent {self.name}: {e}")
            raise

    async def run_streaming(
        self, session_id: str, messages: List[Union[UserMessage, ToolResponseMessage]]
    ) -> AsyncGenerator:
        """
        Streams the execution of the LangGraph agent with the given messages.

        Args:
            session_id (str): The ID of the current session.
            messages (List[Union[UserMessage, ToolResponseMessage]]): Input messages.
        """
        print(f"Running LangGraph agent (streaming): {self.impl_class}")

        try:
            method = getattr(self.instance, self.method_name)
            config = {"configurable": {"thread_id": session_id}, "model": self.model}
            sys_msg = SystemMessage(content=self.instructions)
            lg_messages = [sys_msg] + convert_messages(messages)
            processor = EventProcessor()

            async for event in method().astream_events(
                {"messages": lg_messages}, config, version="v2"
            ):
                chunk = processor.process_event(event)
                if chunk is not None:
                    yield chunk
                    if isinstance(
                        chunk.event.payload, AgentTurnResponseTurnCompletePayload
                    ):
                        return

        except Exception as e:
            print(f"Error during streaming execution: {e}")
            raise
