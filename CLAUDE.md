# CLAUDE.md - Kagenti Repository Guide

This document provides context for AI assistants working with the Kagenti codebase.

## Project Overview

**Kagenti** is a cloud-native middleware platform for deploying and orchestrating AI agents. It provides a framework-neutral, scalable, and secure infrastructure for running agents built with any framework (LangGraph, CrewAI, AG2, etc.) through standardized protocols.

**Key Value Proposition**: Bridges the gap between agent development frameworks and production deployment by providing authentication, authorization, trusted identity, scaling, fault-tolerance, and discovery services.

## Repository Structure

```
kagenti/
├── kagenti/                    # Main Python package
│   ├── ui/                     # Streamlit dashboard (see kagenti/ui/README.md)
│   ├── installer/              # CLI installer tool
│   │   ├── app/
│   │   │   ├── cli.py          # Typer CLI entry point
│   │   │   ├── cluster.py      # Kind cluster management
│   │   │   ├── components/     # Component installers (istio, keycloak, spire, etc.)
│   │   │   └── resources/      # Kubernetes YAML manifests
│   │   └── pyproject.toml
│   ├── auth/                   # Authentication utilities
│   │   ├── agent-oauth-secret/ # Agent OAuth secret generation
│   │   ├── ui-oauth-secret/    # UI OAuth secret generation
│   │   └── client-registration/# Keycloak client registration
│   ├── tests/                  # E2E and integration tests
│   │   └── e2e/                # End-to-end test suite
│   └── examples/               # Example agents and tools
├── charts/                     # Helm charts
│   ├── kagenti/                # Main platform chart (umbrella)
│   ├── kagenti-deps/           # Dependencies chart (gateway-api, etc.)
│   └── gateway-api/            # Gateway API CRDs
├── deployments/
│   ├── ansible/                # Ansible playbooks for deployment
│   │   ├── installer-playbook.yml
│   │   └── roles/kagenti_installer/
│   ├── envs/                   # Environment-specific values files
│   │   ├── dev_values.yaml
│   │   ├── ocp_values.yaml
│   │   └── secret_values.yaml.example
│   └── ui/                     # UI deployment manifests
├── docs/                       # Documentation
│   ├── install.md              # Installation guide
│   ├── components.md           # Component details
│   ├── tech-details.md         # Architecture and design
│   ├── demos/                   # Demo documentation
│   │   └── README.md           # Demo index
│   └── diagrams/               # Mermaid diagrams
├── Makefile                    # Build automation
├── pyproject.toml              # Root Python project config
└── README.md                   # Main documentation
```

## Core Components

### 1. Kagenti UI (`kagenti/ui/`)
- **Technology**: Streamlit multi-page app
- **Purpose**: Web dashboard for managing agents/tools
- **Entry Point**: `Home.py`
- **Pages**: Agent Catalog, Tool Catalog, Observability, Import Agent/Tool, Admin
- **Key Files**:
  - `lib/kube.py` - Kubernetes API integration
  - `lib/a2a_utils.py` - A2A protocol client
  - `lib/mcp_client.py` - MCP protocol client
  - `lib/constants.py` - Configuration constants

### 2. Installer (`kagenti/installer/`)
- **Technology**: Python CLI with Typer
- **Purpose**: Deploy Kagenti platform to Kind/Kubernetes
- **Entry Point (deprecated)**: `uv run kagenti-installer` — use the Ansible-based installer `deployments/ansible/run-install.sh` (recommended)
- **Key Components** (in `app/components/`):
  - `istio.py` - Istio Ambient mesh
  - `keycloak.py` - Identity management
  - `spire.py` - SPIRE/SPIFFE workload identity
  - `operator.py` - Kagenti platform operator
  - `mcp_gateway.py` - MCP Gateway deployment
  - `ui.py` - UI deployment

### 3. Platform Operator (external repo)
- **Repository**: `github.com/kagenti/kagenti-operator`
- **Purpose**: Kubernetes operator for agent lifecycle management
- **CRDs**: `Agent`, `Component`, `AgentBuild`
- **Namespace**: `kagenti-system`

### 4. MCP Gateway (external repo)
- **Repository**: `github.com/kagenti/mcp-gateway`
- **Purpose**: Unified gateway for MCP tools
- **Namespace**: `gateway-system`, `mcp-system`

## Supported Protocols

### A2A (Agent-to-Agent)
- Google's standard for agent communication
- Agent discovery via Agent Cards (`/.well-known/agent.json`)
- Task execution via JSON-RPC
- SDK: `a2a-sdk` package

### MCP (Model Context Protocol)
- Anthropic's protocol for tool integration
- Tool discovery and invocation
- Transport: `streamable-http` or `sse`
- SDK: `mcp` package

## Key Technologies

| Technology | Purpose | Namespace |
|------------|---------|-----------|
| **Istio Ambient** | Service mesh (mTLS, traffic management) | `istio-system` |
| **SPIRE** | Workload identity (SPIFFE) | `zero-trust-workload-identity-manager` |
| **Keycloak** | OAuth/OIDC identity provider | `keycloak` |
| **Tekton** | CI/CD pipelines for agent builds | `tekton-pipelines` |
| **Kubernetes Gateway API** | Ingress routing | `kagenti-system` |
| **Phoenix** | LLM observability/tracing | `kagenti-system` |
| **Kiali** | Service mesh visualization | `kagenti-system` |

## Development Commands

### Running the UI Locally
```bash
cd kagenti/ui
uv sync
uv run streamlit run Home.py
# Access at http://localhost:8501
```

