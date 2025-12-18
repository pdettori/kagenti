# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""
Tool API endpoints.
"""

import logging
from typing import Any, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from kubernetes.client import ApiException
from pydantic import BaseModel

from app.core.config import settings
from app.core.constants import (
    TOOLHIVE_CRD_GROUP,
    TOOLHIVE_CRD_VERSION,
    TOOLHIVE_MCP_PLURAL,
    KAGENTI_TYPE_LABEL,
    KAGENTI_PROTOCOL_LABEL,
    KAGENTI_FRAMEWORK_LABEL,
    APP_KUBERNETES_IO_CREATED_BY,
    KAGENTI_UI_CREATOR_LABEL,
    RESOURCE_TYPE_TOOL,
    DEFAULT_IN_CLUSTER_PORT,
    DEFAULT_RESOURCE_LIMITS,
    DEFAULT_RESOURCE_REQUESTS,
    DEFAULT_ENV_VARS,
)
from app.models.responses import (
    ToolSummary,
    ToolListResponse,
    ResourceLabels,
    DeleteResponse,
)
from app.services.kubernetes import KubernetesService, get_kubernetes_service


class EnvVar(BaseModel):
    """Environment variable."""

    name: str
    value: str


class ServicePort(BaseModel):
    """Service port configuration."""

    name: str = "http"
    port: int = 8000
    targetPort: int = 8000
    protocol: str = "TCP"


class CreateToolRequest(BaseModel):
    """Request to create a new MCP tool.

    Tools are deployed from existing container images using the MCPServer CRD.
    Unlike agents, tools do not support building from source.
    """

    name: str
    namespace: str
    containerImage: str  # Required: full image URL with tag
    protocol: str = "streamable_http"
    framework: str = "Python"
    envVars: Optional[List[EnvVar]] = None
    imagePullSecret: Optional[str] = None
    servicePorts: Optional[List[ServicePort]] = None


class CreateToolResponse(BaseModel):
    """Response after creating a tool."""

    success: bool
    name: str
    namespace: str
    message: str


class MCPToolSchema(BaseModel):
    """Schema for an MCP tool."""

    name: str
    description: Optional[str] = None
    input_schema: Optional[dict] = None


class MCPToolsResponse(BaseModel):
    """Response containing available MCP tools."""

    tools: List[MCPToolSchema]


class MCPInvokeRequest(BaseModel):
    """Request to invoke an MCP tool."""

    tool_name: str
    arguments: dict = {}


class MCPInvokeResponse(BaseModel):
    """Response from MCP tool invocation."""

    result: Any


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


def _is_deployment_ready(resource_data: dict) -> str:
    """Check if a deployment is ready based on status conditions or phase.

    Checks for a condition with type="Ready" and status="True",
    or a status.phase of "Ready" or "Running".
    """
    status = resource_data.get("status", {})
    conditions = status.get("conditions", [])

    # Check conditions array for Ready condition
    for condition in conditions:
        if condition.get("type") == "Ready" and condition.get("status") == "True":
            return "Ready"

    # Fallback: check status.phase for MCPServer CRD
    phase = status.get("phase", "")
    if phase in ("Ready", "Running"):
        return "Ready"

    return "Not Ready"


def _extract_labels(labels: dict) -> ResourceLabels:
    """Extract kagenti labels from Kubernetes labels."""
    return ResourceLabels(
        protocol=labels.get("kagenti.io/protocol"),
        framework=labels.get("kagenti.io/framework"),
        type=labels.get("kagenti.io/type"),
    )


@router.get("", response_model=ToolListResponse)
async def list_tools(
    namespace: str = Query(default="default", description="Kubernetes namespace"),
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> ToolListResponse:
    """
    List all MCP tools in the specified namespace.

    Returns tools that have the kagenti.io/type=tool label.
    """
    try:
        label_selector = f"{KAGENTI_TYPE_LABEL}={RESOURCE_TYPE_TOOL}"

        items = kube.list_custom_resources(
            group=TOOLHIVE_CRD_GROUP,
            version=TOOLHIVE_CRD_VERSION,
            namespace=namespace,
            plural=TOOLHIVE_MCP_PLURAL,
            label_selector=label_selector,
        )

        tools = []
        for item in items:
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})

            tools.append(
                ToolSummary(
                    name=metadata.get("name", ""),
                    namespace=metadata.get("namespace", namespace),
                    description=spec.get("description", "No description"),
                    status=_is_deployment_ready(item),
                    labels=_extract_labels(metadata.get("labels", {})),
                    createdAt=metadata.get("creationTimestamp"),
                )
            )

        return ToolListResponse(items=tools)

    except ApiException as e:
        if e.status == 404:
            raise HTTPException(
                status_code=404,
                detail="MCPServer CRD not found. Is ToolHive installed?",
            )
        if e.status == 403:
            raise HTTPException(
                status_code=403,
                detail="Permission denied. Check RBAC configuration.",
            )
        raise HTTPException(status_code=e.status, detail=str(e.reason))


@router.get("/{namespace}/{name}")
async def get_tool(
    namespace: str,
    name: str,
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> Any:
    """Get detailed information about a specific tool."""
    try:
        tool = kube.get_custom_resource(
            group=TOOLHIVE_CRD_GROUP,
            version=TOOLHIVE_CRD_VERSION,
            namespace=namespace,
            plural=TOOLHIVE_MCP_PLURAL,
            name=name,
        )
        return tool

    except ApiException as e:
        if e.status == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{name}' not found in namespace '{namespace}'",
            )
        raise HTTPException(status_code=e.status, detail=str(e.reason))


@router.delete("/{namespace}/{name}", response_model=DeleteResponse)
async def delete_tool(
    namespace: str,
    name: str,
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> DeleteResponse:
    """Delete a tool from the cluster."""
    try:
        kube.delete_custom_resource(
            group=TOOLHIVE_CRD_GROUP,
            version=TOOLHIVE_CRD_VERSION,
            namespace=namespace,
            plural=TOOLHIVE_MCP_PLURAL,
            name=name,
        )
        return DeleteResponse(success=True, message=f"Tool '{name}' deleted")

    except ApiException as e:
        if e.status == 404:
            return DeleteResponse(success=True, message=f"Tool '{name}' already deleted")
        raise HTTPException(status_code=e.status, detail=str(e.reason))


def _build_mcpserver_manifest(request: CreateToolRequest) -> dict:
    """
    Build an MCPServer CRD manifest for deploying an MCP tool.

    Tools are deployed using the ToolHive MCPServer CRD.
    """
    # Build environment variables
    env_vars = list(DEFAULT_ENV_VARS)
    if request.envVars:
        for ev in request.envVars:
            env_vars.append({"name": ev.name, "value": ev.value})

    # Build service ports
    if request.servicePorts:
        port = request.servicePorts[0].port
        target_port = request.servicePorts[0].targetPort
    else:
        port = DEFAULT_IN_CLUSTER_PORT
        target_port = DEFAULT_IN_CLUSTER_PORT

    manifest = {
        "apiVersion": f"{TOOLHIVE_CRD_GROUP}/{TOOLHIVE_CRD_VERSION}",
        "kind": "MCPServer",
        "metadata": {
            "name": request.name,
            "namespace": request.namespace,
            "labels": {
                APP_KUBERNETES_IO_CREATED_BY: KAGENTI_UI_CREATOR_LABEL,
                KAGENTI_TYPE_LABEL: RESOURCE_TYPE_TOOL,
                KAGENTI_PROTOCOL_LABEL: request.protocol,
                KAGENTI_FRAMEWORK_LABEL: request.framework,
            },
        },
        "spec": {
            "image": request.containerImage,
            "transport": "streamable-http",
            "port": port,
            "targetPort": target_port,
            "proxyPort": DEFAULT_IN_CLUSTER_PORT,
            "podTemplateSpec": {
                "spec": {
                    "serviceAccountName": request.name,
                    "securityContext": {
                        "runAsNonRoot": True,
                        "seccompProfile": {"type": "RuntimeDefault"},
                    },
                    "volumes": [
                        {"name": "cache", "emptyDir": {}},
                        {"name": "tmp-dir", "emptyDir": {}},
                    ],
                    "containers": [
                        {
                            "name": "mcp",
                            "securityContext": {
                                "allowPrivilegeEscalation": False,
                                "capabilities": {"drop": ["ALL"]},
                                "runAsUser": 1000,
                            },
                            "resources": {
                                "limits": DEFAULT_RESOURCE_LIMITS,
                                "requests": DEFAULT_RESOURCE_REQUESTS,
                            },
                            "env": env_vars,
                            "volumeMounts": [
                                {"name": "cache", "mountPath": "/app/.cache", "readOnly": False},
                                {"name": "tmp-dir", "mountPath": "/tmp", "readOnly": False},
                            ],
                        }
                    ],
                },
            },
        },
    }

    # Add image pull secrets if specified
    if request.imagePullSecret:
        manifest["spec"]["podTemplateSpec"]["spec"]["imagePullSecrets"] = [
            {"name": request.imagePullSecret}
        ]

    return manifest


@router.post("", response_model=CreateToolResponse)
async def create_tool(
    request: CreateToolRequest,
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> CreateToolResponse:
    """
    Create a new MCP tool by submitting an MCPServer CRD.

    Tools are deployed from existing container images using the ToolHive
    MCPServer CRD. Unlike agents, tools do not support building from source.
    """
    if not request.containerImage:
        raise HTTPException(
            status_code=400,
            detail="containerImage is required for tool deployment",
        )

    manifest = _build_mcpserver_manifest(request)

    try:
        kube.create_custom_resource(
            group=TOOLHIVE_CRD_GROUP,
            version=TOOLHIVE_CRD_VERSION,
            namespace=request.namespace,
            plural=TOOLHIVE_MCP_PLURAL,
            body=manifest,
        )

        return CreateToolResponse(
            success=True,
            name=request.name,
            namespace=request.namespace,
            message=f"Tool '{request.name}' deployment started.",
        )

    except ApiException as e:
        if e.status == 409:
            raise HTTPException(
                status_code=409,
                detail=f"Tool '{request.name}' already exists in namespace '{request.namespace}'",
            )
        if e.status == 404:
            raise HTTPException(
                status_code=404,
                detail="MCPServer CRD not found. Is ToolHive installed?",
            )
        logger.error(f"Failed to create tool: {e}")
        raise HTTPException(status_code=e.status, detail=str(e.reason))


def _get_tool_url(name: str, namespace: str) -> str:
    """Get the URL for an MCP tool server.

    Note: For off-cluster access, the tool URL does not include the namespace.
    The namespace parameter is kept for potential future use with in-cluster routing.
    """
    domain = settings.domain_name
    return f"http://{name}.{domain}:8080"


@router.post("/{namespace}/{name}/connect", response_model=MCPToolsResponse)
async def connect_to_tool(
    namespace: str,
    name: str,
) -> MCPToolsResponse:
    """
    Connect to an MCP server and list available tools.

    This endpoint connects to the MCP server and retrieves the list of
    available tools using the MCP protocol.
    """
    tool_url = _get_tool_url(name, namespace)
    mcp_endpoint = f"{tool_url}/mcp"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Initialize MCP session
            init_response = await client.post(
                mcp_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "kagenti-backend", "version": "0.1.0"},
                    },
                },
            )
            init_response.raise_for_status()

            # List tools
            tools_response = await client.post(
                mcp_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                },
            )
            tools_response.raise_for_status()
            tools_data = tools_response.json()

            # Parse tools from response
            tools = []
            result = tools_data.get("result", {})
            for tool_info in result.get("tools", []):
                tools.append(
                    MCPToolSchema(
                        name=tool_info.get("name", ""),
                        description=tool_info.get("description"),
                        input_schema=tool_info.get("inputSchema"),
                    )
                )

            return MCPToolsResponse(tools=tools)

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error connecting to MCP server: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"MCP server returned error: {e.response.status_code}",
        )
    except httpx.RequestError as e:
        logger.error(f"Request error connecting to MCP server: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to MCP server at {tool_url}",
        )
    except Exception as e:
        logger.error(f"Unexpected error connecting to MCP server: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting to MCP server: {str(e)}",
        )


@router.post("/{namespace}/{name}/invoke", response_model=MCPInvokeResponse)
async def invoke_tool(
    namespace: str,
    name: str,
    request: MCPInvokeRequest,
) -> MCPInvokeResponse:
    """
    Invoke an MCP tool with the given arguments.

    This endpoint calls a specific tool on the MCP server with
    the provided arguments and returns the result.
    """
    tool_url = _get_tool_url(name, namespace)
    mcp_endpoint = f"{tool_url}/mcp"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Initialize MCP session first
            init_response = await client.post(
                mcp_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "kagenti-backend", "version": "0.1.0"},
                    },
                },
            )
            init_response.raise_for_status()

            # Call the tool
            call_response = await client.post(
                mcp_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": request.tool_name,
                        "arguments": request.arguments,
                    },
                },
            )
            call_response.raise_for_status()
            call_data = call_response.json()

            # Check for JSON-RPC error
            if "error" in call_data:
                error = call_data["error"]
                raise HTTPException(
                    status_code=400,
                    detail=f"Tool error: {error.get('message', 'Unknown error')}",
                )

            result = call_data.get("result", {})
            return MCPInvokeResponse(result=result)

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error invoking MCP tool: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"MCP server returned error: {e.response.status_code}",
        )
    except httpx.RequestError as e:
        logger.error(f"Request error invoking MCP tool: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to MCP server at {tool_url}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error invoking MCP tool: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error invoking MCP tool: {str(e)}",
        )
