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

## Stage 3: Build Progress Page & Auto-Finalization

**Objective**: Implement a dedicated Build Progress page that tracks BuildRun status and automatically creates the Agent upon build completion.

### 3.1 Store Agent Config in Build Annotations

**Problem**: When using Shipwright, the Agent CRD is not created until the build completes. We need to preserve the user's agent configuration (protocol, framework, HTTPRoute, env vars, etc.) during the build.

**Solution**: Store agent configuration in the Shipwright Build's annotations.

**File**: `kagenti/backend/app/routers/agents.py`

In `_build_shipwright_build_manifest()`:
```python
# Build agent configuration to store in annotation
agent_config = {
    "protocol": request.protocol,
    "framework": request.framework,
    "createHttpRoute": request.createHttpRoute,
    "registrySecret": request.registrySecret,
}
if request.envVars:
    agent_config["envVars"] = [ev.model_dump(exclude_none=True) for ev in request.envVars]
if request.servicePorts:
    agent_config["servicePorts"] = [sp.model_dump() for sp in request.servicePorts]

# Add to Build manifest
manifest["metadata"]["annotations"] = {
    "kagenti.io/agent-config": json.dumps(agent_config),
}
```

### 3.2 Add Comprehensive Build Info Endpoint

**File**: `kagenti/backend/app/routers/agents.py`

```python
class ShipwrightBuildInfoResponse(BaseModel):
    """Combined Build and BuildRun status with agent config."""
    # Build info
    name: str
    namespace: str
    buildRegistered: bool
    outputImage: str
    strategy: str
    gitUrl: str
    gitRevision: str
    contextDir: str

    # Latest BuildRun info
    hasBuildRun: bool
    buildRunName: Optional[str] = None
    buildRunPhase: Optional[str] = None  # Pending, Running, Succeeded, Failed
    buildRunStartTime: Optional[str] = None
    buildRunCompletionTime: Optional[str] = None
    buildRunOutputImage: Optional[str] = None
    buildRunOutputDigest: Optional[str] = None
    buildRunFailureMessage: Optional[str] = None

    # Agent configuration from annotations
    agentConfig: Optional[AgentConfigFromBuild] = None

@router.get("/{namespace}/{name}/shipwright-build-info")
async def get_shipwright_build_info(...) -> ShipwrightBuildInfoResponse:
    """Get full Shipwright Build info including agent config and BuildRun status."""
```

### 3.3 Finalize Build Endpoint

**File**: `kagenti/backend/app/routers/agents.py`

```python
@router.post("/{namespace}/{name}/finalize-shipwright-build")
async def finalize_shipwright_build(
    namespace: str,
    name: str,
    request: FinalizeShipwrightBuildRequest,  # All fields optional
    kube: KubernetesService = Depends(get_kubernetes_service),
) -> CreateAgentResponse:
    """Create Agent CRD after Shipwright build completes successfully.

    Reads agent configuration from Build annotations if not provided in request.
    """
    # 1. Get latest BuildRun, verify success
    # 2. Extract output image from BuildRun status
    # 3. Read agent config from Build annotations
    # 4. Merge request with stored config (request takes precedence)
    # 5. Create Agent CRD with built image
    # 6. Create HTTPRoute if createHttpRoute is true
    # 7. Add kagenti.io/shipwright-build annotation to Agent
```

### 3.4 Build Progress Page

**File**: `kagenti/ui-v2/src/pages/BuildProgressPage.tsx`

A dedicated page at `/agents/:namespace/:name/build` that:
- Polls build info every 5 seconds using `shipwrightService.getBuildInfo()`
- Shows progress bar with phase (Pending → Running → Succeeded/Failed)
- Displays build details (strategy, duration, BuildRun name)
- Shows source configuration (Git URL, revision, context dir, output image)
- Shows agent configuration that will be applied (protocol, framework, HTTPRoute, etc.)
- **Auto-finalizes** when build succeeds (calls `finalizeBuild()`)
- Redirects to agent detail page after successful finalization
- Shows retry button on build failure