```bash
# From repository root
cp deployments/envs/secret_values.yaml.example deployments/envs/.secret_values.yaml
# Edit deployments/envs/.secret_values.yaml with your values
deployments/ansible/run-install.sh --env dev
```

Legacy (deprecated):

```bash
cd kagenti/installer
cp app/.env_template app/.env
# Edit .env with GITHUB_USER, GITHUB_TOKEN
# Deprecated: legacy uv-based installer
uv run kagenti-installer
uv run kagenti-installer --help  # View options
```

### Linting
```bash
make lint  # Runs pylint on UI code
```

### Running Tests
```bash
# E2E tests (requires running cluster)
cd kagenti/tests
uv run pytest e2e/ -v
```

### Building UI for Kind
```bash
cd kagenti/ui
./scripts/ui-dev-build.sh
```

## Kubernetes Resources

### Custom Resource Definitions (CRDs)

```yaml
# Agent/Tool deployment via Component CRD
apiVersion: kagenti.operator.dev/v1alpha1
kind: Component
metadata:
  name: weather-service
  namespace: team1
  labels:
    kagenti.io/type: agent  # or "tool"
    kagenti.io/protocol: a2a  # or "mcp"
spec:
  source:
    git:
      url: https://github.com/kagenti/agent-examples
      path: a2a/weather_service
  image:
    tag: v0.0.1
```

### Important Labels
- `kagenti.io/type`: `agent` or `tool`
- `kagenti.io/protocol`: `a2a`, `mcp`, `streamable_http`, `sse`
- `kagenti.io/framework`: `LangGraph`, `CrewAI`, `Python`, etc.
- `kagenti-enabled: "true"`: Marks namespace for agent deployment

### Namespaces
- `kagenti-system`: Platform components (UI, operator, ingress)
- `gateway-system`: MCP Gateway (Envoy proxy)
- `mcp-system`: MCP broker/controller
- `keycloak`: Keycloak server
- `team1`, `team2`, etc.: Agent deployment namespaces

## Environment Variables

### UI Configuration
| Variable | Description |
|----------|-------------|
| `ENABLE_AUTH` | Enable OAuth2 authentication |
| `CLIENT_ID`, `CLIENT_SECRET` | OAuth2 credentials |
| `AUTH_ENDPOINT`, `TOKEN_ENDPOINT` | Keycloak endpoints |
| `DOMAIN_NAME` | Domain for service URLs (default: `localtest.me`) |
| `TRACES_DASHBOARD_URL` | Phoenix dashboard URL |
| `NETWORK_TRAFFIC_DASHBOARD_URL` | Kiali dashboard URL |

### Agent/Tool Environment
| Variable | Description |
|----------|-------------|
| `PORT` | Service port (default: 8000) |
| `HOST` | Bind address (default: 0.0.0.0) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector |
| `KEYCLOAK_URL` | Keycloak server URL |

## Access URLs (Kind Cluster)

| Service | URL |
|---------|-----|
| Kagenti UI | `http://kagenti-ui.localtest.me:8080` |
| Keycloak | `http://keycloak.localtest.me:8080` |
| Phoenix Traces | `http://phoenix.localtest.me:8080` |
| Kiali | `http://kiali.localtest.me:8080` |
| MCP Inspector | `http://mcp-inspector.localtest.me:8080` |
| SPIRE Tornjak | `http://spire-tornjak-ui.localtest.me:8080` |

Default credentials: `admin` / `admin`

## Code Style and Conventions

### Python
- Python ≥3.11 for UI, ≥3.9 for installer
- Package manager: `uv`
- Linter: `pylint`
- Use type hints
- Apache 2.0 license headers required

### Pre-commit Hooks
```bash
pre-commit install
pre-commit run --all-files
```

### Commit Messages
- Sign-off required (`git commit -s`)
- Follow [Conventional Commits](https://www.conventionalcommits.org/) (recommended)

## Testing Agents

### Via UI
1. Navigate to Agent Catalog
2. Select an agent
3. Use the chat interface to send tasks

### Via CLI (A2A)
```bash
# Get agent card
curl http://weather-service.localtest.me:8080/.well-known/agent.json

# Send task
curl -X POST http://weather-service.localtest.me:8080/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tasks/send", "params": {...}}'
```

### Via MCP Inspector
Access `http://mcp-inspector.localtest.me:8080` to browse and test MCP tools through the gateway.

## Common Tasks

### Adding a New Agent
1. Create agent code following A2A protocol
2. Use UI "Import New Agent" or apply Component CRD
3. Agent builds automatically via Tekton pipeline
4. Access via HTTPRoute at `<agent-name>.localtest.me:8080`

### Adding a New MCP Tool
1. Create MCP server following MCP protocol
2. Use UI "Import New Tool" or apply Component CRD
3. Tool registers with MCP Gateway automatically
4. Access via MCP Gateway or direct HTTPRoute

### Debugging
- Check pod logs: `kubectl logs -n <namespace> <pod-name>`
- Check operator logs: `kubectl logs -n kagenti-system -l app=kagenti-operator`
- View traces: Phoenix dashboard
- View network: Kiali dashboard

## Related Repositories

| Repository | Description |
|------------|-------------|
| [kagenti/kagenti-operator](https://github.com/kagenti/kagenti-operator) | Kubernetes operator (Go) |
| [kagenti/mcp-gateway](https://github.com/kagenti/mcp-gateway) | MCP Gateway (Go) |
| [kagenti/agent-examples](https://github.com/kagenti/agent-examples) | Example agents and tools |

## License

Apache 2.0 - See [LICENSE](./LICENSE)
