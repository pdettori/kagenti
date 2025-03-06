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

from llama_stack.providers.inline.agents.meta_reference.agents import MetaReferenceAgentsImpl
from llama_stack.providers.inline.agents.meta_reference import (
    MetaReferenceAgentsImplConfig,
)
from llama_stack.distribution.request_headers import NeedsRequestProviderData
from llama_stack.apis.agents import (
    AgentToolGroup,
    AgentTurnCreateRequest,
    AgentTurnResponseStreamChunk,
    Document,
    AgentTurnResponseEventType,
    AgentTurnResponseEvent,
    AgentTurnResponseTurnCompletePayload,
    AgentTurnResponseStepProgressPayload,
    Turn,
    AgentConfig,
    AgentCreateResponse,
    StepType,
)
from typing import AsyncGenerator, List, Optional, Union
from llama_stack.apis.inference import (
    ToolConfig,
    ToolResponseMessage,
    UserMessage,
)
from llama_stack.apis.common.content_types import (
    TextContentItem,
    ToolCallDelta,
    ToolCallParseStatus,
    TextDelta,
    URL,
)
import logging
import json
from llama_stack.apis.safety import Safety
from llama_stack.apis.tools import ToolGroups, ToolRuntime
from llama_stack.apis.vector_io import VectorIO
from llama_stack.apis.inference import Inference
from .agent_factory import AgentFactory
from .agent_base import MultiFrameworkAgent


from .langgraph.converters import convert_messages, EventProcessor
from langchain_core.messages import SystemMessage, HumanMessage

EventType = AgentTurnResponseEventType

log = logging.getLogger(__name__)


class MultiFrameworkAgentImpl(MetaReferenceAgentsImpl, NeedsRequestProviderData):
    def __init__(
        self,
        config: MetaReferenceAgentsImplConfig,
        inference_api: Inference,
        vector_io_api: VectorIO,
        safety_api: Safety,
        tool_runtime_api: ToolRuntime,
        tool_groups_api: ToolGroups,
    ):
        super().__init__(
            config,
            inference_api,
            vector_io_api,
            safety_api,
            tool_runtime_api,
            tool_groups_api,
        )

    async def initialize(self):
        await super().initialize()

    async def create_agent(
        self,
        agent_config: AgentConfig,
    ) -> AgentCreateResponse:
        # example of getting provider_data
        # provider_data = self.get_request_provider_data()
        # the Web-Queue-Worker pattern requires the enable_session_persistence
        # always True
        agent_config.enable_session_persistence = True
        return await super().create_agent(agent_config)

    async def create_agent_turn(
        self,
        agent_id: str,
        session_id: str,
        messages: List[
            Union[
                UserMessage,
                ToolResponseMessage,
            ]
        ],
        toolgroups: Optional[List[AgentToolGroup]] = None, # type: ignore
        documents: Optional[List[Document]] = None,
        stream: Optional[bool] = False,
        tool_config: Optional[ToolConfig] = None,
        allow_turn_resume: Optional[bool] = False,
    ) -> AsyncGenerator:
        log.info(
            f"MultiFrameworkAgentImpl.create_agent_turn: {agent_id} and session {session_id}"
        )
        request = AgentTurnCreateRequest(
            agent_id=agent_id,
            session_id=session_id,
            messages=messages,
            stream=True,
            toolgroups=toolgroups,
            documents=documents,
            tool_config=tool_config,
            allow_turn_resume=allow_turn_resume,
        )
        if not stream:
            raise NotImplementedError("Non-streaming agent turns not yet implemented")

        agent_config = await self.get_agent_config(request.agent_id)
        agent_metadata = MultiFrameworkAgent.extract_agent_metadata(agent_config)

        if agent_metadata is None:
            log.info("routing to MetaReferenceAgentsImpl")
            return self._create_agent_turn_streaming(request)
            
        log.info("routing to multi-framework agent factory")    
        framework = agent_metadata["framework"]

        try:
            factory = AgentFactory.create_agent(framework)
            agent = factory(agent_config=agent_config)
            log.info("{framework} agent instantiated successfully.")
        except Exception as e:
            print(f"Error instantiating Agent: {e}")
            raise e
        
        try:
            return agent.run_streaming(request.session_id, request.messages)
        except Exception as e:
            print(f"Failed to run agent: {e}")
            raise e


    async def get_agent_config(self, agent_id: str) -> AgentConfig:
        agent_config = await self.persistence_store.get(
            key=f"agent:{agent_id}",
        )
        if not agent_config:
            raise ValueError(f"Could not find agent config for {agent_id}")

        try:
            agent_config = json.loads(agent_config)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not JSON decode agent config for {agent_id}") from e

        try:
            agent_config = AgentConfig(**agent_config)
        except Exception as e:
            raise ValueError(f"Could not validate(?) agent config for {agent_id}") from e
        return agent_config
