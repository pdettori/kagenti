# Cloud Native Proof-Of-Concepts

The following proof on concepts apply Cloud Native technologies to manage agentic workloads.
A diagram and description of the demo architecture is provided [here](./tech-details.md#cloud-native-agent-platform-demo)

## Installation

### Prerequisites

Before running the demo setup script, ensure you have the following prerequisites in place:

* **Python:** Python versionn >=3.9
* **uv** [uv](https://docs.astral.sh/uv/getting-started/installation) must be installed (e.g. `pip install uv`)
* **Docker:** Docker Desktop, Rancher Desktop or Podman Machine.
* **Kind:** A [tool](https://kind.sigs.k8s.io) to run a Kubernetes cluster in docker.
* **kubectl:** The Kubernetes command-line tool.
* **GitHub Token:** Your [GitHub token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic) to allow fetching source and then to push docker image to ghcr.io repository. Make sure to grant: `repo(all), read/write packages`.
* **OpenAI API Key:** The [OpenAI API Key](https://platform.openai.com/api-keys) for accessing A2A agents. Select `read only`.
* **[ollama](https://ollama.com/download)** to run LLMs locally.

At this time the demo has only been tested on MacOS with M1 processor.

When you encounter any problems, review our [Troubleshooting](#troubleshooting) section.

#### Setup

Clone this project:

```shell
git clone https://github.com/kagenti/kagenti.git
cd kagenti
```

Setup your env variables as follow:

```shell
cp kagenti/installer/src/.env_template kagenti/installer/src/.env
```

Edit the file `kagenti/installer/src/.env` to fill in the following:

```shell
GITHUB_USER=<Your public Github User ID>
GITHUB_TOKEN=<Your GitHub Token, as explained above>
OPENAI_API_KEY=<This is required only for A2A agents, if only using the ACP agents can just put a placeholder>
AGENT_NAMESPACES=<comma separated list of namespaces to setup for agents deployment e.g., `team1,team2`>
```

Run the installer.

```shell
cd kagenti/installer
uv run kagenti-installer
```

The installer creates a kind cluster for the agent platform and then deploys all platform components.

## Run the demo

Open the Agent Platform Demo Dashboard:

```shell
open http://kagenti-ui.localtest.me:8080
```

You can import agents written in any framework and wrapped with a2a or acp from github repos, test the agents
and monitor traces and network traffic. You may also import mcp server from source and deploys them on the platform.

## Troubleshooting

### Agent stops responding through gateway

Restart the following daemonset

```shell
kubectl rollout restart daemonset -n istio-system  ztunnel
```

### Using Podman instead of Docker

The install script expects `docker` to be in your runtime path.

A few problem fixes might include:

* create `/usr/local/bin/docker` link to podman:

  ```console
   sudo ln -s /opt/podman/bin/podman /usr/local/bin/docker
   ```

* install `docker-credential-helper`:

   ```console
   brew install docker-credential-helper
   ```
