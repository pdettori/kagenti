# Kagenti Installation Guide

This guide covers installation on both local Kind clusters and OpenShift environments.

**Important:** The Ansible-based Helm installer (deployments/ansible/run-install.sh) is the recommended and default installer for Kagenti. The legacy `kagenti-installer` (uv-based Kind installer) is deprecated and will be removed in a future release. See [kagenti/installer/DEPRECATION.md](../kagenti/installer/DEPRECATION.md) for migration notes and timelines.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Kind Installation (Local Development)](#kind-installation-local-development)
- [OpenShift Installation](#openshift-installation)
- [Accessing the UI](#accessing-the-ui)
- [Verifying the Installation](#verifying-the-installation)

---

## Prerequisites

### Common Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| Python | ≥3.9 | Running the installer |
| [uv](https://docs.astral.sh/uv/getting-started/installation) | Latest | Python package manager |
| kubectl | ≥1.32.1 | Kubernetes CLI |
| [Helm](https://helm.sh/docs/intro/install/) | ≥3.18.0 | Package manager for Kubernetes |
| git | ≥2.48.0 | Cloning repositories |

### Kind-Specific Requirements

| Tool | Purpose |
|------|---------|
| Docker Desktop / Rancher Desktop / Podman | Container runtime (16GB RAM, 4 cores recommended) |
| [Kind](https://kind.sigs.k8s.io) | Local Kubernetes cluster |
| [Ollama](https://ollama.com/download) | Local LLM inference |
| [GitHub Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic) | Image registry access (scopes: `repo(all)`, `read/write packages`) |

### OpenShift-Specific Requirements

| Tool | Purpose |
|------|---------|
| oc | ≥4.16.0 (OpenShift CLI) |
| OpenShift cluster | Admin access required (tested with OpenShift 4.19) |

---

## Kind Installation (Local Development)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/kagenti/kagenti.git
cd kagenti

# Configure environment
cp kagenti/installer/app/.env_template kagenti/installer/app/.env
```

Edit `kagenti/installer/app/.env`:

```bash
GITHUB_USER=<Your GitHub username>
GITHUB_TOKEN=<Your GitHub token>
OPENAI_API_KEY=<Optional: for OpenAI-based agents>
AGENT_NAMESPACES=<Optional: comma-separated namespaces, e.g., team1,team2>
SLACK_BOT_TOKEN=<Optional: for Slack tool integration>
```

Run the installer (recommended: Ansible-based):

```bash
# From repository root
cp deployments/envs/secret_values.yaml.example deployments/envs/.secret_values.yaml
# Edit deployments/envs/.secret_values.yaml with your values
deployments/ansible/run-install.sh --env dev
```

The Ansible-based installer will create a Kind cluster (when appropriate) and deploy platform components.

Legacy (deprecated):

```bash
cd kagenti/installer
# Deprecated: uv-based installer
uv run kagenti-installer
```

If the legacy installer fails due to an `exceeded its progress deadline` issue, you can try logging in and re-running the legacy installer (deprecated):

```shell
docker login -u <username>
uv run kagenti-installer --preload-images --skip-install registry --skip-install tekton
```
Prefer the Ansible installer for repeatable runs; see `deployments/ansible/README.md` for troubleshooting and image preloading guidance.

### Installation Options

```bash
# Using the legacy uv-based installer (deprecated):
# Silent mode (non-interactive)
uv run kagenti-installer --silent

# Use existing cluster (skip Kind creation)
uv run kagenti-installer --use-existing-cluster

# Skip specific components
uv run kagenti-installer --skip-install keycloak --skip-install spire --skip-install mcp_gateway

# Show all options
uv run kagenti-installer --help

# Recommended: use the Ansible installer and its options. See deployments/ansible/README.md
```

### Using an Existing Kubernetes Cluster

If you have an existing cluster:

```bash
# Legacy (deprecated):
uv run kagenti-installer --use-existing-cluster
```

This will:
- Skip Kind and Docker dependency checks
- Use the cluster from your `KUBECONFIG`
- Skip kind-specific operations (image preloading)
- Deploy all platform components

Ensure `KUBECONFIG` points to a cluster with admin privileges.

**Note:** When using an existing cluster, the registry component is automatically skipped as it's primarily designed for kind clusters that have been initialized with a specific configuration.

To skip installation of the specific component e.g. keycloak and SPIRE, issue:

```shell
# Legacy (deprecated):
uv run kagenti-installer --skip-install keycloak --skip-install spire --skip-install mcp_gateway
```

### Ansible-Based Installer (Alternative)

A newer Helm-based installer using Ansible:

```bash
# Copy and configure secrets
cp deployments/envs/secret_values.yaml.example deployments/envs/.secret_values.yaml
# Edit .secret_values.yaml with your values

# Run installer
deployments/ansible/run-install.sh --env dev
```

See [Ansible README](../deployments/ansible/README.md) for details and [override files](../deployments/ansible/README.md#using-override-files).

For Rancher Desktop on macOS, follow [these setup steps](../deployments/ansible/README.md#installation-using-rancher-desktop-on-macos).

**Advanced users:** you may invoke the Ansible playbook directly instead of using the `run-install.sh` wrapper. This can be useful if you prefer to run `ansible-playbook` from a specific Python environment or CI runner. Example:

```bash
ansible-playbook -i localhost, -c local deployments/ansible/installer-playbook.yml \
  -e '{"global_value_files":["../envs/dev_values.yaml"], "secret_values_file": "../envs/.secret_values.yaml"}'
```

Note: The wrapper provides convenience features (path resolution for env/secret files, a `uv`-based venv runner, and a Helm v4 compatibility check). When running Ansible directly, ensure `helm` is v3.x since Helm v4 is incompatible with the Ansible Helm integration used by the playbook.

---

## OpenShift Installation

> **Note**: OpenShift support is work in progress. Current limitations:
> - Only [quay.io](https://quay.io) registry tested for build-from-source
> - Ollama models not tested — OpenAI key required

### Pre-Installation Steps

#### 1. Remove Cert Manager (if installed)

Kagenti installs its own Cert Manager. Remove any existing installation:

```bash
# Check if cert-manager exists
kubectl get all -n cert-manager-operator
kubectl get all -n cert-manager
```

If present, uninstall via OpenShift Console:
1. Go to **Operators > Installed Operators**
2. Find **cert-manager Operator for Red Hat OpenShift**
3. Click **⋮** → **Uninstall Operator**

Then clean up:

```bash
kubectl delete deploy cert-manager cert-manager-cainjector cert-manager-webhook -n cert-manager
kubectl delete service cert-manager cert-manager-cainjector cert-manager-webhook -n cert-manager
kubectl delete ns cert-manager-operator cert-manager
```

#### 2. Configure OVN for Istio Ambient Mode

Check your network type:

```bash
kubectl describe network.config/cluster
```

If using `OVNKubernetes`, enable local gateway mode:

```bash
kubectl patch network.operator.openshift.io cluster --type=merge \
  -p '{"spec":{"defaultNetwork":{"ovnKubernetesConfig":{"gatewayConfig":{"routingViaHost":true}}}}}'
```

#### 3. Set Trust Domain

```bash
export DOMAIN=apps.$(kubectl get dns cluster -o jsonpath='{ .spec.baseDomain }')
```

### Option A: Install from OCI Charts (Recommended)

```bash
# Get latest version
LATEST_TAG=$(git ls-remote --tags --sort="v:refname" https://github.com/kagenti/kagenti.git | tail -n1 | sed 's|.*refs/tags/v||; s/\^{}//')

# Prepare secrets
# Download .secrets_template.yaml from https://github.com/kagenti/kagenti/blob/main/charts/kagenti/.secrets_template.yaml
# Save as .secrets.yaml and fill in required values

# Install dependencies
helm install --create-namespace -n kagenti-system kagenti-deps \
  oci://ghcr.io/kagenti/kagenti/kagenti-deps \
  --version $LATEST_TAG \
  --set spire.trustDomain=${DOMAIN}

# Install MCP Gateway
LATEST_GATEWAY_TAG=$(skopeo list-tags docker://ghcr.io/kagenti/charts/mcp-gateway | jq -r '.Tags[-1]')
helm install mcp-gateway oci://ghcr.io/kagenti/charts/mcp-gateway \
  --create-namespace --namespace mcp-system \
  --version $LATEST_GATEWAY_TAG

# Install Kagenti (with OpenShift CA workaround)
helm upgrade --install --create-namespace -n kagenti-system \
  -f .secrets.yaml kagenti oci://ghcr.io/kagenti/kagenti/kagenti \
  --version $LATEST_TAG \
  --set agentOAuthSecret.spiffePrefix=spiffe://${DOMAIN}/sa \
  --set uiOAuthSecret.useServiceAccountCA=false \
  --set agentOAuthSecret.useServiceAccountCA=false
```

### Option B: Install from Repository

```bash
# Clone repository
git clone https://github.com/kagenti/kagenti.git
cd kagenti

# Prepare secrets
cp charts/kagenti/.secrets_template.yaml charts/kagenti/.secrets.yaml
# Edit .secrets.yaml with your values

# Update chart dependencies
helm dependency update ./charts/kagenti-deps/
helm dependency update ./charts/kagenti/

# Install dependencies
helm install kagenti-deps ./charts/kagenti-deps/ \
  -n kagenti-system --create-namespace \
  --set spire.trustDomain=${DOMAIN} --wait

# Install MCP Gateway
helm install mcp-gateway oci://ghcr.io/kagenti/charts/mcp-gateway \
  --create-namespace --namespace mcp-system --version 0.4.0

# Get latest UI tag
LATEST_TAG=$(git ls-remote --tags --sort="v:refname" https://github.com/kagenti/kagenti.git | tail -n1 | sed 's|.*refs/tags/||; s/\^{}//')

# Install Kagenti (with OpenShift CA workaround)
helm upgrade --install kagenti ./charts/kagenti/ \
  -n kagenti-system --create-namespace \
  -f ./charts/kagenti/.secrets.yaml \
  --set ui.tag=${LATEST_TAG} \
  --set agentOAuthSecret.spiffePrefix=spiffe://${DOMAIN}/sa \
  --set uiOAuthSecret.useServiceAccountCA=false \
  --set agentOAuthSecret.useServiceAccountCA=false
```

### Option C: Ansible-Based Installer

```bash
# Configure secrets
cp deployments/envs/secret_values.yaml.example deployments/envs/.secret_values.yaml
# Edit .secret_values.yaml

# Run installer for OpenShift
deployments/ansible/run-install.sh --env ocp
```

### Verify SPIRE Daemonsets

```bash
kubectl get daemonsets -n zero-trust-workload-identity-manager
```

If `Current` or `Ready` is `0`, see [Troubleshooting](#spire-daemonset-issues).

---

## Accessing the UI

### Kind Cluster

```bash
open http://kagenti-ui.localtest.me:8080
```

### OpenShift

```bash
echo "https://$(kubectl get route kagenti-ui -n kagenti-system -o jsonpath='{.status.ingress[0].host}')"
```

If using self-signed certificates, accept the certificate in your browser.

For MCP Inspector, also accept the proxy certificate:

```bash
echo "https://$(kubectl get route mcp-proxy -n kagenti-system -o jsonpath='{.status.ingress[0].host}')"
```

### Default Credentials

```
Username: admin
Password: admin
```

Keycloak admin credentials (OpenShift):

```bash
kubectl get secret keycloak-initial-admin -n keycloak \
  -o go-template='Username: {{.data.username | base64decode}}  Password: {{.data.password | base64decode}}{{"\n"}}'
```

---

## Verifying the Installation

### Identity Services

```bash
# SPIRE OIDC (Kind)
curl http://spire-oidc.localtest.me:8080/keys
curl http://spire.localtest.me:8080/.well-known/openid-configuration

# Tornjak API
curl http://spire-tornjak-api.localtest.me:8080/
# Expected: "Welcome to the Tornjak Backend!"

# Tornjak UI
open http://spire-tornjak-ui.localtest.me:8080/
```

### Keycloak (Kind)

```bash
open http://keycloak.localtest.me:8080/
# Login: admin / admin
```

### UI Functionality

From the UI you can:
- Import and deploy A2A agents from any framework
- Deploy MCP tools directly from source
- Test agents interactively
- Monitor traces and network traffic

---

## Troubleshooting

### SPIRE Daemonset Issues

If daemonsets show `Current=0` or `Ready=0`:

```bash
kubectl describe daemonsets -n zero-trust-workload-identity-manager spire-agent
kubectl describe daemonsets -n zero-trust-workload-identity-manager spire-spiffe-csi-driver
```

If you see SCC (Security Context Constraint) errors:

```bash
oc adm policy add-scc-to-user privileged -z spire-agent -n zero-trust-workload-identity-manager
kubectl rollout restart daemonsets -n zero-trust-workload-identity-manager spire-agent

oc adm policy add-scc-to-user privileged -z spire-spiffe-csi-driver -n zero-trust-workload-identity-manager
kubectl rollout restart daemonsets -n zero-trust-workload-identity-manager spire-spiffe-csi-driver
```

### OpenShift Upgrade (4.18 → 4.19)

<details>
<summary>Red Hat OpenShift Container Platform (AWS)</summary>

```bash
# Update channel
oc patch clusterversion version --type merge -p '{"spec":{"channel":"fast-4.19"}}'

# Acknowledge changes
oc -n openshift-config patch cm admin-acks --patch '{"data":{"ack-4.18-kube-1.32-api-removals-in-4.19":"true"}}' --type=merge
oc -n openshift-config patch cm admin-acks --patch '{"data":{"ack-4.18-boot-image-opt-out-in-4.19":"true"}}' --type=merge

# Upgrade
oc adm upgrade --to-latest=true --allow-not-recommended=true

# Monitor
oc get clusterversion
```

</details>

For more troubleshooting tips, see [Troubleshooting Guide](./troubleshooting.md).

