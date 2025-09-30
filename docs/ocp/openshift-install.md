# Kagenti Installation on OpenShift

**This document is work in progress - main focus is to define the steps that are required on OpenShift that need to be automated in the installer**


## Current limitations 

These limitations will be addressed in successive PRs.

- UI Auth and token management is disabled
- Only [quay.io](https://quay.io) registry has been tested in build from source
- Istio Ambient and network observability has not been tested and is not enabled by default
- URLs for Kiali, Phoenix and Keycloak are not working in UI
- Ollama models not tested - OpenAI key required for now
- MCP inspector integration in tools details page is not enabled yet
- MCP Gateway integration has not been tested yet

## Requirements 

- helm >= v3.18.0
- kubectl >= v1.32.1 or oc >= 4.16.0
- git >= 2.48.0
- Access to OpenShift cluster with admin authority (We tested with OpenShift 4.18.21)

## Setup

Clone this project:

```shell
git clone https://github.com/kagenti/kagenti.git
cd kagenti
```

Setup your helm secrets file:

```shell
cp charts/kagenti/.secrets_template.yaml charts/kagenti/.secrets.yaml
```

Edit the file `charts/kagenti/.secrets.yaml` to fill in the following:

```yaml
githubUser: # Your public Github User ID
githubToken: # Your personal GitHub Token
openaiApiKey: # Required as Ollama not yet available
slackBotToken: # not required until auth is enabled and slack demo agent is used
adminSlackBotToken: # not required until auth is enabled and slack demo agent is used
```

## Install the helm chart

Make sure your `kubectl` or `oc` points to your OpenShift cluster. You may edit
`charts/kagenti/values.yaml` to define the namespaces to enable for agents and tools
deployment (under `agentNamespaces:`) and enable or disable components to install
under `components:`.

Finally, install the chart with the command:

```shell
helm upgrade --install kagenti ./charts/kagenti/ -n kagenti-system --create-namespace -f ./charts/kagenti/.secrets.yaml 
```

## Access the UI

After the chart installs, you may access the UI following the instructions in the notes; the URL to UI can be found 
running this command:

```shell
echo https://$(kubectl get route kagenti-ui -n kagenti-system -o jsonpath='{.status.ingress[0].host}')
```

## Running the demo

At this time, only the OpenAI API-backed agents have been tested (`a2a-content-extractor` and `a2a-currency-converter`).
You may use the pre-built images available at https://github.com/orgs/kagenti/packages?repo_name=agent-examples
or build from source. Building from source has been tested only with `quay.io`, and requires setting up a robot account on [quay.io](https://quay.io), creating empty repos in your organization for the repos to build (e.g.`a2a-contact-extractor` and `a2a-currency-converter`) and granting the robot account write access to those repos.

Finally, you may get the Kubernetes secret from the robot account you created, and apply the secret to the namespaces
you enabled for agents and tools (e.g. `team1` and `team2`). 

You should now be able to use the UI to:

- Import an agent
- List the agent
- Interact with the agent from the agent details page
- Import a MCP tool 
- List the tool 
- Interact with the tool from the tool details page






