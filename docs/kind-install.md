# Installation

For installing on OpenShift, please refer to [these installation instructions](./ocp/openshift-install.md).

**Note: OpenShift support is currently a work in progress. Be sure to review the limitations detailed in the instructions.**

## Prerequisites

Before running the demo setup script, ensure you have the following prerequisites in place:

- **Python:** Python version >=3.9
- **uv:** [uv](https://docs.astral.sh/uv/getting-started/installation) must be installed (e.g. `pip install uv`)
- **Docker:** Docker Desktop, Rancher Desktop or Podman Machine. You must alias it to `docker` (e.g. `sudo ln -s /opt/homebrew/bin/podman /usr/local/bin/docker`). On MacOS, you will need also to do `brew install docker-credential-helper`. *Not required if using `--use-existing-cluster`*.
  - On Rancher or Podman Desktop, configure VM size to at least 12 GB of memory and 4 cores
  - On Podman Desktop, make sure you use a machine with [rootful connection](https://podman-desktop.io/docs/podman/setting-podman-machine-default-connection)
  - Make sure to increase your resource limits (for [rancher](https://docs.rancherdesktop.io/how-to-guides/increasing-open-file-limit/), for podman you may need to edit inside the machine the file `/etc/security/limits.conf` and restart the machine)
- **Kind:** A [tool](https://kind.sigs.k8s.io) to run a Kubernetes cluster in docker (e.g. `brew install kind`). *Not required if using `--use-existing-cluster`*.
- **kubectl:** The Kubernetes command-line tool (installs with **kind**).
- **Helm:** A package manager for Kubernetes (e.g. `brew install helm`).
- **[ollama](https://ollama.com/download)** to run LLMs locally (e.g. `brew install ollama`). Then start the **ollama* service in the background (e.g.`ollama serve`).
- **GitHub Token:** Your [GitHub token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic) to allow fetching source and then to push docker image to ghcr.io repository. Make sure to grant: `repo(all), read/write packages`. Make sure to choose the "classic" token instead of the "fine-grained" token.
- **OpenAI API Key:** The [OpenAI API Key](https://platform.openai.com/api-keys) for accessing A2A agents. Select `read only`.

At this time the demo has only been tested on MacOS and RHEL.

When you encounter any problems, review our [Troubleshooting](#troubleshooting) section.

### Setup

Clone this project:

```shell
git clone https://github.com/kagenti/kagenti.git
cd kagenti
```

Setup your env variables:

```shell
cp kagenti/installer/app/.env_template kagenti/installer/app/.env
```

Edit the file `kagenti/installer/app/.env` to fill in the following:

```shell
GITHUB_USER=<Your public Github User ID>
GITHUB_TOKEN=<Your GitHub Token, as explained above>
OPENAI_API_KEY=<This is required only for A2A agents using OpenAI. Not needed when using ollama>
AGENT_NAMESPACES=<comma separated list of Kubernetes namespaces to set up in Kind for agents deployment e.g., `team1,team2`>
SLACK_BOT_TOKEN=<This is required only if you wish to use the Slack tool example.>
```

Run the installer. Use the `--help` flag to see all available options.

```shell
cd kagenti/installer
uv run kagenti-installer
```

The installer creates a kind cluster named `agent-platform` and then deploys all platform components.

Using `--silent` flag removes the interactive install mode.

```shell
uv run kagenti-installer --silent
```

### New Ansible-based installer

The new installer relies mainly on helm charts and is 
going to replace `kagenti-installer`. 

1. Copy example secrets file: `deployments/envs/secret_values.yaml.example` to `deployments/envs/.secret_values.yaml` and fill in the values in that file.

2. Run the installer as:

```bash
deployments/ansible/run-install.sh --env dev
```

Check [here](../deployments/ansible/README.md) for more details on the new installer. 

To override existing environments, you may create a [customized override file](../deployments/ansible/README.md#using-override-files).


## Using an Existing Kubernetes Cluster

If you already have a Kubernetes cluster configured and want to skip the kind cluster creation, you can use the `--use-existing-cluster` flag:

```shell
uv run kagenti-installer --use-existing-cluster
```

This option will:
- Skip the kind and Docker dependency checks
- Use the cluster defined in your `KUBECONFIG` environment variable
- Skip kind-specific operations like image preloading
- Deploy all platform components to your existing cluster

Make sure your `KUBECONFIG` is properly set and points to a cluster where you have admin privileges before using this option. (Use `kubectl config get-contexts` and `use-context`)

**Note:** When using an existing cluster, the registry component is automatically skipped as it's primarily designed for kind clusters that have been initialized with a specific configuration.

To skip installation of the specific component e.g. keycloak and SPIRE, issue:

```shell
uv run kagenti-installer --skip-install keycloak --skip-install spire --skip-install mcp_gateway
```

# Connect to the Kagenti UI

Open the Kagenti UI in your browser:

```shell
open http://kagenti-ui.localtest.me:8080
```

You will be required to login using Kagenti userid.

*Important: Please note that Kagenti user is managed by Keycloak, so if you have Keycloak session open in another tab of your browser, Kagenti will be using the same Keycloak userid. To change the user, logout on Keycloak session first.*

## Default Kagenti Userid

Login with the default Kagenti userid:

```console
userid: admin
password: admin
```

From the UI, you can:

- Login and Logout with the Kagenti user id managed by Keycloak
- Import agents written in any framework, wrapped with the A2A protocol.
- Import and deploy MCP Server tools directly from source.
- Test agents interactively and inspect their behavior.
- Monitor traces, logs, and network traffic between agents and tools.

## Troubleshooting

If you run into issues with the install, see [our troubleshooting doc](./troubleshooting.md). 