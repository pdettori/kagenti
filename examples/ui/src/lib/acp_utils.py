# ui/lib/acp_utils.py

import streamlit as st

# Import base events from acp_sdk
from acp_sdk import GenericEvent, MessageCompletedEvent, MessagePartEvent

# AgentMetadataEvent has been removed as per user request.

from acp_sdk.client import Client
from acp_sdk.models import (
    Message,
    MessagePart,
)  # Assuming Metadata, Author etc. are accessible via agent_meta_obj
import logging
from .utils import append_to_log_history
from datetime import datetime  # For formatting datetime objects

logger = logging.getLogger(__name__)


async def run_agent_chat_stream_acp(
    st_object,  # Streamlit object (st, container, etc.)
    session_key_prefix: str,
    user_message: str,
    agent_name_param: str,  # ACP agent name (potentially with hyphens from k8s/UI)
    agent_url: str,
    message_placeholder,  # Streamlit placeholder for assistant's message
    log_container,  # Streamlit container for logs
) -> str:
    """
    Runs the ACP SDK client to chat with the agent and collects the streamed response.
    Updates message_placeholder for chat content and log_container for generic events.
    Args:
        st_object: Streamlit object for displaying messages.
        session_key_prefix: Unique key prefix for session state.
        user_message: The message from the user.
        agent_name_param: The logical name of the ACP agent, as provided (may contain hyphens).
        agent_url: The base URL of the ACP agent service.
        message_placeholder: Streamlit placeholder for the agent's response.
        log_container: Streamlit container for displaying logs.
    Returns:
        The complete response content from the agent as a string.
    """
    full_response_content = ""
    # Normalize the agent name for SDK interaction (typically expects underscores)
    sdk_agent_name = agent_name_param.replace("-", "_")
    logger.info(
        f"Running ACP chat for agent: {agent_name_param} (normalized to SDK name: {sdk_agent_name}) at URL: {agent_url}"
    )

    try:
        async with Client(base_url=agent_url) as client, client.session() as session:  # type: ignore
            user_message_input = Message(
                parts=[MessagePart(content=user_message, role="user")]
            )
            log_msg = f"▶️ Starting ACP stream with agent: {sdk_agent_name} at {agent_url}"  # Use normalized name for log
            append_to_log_history(session_key_prefix, log_msg)
            log_container.markdown(log_msg)

            async for event in client.run_stream(agent=sdk_agent_name, input=[user_message_input]):  # type: ignore # Use normalized name for SDK call
                log_message = None
                match event:
                    case MessagePartEvent(part=MessagePart(content=content)):
                        if content:  # Ensure content is not None
                            full_response_content += content
                            message_placeholder.markdown(full_response_content + "▌")
                    case GenericEvent():
                        # Safely access generic event data
                        generic_data = (
                            event.generic.model_dump() if event.generic else {}
                        )
                        log_type, log_content = (
                            next(iter(generic_data.items()))
                            if generic_data
                            else ("UnknownGeneric", "No data")
                        )
                        log_message = f"ℹ️ **{log_type}**: {log_content}"
                    case MessageCompletedEvent():
                        message_placeholder.markdown(
                            full_response_content
                        )  # Final update
                        log_message = "✅ ACP Message Completed."
                    # AgentMetadataEvent specific handling removed.
                    # Other event types will be caught by the case below.
                    case _:
                        # Try to get a descriptive log message for any other event types
                        event_type_name = (
                            event.type
                            if hasattr(event, "type")
                            else type(event).__name__
                        )
                        log_message = f"🔄 ACP Event: {event_type_name}"
                        # If it's an object with a 'metadata' attribute, it might be the metadata event.
                        if (
                            hasattr(event, "metadata")
                            and event.metadata
                            and hasattr(event.metadata, "documentation")
                        ):
                            doc_url = event.metadata.documentation or "N/A"
                            log_message += f" (Potentially metadata - Docs: {doc_url})"

                if log_message:
                    append_to_log_history(session_key_prefix, log_message)
                    log_container.markdown(log_message)

    except Exception as e:
        error_message = f"Error during ACP agent chat with '{sdk_agent_name}': {e}"  # Use normalized name in error
        logger.error(error_message, exc_info=True)
        st_object.error(error_message)
        message_placeholder.error(error_message)  # Show error in chat
        append_to_log_history(session_key_prefix, f"❌ {error_message}")
        log_container.error(error_message)  # Also log it
        full_response_content = error_message  # Return error as content

    # Fallback if MessageCompletedEvent wasn't received but loop ended
    if (
        not isinstance(full_response_content, str)
        or "Error during ACP agent chat" not in full_response_content
    ):
        message_placeholder.markdown(full_response_content)

    return full_response_content


