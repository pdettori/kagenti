# CLAUDE.md - Kagenti Organization Guide

This document provides context for AI assistants working across the Kagenti organization repositories.

## Organization Overview

**Kagenti** is a cloud-native middleware platform for deploying and orchestrating AI agents. The project provides a framework-neutral, scalable, and secure infrastructure for running agents built with any framework through standardized protocols (A2A, MCP).

**Website**: [kagenti.io](http://kagenti.io)  
**GitHub Organization**: [github.com/kagenti](https://github.com/kagenti)  
**Discord**: [Kagenti Discord](https://discord.gg/kagenti)

## Repository Structure

The Kagenti organization consists of the following repositories:

| Repository | Language | Description |
|------------|----------|-------------|
| **[kagenti](https://github.com/kagenti/kagenti)** | Python | Main installer, UI dashboard, and documentation |
| **[kagenti-operator](https://github.com/kagenti/kagenti-operator)** | Go | Kubernetes operator for agent/tool lifecycle management |
| **[mcp-gateway](https://github.com/kagenti/mcp-gateway)** | Go | Envoy-based MCP Gateway for tool federation |
| **[agent-examples](https://github.com/kagenti/agent-examples)** | Python | Sample agents and tools for the platform |
| **[kagenti-extensions](https://github.com/kagenti/kagenti-extensions)** | Go | Extensions and plugins |
| **[agentic-control-plane](https://github.com/kagenti/agentic-control-plane)** | Python | Control plane of specialized A2A agents |
| **[plugins-adapter](https://github.com/kagenti/plugins-adapter)** | Python | Guardrails configuration for MCP Gateway |
| **[.github](https://github.com/kagenti/.github)** | HTML | Project website (Hugo-based) |

---

## Repository Details

### 1. kagenti (Main Repository)

**Purpose**: Primary entry point containing the installer, web UI, and documentation.

**Key Components**:
```
kagenti/
├── kagenti/
│   ├── ui/                    # Streamlit dashboard
│   │   ├── Home.py            # Entry point
│   │   ├── pages/             # Multi-page app (Agents, Tools, Admin, etc.)
│   │   └── lib/               # Utilities (kube.py, a2a_utils.py, mcp_client.py)
│   ├── installer/             # CLI installer (Typer-based)
│   │   ├── app/cli.py         # CLI entry point
│   │   └── app/components/    # Component installers (istio, keycloak, spire...)
│   ├── auth/                  # OAuth secret generation utilities
│   ├── tests/e2e/             # End-to-end tests
│   └── examples/              # Example configurations
├── charts/                    # Helm charts (kagenti, kagenti-deps)
├── deployments/
│   ├── ansible/               # Ansible playbooks
│   └── envs/                  # Environment-specific values
└── docs/                      # Documentation
```

**Commands**:
```bash
# Run installer
cd kagenti/installer
uv run kagenti-installer

# Run UI locally
cd kagenti/ui
uv run streamlit run Home.py

# Lint
make lint
```

---

### 2. kagenti-operator

**Purpose**: Kubernetes operator managing agent/tool deployment and lifecycle.

**Contains Two Operators**:

#### Platform Operator (`platform-operator/`)
Manages complex multi-component applications through:
- **Component CR**: Individual deployable units (Agent, Tool, Infrastructure)
- **Platform CR**: Orchestration layer managing collections of Components

#### Kagenti Operator (`kagenti-operator/`)
Legacy operator with:
- **Agent CR**: Agent deployment and lifecycle
- **AgentBuild CR**: Build orchestration via Tekton

**Key Files**:
```
kagenti-operator/
├── platform-operator/
│   ├── api/v1alpha1/
│   │   ├── component_types.go    # Component CRD definition
│   │   └── platform_types.go     # Platform CRD definition
│   ├── internal/
│   │   ├── controller/           # Reconciliation logic
│   │   ├── deployer/             # Deployment strategies (K8s, Helm, OLM)
│   │   ├── builder/              # Tekton pipeline management
│   │   └── webhook/              # Admission webhooks
│   └── config/
│       ├── crd/bases/            # CRD YAML definitions
│       ├── samples/              # Example CRs
│       └── tekton/               # Build pipeline templates
├── kagenti-operator/
│   ├── api/v1alpha1/
│   │   ├── agent_types.go
│   │   └── agentbuild_types.go
│   └── internal/controller/
└── charts/                       # Helm charts for both operators
```

**CRDs**:
```yaml
# Component (platform-operator)
apiVersion: kagenti.operator.dev/v1alpha1
kind: Component
spec:
  agent: {}     # or tool: {} or infra: {}
  deployer:
    kubernetes:
      imageSpec: {}      # Deploy from image
      manifest: {}       # Deploy from URL/GitHub manifest
      podTemplateSpec: {} # Full pod control
    helm: {}             # Deploy via Helm chart

# Platform (platform-operator)
apiVersion: kagenti.operator.dev/v1alpha1
kind: Platform
spec:
  globalConfig:
    namespace: kagenti-system
    labels: {}
    annotations: {}
  infrastructure: []
  tools: []
  agents: []
```

**Commands**:
```bash
cd platform-operator

# Build and deploy locally
make ko-local-build
make install-local-chart

# Run tests
make test

# Clean up
./scripts/cleanup.sh
```

---

### 3. mcp-gateway

**Purpose**: Envoy-based gateway for Model Context Protocol (MCP) tool federation.

**Features**:
- Automatic MCP server discovery and registration
- Request routing to appropriate tools
- OAuth/token-based authentication
- Load balancing across tool replicas

**Architecture**:
```
mcp-gateway/
├── cmd/                    # Entry points
├── internal/
│   ├── gateway/            # Core gateway logic
│   ├── broker/             # MCP broker/router
│   └── controller/         # MCPServer CR controller
├── api/v1alpha1/           # CRD definitions
└── charts/                 # Helm charts
```

**CRD**:
```yaml
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

---

### 4. agent-examples

**Purpose**: Reference implementations of agents and MCP tools.

**Structure**:
```
agent-examples/
├── a2a/                    # A2A Protocol Agents
│   ├── weather_service/    # LangGraph weather agent
│   ├── currency_converter/ # LangGraph currency agent
│   ├── contact_extractor/  # Marvin extraction agent
│   ├── slack_researcher/   # AutoGen slack assistant
│   ├── file_organizer/     # File organization agent
│   └── generic_agent/      # Template agent
└── mcp/                    # MCP Tools
    ├── weather_tool/       # Weather MCP server
    ├── slack_tool/         # Slack MCP server
    ├── github_tool/        # GitHub MCP server
    ├── movie_tool/         # Movie database tool
    └── cloud_storage_tool/ # Cloud storage tool
```

**Agent Structure** (typical):
```
agent_name/
├── agent.py            # Main agent logic
├── server.py           # A2A/HTTP server wrapper
├── requirements.txt    # Dependencies
├── Dockerfile          # Container build
└── agent.yaml          # Kubernetes deployment
```

---

### 5. agentic-control-plane

**Purpose**: Kubernetes control plane composed of specialized A2A agents coordinated through Kagenti CRDs.

**Concept**: Uses AI agents themselves to manage and orchestrate the platform, creating a self-managing system.

---

### 6. kagenti-extensions

**Purpose**: Extensions and plugins for the Kagenti platform.

**Examples**:
- Custom deployers
- Additional protocol adapters
- Integration plugins

---

### 7. plugins-adapter

**Purpose**: Configuration and invocation of guardrails for the Envoy-based MCP Gateway.

**Features**:
- Request/response filtering
- Content moderation
- Rate limiting
- Custom policy enforcement

---

## Supported Protocols

### A2A (Agent-to-Agent)
- Google's standard for agent communication
- Agent discovery via Agent Cards (`/.well-known/agent.json`)
- JSON-RPC based task execution
- Python SDK: `a2a-sdk`

**Endpoints**:
```
GET  /.well-known/agent.json    # Agent Card discovery
POST /                          # Send task/message
GET  /tasks/{id}                # Get task status
```

### MCP (Model Context Protocol)
- Anthropic's protocol for tool integration
- Tool discovery and invocation
- Transport: `streamable-http` or `sse`
- Python SDK: `mcp`

**Endpoints**:
```
POST /mcp                       # JSON-RPC messages
GET  /sse                       # Server-sent events (legacy)
```

---

## Key Technologies

| Technology | Purpose | Namespace |
|------------|---------|-----------|
| **Istio Ambient** | Service mesh (mTLS, traffic mgmt) | `istio-system` |
| **SPIRE/SPIFFE** | Workload identity | `zero-trust-workload-identity-manager` |
| **Keycloak** | OAuth/OIDC identity provider | `keycloak` |
| **Tekton** | CI/CD pipelines | `tekton-pipelines` |
| **Kubernetes Gateway API** | Ingress routing | `kagenti-system` |
| **Phoenix** | LLM observability/tracing | `kagenti-system` |
| **Kiali** | Service mesh visualization | `kagenti-system` |
| **Envoy** | MCP Gateway proxy | `gateway-system` |

---

## Development Setup

### Prerequisites
- Python ≥3.11 (UI), ≥3.9 (installer)
- Go ≥1.21 (operators, gateway)
- Docker/Podman
- Kind, kubectl, Helm
- uv (Python package manager)

### Quick Start
```bash
# Clone main repo
git clone https://github.com/kagenti/kagenti.git
cd kagenti

# Configure
cp kagenti/installer/app/.env_template kagenti/installer/app/.env
# Edit .env with GITHUB_USER, GITHUB_TOKEN

# Install platform
cd kagenti/installer
uv run kagenti-installer
```

### Access URLs (Kind)
| Service | URL |
|---------|-----|
| Kagenti UI | `http://kagenti-ui.localtest.me:8080` |
| Keycloak | `http://keycloak.localtest.me:8080` |
| Phoenix | `http://phoenix.localtest.me:8080` |
| Kiali | `http://kiali.localtest.me:8080` |
| MCP Inspector | `http://mcp-inspector.localtest.me:8080` |

Default credentials: `admin` / `admin`

---

## Kubernetes Namespaces

| Namespace | Purpose |
|-----------|---------|
| `kagenti-system` | Platform components (UI, operator, ingress) |
| `gateway-system` | MCP Gateway (Envoy proxy) |
| `mcp-system` | MCP broker/controller |
| `keycloak` | Keycloak server |
| `tekton-pipelines` | Tekton pipeline runtime |
| `zero-trust-workload-identity-manager` | SPIRE/SPIFFE |
| `istio-system` | Istio control plane |
| `team1`, `team2`, ... | Agent deployment namespaces |

---

## Common Labels

```yaml
# Component type
kagenti.io/type: agent | tool

# Protocol
kagenti.io/protocol: a2a | mcp | streamable_http | sse

# Framework
kagenti.io/framework: LangGraph | CrewAI | AG2 | Python

# Enable namespace for agents
kagenti-enabled: "true"

# Created by
app.kubernetes.io/created-by: kagenti-operator | streamlit-ui
```

---

## Code Style & Conventions

### Python
- Package manager: `uv`
- Linter: `pylint`
- Python ≥3.9 minimum
- Type hints required
- Apache 2.0 license headers

### Go
- Go modules
- Standard Go formatting (`gofmt`)
- Kubebuilder patterns for operators
- Apache 2.0 license headers

### Git Workflow
```bash
# Fork and clone
git clone https://github.com/<your-username>/kagenti.git
git remote add upstream https://github.com/kagenti/kagenti.git

# Create branch
git checkout -b feature/my-feature

# Rebase before PR
git fetch upstream
git rebase upstream/main

# Commit with sign-off
git commit -s -m "feat: add new feature"
```

### Pre-commit Hooks
```bash
pre-commit install
pre-commit run --all-files
```

---

## Testing

### End-to-End Tests (kagenti)
```bash
cd kagenti/tests
uv run pytest e2e/ -v
```

### Operator Tests (kagenti-operator)
```bash
cd platform-operator
make test
make test-e2e
```

### Gateway Tests (mcp-gateway)
```bash
make test
make e2e
```

---

## Debugging

### Check Operator Logs
```bash
kubectl logs -n kagenti-system -l app=kagenti-operator -f
kubectl logs -n kagenti-system -l app=platform-operator -f
```

### Check Component Status
```bash
kubectl get components -A
kubectl describe component <name> -n <namespace>
```

### Check Platform Status
```bash
kubectl get platforms -A
kubectl describe platform <name> -n <namespace>
```

### View Tekton Builds
```bash
kubectl get pipelineruns -A
kubectl logs -n <namespace> <pipelinerun-pod>
```

### Traces
Access Phoenix dashboard at `http://phoenix.localtest.me:8080`

### Service Mesh
Access Kiali dashboard at `http://kiali.localtest.me:8080`

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Kubernetes Cluster                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      kagenti-system Namespace                     │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │  │
│  │  │ Kagenti UI │  │  Platform  │  │  Ingress   │  │   Kiali    │  │  │
│  │  │ (Streamlit)│  │  Operator  │  │  Gateway   │  │  Phoenix   │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌────────────────────┐  ┌────────────────────┐  ┌─────────────────┐   │
│  │  gateway-system    │  │     mcp-system     │  │    keycloak     │   │
│  │  ┌──────────────┐  │  │  ┌──────────────┐  │  │  ┌───────────┐  │   │
│  │  │ MCP Gateway  │  │  │  │ MCP Broker   │  │  │  │ Keycloak  │  │   │
│  │  │   (Envoy)    │  │  │  │ Controller   │  │  │  │  Server   │  │   │
│  │  └──────────────┘  │  │  └──────────────┘  │  │  └───────────┘  │   │
│  └────────────────────┘  └────────────────────┘  └─────────────────┘   │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Agent Namespaces (team1, team2, ...)           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │ │
│  │  │  A2A Agents  │  │  MCP Tools   │  │   Istio Ambient Mesh     │ │ │
│  │  │  (LangGraph, │  │  (weather,   │  │  ┌────────┐ ┌─────────┐  │ │ │
│  │  │   CrewAI,    │  │   slack,     │  │  │Ztunnel │ │Waypoint │  │ │ │
│  │  │   AG2...)    │  │   github...) │  │  └────────┘ └─────────┘  │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              zero-trust-workload-identity-manager                  │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────┐ │ │
│  │  │  SPIRE Server  │  │  SPIRE Agent   │  │  SPIFFE CSI Driver   │ │ │
│  │  └────────────────┘  └────────────────┘  └──────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## License

All Kagenti repositories are licensed under **Apache 2.0**.

---

## Contributing

See [CONTRIBUTING.md](https://github.com/kagenti/kagenti/blob/main/CONTRIBUTING.md) for guidelines.

Key points:
- Fork the repository
- Create feature branches
- Sign off commits (`git commit -s`)
- Follow conventional commits (recommended)
- Run pre-commit hooks
- Submit PR with clear description

