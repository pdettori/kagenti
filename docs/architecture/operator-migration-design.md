# Kagenti Platform: Operator Migration Design

**From Ansible/Helm to Kubernetes Operator — "Operator of Operators" Architecture**

| Field | Value |
|-------|-------|
| Version | 8.0 (V8) |
| Date | 2026-03-04 |
| Status | 4-round adversarial architectural review (V5 baseline + 4 rounds with RHOAI/ODH integration) |
| Authors | Paolo Dettori |
| Assisted-By | Claude Opus 4.6 |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Background and Motivation](#2-background-and-motivation)
3. [Architecture Overview](#3-architecture-overview)
   - 3.1 [Three-Tier Deployment Model](#31-three-tier-deployment-model)
   - 3.2 [Tier 1: Kagenti Platform Operator (Product)](#32-tier-1-kagenti-platform-operator-product)
   - 3.3 [Tier 1 Observability Controller](#33-tier-1-observability-controller)
   - 3.4 [Tier 2: RHOAI/ODH DataScienceCluster Integration](#34-tier-2-rhoaiodh-datasciencecluster-integration)
   - 3.5 [Tier 3: Kagenti Quickstart Installer (Dev Tool)](#35-tier-3-kagenti-quickstart-installer-dev-tool)
   - 3.6 [Companion: kagenti-prereqs Helm Chart](#36-companion-kagenti-prereqs-helm-chart)
   - 3.7 [Formal Dependency Mapping](#37-formal-dependency-mapping)
4. [CRD Design: KagentiPlatform](#4-crd-design-kagentiplatform)
   - 4.1 [Full CR Schema](#41-full-cr-schema)
   - 4.2 [Status Subresource](#42-status-subresource)
   - 4.3 [Infrastructure Validation](#43-infrastructure-validation)
5. [Controller Architecture](#5-controller-architecture)
   - 5.1 [Platform Controller](#51-platform-controller)
   - 5.2 [Observability Controller](#52-observability-controller)
   - 5.3 [Two Controllers, One CRD](#53-two-controllers-one-crd)
   - 5.4 [Phase-Based State Machine (Quickstart)](#54-phase-based-state-machine-quickstart)
6. [Component Interface and Extensibility](#6-component-interface-and-extensibility)
   - 6.1 [Component Interface](#61-component-interface)
   - 6.2 [Installation Strategies](#62-installation-strategies)
   - 6.3 [Adding a New Package](#63-adding-a-new-package)
   - 6.4 [Unmanaged Component Semantics](#64-unmanaged-component-semantics)
7. [RBAC and Security](#7-rbac-and-security)
   - 7.1 [Product Operator RBAC](#71-product-operator-rbac)
   - 7.2 [Security Properties](#72-security-properties)
   - 7.3 [Comparison with Monolithic Approach](#73-comparison-with-monolithic-approach)
   - 7.4 [OLM Dependency Strategy — Dual CSV Approach](#74-olm-dependency-strategy--dual-csv-approach)
   - 7.5 [RBAC Verification for Unmanaged Health Checks](#75-rbac-verification-for-unmanaged-health-checks)
8. [OLM Subscription Lifecycle (Quickstart)](#8-olm-subscription-lifecycle-quickstart)
9. [Day-2 Operations](#9-day-2-operations)
   - 9.1 [Upgrade Coordination](#91-upgrade-coordination)
   - 9.2 [Drift Detection](#92-drift-detection)
   - 9.3 [Health and Degradation Model](#93-health-and-degradation-model)
   - 9.4 [Deletion Policy](#94-deletion-policy)
   - 9.5 [Day-2 Comparison: Ansible vs. Operator](#95-day-2-comparison-ansible-vs-operator)
   - 9.6 [Observability Deconfliction with RHOAI](#96-observability-deconfliction-with-rhoai)
10. [Migration Path from Ansible](#10-migration-path-from-ansible)
    - 10.1 [Adoption via Server-Side Apply](#101-adoption-via-server-side-apply)
    - 10.2 [Graduation Path](#102-graduation-path)
    - 10.3 [UX Preservation](#103-ux-preservation)
11. [Implementation Timeline](#11-implementation-timeline)
    - 11.1 [ODH Contribution Governance](#111-odh-contribution-governance)
12. [Decision Record](#12-decision-record)
- [Appendix A: Quickstart Phase Ordering](#appendix-a-quickstart-phase-ordering)
- [Appendix B: Component Criticality Matrix](#appendix-b-component-criticality-matrix)

---

## 1. Executive Summary

This document presents the architecture for migrating the Kagenti platform installer from an Ansible/Helm-based approach to a Kubernetes Operator-based approach. The design was refined through 5 rounds of internal architectural review (V1-V5), followed by 4 additional rounds incorporating product management feedback on RHOAI/ODH DataScienceCluster integration (V6-V8).

### Key Decisions

- **Three-tier deployment model**: A product-grade Platform Operator (Tier 1) manages only Kagenti's own components. An ODH/RHOAI component handler (Tier 2) integrates Kagenti into the DataScienceCluster meta-operator. An optional Quickstart Operator (Tier 3) handles infrastructure prerequisites for dev/PoC environments.
- **Validate, don't install**: The product operator checks that infrastructure prerequisites (Istio, Keycloak, SPIRE, etc.) exist but does NOT install them. This keeps RBAC narrow and enables Konflux/OLM certification.
- **Single CRD, two controllers**: One `KagentiPlatform` CRD with a Platform Controller and an Observability Controller, minimizing user-facing surface area.
- **RHOAI integration via thin wrapper**: The ODH component handler is a ~200-line adapter that creates a `KagentiPlatform` CR. The Kagenti team owns the operator logic; ODH integration is minimal.
- **`managementState` tri-state**: Adopts the ODH/RHOAI `Managed | Removed | Unmanaged` pattern for component lifecycle control.
- **Dual CSV bundles**: Standalone (soft OLM dependencies) and RHOAI (hard CRD requirements) variants from the same operator binary.
- **Narrow RBAC**: The product operator has no escalate, no CRD creation, no OLM management, and no third-party CR mutation. Read-only infrastructure validation only.

---

## 2. Background and Motivation

### 2.1 Current State: Ansible/Helm Installer

Kagenti currently uses an Ansible playbook (`roles/kagenti_installer`) that orchestrates 29+ sequential installation steps. The playbook handles:

- **Platform-adaptive logic**: The same component resolves to different actions depending on whether the target is Kind, OpenShift 4.18, or OpenShift 4.19+.
- **Cross-resource ordering with waits**: CRDs before CRs, operators before operands, webhooks before dependent resources.
- **Conflict detection**: Pre-installed OLM operators on OpenShift are detected and skipped.
- **Post-install fixups**: TektonConfig patches, ConfigMap modifications, CA secret copying.
- **Diagnostic collection on failure** via Ansible rescue blocks.

### 2.2 Why Migrate to an Operator

| Driver | Ansible Limitation | Operator Advantage |
|--------|-------------------|-------------------|
| Self-healing | None. Manual re-run on failure. | Continuous reconciliation restores desired state. |
| Drift detection | None. Manual helm diff required. | Controller detects and repairs drift automatically. |
| Day-2 operations | Re-run full playbook for any change. | Edit CR spec; controller applies minimal diff. |
| Productization | Cannot ship via OLM/Konflux. | Native OLM distribution, Red Hat certification. |
| Declarative UX | Imperative playbook execution. | kubectl apply a CR; watch status converge. |

### 2.3 Product Manager Context

As highlighted in internal discussions, "reducing as much of the dependencies as possible would be desirable as a prevention mechanism, otherwise we end up encoding that complexity somewhere." This directly informed the three-tier split.

The PM review (Adel Zaalouk, Andrew Block) identified that:
- Most Kagenti dependencies already have Red Hat operator equivalents
- RHOAI is a "meta operator" — Kagenti should be a component inside `DataScienceCluster`
- Two scenarios must coexist: Kagenti as part of RHOAI, and Kagenti standalone for dev

---

## 3. Architecture Overview

### 3.1 Three-Tier Deployment Model

Kagenti has three deployment scenarios with different lifecycles and ownership:

| Tier | Name | Who Deploys | Target Environment | CRD Surface |
|------|------|------------|-------------------|-------------|
| **Tier 1** | Kagenti Platform Operator | OLM (standalone) or ODH operator (RHOAI) | Production OpenShift, vanilla K8s | `KagentiPlatform` |
| **Tier 2** | RHOAI/ODH Integration | ODH meta-operator | Production RHOAI clusters | `DataScienceCluster.spec.components.kagenti` |
| **Tier 3** | Kagenti Quickstart Installer | Developer | Kind, dev/PoC | `KagentiQuickstart` |

**Key principle: Tier 1 is the reusable core.** Both Tier 2 (RHOAI) and Tier 3 (Quickstart) deploy Tier 1 underneath. They differ only in how prerequisites are satisfied and who creates the `KagentiPlatform` CR.

```
┌──────────────────────────────────────────────────────────┐
│                  Deployment Scenarios                      │
│                                                            │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │   Tier 3    │  │     Tier 2       │  │  Standalone   │ │
│  │  Quickstart │  │  RHOAI/ODH DSC   │  │  Tier 1 only  │ │
│  │  (dev/PoC)  │  │  (product)       │  │  (adv. user)  │ │
│  └──────┬──────┘  └────────┬─────────┘  └──────┬────────┘ │
│         │                  │                    │          │
│         │  creates CR      │  creates CR        │  user    │
│         ▼                  ▼                    ▼          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │          Tier 1: Kagenti Platform Operator          │  │
│  │          (reconciles KagentiPlatform CR)             │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  Prerequisites satisfied by:                               │
│    Tier 3: Quickstart installs everything                  │
│    Tier 2: DSCi + OLM dependencies handle infra            │
│    Standalone: Admin uses kagenti-prereqs chart / manual    │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Tier 1: Kagenti Platform Operator (Product)

- Shipped via Konflux and OLM. Red Hat certified.
- Manages ONLY Kagenti-owned components: Agent Operator, Webhook, UI, MCP Gateway, Agent Namespaces, OAuth client setup.
- Validates that required infrastructure exists (CRDs present, services reachable) but does NOT install it.
- Contains two controllers in one OLM bundle: Platform Controller and Observability Controller.
- Single CRD: `KagentiPlatform`.
- Narrow RBAC: no escalate, no CRD creation, no OLM management.

### 3.3 Tier 1 Observability Controller

The Observability Controller is part of the Tier 1 OLM bundle but runs as a separate controller watching the same `KagentiPlatform` CRD. It manages:

- **OTel Collector** with Kagenti-specific pipeline configuration (GenAI semantic convention transforms, span filtering for A2A, OAuth2 exporter for MLflow).
- **Phoenix** (LLM observability backend).
- **MLflow** (experiment tracking).

These are included in Tier 1 because the OTel Collector pipeline configuration is Kagenti-specific IP (not generic infrastructure). A user may disable observability entirely via `spec.observability.managementState: Removed`.

### 3.4 Tier 2: RHOAI/ODH DataScienceCluster Integration

#### 3.4.1 The DSC Component Pattern

The ODH operator (RHOAI's meta-operator) uses a two-CRD pattern:

- **`DSCInitialization`** — cluster-level setup: monitoring namespace, trusted CA bundles, network policies. Created once per cluster.
- **`DataScienceCluster`** — component lifecycle management. Each component has a `managementState`:
  - `Managed` — ODH operator installs and reconciles the component
  - `Removed` — ODH operator deletes the component
  - `Unmanaged` — ODH operator ignores; user manages directly

The DSC v2 sample shows 15+ components:

```yaml
apiVersion: datasciencecluster.opendatahub.io/v2
kind: DataScienceCluster
metadata:
  name: default-dsc
spec:
  components:
    dashboard:
      managementState: "Managed"
    kserve:
      managementState: "Managed"
    trustyai:
      managementState: "Managed"
    ray:
      managementState: "Managed"
    mlflowoperator:
      managementState: "Removed"
    kagenti:                          # <-- target state
      managementState: "Managed"
```

#### 3.4.2 How Kagenti Fits the DSC Component Interface

The ODH operator's component handler interface:

```go
type ComponentHandler interface {
    GetComponentName() string
    GetManagementState(dsc *DataScienceCluster) operatorv1.ManagementState
    ReconcileComponent(ctx context.Context, cli client.Client,
        dsc *DataScienceCluster, dsci *DSCInitialization, platform cluster.Platform) error
    Cleanup(ctx context.Context, cli client.Client,
        dsc *DataScienceCluster, dsci *DSCInitialization) error
    UpdateStatus(ctx context.Context, cli client.Client,
        dsc *DataScienceCluster, condition *conditionsv1.Condition) error
}
```

**Kagenti's implementation** within the ODH operator is a thin adapter (~200 lines):

```go
// pkg/components/kagenti/kagenti.go (contributed to ODH operator)
type Kagenti struct {
    components.BaseComponent
}

func (k *Kagenti) ReconcileComponent(ctx context.Context, cli client.Client,
    dsc *dscv2.DataScienceCluster, dsci *dsciv2.DSCInitialization,
    platform cluster.Platform) error {

    // 1. Ensure the Kagenti Platform Operator is installed via OLM
    if err := k.ensureOperatorReady(ctx, cli); err != nil {
        return err
    }

    // 2. Create or update the KagentiPlatform CR
    platformCR := k.buildPlatformCR(dsc, dsci, platform)
    if err := k.applyPlatformCR(ctx, cli, platformCR); err != nil {
        return err
    }

    // 3. Wait for KagentiPlatform status to report Ready
    return k.waitForPlatformReady(ctx, cli)
}
```

**Key design principle: The ODH component is a thin wrapper that creates a `KagentiPlatform` CR.** The actual reconciliation logic lives in the Tier 1 operator. This means:
- The Kagenti team owns the operator logic (ships via OLM as a separate operator)
- The ODH integration is ~200 lines contributed upstream
- The `KagentiPlatform` CRD is the single source of truth regardless of deployment mode

#### 3.4.3 DSC API Surface for Kagenti

The **minimal external API** exposed in the DSC spec:

```yaml
spec:
  components:
    kagenti:
      managementState: "Managed"    # Managed | Removed | Unmanaged
      agentNamespaces:
        - team1
        - team2
      observability:
        enabled: true
```

The **full internal API** (the complete `KagentiPlatform` spec) remains on the `KagentiPlatform` CRD. Users who need fine-grained control can set `managementState: Unmanaged` and manage the `KagentiPlatform` CR directly.

#### 3.4.4 Lifecycle Modes and managementState Mapping

| DSC `managementState` | Effect on Kagenti |
|----------------------|-------------------|
| `Managed` | ODH operator ensures `KagentiPlatform` CR exists, Kagenti Operator OLM Subscription is healthy. ODH owns the CR. |
| `Removed` | ODH operator deletes the `KagentiPlatform` CR. Kagenti Operator's finalizer handles teardown. |
| `Unmanaged` | ODH operator stops reconciling. User manages the `KagentiPlatform` CR directly. Kagenti Operator keeps running. |

#### 3.4.5 KagentiPlatform CR Ownership Model

| DSC `managementState` | CR Owner | User Can Edit CR? | What Happens on Edit |
|----------------------|----------|-------------------|---------------------|
| `Managed` | ODH operator | No (overwritten) | ODH reconciler overwrites on next cycle. User must change DSC fields instead. |
| `Unmanaged` | User | Yes (full control) | ODH stops reconciling. User manages `KagentiPlatform` CR directly. Kagenti Operator still reconciles it. |
| `Removed` | N/A | N/A | ODH deletes the CR. Kagenti Operator's finalizer runs teardown. |

**Managed to Unmanaged graduation path:**

```bash
# Step 1: Start with RHOAI-managed Kagenti (DSC has kagenti.managementState: Managed)
# Step 2: Inspect the generated KagentiPlatform CR
kubectl get kagentiplatform kagenti -n kagenti-system -o yaml
# Step 3: Switch to user-managed (edit DSC: kagenti.managementState: Unmanaged)
# Step 4: Customize freely
kubectl edit kagentiplatform kagenti -n kagenti-system
```

The ODH component handler uses SSA with field manager `odh-kagenti-component`. On transition to Unmanaged, the field manager is released. When `managed-by: odh-operator`, user edits trigger a warning event:

```
Warning  ManagedByODH  KagentiPlatform/kagenti  This CR is managed by the ODH operator.
         Changes will be overwritten. Set kagenti.managementState: Unmanaged in
         your DataScienceCluster to take direct control.
```

#### 3.4.6 DSCInitialization and Infrastructure Prerequisites

When Kagenti runs inside RHOAI, infrastructure prerequisites are handled externally:

| Prerequisite | How Satisfied in RHOAI | How Expressed |
|-------------|----------------------|---------------|
| Service Mesh (Istio) | RHOAI declares `servicemeshoperator3` as OLM dependency | OLM CSV `spec.dependencies` |
| cert-manager | `openshift-cert-manager-operator` OLM dependency | OLM CSV `spec.dependencies` |
| Pipelines (Tekton) | `openshift-pipelines-operator-rh` OLM dependency | OLM CSV `spec.dependencies` |
| Builds (Shipwright) | `openshift-builds-operator` OLM dependency | OLM CSV `spec.dependencies` |
| SPIRE/ZTWIM | `openshift-zero-trust-workload-identity-manager` OLM dependency (OCP 4.19+) | OLM CSV `spec.dependencies` |
| Keycloak | `rhbk-operator` OLM dependency | OLM CSV `spec.dependencies` |
| Monitoring | DSCInitialization `spec.monitoring` | DSCi reconciler |
| Trusted CA | DSCInitialization `spec.trustedCABundle` | DSCi reconciler |

The Kagenti Platform Operator's infrastructure validation still runs but all checks should pass. If they don't, the operator surfaces `phase: Blocked` with details.

### 3.5 Tier 3: Kagenti Quickstart Installer (Dev Tool)

- Optional. For dev/demo/PoC environments only.
- NOT part of the product. NOT shipped via OLM or Konflux.
- Replaces the current Ansible installer.
- Manages all infrastructure prerequisites: Istio, Keycloak, SPIRE, Tekton, Shipwright, cert-manager, Gateway API, Kiali, etc.
- CRD: `KagentiQuickstart`.
- After installing infrastructure, creates a `KagentiPlatform` CR once (create-if-not-exists, never updates). The Platform Operator then takes over.
- Has broader permissions (OLM CRUD, Helm installs, namespace creation) because it runs only in dev environments.

### 3.6 Companion: kagenti-prereqs Helm Chart

For production OpenShift clusters where the Quickstart operator is not used and RHOAI is not installed, a static `kagenti-prereqs` Helm chart provides all prerequisite manifests. The admin can:

- Inspect the chart before applying (audit trail)
- Selectively enable components: `--set istio.enabled=true --set keycloak.enabled=true`
- Commit the rendered manifests to a GitOps repository
- Use it as a reference for crafting their own manifests

> **Note:** `kagenti-prereqs` is only for standalone K8s / vanilla OpenShift (no RHOAI). On RHOAI clusters, prerequisites are handled by DSCi + OLM dependencies.

### 3.7 Formal Dependency Mapping

From PM review — maps each Kagenti component to its Red Hat operator equivalent:

| Kagenti Component | K8s (Kind) Install Method | OpenShift Operator (OLM) | Red Hat Product Name | OLM Package |
|---|---|---|---|---|
| **kagenti-operator** | Helm (bundled) | **To be productized** | — | `kagenti-operator` (future) |
| **Istio** | Helm (istio-release) | `servicemeshoperator3` | OpenShift Service Mesh 3 | `servicemeshoperator3` |
| **Tekton** | Direct manifest | `openshift-pipelines-operator-rh` | OpenShift Pipelines | `openshift-pipelines-operator-rh` |
| **cert-manager** | Direct manifest | `openshift-cert-manager-operator` | cert-manager Operator | `openshift-cert-manager-operator` |
| **Shipwright** | Direct manifest | `openshift-builds-operator` | OpenShift Builds | `openshift-builds-operator` |
| **SPIRE** | Helm (spiffe.io) | `openshift-zero-trust-workload-identity-manager` | ZTWIM (OCP 4.19+) | `openshift-zero-trust-workload-identity-manager` |
| **Keycloak** | Helm/direct | `rhbk-operator` | Red Hat build of Keycloak | `rhbk-operator` |
| **Gateway API** | CRD manifest | Built into OSSM3 | — | (bundled with OSSM) |
| **MCP Gateway** | Helm | **WIP** — Kuadrant MCP Gateway | RHCL? | TBD |
| **Kiali** | Istio samples | `kiali-ossm` | Kiali (OSSM) | `kiali-ossm` |
| **metrics-server** | Helm | Built-in (Prometheus Adapter) | — | N/A |
| **Kagenti UI** | Helm (bundled) | Can be deployed by RHOAI meta-operator (via DSC) | — | (part of kagenti) |

---

## 4. CRD Design: KagentiPlatform

### 4.1 Full CR Schema

```yaml
apiVersion: kagenti.dev/v1alpha1
kind: KagentiPlatform
metadata:
  name: kagenti
  namespace: kagenti-system
spec:
  # --- Core Components (reconciled by Platform Controller) ---
  agentOperator:
    managementState: Managed        # Managed | Removed | Unmanaged
    image: ""                       # Override; defaults to operator-bundled version

  webhook:
    managementState: Managed

  ui:
    managementState: Managed
    auth:
      managementState: Managed      # Can disable auth independently
      keycloak:
        url: https://keycloak.keycloak.svc.cluster.local:8443
        realm: master
        credentialsSecretRef: { name: kagenti-keycloak-admin }
    frontend: { image: "" }
    backend:  { image: "" }

  mcpGateway:
    managementState: Removed

  agentNamespaces:
    - name: team1
      secretRef: { name: team1-credentials }
    - name: team2
      secretRef: { name: team2-credentials }

  # --- Infrastructure References (validate only, do NOT install) ---
  infrastructure:
    istio:       { requirement: Required }     # Required | Optional | Ignored
    spire:       { requirement: Required, trustDomain: localtest.me }
    certManager: { requirement: Required }
    tekton:      { requirement: Required }
    shipwright:  { requirement: Required }
    gatewayApi:  { requirement: Required }

  # --- Observability (reconciled by Observability Controller) ---
  observability:
    managementState: Managed
    collector:
      exporters:
        phoenix: { managementState: Managed }
        mlflow:
          managementState: Managed
          auth: { managementState: Managed, clientSecretRef: { name: kagenti-mlflow-oauth } }
    phoenix:
      managementState: Managed
      storage: { type: postgresql, size: 10Gi }
    mlflow:
      managementState: Managed
      storage: { size: 5Gi }

  # --- Global ---
  domain: localtest.me
  deletionPolicy: Retain            # Retain | Delete
  imageOverrides:
    registry: ""
    pullSecretRef: ""
```

**managementState semantics:**
- **Managed** — Operator installs and continuously reconciles
- **Removed** — Operator deletes the component and its resources
- **Unmanaged** — Operator ignores; user manages directly (useful for custom OTel pipeline or external MLflow)

**Infrastructure requirement semantics:**
- **Required** — Must be present. Operator blocks (`phase: Blocked`) if missing.
- **Optional** — Operator checks but only degrades (`phase: Degraded`) if missing.
- **Ignored** — Operator skips validation entirely.

### 4.2 Status Subresource

Status is partitioned between the two controllers. Each writes to distinct sub-paths using separate SSA field managers.

```yaml
status:
  phase: Ready              # Installing | Ready | Degraded | Blocked | Error
  observedGeneration: 5

  # Written by Platform Controller
  environment:
    platform: OpenShift     # or Kubernetes
    version: "4.19"
    preInstalled: [cert-manager, openshift-pipelines]
  infrastructure:
    certManager: { status: Ready, detected: true }
    istio:       { status: Ready, detected: true }
    spire:       { status: Ready, detected: true }
    tekton:      { status: Ready, detected: true }
    shipwright:  { status: Ready, detected: true }
    gatewayApi:  { status: Ready, detected: true }
  components:
    agentOperator: { status: Ready }
    ui:            { status: Ready }
    webhook:       { status: Ready }
  prerequisiteGuide:
    helmChart: "oci://ghcr.io/kagenti/charts/kagenti-prereqs"
    url: "https://kagenti.dev/docs/prerequisites"

  # Written by Observability Controller
  observability:
    collector: { status: Ready }
    phoenix:   { status: Ready }
    mlflow:    { status: Ready }

  conditions:
    - type: InfrastructureReady
      status: "True"
    - type: PlatformReady
      status: "True"
    - type: ObservabilityReady
      status: "True"
    - type: Available
      status: "True"
    - type: FullyOperational
      status: "True"
```

### 4.3 Infrastructure Validation

The Platform Controller validates infrastructure on every reconciliation by checking CRD existence and service readiness. When prerequisites are missing, the status provides actionable guidance including a pointer to the `kagenti-prereqs` Helm chart.

The controller distinguishes between 'never installed' (hard block) and 'was working, now temporarily unhealthy' (grace period). A configurable grace period (default 10 minutes) prevents false `Blocked` status during infrastructure upgrades.

---

## 5. Controller Architecture

### 5.1 Platform Controller

```go
func (r *PlatformReconciler) Reconcile(ctx, req) (Result, error) {
    platform := &v1alpha1.KagentiPlatform{}
    r.Get(ctx, req.NamespacedName, platform)

    // 1. Detect environment (OpenShift? version? pre-installed operators?)
    env := r.detector.Detect(ctx)

    // 2. Validate infrastructure prerequisites
    infraStatus := r.evaluateInfraHealth(ctx, platform)
    if infraStatus == InfraBlocked {
        platform.Status.Phase = "Blocked"
        return Result{RequeueAfter: 30s}, nil
    }

    // 3. Install/update core Kagenti components
    for _, component := range r.coreComponents {
        if component.Enabled(platform.Spec) {
            component.Install(ctx, platform, env)
        }
    }

    // 4. Configure agent namespaces
    r.reconcileAgentNamespaces(ctx, platform)

    // 5. Set status
    platform.Status.Phase = "Ready"
    return Result{RequeueAfter: 5 * time.Minute}, nil
}
```

### 5.2 Observability Controller

Watches the same `KagentiPlatform` CRD but only reconciles the `spec.observability` section. Uses a hash of the observability spec to avoid unnecessary work when only core spec changes.

### 5.3 Two Controllers, One CRD

Both controllers ship in the same OLM bundle as separate Deployments. They use distinct SSA field managers for status updates to avoid write conflicts. Each controller uses spec-hash comparison to skip reconciliation when only the other controller's section changed.

### 5.4 Phase-Based State Machine (Quickstart)

The Quickstart Operator uses a phase-based state machine:

| Phase | Components | Notes |
|-------|-----------|-------|
| 1. Foundation | cert-manager, Gateway API CRDs, metrics-server | No dependencies |
| 2. Mesh | Istio (base -> istiod -> CNI -> ztunnel) | Strict internal ordering |
| 3. Identity | SPIRE (server -> agent -> CSI -> OIDC) | Strict internal ordering |
| 4. Build | Tekton -> Shipwright | Shipwright depends on Tekton |
| 5. Auth | Keycloak (operator -> instance -> realm -> clients) | Sequential |
| 6. Observability | OTel Collector, Phoenix, MLflow | Concurrent |
| 7. Platform | Ingress Gateway, container registry, Kiali | Concurrent |
| 8. Handoff | Creates `KagentiPlatform` CR | Platform operator takes over |

---

## 6. Component Interface and Extensibility

### 6.1 Component Interface

```go
type Component interface {
    Name() string
    Enabled(resolved *ResolvedConfig) bool
    Install(ctx context.Context, p *KagentiPlatform, env *Environment) error
    IsReady(ctx context.Context) (bool, string, error)
    Uninstall(ctx context.Context) error
}
```

### 6.2 Installation Strategies

| Strategy | When Used | Example |
|----------|----------|---------|
| HelmComponent | Vanilla K8s, or OCP when no OLM operator exists | Istio on K8s, Phoenix, MLflow |
| OLMComponent | OpenShift with operator in catalog | OSSM v3, RHBK, OpenShift Pipelines |
| ManifestComponent | Simple CRD/YAML-only installs | Gateway API CRDs, Kiali addons |
| ExternalComponent | User-managed, validate connectivity only | External Keycloak, pre-existing Istio |

### 6.3 Adding a New Package

Adding a new component is a 3-file change:

| File | Change |
|------|--------|
| `api/v1alpha1/types.go` | Add field to `ComponentsSpec` struct |
| `controllers/components/newpkg.go` | Implement `Component` interface |
| `controllers/phases/<phase>.go` or `main.go` | Register in the appropriate phase |

### 6.4 Unmanaged Component Semantics

| Scenario | How Component Gets to `Unmanaged` | Operator Behavior |
|----------|----------------------------------|-------------------|
| **Operator deployed, user takes over** | User changes `Managed` -> `Unmanaged` | Operator **releases SSA field ownership** on the component's resources. Stops reconciling. Existing resources remain. Operator still reports health (read-only). |
| **User pre-installed, operator acknowledges** | User sets `Unmanaged` from the start | Operator **never touches** the component's resources. Validates expected endpoints/CRDs exist (read-only). Reports status. |

Both cases converge to the same steady state: operator doesn't write, only reads.

```go
func (c *Component) reconcileUnmanaged(ctx context.Context, prev operatorv1.ManagementState) error {
    if prev == operatorv1.Managed {
        c.releaseFieldOwnership(ctx)
        c.recorder.Event(platform, "Normal", "Unmanaged",
            fmt.Sprintf("%s is now user-managed.", c.Name()))
    }
    healthy, msg, err := c.IsReady(ctx)
    c.updateStatusReadOnly(ctx, healthy, msg)
    return err
}
```

---

## 7. RBAC and Security

### 7.1 Product Operator RBAC (Tier 1)

```yaml
# Read-only: infrastructure validation
- apiGroups: ["apiextensions.k8s.io"]
  resources: ["customresourcedefinitions"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["config.openshift.io"]
  resources: ["clusterversions"]
  verbs: ["get"]

# Own CRDs
- apiGroups: ["kagenti.dev"]
  resources: ["kagentiplatforms", "kagentiplatforms/status", "kagentiplatforms/finalizers"]
  verbs: ["get", "list", "watch", "update", "patch"]

# Kagenti components (namespaced)
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "secrets", "serviceaccounts"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

# Networking
- apiGroups: ["gateway.networking.k8s.io"]
  resources: ["httproutes", "referencegrants"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["route.openshift.io"]
  resources: ["routes"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

# Namespace management (agent namespaces)
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "list", "create", "update", "patch"]
```

### 7.2 Security Properties

| Property | How Achieved |
|----------|-------------|
| Least privilege | Operator can only manage Kagenti-owned resources |
| No escalation | No 'escalate' or 'bind' verbs |
| Infrastructure isolation | Read-only access to infrastructure CRDs for validation |
| Secret scoping | Per-namespace secretRef for agent namespaces |
| Audit trail | All actions attributable to kagenti-platform-operator ServiceAccount |
| Certifiability | RBAC surface passes Red Hat operator certification requirements |

### 7.3 Comparison: Monolithic vs. Two-Tier RBAC

| Permission | Monolithic Orchestrator (rejected) | Product Operator (V8) |
|-----------|-----------------------------------|----------------------|
| CRD management | create, update, delete on ALL CRDs | get, list, watch only |
| OLM access | Full Subscription/InstallPlan/CSV CRUD | None |
| Namespace scope | All namespaces | kagenti-system + agent namespaces |
| RBAC verbs | bind, escalate | None |
| Third-party CRs | Full CRUD on Istio, Keycloak, SPIRE | Read-only (validation) |
| Blast radius | Compromised operator = cluster-admin equivalent | Compromised operator = Kagenti components only |

### 7.4 OLM Dependency Strategy — Dual CSV Approach

| Bundle | Target | Dependency Strategy | Rationale |
|--------|--------|-------------------|-----------|
| `kagenti-operator` (standalone) | OpenShift without RHOAI | `spec.dependencies` at package level (soft) | Admin may install deps incrementally. Operator starts, validates at runtime. |
| `kagenti-operator` (RHOAI) | RHOAI DSC-managed | `spec.customresourcedefinitions.required` (hard) | RHOAI guarantees all deps. Hard block catches misconfigurations. |

**Standalone CSV (soft dependencies):**

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: ClusterServiceVersion
metadata:
  name: kagenti-operator.v1.0.0
spec:
  dependencies:
    - type: olm.package
      value:
        packageName: servicemeshoperator3
        version: ">=3.0.0"
    - type: olm.package
      value:
        packageName: openshift-cert-manager-operator
        version: ">=1.0.0"
  customresourcedefinitions:
    owned:
      - name: kagentiplatforms.kagenti.dev
        version: v1alpha1
        kind: KagentiPlatform
```

**RHOAI CSV (hard dependencies):**

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: ClusterServiceVersion
metadata:
  name: kagenti-operator.v1.0.0-rhoai
spec:
  customresourcedefinitions:
    owned:
      - name: kagentiplatforms.kagenti.dev
        version: v1alpha1
        kind: KagentiPlatform
    required:
      - name: istios.sailoperator.io
        version: v1
        kind: Istio
      - name: keycloaks.k8s.keycloak.org
        version: v2alpha1
        kind: Keycloak
      - name: clusterissuers.cert-manager.io
        version: v1
        kind: ClusterIssuer
      - name: clusterspiffeids.spire.spiffe.io
        version: v1alpha1
        kind: ClusterSPIFFEID
```

Both bundles are generated by the same Konflux pipeline from the same operator binary.

### 7.5 RBAC Verification for Unmanaged Health Checks

| Unmanaged Component | Health Check Method | Required RBAC | Already in ClusterRole? |
|---------------------|-------------------|---------------|------------------------|
| MLflow | Deployment readiness in `kagenti-system` | `apps/deployments: get` | Yes |
| Phoenix | Deployment readiness in `kagenti-system` | `apps/deployments: get` | Yes |
| OTel Collector | Deployment readiness in `kagenti-system` | `apps/deployments: get` | Yes |
| External MLflow | HTTP health probe | No RBAC needed | N/A |
| External Keycloak | HTTP health probe | No RBAC needed | N/A |

**Limitation:** Unmanaged health checks only work for resources in `kagenti-system` and declared `agentNamespaces`. Components deployed elsewhere report `Unknown` health.

---

## 8. OLM Subscription Lifecycle (Quickstart)

| Aspect | Design Decision | Rationale |
|--------|----------------|-----------|
| Approval Policy | Always Manual | Prevents OLM from auto-upgrading operators |
| Version Gating | Compatibility matrix (compiled + ConfigMap override) | Only approve InstallPlans for tested CSV versions |
| Operand CRs | Unstructured (no Go type imports) | Decouples from upstream API changes |
| Health Checking | CSV phase + operator Pod readiness + operand status conditions | Three-layer verification |
| Version Pinning | Compiled defaults + ConfigMap override | Fast CVE response without rebuilding |

---

## 9. Day-2 Operations

### 9.1 Upgrade Coordination

Default grace period: 10 minutes (configurable). During grace period, status shows `Degraded`, not `Blocked`. The Quickstart operator can set `kagenti.dev/infra-upgrade-in-progress` annotation to extend indefinitely.

### 9.2 Drift Detection

| Tier | Mechanism | Latency | What It Catches |
|------|----------|---------|----------------|
| Tier 1: Security watches | controller-runtime Watches on AuthorizationPolicy, ClusterSPIFFEID | Immediate | Deleted/modified security policies |
| Tier 2: Owned resources | controller-runtime Owns() on Deployments, Services | Immediate | Modified/deleted Kagenti components |
| Tier 3: Periodic poll | RequeueAfter: 5 minutes | Up to 5 min | Everything else |

### 9.3 Health and Degradation Model

| Condition | Meaning | When True |
|-----------|---------|-----------|
| Available | Core platform is functional | All Critical + Required components healthy |
| Degraded | Optional component unhealthy | Any Optional component is down |
| FullyOperational | Everything works | All components including optional ones healthy |
| Blocked | Cannot proceed | Missing infrastructure prerequisites |

### 9.4 Deletion Policy

| Policy | Behavior |
|--------|----------|
| Retain (default) | Finalizer removed, all components left running. |
| Delete | Reverse-order teardown. Requires `kagenti.dev/confirm-delete=yes-destroy-everything`. Infrastructure is NEVER deleted by the product operator. |

### 9.5 Day-2 Comparison: Ansible vs. Operator

| Operation | Current (Ansible/Helm) | Proposed (Operator) |
|-----------|----------------------|-------------------|
| Upgrade a component | Re-run full playbook (~15 min) | Edit CR or upgrade operator image |
| Self-healing | None | Continuous reconciliation |
| Drift detection | None | Automatic, tiered watches |
| Add component post-install | Edit env file, re-run playbook | Edit CR; controller installs only the new component |
| Remove component | Edit env file, re-run (orphaned resources) | Set `managementState: Removed`; controller cleans up |
| Multi-cluster | Run playbook per cluster | Apply CR per cluster (GitOps-friendly) |

### 9.6 Observability Deconfliction with RHOAI

When running inside RHOAI:

| Component | RHOAI Provides | Kagenti Provides | Resolution |
|-----------|---------------|-----------------|------------|
| Monitoring (Prometheus) | DSCi `spec.monitoring` | Not provided | Use RHOAI's monitoring |
| MLflow | DSC `mlflowoperator` component | Kagenti Observability Controller | Defer to RHOAI's MLflow when `mlflowoperator.managementState: Managed` in DSC |
| OTel Collector | Not provided (Kagenti-specific) | GenAI semantic conventions, A2A span filtering | Kagenti-owned |
| Phoenix | Not provided | LLM observability | Kagenti-owned |

```go
func (k *Kagenti) mapObservability(dsc *dscv2.DataScienceCluster) kagentiv1alpha1.ObservabilitySpec {
    obs := kagentiv1alpha1.ObservabilitySpec{
        ManagementState: operatorv1.Managed,
        // ... GenAI pipeline config ...
    }
    if dsc.Spec.Components.MLflowOperator.ManagementState == operatorv1.Managed {
        obs.MLflow.ManagementState = operatorv1.Removed // Defer to RHOAI
    } else {
        obs.MLflow.ManagementState = operatorv1.Managed
    }
    return obs
}
```

---

## 10. Migration Path from Ansible

### 10.1 Adoption via Server-Side Apply

For existing clusters, the Quickstart Operator adopts resources using SSA with `ForceOwnership`:

1. Discover existing resources by label, annotation, or well-known names
2. Apply SSA patch with `kagenti-quickstart` field manager
3. Delete Helm release Secret (tracking metadata only; resources remain)
4. Label adopted resources with `kagenti.dev/managed-by=quickstart`
5. Record provenance in status

### 10.2 Graduation Path

| Step | Action | Result |
|------|--------|--------|
| 1. Parallel install | Install Tier 1 operator alongside Ansible-managed cluster | Operator validates infra, manages Kagenti components. |
| 2. Quickstart adoption | Install Quickstart operator; adopts existing infra resources | Quickstart manages infra lifecycle. Ansible no longer needed. |
| 3. Production graduation | Delete KagentiQuickstart CR with `deletionPolicy: Retain` | Infra remains, managed by admin/GitOps. Platform operator continues. |

### 10.3 UX Preservation

```bash
# Dev (Kind) — identical simplicity:
./deploy.sh dev

# Production (OpenShift):
./deploy.sh ocp
```

---

## 11. Implementation Timeline

| Phase | Duration | Deliverables | Dependencies |
|-------|----------|-------------|-------------|
| A: CRD + Platform Controller | 4 weeks | `KagentiPlatform` CRD with `managementState`, infra validation, core component install, envtest | None |
| B: Observability + Prereqs Chart | 3 weeks | Observability controller, `kagenti-prereqs` chart, MLflow deconfliction | Phase A |
| C: Quickstart Operator (Tier 3) | 3 weeks | Port Ansible phases to Go, adoption logic, `deploy.sh` | Phase A |
| D: ODH Component Handler (Tier 2) | 2 weeks | Kagenti component for ODH operator, DSC spec fields, OLM CSV with dependencies | Phase A |
| E: Productization | 2 weeks | Konflux pipeline, OLM bundle, Red Hat cert prep, docs | Phases A-D |

Phases C and D run in parallel. Total: ~12 weeks.

### 11.1 ODH Contribution Governance

#### Phased Upstream Strategy

```
Week 1-4:   Phase A — KagentiPlatform CRD + Platform Controller (standalone)
Week 5-7:   Phase B/C/D in parallel
              D.1: Write component handler + tests
              D.2: Open upstream PR to opendatahub-io/opendatahub-operator
              D.3: Ship overlay/fork for RHOAI internal testing
Week 8-9:   Phase E — Productization (standalone OLM bundle)
Week 8-14:  D.4 — Upstream review cycle (async, non-blocking)
```

#### Overlay Bridge Strategy

While the upstream ODH PR is in review, an overlay image includes the Kagenti component handler:

- Used only for RHOAI internal integration testing
- Never shipped to customers before the upstream merge lands
- Three technical gates: image tag `-internal` suffix, separate registry (`quay.io/kagenti-internal`), 90-day TTL expiry

#### ODH RFC Ownership

| Action | Owner | Deadline | Artifact |
|--------|-------|----------|----------|
| Draft ODH component RFC | Kagenti tech lead (Paolo Dettori) | End of Phase A, Week 2 | GitHub Issue on `opendatahub-io/opendatahub-operator` |
| Present at ODH community meeting | Kagenti tech lead + PM | Week 3-4 | Slide deck / demo |
| Open upstream PR | Kagenti developer (Phase D) | Week 5 | PR to ODH repo |
| Track upstream review | Kagenti tech lead | Weekly | Status in standup |

---

## 12. Decision Record

| Decision | Rationale | Round |
|----------|-----------|-------|
| Three-tier deployment model (Product, RHOAI/DSC, Quickstart) | PM feedback: RHOAI integration is primary productization vehicle | V6 (R2) |
| ODH component handler creates `KagentiPlatform` CR (thin wrapper) | Mirrors kserve/ray pattern. ~200 lines contributed upstream | V6 (R2) |
| `managementState` tri-state replaces `enabled: bool` | Aligns with ODH/RHOAI vocabulary | V6 (R2) |
| Dual CSV bundles (standalone: soft deps, RHOAI: hard deps) | Standalone needs incremental adoption; RHOAI guarantees all deps | V7 (R3) |
| Overlay image bridge for ODH contribution gap | Standard Red Hat practice. Non-blocking | V7 (R3) |
| SSA field manager boundaries for CRD ownership transfer | Clean Managed->Unmanaged graduation | V7 (R3) |
| ODH RFC filed by Week 2, owned by Kagenti tech lead | Early visibility prevents review bottleneck | V8 (R4) |
| Overlay governance via technical gates (tag, registry, TTL) | Policy-only controls insufficient | V8 (R4) |
| Unmanaged health checks: same RBAC, `Unknown` for off-namespace | No RBAC expansion needed | V8 (R4) |
| Infrastructure `requirement: Required\|Optional\|Ignored` | Consistent vocabulary | V7 (R3) |
| Observability deconfliction: defer MLflow to RHOAI | Avoids duplicate instances | V6 (R2) |
| Formal dependency mapping table | Connects components to Red Hat operators | V6 (R2) |
| Two-tier operator split (Product vs. Quickstart) | Productization requires narrow RBAC | V3 (original) |
| Product operator validates but does not install infrastructure | Reduces RBAC, enables certification | V3 (original) |
| Single CRD with two controllers | Minimizes user-facing surface | V5 (original) |
| `kagenti-prereqs` static Helm chart | Bridges validate-only and 30 manual steps | V5 (original) |
| Narrow RBAC (no escalate, no CRD creation) | Passes Red Hat security review | V4 (original) |
| Quickstart creates Platform CR once, never updates | Clean ownership boundary | V4 (original) |
| SSA for adoption, not Helm release import | Native K8s API, auditable | V5 (original) |
| Grace period + annotation for upgrade coordination | Prevents false Blocked during upgrades | V4 (original) |
| Component mode: Managed \| Removed \| Unmanaged | Clear semantics, ODH-compatible | V6 (R2) |
| Deletion policy with confirmation annotation | Prevents accidental destruction | V2 (original) |
| Dynamic component criticality (computed from config) | Avoids false alerts | V3 (original) |

---

## Appendix A: Quickstart Phase Ordering

```
cert-manager ──┐
               ├──► kagenti-deps ──┐
Gateway API ───┘                    │
                                    ├──► kagenti (operator + UI + webhook)
Istio ─────────► ztunnel ready ─────┘
                                    │
Tekton ────────► Shipwright ────────┘
                                    │
SPIRE ─────────► CSI driver ────────┘
                                    │
Keycloak ──────► realm ready ───────┘
```

## Appendix B: Component Criticality Matrix

Criticality is computed dynamically from the resolved `KagentiPlatform` spec:

| Component | Default Criticality | Condition for Change |
|-----------|-------------------|---------------------|
| Istio | Critical | Always Critical when required |
| SPIRE | Critical | Always Critical when required |
| cert-manager | Critical | Always Critical when required |
| Gateway API | Critical | Always Critical when required |
| Tekton | Required | Critical if `agentOperator` enabled |
| Shipwright | Required | Critical if `agentOperator` enabled |
| Keycloak | Required | Critical if `ui.auth` Managed; Optional if not |
| OTel Collector | Optional | Required if `observability` Managed |
| Phoenix | Optional | Required if `observability.phoenix` Managed |
| MLflow | Optional | Always Optional |
| Kiali | Optional | Always Optional |
| MCP Inspector | Optional | Always Optional |
| metrics-server | Optional | Always Optional |
| Container Registry | Optional | Required on Kind (no external registry) |
