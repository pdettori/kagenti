# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""
A2A Chat API endpoints.

Provides endpoints for chatting with A2A agents using the Agent-to-Agent protocol.
"""

import logging
from typing import Optional, List, Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# A2A protocol constants
A2A_AGENT_CARD_PATH = "/.well-known/agent.json"


class ChatMessage(BaseModel):
    """A chat message."""

    role: str  # "user" or "assistant"
    content: str


class AgentCardResponse(BaseModel):
    """Simplified agent card response."""

    name: str
    description: Optional[str] = None
    version: str
    url: str
    streaming: bool = False
    skills: List[dict] = []


class ChatRequest(BaseModel):
    """Request to chat with an A2A agent."""

    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from A2A agent chat."""

    content: str
    session_id: str
    is_complete: bool = True


def _get_agent_url(name: str, namespace: str) -> str:
    """Get the URL for an A2A agent.

    Note: For off-cluster access, the agent URL does not include the namespace.
    The namespace parameter is kept for potential future use with in-cluster routing.
    """
    domain = settings.domain_name
    return f"http://{name}.{domain}:8080"


@router.get("/{namespace}/{name}/agent-card", response_model=AgentCardResponse)
async def get_agent_card(
    namespace: str,
    name: str,
) -> AgentCardResponse:
    """
    Fetch the A2A agent card for an agent.

    The agent card describes the agent's capabilities, skills, and metadata.
    """
    agent_url = _get_agent_url(name, namespace)
    card_url = f"{agent_url}{A2A_AGENT_CARD_PATH}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(card_url)
            response.raise_for_status()
            card_data = response.json()

            # Parse capabilities
            capabilities = card_data.get("capabilities", {})
            streaming = capabilities.get("streaming", False)

            # Parse skills
            skills = []
            for skill in card_data.get("skills", []):
                skills.append(
                    {
                        "id": skill.get("id", ""),
                        "name": skill.get("name", ""),
                        "description": skill.get("description", ""),
                        "examples": skill.get("examples", []),
                    }
                )

            return AgentCardResponse(
                name=card_data.get("name", name),
                description=card_data.get("description"),
                version=card_data.get("version", "unknown"),
                url=card_data.get("url", agent_url),
                streaming=streaming,
                skills=skills,
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching agent card: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Failed to fetch agent card: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error(f"Request error fetching agent card: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to agent at {agent_url}",
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching agent card: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching agent card: {str(e)}",
        )


@router.post("/{namespace}/{name}/send", response_model=ChatResponse)
async def send_message(
    namespace: str,
    name: str,
    request: ChatRequest,
) -> ChatResponse:
    """
    Send a message to an A2A agent and get the response.

    This endpoint sends a message using the A2A protocol and returns
    the agent's response. For streaming agents, use the /stream endpoint.
    """
    agent_url = _get_agent_url(name, namespace)
    session_id = request.session_id or uuid4().hex

    # Build A2A message payload
    message_payload = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": request.message}],
                "messageId": uuid4().hex,
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                agent_url,
                json=message_payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

            # Extract response content from A2A response
            content = ""
            if "result" in result:
                result_data = result["result"]
                # Handle Task response
                if "status" in result_data and "message" in result_data.get("status", {}):
                    parts = result_data["status"]["message"].get("parts", [])
                    for part in parts:
                        if isinstance(part, dict) and "text" in part:
                            content += part["text"]
                        elif hasattr(part, "text"):
                            content += part.text
                # Handle direct message response
                elif "parts" in result_data:
                    for part in result_data["parts"]:
                        if isinstance(part, dict) and "text" in part:
                            content += part["text"]

            if "error" in result:
                error = result["error"]
                content = f"Error: {error.get('message', 'Unknown error')}"

            return ChatResponse(
                content=content or "No response from agent",
                session_id=session_id,
                is_complete=True,
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error sending message: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Agent returned error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error(f"Request error sending message: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to agent at {agent_url}",
        )
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error sending message: {str(e)}",
        )


async def _stream_a2a_response(agent_url: str, message: str, session_id: str):
    """Generator for streaming A2A responses."""
    import json

    # Build A2A streaming message payload
    message_payload = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": message}],
                "messageId": uuid4().hex,
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                agent_url,
                json=message_payload,
                headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # Parse SSE format
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
                            break

                        try:
                            chunk = json.loads(data)

                            # Extract text content from various A2A response formats
                            content = ""

                            if "result" in chunk:
                                result = chunk["result"]

                                # TaskArtifactUpdateEvent
                                if "artifact" in result:
                                    parts = result.get("artifact", {}).get("parts", [])
                                    for part in parts:
                                        if isinstance(part, dict) and "text" in part:
                                            content += part["text"]

                                # TaskStatusUpdateEvent
                                elif "status" in result:
                                    status = result["status"]
                                    if "message" in status:
                                        parts = status["message"].get("parts", [])
                                        for part in parts:
                                            if isinstance(part, dict) and "text" in part:
                                                content += part["text"]

                                # Direct message
                                elif "parts" in result:
                                    for part in result["parts"]:
                                        if isinstance(part, dict) and "text" in part:
                                            content += part["text"]

                            if content:
                                yield f"data: {json.dumps({'content': content, 'session_id': session_id})}\n\n"

                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse SSE data: {data}")
                            continue

    except httpx.HTTPStatusError as e:
        error_msg = f"Agent error: {e.response.status_code}"
        yield f"data: {json.dumps({'error': error_msg, 'session_id': session_id})}\n\n"
    except httpx.RequestError as e:
        error_msg = f"Connection error: {str(e)}"
        yield f"data: {json.dumps({'error': error_msg, 'session_id': session_id})}\n\n"
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        yield f"data: {json.dumps({'error': error_msg, 'session_id': session_id})}\n\n"


@router.post("/{namespace}/{name}/stream")
async def stream_message(
    namespace: str,
    name: str,
    request: ChatRequest,
):
    """
    Send a message to an A2A agent and stream the response.

    This endpoint uses Server-Sent Events (SSE) to stream the agent's
    response in real-time. Requires an agent that supports streaming.
    """
    agent_url = _get_agent_url(name, namespace)
    session_id = request.session_id or uuid4().hex

    return StreamingResponse(
        _stream_a2a_response(agent_url, request.message, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
