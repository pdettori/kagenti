# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""
Agent API endpoints.
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from kubernetes.client import ApiException
from pydantic import BaseModel

from app.core.constants import (
    CRD_GROUP,
    CRD_VERSION,
    AGENTS_PLURAL,
    AGENTBUILDS_PLURAL,
    KAGENTI_TYPE_LABEL,
    KAGENTI_PROTOCOL_LABEL,
    KAGENTI_FRAMEWORK_LABEL,
    APP_KUBERNETES_IO_CREATED_BY,
    APP_KUBERNETES_IO_NAME,
    KAGENTI_UI_CREATOR_LABEL,
    KAGENTI_OPERATOR_LABEL_NAME,
    RESOURCE_TYPE_AGENT,
    DEFAULT_IN_CLUSTER_PORT,
    DEFAULT_IMAGE_POLICY,
    DEFAULT_RESOURCE_LIMITS,
    DEFAULT_RESOURCE_REQUESTS,
    DEFAULT_ENV_VARS,
    OPERATOR_NS,
    GIT_USER_SECRET_NAME,
    PYTHON_VERSION,
)
from app.models.responses import (
    AgentSummary,
    AgentListResponse,
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
    port: int = 8080
    targetPort: int = 8080
    protocol: str = "TCP"


class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""

    name: str
    namespace: str
    protocol: str = "a2a"
    framework: str = "LangGraph"
    envVars: Optional[List[EnvVar]] = None

    # Deployment method: 'source' (build from git) or 'image' (use existing image)
    deploymentMethod: str = "source"

    # Build from source fields
    gitUrl: str = ""
    gitPath: str = ""
    gitBranch: str = "main"
    imageTag: str = "v0.0.1"
    registryUrl: Optional[str] = None
    registrySecret: Optional[str] = None
    startCommand: Optional[str] = None

    # Deploy from existing image fields
    containerImage: Optional[str] = None
    imagePullSecret: Optional[str] = None

    # Pod configuration
    servicePorts: Optional[List[ServicePort]] = None


class CreateAgentResponse(BaseModel):
    """Response after creating an agent."""

    success: bool
    name: str
    namespace: str
    message: str


class BuildStatusCondition(BaseModel):
    """Build status condition."""

    type: str
    status: str
    reason: Optional[str] = None
    message: Optional[str] = None
    lastTransitionTime: Optional[str] = None


class BuildStatusResponse(BaseModel):
    """Response containing build status information."""

    name: str
    namespace: str
    phase: str
    conditions: List[BuildStatusCondition]
    image: Optional[str] = None
    imageTag: Optional[str] = None
    startTime: Optional[str] = None
    completionTime: Optional[str] = None


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])


def _is_deployment_ready(resource_data: dict) -> str:
    """Check if a deployment is ready based on status conditions.

    Checks for a condition with type="Ready" and status="True".
    The reason field can be anything (e.g., "Ready", "Available", etc.).
    """
    status = resource_data.get("status", {})
    conditions = status.get("conditions", [])

    # Check conditions array for Ready condition
    for condition in conditions:
        if condition.get("type") == "Ready" and condition.get("status") == "True":
            return "Ready"

    # Fallback: check deploymentStatus.phase for older CRD versions
    deployment_status = status.get("deploymentStatus", {})
    phase = deployment_status.get("phase", "")
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


