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

import streamlit as st
from acp_sdk import GenericEvent, MessageCompletedEvent, MessagePartEvent
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart

async def run_agent_chat_stream(
    st,
    sanitized_agent_name: str,
    user_message: str,
    agent_url: str,
    message_placeholder,
    log_container
) -> str:
    """
    Runs the ACP SDK client to chat with the agent and collects the streamed response,
    updating the Streamlit message_placeholder in real-time for chat content,
    and log_container for generic events.
    """
    full_response_content = ""
    try:
        async with Client(base_url=agent_url) as client, client.session() as session:
            user_message_input = Message(parts=[MessagePart(content=user_message, role="user")])

            async for event in client.run_stream(agent=sanitized_agent_name, input=[user_message_input]):
                match event:
                    case MessagePartEvent(part=MessagePart(content=content)):
                        full_response_content += content
                        message_placeholder.markdown(full_response_content + "▌")
                    case GenericEvent():
                        log_type, log_content = next(iter(event.generic.model_dump().items()))
                        log_message = f"**{log_type}**: {log_content}"
                        st.session_state[f"log_history_{sanitized_agent_name}"].append(log_message)
                        log_container.markdown(log_message)
                    case MessageCompletedEvent():
                        message_placeholder.markdown(full_response_content)
                    case _:
                        log_message = f"ℹ️ {event.type}"
                        st.session_state[f"log_history_{sanitized_agent_name}"].append(log_message)
                        log_container.markdown(log_message)
    except Exception as e:
        error_message = f"Error during agent chat: {e}"
        st.error(error_message)
        message_placeholder.error(error_message)
        st.session_state[f"log_history_{sanitized_agent_name}"].append(f"ERROR: {e}")
        log_container.markdown(f"ERROR: {e}")
        full_response_content = error_message

    return full_response_content

async def display_agent_details(
    st,
    sanitized_agent_name: str,
    agent_url: str,
) -> str:
    """
    Runs the ACP SDK client to get metadata from the agent
    """
    full_response_content = ""
    try:
        async with Client(base_url=agent_url) as client, client.session() as session:
            async for agent in client.agents():
                st.markdown(agent.metadata.documentation)
                st.markdown(f":gray-background[License: {agent.metadata.license}]      :gray-background[Language: {agent.metadata.programming_language}]")
    except Exception as e:
        error_message = f"Error communicating with agent to get agent details: {e}"
        st.error(error_message)       