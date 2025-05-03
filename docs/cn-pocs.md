# Cloud Native Proof-Of-Concepts

The following proof on concepts apply Cloud Native technologies to manage agentic workloads.

## Installation

This section shows how to install teh kagenti operator.

### Prerequisites

Before installing the `kagenti-operator`, ensure you have the following prerequisites in place:

* **Kubernetes Cluster:** A working Kubernetes Kind cluster.
* **kubectl:** The Kubernetes command-line tool.
* **Agent Source:** Your agent source code in GitHub repository including working Dockerfile.
* **GitHub Token:** Your [GitHub token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic) to allow fetching source and then to push docker image to ghcr.io repository. 
* **Install [ollama]:**(https://ollama.com/download)


####  Setup

Clone this project:

```shell
git clone https://github.com/kagenti/kagenti.git
cd kagenti
```

Create kind cluster and install the Kagenti operator:

```shell
curl -sSL https://raw.githubusercontent.com/kagenti/kagenti-operator/main/beeai/scripts/install.sh | bash
```

Create a k8s secret for GitHub which will be used for acceess to
your private repos (if any) and for pushing images to `ghcr.io`

```shell
TOKEN="your-github-token"
kubectl create secret generic github-token-secret --from-literal=token="${TOKEN}"
```

## Build and Deploy an ACP agent

The example ACP agent uses ollama, so there is no need to have external LLM providers.
Fron the root of the kagenti project, run the command (where `<some-user>` is your github user name)

Start ollama on a new terminal:

```shell
ollama run llama3.2:1b-instruct-fp16 --keepalive 60m
```

```shell
REPO_USER=<your-github-user-name>
sed  "s|\${REPO_USER}|${REPO_USER}|g" examples/templates/acp/acp-ollama-researcher.yaml | kubectl apply -f -
```

## Build and Deploy A2A agents

The examples here use Open AI API for LLM, so you need to [get a key](https://platform.openai.com/api-keys) to run these examples.

Create a secret with your key:

```shell
OPENAI_API_KEY="your-key"
kubectl create secret generic openai-secret --from-literal=apikey="${OPENAI_API_KEY}"
```


build and deploy the a2a langgraph currency agent:

```shell
REPO_USER=<your-github-user-name>
sed  "s|\${REPO_USER}|${REPO_USER}|g" examples/templates/a2a/a2a-currency-agent.yaml | kubectl apply -f -
```

build and deploy the a2a langgraph contact-extractor-agent:

```shell
sed  "s|\${REPO_USER}|${REPO_USER}|g" examples/templates/a2a/a2a-contact-extractor-agent.yaml | kubectl apply -f -
```