@router.get("", response_model=AgentListResponse)
async def list_agents(
    namespace: str = Query(default="default", description="Kubernetes namespace"),
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> AgentListResponse:
    """
    List all agents in the specified namespace.

    Returns agents that have the kagenti.io/type=agent label.
    """
    try:
        label_selector = f"{KAGENTI_TYPE_LABEL}={RESOURCE_TYPE_AGENT}"

        items = kube.list_custom_resources(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=namespace,
            plural=AGENTS_PLURAL,
            label_selector=label_selector,
        )

        agents = []
        for item in items:
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})

            agents.append(
                AgentSummary(
                    name=metadata.get("name", ""),
                    namespace=metadata.get("namespace", namespace),
                    description=spec.get("description", "No description"),
                    status=_is_deployment_ready(item),
                    labels=_extract_labels(metadata.get("labels", {})),
                    createdAt=metadata.get("creationTimestamp"),
                )
            )

        return AgentListResponse(items=agents)

    except ApiException as e:
        if e.status == 404:
            raise HTTPException(
                status_code=404,
                detail="Agent CRD not found. Is the operator installed?",
            )
        if e.status == 403:
            raise HTTPException(
                status_code=403,
                detail="Permission denied. Check RBAC configuration.",
            )
        raise HTTPException(status_code=e.status, detail=str(e.reason))


@router.get("/{namespace}/{name}")
async def get_agent(
    namespace: str,
    name: str,
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> Any:
    """Get detailed information about a specific agent."""
    try:
        agent = kube.get_custom_resource(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=namespace,
            plural=AGENTS_PLURAL,
            name=name,
        )
        return agent

    except ApiException as e:
        if e.status == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{name}' not found in namespace '{namespace}'",
            )
        raise HTTPException(status_code=e.status, detail=str(e.reason))


