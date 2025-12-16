# Kagenti UI

A Streamlit-based dashboard for managing, deploying, and monitoring AI agents and tools on the Kagenti Cloud Native Agent Platform.

## Overview

The Kagenti UI provides a web-based interface for:

- **Agent Catalog**: Browse, interact with, and manage deployed A2A (Agent-to-Agent) agents
- **Tool Catalog**: Discover and manage MCP (Model Context Protocol) tools available to agents
- **Import New Agent**: Build and deploy agents directly from source repositories
- **Import New Tool**: Integrate and deploy new MCP tools from source
- **Observability**: Access dashboards for traces (Phoenix/OpenTelemetry), network traffic (Kiali/Istio), and MCP Inspector
- **Administration**: Manage identity and authorization via Keycloak console

## Features

- 🔐 **OAuth2 Authentication** - Secure login with Keycloak integration
- 🚀 **One-Click Deployment** - Import agents/tools directly from Git repositories
- 🔍 **Interactive Testing** - Test agents with A2A protocol directly from the UI
- 📊 **Observability Integration** - Links to Phoenix traces, Kiali service mesh, and MCP Inspector
- ☸️ **Kubernetes Native** - Full integration with Kubernetes CRDs and APIs

## Project Structure

```
ui/
├── Home.py                  # Main entry point and home page
├── pages/
│   ├── 01_Agent_Catalog.py  # Browse and manage A2A agents
│   ├── 02_Tool_Catalog.py   # Browse and manage MCP tools
│   ├── 03_Observability.py  # Links to monitoring dashboards
│   ├── 04_Import_New_Agent.py  # Deploy agents from source
│   ├── 05_Import_New_Tool.py   # Deploy tools from source
│   └── 06_Admin.py          # Administration and identity management
├── lib/
│   ├── a2a_utils.py         # A2A protocol utilities
│   ├── agent_details_page.py # Agent details rendering
│   ├── build_utils.py       # Import form utilities
│   ├── common_ui.py         # Shared UI components
│   ├── constants.py         # Configuration constants
│   ├── kube.py              # Kubernetes API integration
│   ├── logging_config.py    # Logging configuration
│   ├── mcp_client.py        # MCP client utilities
│   ├── tool_details_page.py # Tool details rendering
│   └── utils.py             # General utilities
├── tests/                   # Unit and integration tests
├── scripts/                 # Development build scripts
├── Dockerfile               # Container image definition
├── pyproject.toml           # Python project configuration
└── uv.lock                  # Dependency lock file
```

## Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/getting-started/installation) package manager
- Access to a Kubernetes cluster with Kagenti platform installed
- Valid kubeconfig or in-cluster deployment

## Installation

### Local Development

```bash
# Navigate to the UI directory
cd kagenti/ui

# Install dependencies
uv sync

# Run the Streamlit app
uv run streamlit run Home.py
```

The UI will be available at `http://localhost:8501`.

### Docker Build

```bash
# Build the Docker image
docker build -t kagenti-ui:latest .

# Run the container
docker run -p 8501:8501 kagenti-ui:latest
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_AUTH` | Enable OAuth2 authentication | `false` |
| `CLIENT_ID` | OAuth2 client ID | `kagenti` |
| `CLIENT_SECRET` | OAuth2 client secret | *required if auth enabled* |
| `AUTH_ENDPOINT` | OAuth2 authorization endpoint | *required if auth enabled* |
| `TOKEN_ENDPOINT` | OAuth2 token endpoint | *required if auth enabled* |
| `REDIRECT_URI` | OAuth2 redirect URI | *required if auth enabled* |
| `SCOPE` | OAuth2 scopes | `openid profile email` |
| `DOMAIN_NAME` | Domain name for service URLs | `localtest.me` |
| `TRACES_DASHBOARD_URL` | Phoenix traces dashboard URL | `http://phoenix.{DOMAIN_NAME}:8080` |
| `NETWORK_TRAFFIC_DASHBOARD_URL` | Kiali dashboard URL | `http://kiali.{DOMAIN_NAME}:8080` |
| `MCP_INSPECTOR_URL` | MCP Inspector URL | `http://mcp-inspector.{DOMAIN_NAME}:8080` |
| `KEYCLOAK_CONSOLE_URL` | Keycloak admin console URL | `http://keycloak.{DOMAIN_NAME}:8080/admin/master/console/` |

## Development

### Running Tests

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/
```

### Building for Kind Cluster

Use the provided development build script:

```bash
./scripts/ui-dev-build.sh
```

This script:
1. Builds a Docker image with a timestamped tag
2. Loads the image into the Kind cluster
3. Updates the deployment
4. Waits for rollout completion

### Code Style

The project uses `pylint` for linting:

```bash
uv run pylint lib/ pages/ Home.py
```

## Dependencies

Key dependencies (see `pyproject.toml` for full list):

- **streamlit** - Web UI framework
- **streamlit-oauth** - OAuth2 authentication component
- **kubernetes** - Kubernetes Python client
- **a2a-sdk** - Agent-to-Agent protocol SDK
- **mcp** - Model Context Protocol client
- **python-keycloak** - Keycloak integration
- **pyjwt** - JWT token handling

## Integration with Kagenti Platform

The UI integrates with the following Kagenti platform components:

- **Kagenti Operator**: Manages agent/tool lifecycle through Kubernetes CRDs
- **MCP Gateway**: Provides unified access to MCP tools
- **Keycloak**: Identity and access management
- **SPIRE**: Workload identity
- **Istio**: Service mesh and network traffic management
- **Phoenix**: OpenTelemetry-based tracing

## Accessing the UI

When deployed on the Kagenti platform:

```bash
open http://kagenti-ui.localtest.me:8080
```

Default credentials (when auth is enabled):
- **Username**: admin
- **Password**: admin

## Environment Variable Precedence

When creating Agent or Tool resources from the UI, environment variables can come from three sources:

- **Environment variable sets** (from the `environments` ConfigMap)
- **.env file imports** (imported from a repository `.env` file)
- **Custom environment variables** added manually in the UI

Precedence when names collide (highest → lowest):

1. Custom environment variables (user-added) — highest precedence, override any conflicting entries
2. `.env` file imports — override entries from environment variable sets
3. Environment variable sets (ConfigMap) — lowest precedence

This precedence is achieved by relying on Kubernetes' "last-wins" behavior when duplicate environment variable names are present in the manifest (see `lib/build_utils.py`). The UI does not explicitly deduplicate or enforce precedence; instead, the order of environment variables in the generated CustomResource ensures that higher-precedence values override lower-precedence ones at deployment time.

## License

Copyright 2025 IBM Corp.

Licensed under the Apache License, Version 2.0. See [LICENSE](../../LICENSE) for details.

