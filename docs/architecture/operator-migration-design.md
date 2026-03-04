# Kagenti Operator Migration Design

> **Version**: 5.0 (Final)
> **Date**: 2026-03-04
> **Status**: Approved after 5-round architectural review
> **Tracking Issue**: [#828](https://github.com/kagenti/kagenti/issues/828)

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. Background and Motivation](#2-background-and-motivation)
  - [2.1 Current State: Ansible/Helm Installer](#21-current-state-ansiblehelm-installer)
  - [2.2 Why Migrate to an Operator](#22-why-migrate-to-an-operator)
  - [2.3 Product Manager Context](#23-product-manager-context)
- [3. Architecture Overview](#3-architecture-overview)
  - [3.1 Two-Tier Operator Model](#31-two-tier-operator-model)
  - [3.2 Tier 1: Kagenti Platform Operator (Product)](#32-tier-1-kagenti-platform-operator-product)
  - [3.3 Tier 1 Observability Controller](#33-tier-1-observability-controller)
  - [3.4 Tier 2: Kagenti Quickstart Installer (Dev Tool)](#34-tier-2-kagenti-quickstart-installer-dev-tool)
  - [3.5 Companion: kagenti-prereqs Helm Chart](#35-companion-kagenti-prereqs-helm-chart)
- [4. CRD Design: KagentiPlatform](#4-crd-design-kagentiplatform)
  - [4.1 Full CR Schema](#41-full-cr-schema)
  - [4.2 Status Subresource](#42-status-subresource)
  - [4.3 Infrastructure Validation](#43-infrastructure-validation)
- [5. Controller Architecture](#5-controller-architecture)
  - [5.1 Platform Controller](#51-platform-controller)
  - [5.2 Observability Controller](#52-observability-controller)
  - [5.3 Two Controllers, One CRD](#53-two-controllers-one-crd)
  - [5.4 Phase-Based State Machine (Quickstart)](#54-phase-based-state-machine-quickstart)
- [6. Component Interface and Extensibility](#6-component-interface-and-extensibility)
  - [6.1 Component Interface](#61-component-interface)
  - [6.2 Installation Strategies](#62-installation-strategies)
  - [6.3 Adding a New Package](#63-adding-a-new-package)
- [7. RBAC and Security](#7-rbac-and-security)
  - [7.1 Product Operator RBAC (Tier 1)](#71-product-operator-rbac-tier-1)
  - [7.2 Security Properties](#72-security-properties)
  - [7.3 Comparison: Monolithic vs. Two-Tier RBAC](#73-comparison-monolithic-vs-two-tier-rbac)
- [8. OLM Subscription Lifecycle (Quickstart)](#8-olm-subscription-lifecycle-quickstart)
- [9. Day-2 Operations](#9-day-2-operations)
  - [9.1 Upgrade Coordination](#91-upgrade-coordination)
  - [9.2 Drift Detection](#92-drift-detection)
  - [9.3 Health and Degradation Model](#93-health-and-degradation-model)
  - [9.4 Deletion Policy](#94-deletion-policy)
  - [9.5 Ansible vs. Operator Comparison](#95-ansible-vs-operator-comparison)
- [10. Migration Path from Ansible](#10-migration-path-from-ansible)
  - [10.1 Adoption via Server-Side Apply](#101-adoption-via-server-side-apply)
  - [10.2 Graduation Path](#102-graduation-path)
  - [10.3 UX Preservation](#103-ux-preservation)
- [11. Implementation Timeline](#11-implementation-timeline)
- [12. Consolidated Decision Record](#12-consolidated-decision-record)
- [Appendix A: Quickstart Phase Ordering](#appendix-a-quickstart-phase-ordering)
- [Appendix B: Component Criticality Matrix](#appendix-b-component-criticality-matrix)

---

## 1. Executive Summary

This document presents the final architecture for migrating the Kagenti platform installer from an Ansible/Helm-based approach to a Kubernetes Operator-based approach. The design was refined through 5 rounds of internal architectural review between a Lead Architect and a Quality Advocate, with human reviewer input on security, RBAC, and productization constraints.

### Key Decisions

- **Two-tier split**: A product-grade Platform Operator (Tier 1) manages only Kagenti's own components. An optional Quickstart Operator (Tier 2) handles infrastructure prerequisites for dev/PoC environments.
- **Validate, don't install**: The product operator checks that infrastructure prerequisites (Istio, Keycloak, SPIRE, etc.) exist but does NOT install them. This keeps RBAC narrow and enables Konflux/OLM certification.
- **Single CRD, two controllers**: One `KagentiPlatform` CRD with a Platform Controller and an Observability Controller, minimizing user-facing surface area.
- **Static prereqs chart**: A `kagenti-prereqs` Helm chart provides auditable, review-before-apply prerequisite manifests for production clusters.
- **Narrow RBAC**: The product operator has no `escalate`, no CRD creation, no OLM management, and no third-party CR mutation. Read-only infrastructure validation only.

---

## 2. Background and Motivation

### 2.1 Current State: Ansible/Helm Installer

Kagenti currently uses an Ansible playbook (`roles/kagenti_installer`) that orchestrates 29+ sequential installation steps. The playbook handles:

- **Platform-adaptive logic**: The same component (e.g., "install SPIRE") resolves to completely different actions depending on whether the target is Kind, OpenShift 4.18 (fallback to upstream SPIRE Helm charts), or OpenShift 4.19+ (ZTWIM operator via OLM). This requires runtime detection of the cluster type and OCP version with multi-step fallback chains.
- **Cross-resource ordering with waits**: CRDs must exist before CRs can be created, operators must reach `Succeeded` before operands are applied, webhooks must be healthy before dependent resources are submitted. The playbook has retry loops ranging from 3 retries/15s (Helm installs) up to 90 retries/10s (TektonConfig readiness — 15 min).
- **Conflict detection**: On OpenShift, existing OLM-installed operators (cert-manager, Tekton) need to be detected and skipped rather than re-installed.
- **Post-install fixups**: Several resources created by operators need imperative patches afterward (TektonConfig security context, github-clone-step ConfigMap for Istio ambient, CA secret copying across namespaces, container registry DNS in Kind).
- **Diagnostic collection on failure**: Ansible's rescue blocks collect targeted pod status and logs before failing.

The two-level toggle architecture uses Ansible-level flags (controlling whether Ansible installs components natively) and Helm `components.*` toggles (controlling which resources Helm templates render). Environment files (`dev_values.yaml`, `ocp_values.yaml`, etc.) configure these for different deployment targets.

### 2.2 Why Migrate to an Operator

| Driver | Ansible Limitation | Operator Advantage |
|--------|--------------------|--------------------|
| Self-healing | None. Manual re-run on failure. | Continuous reconciliation restores desired state. |
| Drift detection | None. Manual `helm diff` required. | Controller detects and repairs drift automatically. |
| Day-2 operations | Re-run full playbook for any change. | Edit CR spec; controller applies minimal diff. |
| Productization | Cannot ship via OLM/Konflux. | Native OLM distribution, Red Hat certification. |
| Declarative UX | Imperative playbook execution. | `kubectl apply` a CR; watch status converge. |
| GitOps | Not GitOps-friendly. | CR can be managed by ArgoCD. |
| Observability | Check Ansible logs, manual `kubectl`. | `kubectl get kagentiplatform` shows full status. |

### 2.3 Product Manager Context

Internal discussions established several constraints that directly shaped this architecture:

> "Reducing as much of the dependencies as possible would be desirable as a prevention mechanism, otherwise we end up encoding that complexity somewhere."

This informed the two-tier split: the product operator is lean and certifiable; infrastructure complexity lives in an optional dev tool.

> "As we move the kagenti pieces to the product, the operator pattern would make most sense especially."

Team consensus that the operator pattern is the right long-term approach.

Additionally, images for Kagenti need to be provided through Konflux once APIs are solidified (RHAIRFE-1351). The operator architecture is designed with this constraint from the start.

---

## 3. Architecture Overview

### 3.1 Two-Tier Operator Model

The fundamental insight driving this architecture is that Kagenti has two fundamentally different concerns with different lifecycles and ownership:

| Concern | What | Lifecycle | Owner |
|---------|------|-----------|-------|
| Kagenti itself | Operator, Webhook, UI, MCP Gateway | Product lifecycle (Konflux, OLM) | Kagenti team |
| Infrastructure prerequisites | Istio, Keycloak, SPIRE, Tekton, etc. | External operator lifecycles | Platform team / cluster admin |

Encoding infrastructure installation into the product operator would mean that when Istio breaks, **our** operator is on the hook. When OSSM v3 changes its CR schema, **our** operator must be updated. The two-tier model avoids this coupling entirely.

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER ENTRY POINTS                           │
├──────────────────────┬──────────────────────┬───────────────────┤
│  Dev / Kind          │  Production OCP      │  GitOps           │
│  ./deploy.sh dev     │  OperatorHub +       │  ArgoCD applies   │
│                      │  kagenti-prereqs     │  manifests from   │
│                      │  chart               │  git repo         │
└──────────┬───────────┴──────────┬───────────┴─────────┬─────────┘
           │                      │                     │
           ▼                      │                     │
┌──────────────────────┐          │                     │
│ Tier 2: Quickstart   │          │                     │
│ Operator (dev only)  │          │                     │
│                      │          │                     │
│ Installs: Istio,     │          │                     │
│ Keycloak, SPIRE,     │          │                     │
│ Tekton, Shipwright,  │          │                     │
│ cert-manager, etc.   │          │                     │
│                      │          │                     │
│ CRD: KagentiQuick-   │          │                     │
│ start                │          │                     │
│                      │          │                     │
│ Creates once:        │          │                     │
│ KagentiPlatform CR ──┼──┐       │                     │
└──────────────────────┘  │       │                     │
                          ▼       ▼                     ▼
                    ┌─────────────────────────────────────────┐
                    │ Tier 1: Kagenti Platform Operator       │
                    │ (PRODUCT — Konflux / OLM)               │
                    │                                         │
                    │ CRD: KagentiPlatform                    │
                    │                                         │
                    │ ┌─────────────────────────────────────┐ │
                    │ │ Platform Controller                 │ │
                    │ │ • Validates infrastructure (r/o)    │ │
                    │ │ • Installs: Agent Operator,         │ │
                    │ │   Webhook, UI, MCP Gateway          │ │
                    │ │ • Configures: agent namespaces,     │ │
                    │ │   OAuth clients, SPIFFE configs     │ │
                    │ │ • Drift detection + self-healing    │ │
                    │ └─────────────────────────────────────┘ │
                    │ ┌─────────────────────────────────────┐ │
                    │ │ Observability Controller             │ │
                    │ │ • Installs: OTel Collector (with    │ │
                    │ │   Kagenti-specific pipeline config) │ │
                    │ │ • Installs: Phoenix, MLflow         │ │
                    │ │ • Owns GenAI semconv transforms     │ │
                    │ └─────────────────────────────────────┘ │
                    │                                         │
                    │ Same OLM bundle, two controllers,       │
                    │ one CRD, narrow RBAC                    │
                    └─────────────────────────────────────────┘
                                      │
                          validates presence of
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │ Infrastructure (NOT managed by Kagenti) │
                    │                                         │
                    │ Istio (OSSM v3 / upstream Helm)         │
                    │ Keycloak (RHBK / upstream Helm)         │
                    │ SPIRE (ZTWIM / upstream Helm)           │
                    │ Tekton (OpenShift Pipelines / upstream) │
                    │ Shipwright (OpenShift Builds / upstream) │
                    │ cert-manager (OCP operator / upstream)  │
                    │ Gateway API CRDs                        │
                    │                                         │
                    │ Installed by: cluster admin, GitOps,    │
                    │ kagenti-prereqs chart, or Quickstart    │
                    └─────────────────────────────────────────┘
```

### 3.2 Tier 1: Kagenti Platform Operator (Product)

- Shipped via Konflux and OLM. Red Hat certified.
- Manages ONLY Kagenti-owned components: Agent Operator, Webhook, UI, MCP Gateway, Agent Namespaces, OAuth client setup.
- Validates that required infrastructure exists (CRDs present, services reachable) but does NOT install it.
- Contains two controllers in one OLM bundle: Platform Controller and Observability Controller.
- Single CRD: `KagentiPlatform`.
- Narrow RBAC: no `escalate`, no CRD creation, no OLM management.

### 3.3 Tier 1 Observability Controller

The Observability Controller is part of the Tier 1 OLM bundle but runs as a separate controller watching the same `KagentiPlatform` CRD. It manages:

- OTel Collector with Kagenti-specific pipeline configuration (GenAI semantic convention transforms, span filtering for A2A, OAuth2 exporter for MLflow).
- Phoenix (LLM observability backend).
- MLflow (experiment tracking).

These are included in Tier 1 because the OTel Collector pipeline configuration is Kagenti-specific IP (not generic infrastructure). A user may disable observability entirely via `spec.observability.enabled: false`.

### 3.4 Tier 2: Kagenti Quickstart Installer (Dev Tool)

- Optional. For dev/demo/PoC environments only.
- NOT part of the product. NOT shipped via OLM or Konflux.
- Replaces the current Ansible installer.
- Manages all infrastructure prerequisites: Istio, Keycloak, SPIRE, Tekton, Shipwright, cert-manager, Gateway API, Kiali, etc.
- CRD: `KagentiQuickstart`.
- After installing infrastructure, creates a `KagentiPlatform` CR **once** (create-if-not-exists, never updates). The Platform Operator then takes over.
- Has broader permissions (OLM CRUD, Helm installs, namespace creation) because it runs only in dev environments.

### 3.5 Companion: kagenti-prereqs Helm Chart

For production OpenShift clusters where the Quickstart operator is not used, a static `kagenti-prereqs` Helm chart provides all prerequisite manifests (OLM Subscriptions, operand CRs, raw YAML). The admin can:

- Inspect the chart before applying (audit trail).
- Selectively enable components: `--set istio.enabled=true --set keycloak.enabled=true`.
- Commit the rendered manifests to a GitOps repository.
- Use it as a reference for crafting their own manifests.

The chart lives in the Kagenti repo alongside the operator (`charts/kagenti-prereqs/`), is versioned and tested alongside the operator (same CI matrix), but is NOT an operator — it's a plain Helm chart the admin runs once.

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
    enabled: true
    image: ""               # Override; defaults to operator-bundled version

  webhook:
    enabled: true           # SPIFFE identity injection
    image: ""

  ui:
    enabled: true
    auth:
      enabled: true
      keycloak:
        url: https://keycloak.keycloak.svc.cluster.local:8443
        realm: master
        credentialsSecretRef: { name: kagenti-keycloak-admin }
    frontend: { image: "" }
    backend:  { image: "" }

  mcpGateway:
    enabled: false

  agentNamespaces:
    - name: team1
      secretRef: { name: team1-credentials }
    - name: team2
      secretRef: { name: team2-credentials }

  # --- Infrastructure References (validate only, do NOT install) ---
  infrastructure:
    istio:       { required: true }
    spire:       { required: true, trustDomain: localtest.me }
    certManager: { required: true }
    tekton:      { required: true }
    shipwright:  { required: true }
    gatewayApi:  { required: true }

  # --- Observability (reconciled by Observability Controller) ---
  observability:
    enabled: true
    collector:
      exporters:
        phoenix: { enabled: true }
        mlflow:
          enabled: true
          auth: { enabled: true, clientSecretRef: { name: kagenti-mlflow-oauth } }
    phoenix:
      enabled: true
      storage: { type: postgresql, size: 10Gi }
    mlflow:
      enabled: true
      storage: { size: 5Gi }

  # --- Global ---
  domain: localtest.me
  deletionPolicy: Retain    # Retain | Delete
  imageOverrides:
    registry: ""
    pullSecretRef: ""
```

### 4.2 Status Subresource

Status is partitioned between the two controllers. Each writes to distinct sub-paths using separate SSA field managers to avoid conflicts.

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
    - type: InfrastructureReady   # All required infra present
      status: "True"
    - type: PlatformReady         # Core Kagenti components running
      status: "True"
    - type: ObservabilityReady    # OTel/Phoenix/MLflow running
      status: "True"
    - type: Available             # Core platform functional
      status: "True"
    - type: FullyOperational      # Core + observability
      status: "True"
```

### 4.3 Infrastructure Validation

The Platform Controller validates infrastructure on every reconciliation by checking CRD existence and service readiness. When prerequisites are missing, the status provides actionable guidance including a pointer to the `kagenti-prereqs` Helm chart.

The controller distinguishes between "never installed" (hard block) and "was working, now temporarily unhealthy" (grace period). A configurable grace period (default 10 minutes) prevents false `Blocked` status during infrastructure upgrades.

```go
func (r *Reconciler) evaluateInfraHealth(ctx context.Context,
    p *v1alpha1.KagentiPlatform) InfraStatus {

    for _, req := range p.Spec.Infrastructure.RequiredComponents() {
        if !r.detector.HasCRD(ctx, req.CRDGroupResource) {
            return InfraBlocked  // Hard block — never installed
        }

        prev := p.Status.Infrastructure[req.Name]
        ready, msg, _ := req.ReadinessCheck(ctx)
        if ready {
            continue
        }

        if prev.Status == "Ready" {
            // Was healthy, now unhealthy — apply grace period
            if prev.LastReadyTime.Add(r.infraGracePeriod).After(time.Now()) {
                r.setInfraCondition(p, req.Name, "Degraded", msg)
                continue
            }
        }
        return InfraBlocked
    }
    return InfraReady
}
```

The Quickstart operator can also set an annotation (`kagenti.dev/infra-upgrade-in-progress`) before starting an upgrade, which extends the grace period indefinitely while present.

---

## 5. Controller Architecture

### 5.1 Platform Controller

The Platform Controller handles the core Kagenti lifecycle:

```go
func (r *PlatformReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    platform := &v1alpha1.KagentiPlatform{}
    r.Get(ctx, req.NamespacedName, platform)

    // 1. Detect environment (OpenShift? version? pre-installed operators?)
    env := r.detector.Detect(ctx)

    // 2. Validate infrastructure prerequisites
    infraStatus := r.evaluateInfraHealth(ctx, platform)
    if infraStatus == InfraBlocked {
        platform.Status.Phase = "Blocked"
        return ctrl.Result{RequeueAfter: 30 * time.Second}, nil
    }

    // 3. Install/update core Kagenti components
    for _, component := range r.coreComponents {
        if component.Enabled(platform.Spec) {
            component.Install(ctx, platform, env)
        }
    }

    // 4. Configure agent namespaces (secrets, RBAC, labels)
    r.reconcileAgentNamespaces(ctx, platform)

    // 5. Set status
    platform.Status.Phase = "Ready"
    return ctrl.Result{RequeueAfter: 5 * time.Minute}, nil  // drift check
}
```

### 5.2 Observability Controller

The Observability Controller watches the same `KagentiPlatform` CRD but only reconciles the `spec.observability` section. It uses a hash of the observability spec to avoid unnecessary work when only core spec changes.

### 5.3 Two Controllers, One CRD

Both controllers ship in the same OLM bundle as separate Deployments. They use distinct SSA field managers for status updates to avoid write conflicts. Each controller uses spec-hash comparison to skip reconciliation when only the other controller's section changed.

### 5.4 Phase-Based State Machine (Quickstart)

The Quickstart Operator uses a phase-based state machine for infrastructure installation. Phases execute sequentially; components within a phase install concurrently:

| Phase | Components | Notes |
|-------|-----------|-------|
| 1. Foundation | cert-manager, Gateway API CRDs, metrics-server | No dependencies |
| 2. Mesh | Istio (base → istiod → CNI → ztunnel) | Strict internal ordering |
| 3. Identity | SPIRE (server → agent → CSI → OIDC) | Strict internal ordering |
| 4. Build | Tekton → Shipwright | Shipwright depends on Tekton |
| 5. Auth | Keycloak (operator → instance → realm → clients) | Sequential |
| 6. Observability | OTel Collector, Phoenix, MLflow | Concurrent |
| 7. Platform | Ingress Gateway, container registry, Kiali | Concurrent |
| 8. Handoff | Creates `KagentiPlatform` CR | Platform operator takes over |

Empty phases (all components disabled) are skipped. Already-ready phases are short-circuited on subsequent reconciliations.

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
|----------|-----------|---------|
| `HelmComponent` | Vanilla K8s, or OCP when no OLM operator exists | Istio on K8s, Phoenix, MLflow |
| `OLMComponent` | OpenShift with operator in catalog | OSSM v3, RHBK, OpenShift Pipelines |
| `ManifestComponent` | Simple CRD/YAML-only installs | Gateway API CRDs, Kiali addons |
| `ExternalComponent` | User-managed, validate connectivity only | External Keycloak, pre-existing Istio |

The OpenShift vs. Kubernetes branching is encapsulated inside each component, not in the phase or reconciler:

```go
func (k *KeycloakComponent) Install(ctx context.Context, p *KagentiPlatform, env *Environment) error {
    if p.Spec.Components.Keycloak.External != nil {
        return k.validateExternal(ctx, p.Spec.Components.Keycloak.External)
    }
    if env.IsOpenShift {
        return k.installViaOLM(ctx, p)   // RHBK Subscription → Keycloak CR
    }
    return k.installViaHelm(ctx, p)      // Helm chart with PostgreSQL
}
```

### 6.3 Adding a New Package

Adding a new component is a 3-file change with zero core refactoring:

| File | Change |
|------|--------|
| `api/v1alpha1/types.go` | Add field to `ComponentsSpec` struct |
| `controllers/components/newpkg.go` | Implement `Component` interface (embed `BaseHelmComponent` or `BaseOLMComponent`) |
| `controllers/phases/<phase>.go` or `main.go` | Register in the appropriate phase |

No changes to the reconciler, no changes to existing components.

---

## 7. RBAC and Security

### 7.1 Product Operator RBAC (Tier 1)

The product operator's ClusterRole is deliberately narrow:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kagenti-platform-operator
rules:
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
  - apiGroups: ["batch"]
    resources: ["jobs"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

  # Networking
  - apiGroups: ["gateway.networking.k8s.io"]
    resources: ["httproutes", "referencegrants"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["route.openshift.io"]
    resources: ["routes"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

  # Agent Operator sub-chart (read-only)
  - apiGroups: ["agent.kagenti.dev"]
    resources: ["agents", "agentbuilds", "agentcards"]
    verbs: ["get", "list", "watch"]

  # Namespace management (agent namespaces)
  - apiGroups: [""]
    resources: ["namespaces"]
    verbs: ["get", "list", "create", "update", "patch"]

  # Istio waypoints (read + create, not modify mesh)
  - apiGroups: ["gateway.networking.k8s.io"]
    resources: ["gateways"]
    verbs: ["get", "list", "watch", "create"]
```

### 7.2 Security Properties

| Property | How Achieved |
|----------|-------------|
| Least privilege | Operator can only manage Kagenti-owned resources. Cannot create CRDs, manage OLM, or modify third-party operator CRs. |
| No escalation | No `escalate` or `bind` verbs. Cannot create ClusterRoles or ClusterRoleBindings. |
| Infrastructure isolation | Read-only access to infrastructure CRDs for validation. Cannot modify Istio, Keycloak, or SPIRE resources. |
| Secret scoping | Per-namespace `secretRef` for agent namespaces. No single Secret with all credentials. |
| Audit trail | All actions attributable to `kagenti-platform-operator` ServiceAccount in audit logs. |
| Certifiability | RBAC surface passes Red Hat operator certification requirements. |

### 7.3 Comparison: Monolithic vs. Two-Tier RBAC

| Permission | Monolithic Orchestrator (rejected) | Product Operator (V5) |
|------------|------------------------------------|-----------------------|
| CRD management | `create`, `update`, `delete` on ALL CRDs | `get`, `list`, `watch` only |
| OLM access | Full Subscription/InstallPlan/CSV CRUD | None |
| Namespace scope | All namespaces | `kagenti-system` + agent namespaces |
| RBAC verbs | `bind`, `escalate` | None |
| Third-party CRs | Full CRUD on Istio, Keycloak, SPIRE | Read-only (validation) |
| Blast radius | Compromised operator = cluster-admin equivalent | Compromised operator = Kagenti components only |

---

## 8. OLM Subscription Lifecycle (Quickstart)

The Quickstart Operator (Tier 2 only) manages OLM Subscriptions for OpenShift prerequisites with the following safeguards:

| Aspect | Design Decision | Rationale |
|--------|----------------|-----------|
| Approval Policy | Always `Manual` | Prevents OLM from auto-upgrading operators and breaking operand CR schemas |
| Version Gating | Compatibility matrix (compiled + ConfigMap override) | Only approve InstallPlans for tested CSV versions |
| Operand CRs | `Unstructured` (no Go type imports) | Decouples from upstream API changes |
| Health Checking | CSV phase + operator Pod readiness + operand status conditions | Three-layer verification before marking Ready |
| Version Pinning | Compiled defaults + ConfigMap override | Fast CVE response without rebuilding the operator binary |

The version manifest is compiled into the Quickstart operator binary with ConfigMap override for CVE response:

```go
var DefaultVersions = VersionManifest{
    Istio:       {Chart: "istio/istiod", Version: "1.24.2"},
    SPIRE:       {Chart: "spiffe/spire", Version: "0.23.0"},
    Keycloak:    {Manifest: "github.com/keycloak/keycloak-k8s-resources", Version: "26.4"},
    Tekton:      {Manifest: "storage.googleapis.com/tekton-releases/pipeline", Version: "0.62.2"},
    CertManager: {Manifest: "github.com/cert-manager/cert-manager", Version: "1.16.3"},
    // OLM channels for OpenShift
    OSSM:        {OLMChannel: "stable-v3"},
    RHBK:        {OLMChannel: "stable-v26.4"},
    ZTWIM:       {OLMChannel: "stable-v1"},
}
```

---

## 9. Day-2 Operations

### 9.1 Upgrade Coordination

When infrastructure is upgraded (e.g., Istio OSSM v3.1 → v3.2), the Platform Operator may see transient unavailability. The grace period mechanism prevents false `Blocked` status:

- Default grace period: **10 minutes** (configurable).
- During grace period: status shows `Degraded`, not `Blocked`. Platform components remain operational.
- The Quickstart operator can set annotation `kagenti.dev/infra-upgrade-in-progress` to extend the grace period indefinitely during planned upgrades.
- After grace period expires without recovery: status escalates to `Blocked`.

### 9.2 Drift Detection

Three-tiered watch strategy:

| Tier | Mechanism | Latency | What It Catches |
|------|-----------|---------|-----------------|
| Tier 1: Security watches | controller-runtime `Watches` on `AuthorizationPolicy`, `ClusterSPIFFEID` | Immediate | Deleted/modified security policies |
| Tier 2: Owned resources | controller-runtime `Owns()` on Deployments, Services | Immediate | Modified/deleted Kagenti components |
| Tier 3: Periodic poll | `RequeueAfter: 5 minutes` | Up to 5 min | Everything else (ConfigMap drift, label changes) |

### 9.3 Health and Degradation Model

| Condition | Meaning | When True |
|-----------|---------|-----------|
| `Available` | Core platform is functional | All Critical + Required components healthy |
| `Degraded` | Optional component unhealthy | Any Optional component (MLflow, Kiali) is down |
| `FullyOperational` | Everything works | All components including optional are healthy |
| `Blocked` | Cannot proceed | Missing infrastructure prerequisites |

Component criticality is **computed dynamically** from the resolved config, not hardcoded. For example, Tekton is `Critical` only if `agentOperator.enabled` (build pipelines need it). Keycloak is `Critical` only if `ui.auth.enabled`.

### 9.4 Deletion Policy

| Policy | Behavior |
|--------|----------|
| `Retain` (default) | Finalizer removed, all components left running. Resources become unmanaged. |
| `Delete` | Reverse-order teardown of Kagenti components. Requires explicit annotation `kagenti.dev/confirm-delete=yes-destroy-everything`. Infrastructure is NEVER deleted by the product operator. |

A `ValidatingAdmissionWebhook` prevents accidental deletion with `Delete` policy unless the confirmation annotation is present.

### 9.5 Ansible vs. Operator Comparison

| Operation | Current (Ansible/Helm) | Proposed (Operator) |
|-----------|----------------------|---------------------|
| Upgrade a component | Re-run full playbook (~15 min) | Edit CR or upgrade operator image |
| Self-healing | None. Manual re-run. | Continuous reconciliation |
| Drift detection | None. Manual `helm diff`. | Automatic, tiered watches |
| Add component post-install | Edit env file, re-run playbook | Edit CR; controller installs only the new component |
| Remove component | Edit env file, re-run (orphaned resources) | Set `enabled: false`; controller cleans up |
| Multi-cluster | Run playbook per cluster | Apply CR per cluster (GitOps-friendly) |
| Disaster recovery | Re-run from scratch | CR + secrets exist; controller converges |
| Rollback | `helm rollback` per chart (manual) | Revert CR (or GitOps revision) |

---

## 10. Migration Path from Ansible

### 10.1 Adoption via Server-Side Apply

For existing clusters running the Ansible-installed stack, the Quickstart Operator can adopt existing resources using Kubernetes Server-Side Apply (SSA) with field ownership transfer. This is preferred over Helm release manipulation because SSA is a native, well-tested Kubernetes API.

The adoption process per component:

1. Discover existing resources by label, annotation, or well-known names.
2. Apply SSA patch with `kagenti-quickstart` field manager and `ForceOwnership`.
3. For Helm-installed resources: delete the Helm release Secret (tracking metadata only; actual resources remain).
4. Label all adopted resources with `kagenti.dev/managed-by=quickstart`.
5. Record provenance in status (original install method, version).

### 10.2 Graduation Path

| Step | Action | Result |
|------|--------|--------|
| 1. Parallel install | Install Tier 1 operator alongside Ansible-managed cluster | Operator validates infra (passes), manages Kagenti components. Ansible still manages infra. |
| 2. Quickstart adoption (optional) | Install Quickstart operator; it adopts existing infra resources | Quickstart manages infra lifecycle. Ansible no longer needed. |
| 3. Production graduation | Delete `KagentiQuickstart` CR with `deletionPolicy: Retain` | Infra remains, managed by admin/GitOps. Platform operator continues. |

### 10.3 UX Preservation

A `deploy.sh` wrapper script preserves the single-command experience:

```bash
# Dev (Kind) — identical simplicity to Ansible:
./deploy.sh dev

# Production (OpenShift) — admin applied prereqs already:
./deploy.sh ocp
```

The script includes the same preflight checks as the Ansible wrapper: Docker/Podman memory (>=16GB), CPU count (>=4), Helm version validation, and macOS SSL fixes.

---

## 11. Implementation Timeline

| Phase | Duration | Deliverables | Dependencies |
|-------|----------|-------------|-------------|
| **A: CRD + Platform Controller** | 4 weeks | `KagentiPlatform` CRD types, infra validation, core component installation (operator, webhook, UI), Helm SDK integration, envtest unit tests, Kind integration tests | None. Ansible continues working unchanged. |
| **B: Observability + Prereqs Chart** | 3 weeks | Observability controller (OTel, Phoenix, MLflow), `kagenti-prereqs` Helm chart extracted from `kagenti-deps`, E2E validation | Phase A complete. |
| **C: Quickstart Operator** | 3 weeks | Port Ansible phase logic to Go controller, all component strategies (Helm, OLM, Manifest), OpenShift/K8s detection, adoption logic (SSA), `deploy.sh` wrapper | Phase A complete. Phase B for full E2E. |
| **D: Productization** | 2 weeks | Konflux pipeline, OLM bundle generation, Red Hat certification prep, documentation (prereqs guide, migration guide, API reference), deprecate Ansible | Phases A-C complete. |

**Total estimated duration: ~12 weeks of focused development.**

---

## 12. Consolidated Decision Record

| Decision | Rationale | Round |
|----------|-----------|-------|
| Two-tier operator split (Product vs. Quickstart) | Productization requires narrow RBAC and no third-party coupling. Complexity stays in the dev tool. | R3 |
| Product operator validates but does not install infrastructure | Red Hat operator pattern. Reduces RBAC, eliminates third-party API coupling, enables Konflux certification. | R3 |
| Single CRD with two controllers | Minimizes user-facing surface. Hash-based reconciliation avoids status conflicts. | R5 |
| `kagenti-prereqs` static Helm chart | Bridges the gap between "validate only" and "30 manual steps." Admin can review, modify, or GitOps it. | R5 |
| Narrow RBAC (no `escalate`, no CRD creation) | Passes Red Hat security review. Minimal blast radius on compromise. | R4 |
| Quickstart creates Platform CR once, never updates | Clean ownership boundary. User can modify freely after creation. | R4 |
| SSA for adoption, not Helm release import | Native K8s API, auditable field ownership, works across all install methods. | R5 |
| Grace period + annotation for upgrade coordination | Prevents false `Blocked` during infra upgrades. No tight coupling. | R4 |
| Component mode enum: `Managed | External | Disabled | Adopted` | Clear semantics, no ambiguity about who manages what. | R2 |
| Version manifest compiled in binary + ConfigMap override | Fast CVE response without rebuilding. Sane defaults. | R4 |
| Component interface with strategy embedding | Adding a new package is a 3-file change. No core refactoring. | R1 |
| Deletion policy with confirmation annotation | Prevents accidental destruction of infrastructure. | R2 |
| Dynamic component criticality (computed from config) | Tekton is Critical only if builds enabled. Avoids false alerts. | R3 |

---

## Appendix A: Quickstart Phase Ordering

The Quickstart Operator's phase-based state machine mirrors the current Ansible installer's dependency graph:

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

Each phase gates on the previous phase's health. Within a phase, independent components install concurrently. Empty phases (all components disabled) are skipped. Already-ready phases are short-circuited on subsequent reconciliations.

---

## Appendix B: Component Criticality Matrix

Criticality is computed dynamically from the resolved `KagentiPlatform` spec:

| Component | Default Criticality | Condition for Change |
|-----------|--------------------|-----------------------|
| Istio | Critical | Always Critical when required |
| SPIRE | Critical | Always Critical when required |
| cert-manager | Critical | Always Critical when required |
| Gateway API | Critical | Always Critical when required |
| Tekton | Required | Critical if `agentOperator.enabled` |
| Shipwright | Required | Critical if `agentOperator.enabled` |
| Keycloak | Required | Critical if `ui.auth.enabled`; Optional if not |
| OTel Collector | Optional | Required if `observability.enabled` |
| Phoenix | Optional | Required if `observability.phoenix.enabled` |
| MLflow | Optional | Always Optional |
| Kiali | Optional | Always Optional |
| MCP Inspector | Optional | Always Optional |
| Metrics Server | Optional | Always Optional |
| Container Registry | Optional | Required on Kind (no external registry) |