@router.delete("/{namespace}/{name}", response_model=DeleteResponse)
async def delete_agent(
    namespace: str,
    name: str,
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> DeleteResponse:
    """Delete an agent from the cluster."""
    try:
        kube.delete_custom_resource(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=namespace,
            plural=AGENTS_PLURAL,
            name=name,
        )
        return DeleteResponse(success=True, message=f"Agent '{name}' deleted")

    except ApiException as e:
        if e.status == 404:
            return DeleteResponse(success=True, message=f"Agent '{name}' already deleted")
        raise HTTPException(status_code=e.status, detail=str(e.reason))


@router.get("/{namespace}/{name}/build", response_model=BuildStatusResponse)
async def get_agent_build_status(
    namespace: str,
    name: str,
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> BuildStatusResponse:
    """Get the build status for an agent.

    Returns the AgentBuild resource status including conditions,
    phase, and image information.
    """
    try:
        build = kube.get_custom_resource(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=namespace,
            plural=AGENTBUILDS_PLURAL,
            name=name,
        )

        metadata = build.get("metadata", {})
        status = build.get("status", {})
        spec = build.get("spec", {})

        # Extract conditions
        conditions = []
        for cond in status.get("conditions", []):
            conditions.append(
                BuildStatusCondition(
                    type=cond.get("type", ""),
                    status=cond.get("status", ""),
                    reason=cond.get("reason"),
                    message=cond.get("message"),
                    lastTransitionTime=cond.get("lastTransitionTime"),
                )
            )

        # Determine phase from conditions or status
        phase = "Unknown"
        for cond in conditions:
            if cond.type == "Ready":
                if cond.status == "True":
                    phase = "Completed"
                elif cond.reason:
                    phase = cond.reason
                break
            if cond.type == "Building" and cond.status == "True":
                phase = "Building"

        # Get image info from spec.buildOutput
        build_output = spec.get("buildOutput", {})
        image = build_output.get("image")
        image_tag = build_output.get("imageTag")

        return BuildStatusResponse(
            name=metadata.get("name", name),
            namespace=metadata.get("namespace", namespace),
            phase=phase,
            conditions=conditions,
            image=image,
            imageTag=image_tag,
            startTime=status.get("startTime"),
            completionTime=status.get("completionTime"),
        )

    except ApiException as e:
        if e.status == 404:
            raise HTTPException(
                status_code=404,
                detail=f"AgentBuild '{name}' not found in namespace '{namespace}'",
            )
        raise HTTPException(status_code=e.status, detail=str(e.reason))


def _strip_protocol(url: str) -> str:
    """Remove protocol prefix from URL."""
    if url.startswith("https://"):
        return url[8:]
    if url.startswith("http://"):
        return url[7:]
    return url


def _build_agent_build_manifest(request: CreateAgentRequest) -> dict:
    """
    Build an AgentBuild CRD manifest for building from source.

    Uses the Tekton pipeline to build the agent from git.
    """
    cleaned_url = _strip_protocol(request.gitUrl) if request.gitUrl else ""
    registry_url = request.registryUrl or "registry.cr-system.svc.cluster.local:5000"
    start_command = request.startCommand or "python main.py"

    manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "AgentBuild",
        "metadata": {
            "name": request.name,
            "namespace": request.namespace,
            "labels": {
                APP_KUBERNETES_IO_CREATED_BY: KAGENTI_UI_CREATOR_LABEL,
                APP_KUBERNETES_IO_NAME: KAGENTI_OPERATOR_LABEL_NAME,
                KAGENTI_TYPE_LABEL: RESOURCE_TYPE_AGENT,
                KAGENTI_PROTOCOL_LABEL: request.protocol,
                KAGENTI_FRAMEWORK_LABEL: request.framework,
            },
        },
        "spec": {
            "model": "dev",
            "source": {
                "sourceRepository": cleaned_url,
                "sourceRevision": request.gitBranch,
                "sourceSubfolder": request.gitPath,
                "sourceCredentials": {"name": GIT_USER_SECRET_NAME},
            },
            "pipeline": {
                "namespace": OPERATOR_NS,
                "parameters": [
                    {"name": "SOURCE_REPO_SECRET", "value": GIT_USER_SECRET_NAME},
                    {"name": "START_COMMAND", "value": start_command},
                    {"name": "PYTHON_VERSION", "value": PYTHON_VERSION},
                ],
            },
            "buildOutput": {
                "image": request.name,
                "imageTag": request.imageTag,
                "imageRegistry": registry_url,
            },
        },
    }

    # Add registry credentials if using external registry
    if request.registrySecret:
        manifest["spec"]["buildOutput"]["imageRepoCredentials"] = {"name": request.registrySecret}

    return manifest


def _build_agent_manifest(
    request: CreateAgentRequest, build_ref_name: Optional[str] = None
) -> dict:
    """
    Build an Agent CRD manifest.

    If build_ref_name is provided, creates an Agent with imageSource.buildRef
    referencing the AgentBuild. Otherwise, creates an Agent with direct image URL.
    """
    # Build environment variables
    env_vars = list(DEFAULT_ENV_VARS)
    if request.envVars:
        for ev in request.envVars:
            env_vars.append({"name": ev.name, "value": ev.value})

    # Build service ports
    if request.servicePorts:
        service_ports = [
            {
                "name": sp.name,
                "port": sp.port,
                "targetPort": sp.targetPort,
                "protocol": sp.protocol,
            }
            for sp in request.servicePorts
        ]
    else:
        service_ports = [
            {
                "name": "http",
                "port": DEFAULT_IN_CLUSTER_PORT,
                "targetPort": DEFAULT_IN_CLUSTER_PORT,
                "protocol": "TCP",
            }
        ]

    manifest = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "Agent",
        "metadata": {
            "name": request.name,
            "namespace": request.namespace,
            "labels": {
                APP_KUBERNETES_IO_CREATED_BY: KAGENTI_UI_CREATOR_LABEL,
                APP_KUBERNETES_IO_NAME: KAGENTI_OPERATOR_LABEL_NAME,
                KAGENTI_TYPE_LABEL: RESOURCE_TYPE_AGENT,
                KAGENTI_PROTOCOL_LABEL: request.protocol,
                KAGENTI_FRAMEWORK_LABEL: request.framework,
            },
        },
        "spec": {
            "description": f"Agent '{request.name}' deployed from UI.",
            "replicas": 1,
            "podTemplateSpec": {
                "spec": {
                    "containers": [
                        {
                            "name": "agent",
                            "imagePullPolicy": DEFAULT_IMAGE_POLICY,
                            "resources": {
                                "limits": DEFAULT_RESOURCE_LIMITS,
                                "requests": DEFAULT_RESOURCE_REQUESTS,
                            },
                            "env": env_vars,
                            "ports": [
                                {
                                    "name": "http",
                                    "containerPort": DEFAULT_IN_CLUSTER_PORT,
                                    "protocol": "TCP",
                                },
                            ],
                            "volumeMounts": [
                                {"name": "cache", "mountPath": "/app/.cache"},
                                {"name": "marvin", "mountPath": "/.marvin"},
                                {"name": "shared-data", "mountPath": "/shared"},
                            ],
                        }
                    ],
                    "volumes": [
                        {"name": "cache", "emptyDir": {}},
                        {"name": "marvin", "emptyDir": {}},
                        {"name": "shared-data", "emptyDir": {}},
                    ],
                },
            },
        },
    }

    # Set imageSource based on deployment method
    if build_ref_name:
        # Reference the AgentBuild - operator will fill in the image after build completes
        manifest["spec"]["imageSource"] = {
            "buildRef": {
                "name": build_ref_name,
            }
        }
    else:
        # Direct image deployment
        image_url = request.containerImage or ""
        manifest["spec"]["imageSource"] = {
            "image": image_url,
        }
        # Set image on container for direct deployment
        manifest["spec"]["podTemplateSpec"]["spec"]["containers"][0]["image"] = image_url

    # Add image pull secrets if specified
    if request.imagePullSecret:
        manifest["spec"]["podTemplateSpec"]["spec"]["imagePullSecrets"] = [
            {"name": request.imagePullSecret}
        ]

    return manifest


