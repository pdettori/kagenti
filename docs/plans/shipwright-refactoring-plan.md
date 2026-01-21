# Shipwright Build Refactoring Plan

## Overview

This plan outlines the refactoring of the Kagenti UI to trigger container image builds via **Shipwright Build** (`build.shipwright.io`) instead of the current AgentBuild CRD + Tekton pipeline approach.

### Current State
- **UI** creates `AgentBuild` CRD → Kagenti Operator triggers Tekton Pipeline
- **Agent CRD** references `AgentBuild` via `imageSource.buildRef`
- Operator watches AgentBuild completion and updates Agent with built image

### Target State
- **UI** creates Shipwright `Build` + `BuildRun` CRDs directly
- **Agent CRD** is created with direct image reference (after build completes) OR uses a new field to reference Shipwright Build
- UI polls BuildRun status and creates Agent when build succeeds
- User can select `ClusterBuildStrategy` in UI

### Key Resources

| Resource | API Group | Purpose |
|----------|-----------|---------|
| Build | `shipwright.io/v1beta1` | Defines build configuration (source, strategy, output) |
| BuildRun | `shipwright.io/v1beta1` | Triggers and tracks a build execution |
| ClusterBuildStrategy | `shipwright.io/v1beta1` | Cluster-wide build strategy (e.g., `buildah`, `buildah-insecure-push`) |

### Available ClusterBuildStrategies

| Strategy | Use Case |
|----------|----------|
| `buildah-insecure-push` | Dev environment with internal registry (no TLS) |
| `buildah` | Production with external registries (quay.io, ghcr.io, docker.io) |

---

## Stage 1: Backend API Changes

**Objective**: Add Shipwright Build/BuildRun support to the backend without removing existing AgentBuild support.

### 1.1 Add Shipwright Constants

**File**: `kagenti/backend/app/core/constants.py`

Add new constants:
```python
# Shipwright CRD Definitions
SHIPWRIGHT_CRD_GROUP = "shipwright.io"
SHIPWRIGHT_CRD_VERSION = "v1beta1"
SHIPWRIGHT_BUILDS_PLURAL = "builds"
SHIPWRIGHT_BUILDRUNS_PLURAL = "buildruns"
SHIPWRIGHT_CLUSTER_BUILD_STRATEGIES_PLURAL = "clusterbuildstrategies"

# Shipwright defaults
DEFAULT_BUILD_STRATEGY_DEV = "buildah-insecure-push"
DEFAULT_BUILD_STRATEGY_PROD = "buildah"
SHIPWRIGHT_GIT_SECRET_NAME = "github-shipwright-secret"
DEFAULT_BUILD_TIMEOUT = "15m"
```

### 1.2 Add Shipwright Models

**File**: `kagenti/backend/app/routers/agents.py`

Add new Pydantic models:
```python
class ShipwrightBuildRequest(BaseModel):
    """Request fields for Shipwright build configuration."""
    buildStrategy: str = "buildah-insecure-push"  # ClusterBuildStrategy name
    dockerfile: str = "Dockerfile"
    buildArgs: Optional[List[str]] = None  # KEY=VALUE format
    buildTimeout: str = "15m"

class CreateAgentRequest(BaseModel):
    # ... existing fields ...

    # New: Shipwright build configuration
    useShipwright: bool = True  # Default to Shipwright for new builds
    shipwrightConfig: Optional[ShipwrightBuildRequest] = None
```

### 1.3 Add Shipwright Manifest Builders

**File**: `kagenti/backend/app/routers/agents.py`

Add new functions:

```python
def _build_shipwright_build_manifest(request: CreateAgentRequest) -> dict:
    """Build a Shipwright Build CRD manifest."""
    # Returns Build manifest with:
    # - source.git (url, revision, cloneSecret, contextDir)
    # - strategy (ClusterBuildStrategy reference)
    # - paramValues (dockerfile, build-args)
    # - output (image, pushSecret)
    # - timeout
    # - retention (succeededLimit, failedLimit)
    pass

def _build_shipwright_buildrun_manifest(build_name: str, namespace: str) -> dict:
    """Build a Shipwright BuildRun CRD manifest to trigger a build."""
    # Returns BuildRun manifest with:
    # - generateName: {build_name}-run-
    # - build.name reference
    pass
```

