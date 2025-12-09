
# Kagenti

[![License](https://img.shields.io/github/license/kagenti/kagenti)](LICENSE)
![Contributors](https://img.shields.io/github/contributors/kagenti/kagenti)
![Issues](https://img.shields.io/github/issues/kagenti/kagenti)
![Pull Requests](https://img.shields.io/github/issues-pr/kagenti/kagenti)

**Kagenti** is a Cloud-native middleware providing a *framework-neutral*, *scalable* and *secure* platform for deploying and orchestrating AI agents through a standardized REST API.

| Included Services: |  |
|--------------------|--------|
| - Authentication and Authorization<br>- Trusted identity<br>- Deployment<br>- Configuration<br>- Scaling<br>- Fault-tolerance<br>- Checkpointing<br>- Discovery of agents and tools<br>- Persistences | <img src="banner.png" width="400"/> |

## Core Components

| Component | Description |
|-----------|-------------|
| **[Platform Operator](https://github.com/kagenti/kagenti-operator)** | Kubernetes operator for building agents from source, managing lifecycle, and coordinating platform services |
| **[MCP Gateway](./docs/gateway.md)** | Unified gateway for Model Context Protocol (MCP) servers and tools |
| **[Kagenti UI](./kagenti/ui/)** | Dashboard for deploying agents/tools, interactive testing, and monitoring |
| **[Identity & Auth](./docs/demo-identity.md)** | SPIRE-based workload identity with Keycloak integration for secure token exchange |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  Kagenti UI  │  │ MCP Gateway  │  │   Platform Operator      │   │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │
│         │                 │                       │                 │
│  ┌──────▼─────────────────▼───────────────────────▼──────────────┐  │
│  │                    Ingress Gateway                            │  │
│  │              (Kubernetes Gateway API + Istio)                 │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────▼───────────────────────────────────┐  │
│  │                    Agent Namespaces                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │  │
│  │  │ A2A Agents  │  │ MCP Tools   │  │ Custom Workloads    │    │  │
│  │  │ (LangGraph, │  │ (weather,   │  │                     │    │  │
│  │  │  CrewAI...) │  │  slack...)  │  │                     │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐     │
│  │     SPIRE      │  │    Keycloak    │  │  Istio Ambient     │     │
│  │  (Identity)    │  │    (Auth)      │  │  (Service Mesh)    │     │
│  └────────────────┘  └────────────────┘  └────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python ≥3.9 with [uv](https://docs.astral.sh/uv/getting-started/installation) installed
- Docker Desktop, Rancher Desktop, or Podman (16GB RAM, 4 cores recommended)
- [Kind](https://kind.sigs.k8s.io), [kubectl](https://kubernetes.io/docs/tasks/tools/), [Helm](https://helm.sh/docs/intro/install/)
- [Ollama](https://ollama.com/download) for local LLM inference

### Install

```bash
# Clone the repository
git clone https://github.com/kagenti/kagenti.git
cd kagenti

# Configure environment
cp kagenti/installer/app/.env_template kagenti/installer/app/.env
# Edit .env with your GITHUB_USER, GITHUB_TOKEN, and optionally OPENAI_API_KEY

# Run the installer
cd kagenti/installer
uv run kagenti-installer
```

The installer creates a Kind cluster and deploys all platform components. Use `--help` for options.

### Access the UI

```bash
open http://kagenti-ui.localtest.me:8080
# Login: admin / admin
```

From the UI you can:
- Import and deploy A2A agents from any framework
- Deploy MCP tools directly from source
- Test agents interactively
- Monitor traces and network traffic

## Documentation

| Topic | Link |
|-------|------|
| **Installation** | [Installation Guide](./docs/install.md) (Kind & OpenShift) |
| **Components** | [Component Details](./docs/components.md) |
| **Demos & Tutorials** | [Demo Documentation](./docs/demos.md) |
| **Import Your Own Agent** | [New Agent Guide](./docs/new-agent.md) |
| **Architecture Details** | [Technical Details](./docs/tech-details.md) |
| **Identity & Security** | [Identity Demo](./docs/demo-identity.md) |
| **Developer Guide** | [Contributing](./docs/dev-guide.md) |
| **Troubleshooting** | [Troubleshooting Guide](./docs/troubleshooting.md) |
| **Blog Posts** | [Kagenti Blog](./docs/blogs.md) |

## Supported Protocols

- **[A2A (Agent-to-Agent)](https://google.github.io/A2A)** — Standard protocol for agent communication
- **[MCP (Model Context Protocol)](https://modelcontextprotocol.io)** — Protocol for tool/server integration

## Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

[Apache 2.0](./LICENSE)