@router.post("", response_model=CreateAgentResponse)
async def create_agent(
    request: CreateAgentRequest,
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> CreateAgentResponse:
    """
    Create a new agent.

    Supports two deployment methods:
    - 'source': Build from git repository using AgentBuild CRD + Agent CRD with buildRef
    - 'image': Deploy from existing container image using Agent CRD
    """
    try:
        if request.deploymentMethod == "image":
            # Deploy from existing container image using Agent CRD
            if not request.containerImage:
                raise HTTPException(
                    status_code=400,
                    detail="containerImage is required for image deployment",
                )

            agent_manifest = _build_agent_manifest(request)
            kube.create_custom_resource(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=request.namespace,
                plural=AGENTS_PLURAL,
                body=agent_manifest,
            )
            message = f"Agent '{request.name}' deployment started."

        else:
            # Build from source: create both AgentBuild and Agent CRs
            if not request.gitUrl or not request.gitPath:
                raise HTTPException(
                    status_code=400,
                    detail="gitUrl and gitPath are required for source deployment",
                )

            # Step 1: Create AgentBuild CR (triggers Tekton pipeline)
            agentbuild_manifest = _build_agent_build_manifest(request)
            kube.create_custom_resource(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=request.namespace,
                plural=AGENTBUILDS_PLURAL,
                body=agentbuild_manifest,
            )
            logger.info(f"Created AgentBuild '{request.name}' in namespace '{request.namespace}'")

            # Step 2: Create Agent CR with buildRef pointing to the AgentBuild
            # The operator will watch the AgentBuild and deploy once it completes
            agent_manifest = _build_agent_manifest(request, build_ref_name=request.name)
            kube.create_custom_resource(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=request.namespace,
                plural=AGENTS_PLURAL,
                body=agent_manifest,
            )
            logger.info(
                f"Created Agent '{request.name}' with buildRef in namespace '{request.namespace}'"
            )

            message = f"Agent '{request.name}' build started. The agent will be deployed automatically once the build completes."

        return CreateAgentResponse(
            success=True,
            name=request.name,
            namespace=request.namespace,
            message=message,
        )

    except ApiException as e:
        if e.status == 409:
            raise HTTPException(
                status_code=409,
                detail=f"Agent '{request.name}' already exists in namespace '{request.namespace}'",
            )
        if e.status == 404:
            raise HTTPException(
                status_code=404,
                detail="Agent CRD not found. Is the kagenti-operator installed?",
            )
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(status_code=e.status, detail=str(e.reason))