### 1.4 Add Shipwright API Endpoints

**File**: `kagenti/backend/app/routers/agents.py`

Add new endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/agents/{namespace}/{name}/shipwright-build` | GET | Get Shipwright Build status |
| `/agents/{namespace}/{name}/shipwright-buildrun` | GET | Get BuildRun status |
| `/agents/{namespace}/{name}/shipwright-buildrun` | POST | Trigger new BuildRun |
| `/build-strategies` | GET | List available ClusterBuildStrategies |

### 1.5 Modify Agent Creation Flow

**File**: `kagenti/backend/app/routers/agents.py`

Modify `create_agent` function:

```python
async def create_agent(request: CreateAgentRequest, kube: KubernetesService):
    if request.deploymentMethod == "source":
        if request.useShipwright:
            # 1. Create Shipwright Build
            build_manifest = _build_shipwright_build_manifest(request)
            await kube.create_custom_resource(
                group=SHIPWRIGHT_CRD_GROUP,
                version=SHIPWRIGHT_CRD_VERSION,
                plural=SHIPWRIGHT_BUILDS_PLURAL,
                namespace=request.namespace,
                body=build_manifest
            )

            # 2. Create BuildRun to trigger build
            buildrun_manifest = _build_shipwright_buildrun_manifest(
                request.name, request.namespace
            )
            buildrun = await kube.create_custom_resource(
                group=SHIPWRIGHT_CRD_GROUP,
                version=SHIPWRIGHT_CRD_VERSION,
                plural=SHIPWRIGHT_BUILDRUNS_PLURAL,
                namespace=request.namespace,
                body=buildrun_manifest
            )

            # 3. Return response (Agent created later after build completes)
            return CreateAgentResponse(
                success=True,
                name=request.name,
                namespace=request.namespace,
                message=f"Shipwright build started. BuildRun: {buildrun['metadata']['name']}"
            )
        else:
            # Existing AgentBuild flow (for backward compatibility)
            ...
```

---

## Stage 2: Frontend UI Changes

**Objective**: Update the Import Agent page to support Shipwright configuration and build strategy selection.

### 2.1 Add Build Strategy State

**File**: `kagenti/ui-v2/src/pages/ImportAgentPage.tsx`

Add new state:
```typescript
// Build configuration
const [useShipwright, setUseShipwright] = useState(true);
const [buildStrategy, setBuildStrategy] = useState('buildah-insecure-push');
const [availableStrategies, setAvailableStrategies] = useState<string[]>([]);
const [dockerfile, setDockerfile] = useState('Dockerfile');
const [buildTimeout, setBuildTimeout] = useState('15m');
```

### 2.2 Add API Service Methods

**File**: `kagenti/ui-v2/src/services/api.ts`

Add new methods:
```typescript
export const buildService = {
  // List available ClusterBuildStrategies
  listStrategies: async (): Promise<string[]> => {
    const response = await apiClient.get('/build-strategies');
    return response.data;
  },

  // Get Shipwright build status
  getBuildStatus: async (namespace: string, name: string): Promise<BuildStatus> => {
    const response = await apiClient.get(`/agents/${namespace}/${name}/shipwright-build`);
    return response.data;
  },

  // Get BuildRun status
  getBuildRunStatus: async (namespace: string, name: string): Promise<BuildRunStatus> => {
    const response = await apiClient.get(`/agents/${namespace}/${name}/shipwright-buildrun`);
    return response.data;
  },

  // Trigger new BuildRun
  triggerBuildRun: async (namespace: string, name: string): Promise<void> => {
    await apiClient.post(`/agents/${namespace}/${name}/shipwright-buildrun`);
  },
};
```

### 2.3 Add Build Strategy Selector Component

**File**: `kagenti/ui-v2/src/components/BuildStrategySelector.tsx`

Create new component:
```typescript
interface BuildStrategySelectorProps {
  value: string;
  onChange: (strategy: string) => void;
  registryType: string;  // Auto-select based on registry
}