```typescript
// Auto-finalize when build succeeds
useEffect(() => {
  if (buildInfo?.buildRunPhase === 'Succeeded' && !isAutoFinalizing) {
    setIsAutoFinalizing(true);
    finalizeMutation.mutate();
  }
}, [buildInfo?.buildRunPhase]);
```

### 3.5 Smart Navigation Flow

**Files**:
- `kagenti/ui-v2/src/App.tsx` - Add route for `/agents/:namespace/:name/build`
- `kagenti/ui-v2/src/pages/ImportAgentPage.tsx` - Navigate to build page after submission
- `kagenti/ui-v2/src/pages/AgentDetailPage.tsx` - Redirect to build page if build exists but agent doesn't

**Import Flow**:
1. User submits form → Creates Build + BuildRun
2. Navigate to `/agents/{namespace}/{name}/build`
3. Build Progress page polls status
4. On success → Auto-finalize → Redirect to `/agents/{namespace}/{name}`

**Direct Navigation Handling**:
- If user navigates to `/agents/{namespace}/{name}` while build is in progress:
  - Check if Agent exists → If not, check for Shipwright Build
  - If Build exists → Redirect to `/agents/{namespace}/{name}/build`
  - If no Build → Show "Agent not found" error

### 3.6 Agent Detail Page - Shipwright Build Status

**File**: `kagenti/ui-v2/src/pages/AgentDetailPage.tsx`

For agents built with Shipwright (have `kagenti.io/shipwright-build` annotation):
- Fetch and display Shipwright Build status on the Status tab
- Show Build info (name, strategy, output image, Git source)
- Show latest BuildRun info (phase, duration, output image with digest)

---

## Stage 4: Cleanup and Migration

**Objective**: Deprecate AgentBuild, enforce Shipwright for new builds, and update documentation.

### 4.1 Feature Flag (Already Implemented)

**File**: `kagenti/backend/app/core/config.py`

```python
class Settings(BaseSettings):
    use_shipwright_builds: bool = True
    shipwright_default_strategy: str = "buildah-insecure-push"
    shipwright_default_timeout: str = "15m"
```

### 4.2 Backend Deprecation

**File**: `kagenti/backend/app/routers/agents.py`

**Implemented changes:**
1. Marked `get_agent_build_status` endpoint as deprecated using FastAPI's `deprecated=True`
2. Added warning log when deprecated endpoint is called
3. Added warning log when AgentBuild creation is attempted (useShipwright=False)
4. Added deprecation docstring to `_build_agent_build_manifest()` function
5. Updated `delete_agent` to also delete Shipwright Build and BuildRuns

```python
@router.get(
    "/{namespace}/{name}/build",
    response_model=BuildStatusResponse,
    deprecated=True,
    summary="Get AgentBuild status (deprecated)",
)
async def get_agent_build_status(...):
    """DEPRECATED: Use /shipwright-build-info endpoint instead."""
    logger.warning("Deprecated endpoint called: get_agent_build_status...")
```

### 4.3 UI Migration

**File**: `kagenti/ui-v2/src/pages/ImportAgentPage.tsx`

**Implemented changes:**
1. Removed "Use Shipwright" checkbox - Shipwright is now always used for source builds
2. Removed `useShipwright` state variable
3. Form submission always sets `useShipwright: true`
4. Kept backward compatibility for viewing existing AgentBuild status on Agent detail page

### 4.4 Documentation Updates

**Updated files:**

**`docs/components.md`:**
- Added "Container Build Systems" section comparing Shipwright vs AgentBuild
- Documented Shipwright build flow and ClusterBuildStrategies
- Added Shipwright Build YAML example
- Marked AgentBuild example as deprecated

**`docs/new-agent.md`:**
- Added "Step 5: Configure Build Options" for Shipwright settings
- Documented build strategy auto-selection based on registry type
- Documented advanced build options (Dockerfile, timeout, build args)
- Updated to describe Build Progress page flow
- Updated Troubleshooting section with Shipwright-specific commands

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
