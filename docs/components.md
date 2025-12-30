# Kagenti Components

This document provides detailed information about each component of the Kagenti platform.

## Table of Contents

- [Overview](#overview)
- [Architecture Diagram](#architecture-diagram)
- [Agent Lifecycle Operator](#agent-lifecycle-operator)
- [MCP Gateway](#mcp-gateway)
- [Kagenti UI](#kagenti-ui)
- [Identity & Auth Bridge](#identity--auth-bridge)
- [Infrastructure Services](#infrastructure-services)
- [Supported Agent Frameworks](#supported-agent-frameworks)
- [Communication Protocols](#communication-protocols)

---

## Overview

Kagenti is a cloud-native middleware providing a **framework-neutral**, **scalable**, and **secure** platform for deploying and orchestrating AI agents through a standardized REST API. It addresses the gap between agent development frameworks and production deployment by providing:

- **Authentication and Authorization** — Secure access control for agents and tools
- **Trusted Identity** — SPIRE-managed workload identities
- **Deployment & Configuration** — Kubernetes-native lifecycle management
- **Scaling & Fault-tolerance** — Auto-scaling and resilient deployments
- **Discovery** — Agent and tool discovery via A2A protocol
- **Persistence** — State management for agent workflows

### Value Proposition

Despite the extensive variety of frameworks available for developing agent-based applications, there is a distinct lack of standardized methods for deploying and operating agent code in production environments, as well as for exposing it through a standardized API. Agents are adept at reasoning, planning, and interacting with various tools, but their full potential can be limited by deployment challenges.

Kagenti addresses this gap by enhancing existing agent frameworks with production-ready infrastructure.

---

## Architecture Diagram

All the Kagenti components and their deployment namespaces

```shell
┌───────────────────────────────────────────────────────────────────────┐
│                           Kubernetes Cluster                          │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                      kagenti-system Namespace                   │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │  │
│  │  │ Kagenti UI │  │  Agent     │  │  Ingress   │  │   Kiali    │ │  │
│  │  │            │  │  Lifecycle │  │  Gateway   │  │            │ │  │
│  │  │            │  │  Operator  │  │            │  │            │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                Workload Namespaces (team1, team2, ...)           │ │
│  │     ┌──────────────┐  ┌──────────────┐   ┌──────────────┐        │ │
│  │     │  A2A Agents  │  │  MCP Tools   │   │ Custom       │        │ │
│  │     │  (LangGraph, │  │  (weather,   │   │ Workloads    │        │ │
│  │     │   CrewAI,    │  │   slack,     │   │              │        │ │
│  │     │   AG2...)    │  │   fetch...)  │   │              │        │ │
│  │     └──────────────┘  └──────────────┘   └──────────────┘        │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│           ┌────────────────────┐  ┌────────────────────┐              |
│           │  gateway-system    │  │     mcp-system     │              │
│           │  ┌──────────────┐  │  │  ┌──────────────┐  │              │
│           │  │ MCP Gateway  │  │  │  │ MCP Broker   │  │              │
│           │  │   (Envoy)    │  │  │  │ Controller   │  │              │
│           │  └──────────────┘  │  │  └──────────────┘  │              │
│           └────────────────────┘  └────────────────────┘              │
│                                                                       │
│    ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐     │
│    │     SPIRE      │  │       IAM      │  │  Istio Ambient     │     │
│    │  (Identity)    │  │(e.g. Keycloak) |  │  (Service Mesh)    │     │
│    └────────────────┘  └────────────────┘  └────────────────────┘     │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Agent Lifecycle Operator

**Repository**: [kagenti/kagenti-operator](https://github.com/kagenti/kagenti-operator)

The Kubernetes Platform Operator facilitates the deployment and configuration of agents along with infrastructure dependencies on Kubernetes. It enables scaling and updating configurations seamlessly.

### Capabilities

| Feature | Description |
|---------|-------------|
| **Agent Deployment** | Deploy agents from source code or container images |
| **Build Automation** | Build agent containers using Tekton pipelines |
| **Lifecycle Management** | Handle agent updates, rollbacks, and scaling |
| **Configuration Management** | Manage environment variables, secrets, and config maps |
| **Multi-Namespace Support** | Deploy agents to isolated team namespaces |

### Custom Resources

The operator manages several Custom Resource Definitions (CRDs):

```yaml
# Agent - Defines an agent deployment
apiVersion: agent.kagenti.dev/v1alpha1
kind: Agent
metadata:
  name: weather-service
spec:
  image: ghcr.io/kagenti/weather-service:latest
  replicas: 1
  env:
    - name: OPENAI_API_KEY
      valueFrom:
        secretKeyRef:
          name: openai-secret
          key: api-key
```

```yaml
# AgentBuild - Triggers a build from source
apiVersion: agent.kagenti.dev/v1alpha1
kind: AgentBuild
metadata:
  name: weather-service-build
spec:
  source:
    git:
      url: https://github.com/kagenti/agent-examples
      path: agents/weather-service
```

### Architecture

```
┌─────────────────────────────────────────────────────┐
│              Platform Operator                      │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   Agent     │  │ AgentBuild  │  │ AgentCard   │  │
│  │ Controller  │  │ Controller  │  │ Controller  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │
│         │                │                │         │
│         ▼                ▼                ▼         │
│  ┌─────────────────────────────────────────────┐    │
│  │            Kubernetes API Server            │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

For installation and operation help, see our [Agent Lifecycle Operator Guide](https://github.com/kagenti/kagenti-operator/blob/main/kagenti-operator/GETTING_STARTED.md).

---

## MCP Gateway

**Repository**: [kagenti/mcp-gateway](https://github.com/kagenti/mcp-gateway)

The MCP Gateway provides a unified entry point for [Model Context Protocol (MCP)](https://modelcontextprotocol.io) servers and tools. It acts as a "front door" for all MCP-based tool interactions.

### Capabilities

| Feature | Description |
|---------|-------------|
| **Tool Discovery** | Automatic discovery and registration of MCP servers |
| **Routing** | Route agent requests to appropriate MCP tools |
| **Authentication** | OAuth/token-based authentication for tool access |
| **Load Balancing** | Distribute requests across tool replicas |

### Components

| Component | Namespace | Purpose |
|-----------|-----------|---------|
| `mcp-gateway-istio` | `gateway-system` | Envoy proxy for request routing |
| `mcp-controller` | `mcp-system` | Manages MCPServer custom resources |
| `mcp-broker-router` | `mcp-system` | Routes requests to registered MCP servers |

### Registering Tools with the Gateway

Tools are registered using Kubernetes Gateway API resources:

```yaml
# HTTPRoute - Define routing to MCP server
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: weather-tool-route
  labels:
    mcp-server: "true"
spec:
  parentRefs:
  - name: mcp-gateway
    namespace: gateway-system
  hostnames:
  - "weather-tool.mcp.local"
  rules:
  - backendRefs:
    - name: weather-tool
      port: 8000
```

```yaml
# MCPServer - Register with the gateway
apiVersion: mcp.kagenti.com/v1alpha1
kind: MCPServer
metadata:
  name: weather-tool-servers
spec:
  toolPrefix: weather_
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: weather-tool-route
```

For detailed gateway configuration, see [MCP Gateway Instructions](./gateway.md).

---

## Kagenti UI

**Location**: `kagenti/ui/`

A Streamlit-based dashboard for managing agents and tools.

### Features

| Feature | Description |
|---------|-------------|
| **Agent Import** | Import A2A agents from any framework via Git URL |
| **Tool Deployment** | Deploy MCP tools directly from source |
| **Interactive Testing** | Chat interface to test agent capabilities |
| **Monitoring** | View traces, logs, and network traffic |
| **Authentication** | Keycloak-based login/logout |

### Pages

| Page | Purpose |
|------|---------|
| Home | Overview and quick actions |
| Agents | List, import, and manage agents |
| Tools | List, import, and manage MCP tools |
| Admin | Keycloak and system configuration |
| Traces | Phoenix-based observability |

### Access

```bash
# Kind cluster
open http://kagenti-ui.localtest.me:8080

# OpenShift
kubectl get route kagenti-ui -n kagenti-system -o jsonpath='{.status.ingress[0].host}'
```

---

## Identity & Auth Bridge

**Repository**: [kagenti/kagenti-extensions/AuthBridge](https://github.com/kagenti/kagenti-extensions/tree/main/AuthBridge)

Kagenti provides a unified framework for identity and authorization in agentic systems, replacing static credentials with dynamic, short-lived tokens. We call this collection of assets **Auth Bridge**.

**Auth Bridge** solves a critical challenge in microservices and agentic architectures: **how can workloads authenticate and communicate securely without pre-provisioned static credentials?**

### Auth Bridge Components

| Component | Purpose | Repository |
|-----------|---------|------------|
| **[Client Registration](https://github.com/kagenti/kagenti-extensions/tree/main/AuthBridge/client-registration)** | Automatic OAuth2/OIDC client provisioning using SPIFFE ID | `AuthBridge/client-registration` |
| **[AuthProxy](https://github.com/kagenti/kagenti-extensions/tree/main/AuthBridge/AuthProxy)** | JWT validation and transparent token exchange | `AuthBridge/AuthProxy` |
| **SPIRE** | Workload identity and attestation | External |
| **Keycloak** | Identity provider and access management | External |

### Client Registration

Automatically registers Kubernetes workloads as Keycloak clients at pod startup:

- Uses **SPIFFE ID** as client identifier (e.g., `spiffe://localtest.me/ns/team/sa/my-agent`)
- Eliminates manual client creation and secret distribution
- Writes credentials to shared volume for application use

### AuthProxy

A sidecar that validates incoming tokens and transparently exchanges them for downstream services:

```
┌─────────────────────────────────────────────────────────────────┐
│                         CALLER POD                              │
│  ┌──────────────┐    ┌─────────────────────────────────────┐    │
│  │              │    │         AuthProxy Sidecar           │    │
│  │  Application │───►│  1. Validate token (aud: authproxy) │    │
│  │              │    │  2. Exchange for target audience    │    │
│  │              │    │  3. Forward with new token          │    │
│  └──────────────┘    └─────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   TARGET SERVICE    │
                         │  (aud: auth-target) │
                         └─────────────────────┘
```

**Key Features:**
- **JWT Validation** using JWKS from Keycloak
- **OAuth 2.0 Token Exchange** ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693))
- **Transparent to applications** - handled by Envoy sidecar
- **Audience scoping** - tokens are scoped to specific services

### SPIRE (Workload Identity)

[SPIRE](https://spiffe.io/docs/latest/spire-about/) provides cryptographic workload identities using the SPIFFE standard.

| Component | Purpose |
|-----------|---------|
| **SPIRE Server** | Issues SVIDs (SPIFFE Verifiable Identity Documents) |
| **SPIRE Agent** | Node-level agent that attests workloads |
| **CSI Driver** | Mounts SVID certificates into pods |

**Identity Format**: `spiffe://<trust-domain>/ns/<namespace>/sa/<service-account>`

### Keycloak (Access Management)

[Keycloak](https://www.keycloak.org/) manages user authentication and OAuth/OIDC flows.

| Feature | Description |
|---------|-------------|
| **User Management** | Create and manage Kagenti users |
| **Client Registration** | OAuth clients for agents and UI (automated via Client Registration) |
| **Token Exchange** | Exchange tokens between audiences ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693)) |
| **SSO** | Single sign-on across Kagenti components |

### Authorization Pattern

The Agent and Tool Authorization Pattern replaces static credentials with dynamic SPIRE-managed identities, enforcing least privilege and continuous authentication:

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   User   │────▶│ Keycloak │────▶│  Agent   │────▶│   Tool   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                │                │
                      ▼                ▼                ▼
                 ┌─────────────────────────────────────────┐
                 │              SPIRE Server               │
                 │    (Issues short-lived identities)      │
                 └─────────────────────────────────────────┘
```

1. **User authenticates** with Keycloak, receives access token
2. **Agent receives** user context via delegated token
3. **Agent identity** is attested by SPIRE
4. **Tool access** uses exchanged tokens with minimal scope

### End-to-End Authorization Flow

The complete Auth Bridge flow combines all components for zero-trust authentication:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  1. SPIFFE Helper obtains SVID from SPIRE Agent                                 │
│  2. Client Registration registers workload with Keycloak (using SPIFFE ID)      │
│  3. Caller gets token from Keycloak (audience: "authproxy")                     │
│  4. Caller sends request to target with token                                   │
│  5. Envoy+GoPro AuthProxy (Go Processor) intercepts, exchanges token            │
│     (audience: "auth-target")                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Security Properties:**
- **No Static Secrets** - Credentials are dynamically generated at pod startup
- **Short-Lived Tokens** - JWT tokens expire and must be refreshed
- **Audience Scoping** - Tokens are scoped to specific audiences, preventing reuse
- **Transparent to Application** - Token exchange is handled by the sidecar

For detailed overview of Identity and Authorization Patterns, see the [Identity Guide](./identity-guide.md).

### Tornjak (SPIRE Management UI)

```bash
# API
curl http://spire-tornjak-api.localtest.me:8080/

# UI
open http://spire-tornjak-ui.localtest.me:8080/
```

---

## Infrastructure Services

### Ingress Gateway

The Ingress Gateway routes external HTTP requests to internal services using the [Kubernetes Gateway API](https://gateway-api.sigs.k8s.io).

- **Namespace**: `kagenti-system`
- **Implementation**: Istio Gateway

### Istio Ambient Mesh

[Istio Ambient](https://istio.io/latest/docs/ambient/) provides service mesh capabilities without sidecar proxies.

| Component | Purpose |
|-----------|---------|
| **Ztunnel** | Node-local proxy for mTLS and traffic interception |
| **Waypoint** | Optional L7 proxy for advanced traffic policies |

**Benefits**:

- Zero-config mTLS between services
- No sidecar resource overhead
- Transparent to applications

### Kiali (Service Mesh Observability)

[Kiali](https://kiali.io) provides visualization of the service mesh topology and traffic flows.

### Phoenix (Tracing)

LLM observability and tracing for agent interactions.

---

## Supported Agent Frameworks

Kagenti is framework-neutral and supports agents built with any framework that can be exposed via the A2A protocol:

| Framework | Description | Use Case |
|-----------|-------------|----------|
| **[LangGraph](https://github.com/langchain-ai/langgraph)** | Graph-based agent orchestration | Complex workflows with explicit control |
| **[CrewAI](https://www.crewai.com/)** | Role-based multi-agent collaboration | Autonomous goal-driven teams |
| **[AG2 (AutoGen)](https://microsoft.github.io/autogen/)** | Multi-agent conversation framework | Conversational agents |
| **[Llama Stack](https://github.com/meta-llama/llama-stack)** | Meta's agent framework | ReAct-style patterns |
| **[BeeAI](https://github.com/i-am-bee/bee-agent-framework)** | IBM's agent framework | Enterprise agents |

### Example Agents

| Agent | Framework | Description |
|-------|-----------|-------------|
| `weather-service` | LangGraph | Weather information assistant |
| `a2a-currency-converter` | LangGraph | Currency exchange rates |
| `a2a-contact-extractor` | Marvin | Extract contact info from text |
| `slack-researcher` | AutoGen | Slack research assistant |

---

## Communication Protocols

### A2A (Agent-to-Agent)

[A2A](https://google.github.io/A2A) is Google's standard protocol for agent communication.

**Features**:

- Agent discovery via Agent Cards
- Standardized task execution API
- Streaming support for long-running tasks

**Endpoints**:
```
GET  /.well-known/agent.json    # Agent Card (discovery)
POST /                          # Send message/task
GET  /tasks/{id}                # Get task status
```

### MCP (Model Context Protocol)

[MCP](https://modelcontextprotocol.io) is Anthropic's protocol for tool integration.

**Features**:

- Tool discovery and invocation
- Resource access
- Prompt templates

**Endpoints**:
```
POST /mcp    # MCP JSON-RPC messages
```

---

## Related Documentation

- [Installation Guide](./install.md)
- [Demo Documentation](./demos/README.md)
- [Technical Details](./tech-details.md)
- [Identity, Security, and Auth Bridge](./identity-guide.md)
- [MCP Gateway Instructions](./gateway.md)
- [New Agent Guide](./new-agent.md)