export const BuildStrategySelector: React.FC<BuildStrategySelectorProps> = ({
  value,
  onChange,
  registryType,
}) => {
  // Fetch available strategies
  // Auto-select appropriate strategy based on registry:
  // - local → buildah-insecure-push
  // - external (quay, ghcr, dockerhub) → buildah
  // Allow manual override
};
```

### 2.4 Update Import Agent Form

**File**: `kagenti/ui-v2/src/pages/ImportAgentPage.tsx`

Add new form sections:

1. **Build Configuration Section** (expandable):
   - Build Strategy dropdown (with auto-selection based on registry)
   - Dockerfile path input
   - Build timeout input
   - Build arguments (optional, expandable list)

2. **Strategy Descriptions** (helper text):
   - `buildah-insecure-push`: "For internal registries without TLS (dev/kind clusters)"
   - `buildah`: "For external registries with TLS (quay.io, ghcr.io, docker.io)"

### 2.5 Update Submit Handler

Modify the mutation to include Shipwright config:
```typescript
const mutation = useMutation({
  mutationFn: async (data: CreateAgentData) => {
    return agentService.create({
      ...data,
      useShipwright: true,
      shipwrightConfig: {
        buildStrategy: buildStrategy,
        dockerfile: dockerfile,
        buildTimeout: buildTimeout,
        buildArgs: buildArgs.filter(arg => arg.trim()),
      },
    });
  },
});
```

---

## Stage 3: Build Status Polling & Agent Creation

**Objective**: Implement BuildRun status tracking and automatic Agent creation upon build completion.

### 3.1 Add BuildRun Status Types

**File**: `kagenti/backend/app/routers/agents.py`

```python
class BuildRunPhase(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"

class BuildRunStatusResponse(BaseModel):
    name: str
    namespace: str
    buildName: str
    phase: BuildRunPhase
    startTime: Optional[str] = None
    completionTime: Optional[str] = None
    outputImage: Optional[str] = None  # Populated on success
    failureMessage: Optional[str] = None  # Populated on failure
    conditions: List[BuildStatusCondition]
```

### 3.2 Implement Status Endpoint

**File**: `kagenti/backend/app/routers/agents.py`

```python
@router.get("/{namespace}/{name}/shipwright-buildrun")
async def get_shipwright_buildrun_status(
    namespace: str,
    name: str,
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> BuildRunStatusResponse:
    """Get the latest BuildRun status for an agent build."""
    # List BuildRuns with label selector for the agent name
    # Return the most recent one's status
    # Extract output image from status.output.digest
    pass
```

### 3.3 Add Agent Creation After Build

**File**: `kagenti/backend/app/routers/agents.py`

Add endpoint to create Agent after build succeeds:
```python
@router.post("/{namespace}/{name}/finalize-build")
async def finalize_build_and_create_agent(
    namespace: str,
    name: str,
    request: FinalizeAgentRequest,  # Contains original agent config
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> CreateAgentResponse:
    """Create Agent CRD after Shipwright build completes successfully."""
    # 1. Get BuildRun status, verify success
    # 2. Extract output image from BuildRun status
    # 3. Create Agent CRD with direct image reference
    # 4. Optionally create HTTPRoute
    pass
```

### 3.4 Frontend Build Progress Component

**File**: `kagenti/ui-v2/src/components/BuildProgress.tsx`

Create a component to show build progress:
```typescript
interface BuildProgressProps {
  namespace: string;
  name: string;
  onComplete: (image: string) => void;
  onError: (error: string) => void;
}

export const BuildProgress: React.FC<BuildProgressProps> = ({
  namespace,
  name,
  onComplete,
  onError,
}) => {
  // Poll BuildRun status every 5 seconds
  // Show progress indicator with phase
  // Show logs link (optional)
  // Call onComplete when succeeded
  // Call onError when failed
};
```

### 3.5 Update Import Flow

**File**: `kagenti/ui-v2/src/pages/ImportAgentPage.tsx`

Two-phase import flow:
1. **Submit**: Create Build + BuildRun, navigate to progress page
2. **Progress Page**: Poll status, show progress, create Agent on completion

Or single-page flow with modal:
1. **Submit**: Create Build + BuildRun
2. **Show Modal**: Display build progress
3. **On Success**: Create Agent automatically, close modal, show success

---

## Stage 4: Cleanup and Migration

**Objective**: Remove AgentBuild dependency and ensure smooth transition.

### 4.1 Add Feature Flag

**File**: `kagenti/backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # ...existing settings...

    # Build system configuration
    use_shipwright_builds: bool = True  # Feature flag for Shipwright
    default_build_strategy: str = "buildah-insecure-push"
```

### 4.2 Backend Deprecation

**File**: `kagenti/backend/app/routers/agents.py`

1. Add deprecation warning to AgentBuild endpoints
2. Keep AgentBuild support for existing builds (read-only)
3. Log warning when AgentBuild is used

### 4.3 UI Migration

**File**: `kagenti/ui-v2/src/pages/ImportAgentPage.tsx`

1. Default to Shipwright for all new builds
2. Remove AgentBuild-specific UI elements
3. Keep backward compatibility for viewing existing AgentBuild status

### 4.4 Documentation Updates

Update documentation:
- `docs/install.md`: Add Shipwright requirements
- `docs/new-agent.md`: Update build instructions
- `docs/components.md`: Document Shipwright integration

---

## Stage 5: Testing and Validation

### 5.1 Backend Unit Tests

**File**: `kagenti/backend/tests/test_shipwright.py`

Test cases:
- Build manifest generation (dev registry, external registry)
- BuildRun manifest generation
- Build strategy selection logic
- Status parsing

### 5.2 Integration Tests

**File**: `kagenti/tests/e2e/test_shipwright_build.py`

Test cases:
- Create Build + BuildRun for internal registry
- Create Build + BuildRun for external registry (quay.io)
- Poll BuildRun status until completion
- Create Agent after successful build
- Handle build failures gracefully

### 5.3 Manual Testing Checklist

- [ ] Build with `buildah-insecure-push` on Kind cluster
- [ ] Build with `buildah` pushing to quay.io
- [ ] Strategy auto-selection based on registry
- [ ] Manual strategy override
- [ ] Build progress display
- [ ] Build failure handling
- [ ] Agent creation after successful build
- [ ] HTTPRoute creation

---

## Implementation Order

| Stage | Description | Dependencies | Estimated Effort |
|-------|-------------|--------------|------------------|
| 1 | Backend API Changes | None | Medium |
| 2 | Frontend UI Changes | Stage 1 | Medium |
| 3 | Build Status & Agent Creation | Stages 1, 2 | Medium |
| 4 | Cleanup and Migration | Stages 1-3 | Low |
| 5 | Testing and Validation | Stages 1-4 | Medium |

---

## Shipwright Build Manifest Example

```yaml
apiVersion: shipwright.io/v1beta1
kind: Build
metadata:
  name: weather-service
  namespace: team1
  labels:
    kagenti.io/type: agent
    kagenti.io/protocol: a2a
    kagenti.io/framework: LangGraph
    app.kubernetes.io/created-by: kagenti-ui
spec:
  source:
    type: Git
    git:
      url: https://github.com/kagenti/agent-examples
      revision: main
      cloneSecret: github-shipwright-secret
    contextDir: a2a/weather_service
  strategy:
    name: buildah-insecure-push
    kind: ClusterBuildStrategy
  paramValues:
    - name: dockerfile
      value: Dockerfile
  output:
    image: registry.cr-system.svc.cluster.local:5000/weather-service:v0.0.1
  timeout: 15m
  retention:
    succeededLimit: 3
    failedLimit: 3
```

## Shipwright BuildRun Manifest Example

```yaml
apiVersion: shipwright.io/v1beta1
kind: BuildRun
metadata:
  generateName: weather-service-run-
  namespace: team1
  labels:
    kagenti.io/type: agent
    kagenti.io/agent-name: weather-service
    app.kubernetes.io/created-by: kagenti-ui
spec:
  build:
    name: weather-service
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Shipwright not installed | Check for Shipwright CRDs on startup, show error if missing |
| Build strategy not found | Validate strategy exists before creating Build |
| Registry push failures | Clear error messages with troubleshooting steps |
| Backward compatibility | Keep AgentBuild support read-only for existing builds |

---

## Future Considerations

1. **Tool Builds**: Apply same pattern to MCP tool builds (Phase 2)
2. **Build Caching**: Configure Shipwright build caching for faster rebuilds
3. **Multi-arch Builds**: Support building for multiple architectures
4. **Build Logs Streaming**: Stream build logs to UI in real-time
5. **Webhook Triggers**: Support GitHub webhook-triggered builds