async def display_acp_agent_metadata(
    st_object,  # Streamlit object (st, container, etc.)
    agent_logical_name: str,  # ACP agent's logical name (e.g., acp-weather-service)
    agent_url: str,
) -> None:
    """
    Uses the ACP SDK client to get and display metadata from the agent.
    Relies on duck typing and the provided Pydantic model structure.
    Args:
        st_object: Streamlit object for displaying messages.
        agent_logical_name: The logical name of the ACP agent.
        agent_url: The base URL of the ACP agent service.
    """
    displayed_once = False
    # Normalize the logical name from UI/K8s to match SDK's typical underscore usage for comparison
    normalized_logical_name_for_comparison = agent_logical_name.replace("-", "_")
    logger.info(
        f"Displaying ACP metadata for: {agent_logical_name} (normalized for comparison to: {normalized_logical_name_for_comparison})"
    )

    try:
        st_object.markdown(
            f"#### ACP Agent Metadata for: {agent_logical_name}"
        )  # Display original name
        async with Client(base_url=agent_url) as client:  # type: ignore
            async for agent_obj in client.agents():  # type: ignore
                if hasattr(agent_obj, "name"):
                    sdk_agent_name = agent_obj.name
                    # Normalize SDK name as well, just in case it could also have hyphens sometimes (though typically underscores)
                    normalized_sdk_agent_name_for_comparison = sdk_agent_name.replace(
                        "-", "_"
                    )

                    logger.debug(
                        f"Checking SDK agent: '{sdk_agent_name}' (normalized: '{normalized_sdk_agent_name_for_comparison}') against logical: '{normalized_logical_name_for_comparison}'"
                    )
                    if (
                        normalized_sdk_agent_name_for_comparison
                        == normalized_logical_name_for_comparison
                    ):
                        logger.info(
                            f"Matched agent: {sdk_agent_name}"
                        )  # Log the original SDK name
                        if hasattr(agent_obj, "description") and agent_obj.description:
                            st_object.markdown(
                                f"**Description**: {agent_obj.description}"
                            )
                        else:
                            st_object.markdown("**Description**: Not provided")

                        if hasattr(agent_obj, "metadata") and agent_obj.metadata:
                            metadata = (
                                agent_obj.metadata
                            )  # This should be the Metadata Pydantic model

                            # Display License, Language, Framework first
                            details_list = []
                            if hasattr(metadata, "license") and metadata.license:
                                details_list.append(f"License: `{metadata.license}`")
                            if (
                                hasattr(metadata, "programming_language")
                                and metadata.programming_language
                            ):
                                details_list.append(
                                    f"Language: `{metadata.programming_language}`"
                                )
                            if hasattr(metadata, "framework") and metadata.framework:
                                details_list.append(
                                    f"Framework: `{metadata.framework}`"
                                )

                            if details_list:
                                st_object.markdown(" ".join(details_list))

                            # Display Documentation in an expander
                            if (
                                hasattr(metadata, "documentation")
                                and metadata.documentation
                            ):
                                with st_object.expander(
                                    "Documentation", expanded=False
                                ):
                                    st.markdown(
                                        f"```markdown\n{metadata.documentation}\n```"
                                    )
                            else:
                                st_object.markdown("**Documentation**: Not available")

                            # Other metadata fields
                            if (
                                hasattr(metadata, "natural_languages")
                                and metadata.natural_languages
                            ):
                                st_object.markdown(
                                    f"**Natural Languages**: `{', '.join(metadata.natural_languages)}`"
                                )

                            if (
                                hasattr(metadata, "tags") and metadata.tags
                            ):  # ACP SDK specific tags
                                st_object.markdown(
                                    f"**ACP Tags**: `{', '.join(metadata.tags)}`"
                                )

                            if hasattr(metadata, "domains") and metadata.domains:
                                st_object.markdown(
                                    f"**Domains**: `{', '.join(metadata.domains)}`"
                                )

                            if (
                                hasattr(metadata, "capabilities")
                                and metadata.capabilities
                            ):
                                cap_names = [
                                    cap.name if hasattr(cap, "name") else str(cap)
                                    for cap in metadata.capabilities
                                ]
                                if cap_names:
                                    st_object.markdown(
                                        f"**Capabilities**: `{', '.join(cap_names)}`"
                                    )

                            if hasattr(metadata, "author") and metadata.author:
                                author = metadata.author
                                author_info = (
                                    f"**Author**: {getattr(author, 'name', 'N/A')}"
                                )
                                if hasattr(author, "email") and author.email:
                                    author_info += f" ({getattr(author, 'email')})"
                                if hasattr(author, "url") and author.url:
                                    author_info += (
                                        f" [[Homepage]({str(getattr(author, 'url'))})]"
                                    )
                                st_object.markdown(author_info)

                            if (
                                hasattr(metadata, "created_at")
                                and metadata.created_at
                                and isinstance(metadata.created_at, datetime)
                            ):
                                st_object.markdown(
                                    f"**Created At**: `{metadata.created_at.strftime('%Y-%m-%d %H:%M:%S %Z')}`"
                                )
                            if (
                                hasattr(metadata, "updated_at")
                                and metadata.updated_at
                                and isinstance(metadata.updated_at, datetime)
                            ):
                                st_object.markdown(
                                    f"**Updated At**: `{metadata.updated_at.strftime('%Y-%m-%d %H:%M:%S %Z')}`"
                                )

                            if (
                                hasattr(metadata, "recommended_models")
                                and metadata.recommended_models
                            ):
                                st_object.markdown(
                                    f"**Recommended Models**: `{', '.join(metadata.recommended_models)}`"
                                )

                            if hasattr(metadata, "use_cases") and metadata.use_cases:
                                with st_object.expander("Use Cases", expanded=False):
                                    for uc in metadata.use_cases:
                                        st.markdown(f"- {uc}")

                            if hasattr(metadata, "env") and metadata.env:
                                with st_object.expander(
                                    "Environment Variables Configured", expanded=False
                                ):
                                    for env_var in metadata.env:
                                        env_name = (
                                            env_var.get("name", "N/A")
                                            if isinstance(env_var, dict)
                                            else "N/A"
                                        )
                                        env_desc = (
                                            env_var.get("description", "No description")
                                            if isinstance(env_var, dict)
                                            else ""
                                        )
                                        st.markdown(f"- `{env_name}`: {env_desc}")

                            if hasattr(metadata, "links") and metadata.links:
                                with st_object.expander("Links", expanded=False):
                                    for (
                                        link_item
                                    ) in (
                                        metadata.links
                                    ):  # Renamed to avoid conflict with st.link_button
                                        link_type = getattr(link_item, "type", "N/A")
                                        link_url = str(getattr(link_item, "url", "#"))
                                        # Ensure link_type is a simple string if it's an Enum
                                        if hasattr(link_type, "value"):
                                            link_type = link_type.value
                                        st.markdown(
                                            f"- ({link_type}): [{link_url}]({link_url})"
                                        )

                            if (
                                hasattr(metadata, "annotations")
                                and metadata.annotations
                            ):
                                with st_object.expander("Annotations", expanded=False):
                                    try:
                                        st.json(
                                            (
                                                metadata.annotations.model_dump_json()
                                                if hasattr(
                                                    metadata.annotations,
                                                    "model_dump_json",
                                                )
                                                else str(metadata.annotations)
                                            ),
                                            expanded=False,
                                        )
                                    except Exception as annot_ex:
                                        logger.warning(
                                            f"Could not serialize annotations: {annot_ex}"
                                        )
                                        st.caption(
                                            "(Annotations present but could not be displayed)"
                                        )
                        else:
                            st_object.caption(
                                "No detailed ACP metadata (metadata object missing)."
                            )

                        displayed_once = True
                        break

            if not displayed_once:
                st_object.info(
                    f"No ACP metadata object found for agent named '{agent_logical_name}' (normalized: '{normalized_logical_name_for_comparison}') from `client.agents()` stream."
                )
                logger.warning(
                    f"Could not find match for {normalized_logical_name_for_comparison} in client.agents() output."
                )

    except Exception as e:
        error_message = f"Error fetching/displaying ACP agent metadata for '{agent_logical_name}': {e}"
        logger.error(error_message, exc_info=True)
        st_object.error(error_message)
