# Enhanced Test Scanning + orchestrate:review

**Date:** 2026-02-26
**Status:** Approved

## Problem

The current `orchestrate:scan` test coverage section is minimal — it counts test files
and checks if CI runs them. This misses:

- Which test frameworks and coverage tools are configured
- What coverage tool to add when missing
- Categorized analysis (backend vs UI vs E2E vs infra)
- Infra testing is about variant coverage, not code coverage
- No review phase exists in the orchestration pipeline

## Design

### 1. Enhanced Test Section in orchestrate:scan

Replace the current flat test coverage section with 4 categorized subsections.

#### 1.1 Backend Tests (pytest / go test)

Detect:
- Framework + version (pytest from pyproject.toml, go test from go.mod)
- Test file count and test function count (grep `def test_` / `func Test`)
- Coverage tooling: pytest-cov in deps, `[tool.coverage]` in pyproject.toml,
  `-coverprofile` in Makefile/go test invocations
- CI execution: which workflow runs tests, which triggers

Report format:
```markdown
### Backend Tests
- Framework: pytest 8.x (Python) / go test + Ginkgo v2.21 (Go)
- Test files: N
- Test functions: ~M
- Coverage tool: missing (recommend: add `pytest-cov>=4.0` to dev deps)
- Coverage config: missing (recommend: add `[tool.coverage.run] source = ["src"]` to pyproject.toml)
- CI execution: running in ci.yaml on PR + push
```

#### 1.2 UI Tests (Playwright / jest / vitest)

Detect:
- Framework from package.json devDependencies
- Spec file count and test block count
- Coverage config (istanbul, c8, playwright coverage plugin)
- CI execution status

Report format:
```markdown
### UI Tests
- Framework: Playwright 1.50 (TypeScript)
- Spec files: N
- Test blocks: ~M
- Coverage tool: n/a (Playwright E2E — coverage not applicable)
- CI execution: runs in e2e-kind.yaml
```

#### 1.3 E2E Tests (cluster-level)

Detect:
- Test files and functions
- Feature coverage map: scan test file names and imports to identify which
  platform features are tested (keycloak, shipwright, agent conversation,
  mlflow, phoenix, etc.)
- CI trigger matrix: which workflows run E2E, on which events (push, PR,
  manual), on which platforms (Kind, OCP, HyperShift)

Report format:
```markdown
### E2E Tests
- Test files: N
- Test functions: ~M
- Feature coverage:
  | Feature | Test File | Status |
  |---------|-----------|--------|
  | Keycloak auth | test_keycloak.py | covered |
  | Shipwright builds | test_shipwright_build.py | covered |
  | Agent conversation | test_agent_conversation.py | covered |
  | MLflow traces | test_mlflow_traces.py | covered |
  | UI agent discovery | test_ui_agent_discovery.py | covered |
- CI trigger matrix:
  | Platform | Push to main | PR | Manual |
  |----------|-------------|-----|--------|
  | Kind | e2e-kind.yaml | e2e-kind-pr.yaml | — |
  | HyperShift | e2e-hypershift.yaml | e2e-hypershift-pr.yaml | — |
```

#### 1.4 Infra Tests (Helm / Ansible / Shell)

No code coverage percentage. Score as variant coverage.

Detect:
- Deployment targets: scan CI workflows and scripts for Kind, OCP,
  HyperShift references
- Value variants: scan Helm values files and CI env vars for which config
  combos are exercised (istio.enabled, spire.enabled, auth modes, etc.)
- Static validation: Helm lint in CI? shellcheck in CI? Ansible molecule
  tests? Dockerfile lint (hadolint)?

Report format:
```markdown
### Infra Tests
- Deployment variants tested:
  | Variant | CI Workflow | Values File |
  |---------|------------|-------------|
  | Kind K8s 1.32 | e2e-kind.yaml | envs/kind/values.yaml |
  | OCP 4.20 HyperShift | e2e-hypershift.yaml | envs/ocp/values.yaml |
- Value variant coverage:
  | Feature Toggle | Tested On | Tested Off |
  |---------------|-----------|------------|
  | istio.enabled | Kind, OCP | — |
  | spire.enabled | OCP | Kind |
- Static validation:
  | Check | Status |
  |-------|--------|
  | Helm lint | in CI |
  | shellcheck | in CI |
  | hadolint | in CI |
  | yamllint | in CI |
  | Ansible molecule | missing |
```

### 2. orchestrate:review — Phase 7

New skill added as Phase 7 in the orchestration pipeline.

#### Purpose

Review all orchestration PRs after phases 2-6 create them. Acts as a quality
gate before merge.

#### Workflow

1. List open PRs on the target repo created by orchestration phases
2. For each PR, run `github:pr-review` checklist:
   - Commit conventions (signed-off, emoji prefix, imperative mood)
   - PR format (title, summary section)
   - Area-specific checks (Python lint, Helm lint, shell checks, security)
3. Cross-PR consistency checks:
   - Pre-commit hooks (phase 2) align with CI lint jobs (phase 4)
   - Tests added (phase 3) are run by CI workflows (phase 4)
   - CODEOWNERS (phase 5) covers paths from earlier phases
   - Replicated skills (phase 6) reference correct paths
4. Draft review summary per PR with verdict (approve/request changes/comment)
5. Present to user for approval
6. Post reviews via GitHub API

#### Router Table Update

| Phase | Skill | PR | Description |
|-------|-------|-----|-------------|
| 0 | orchestrate:scan | -- | Assess target repo |
| 1 | orchestrate:plan | -- | Create phased plan |
| 2 | orchestrate:precommit | PR #1 | Pre-commit + linting |
| 3 | orchestrate:tests | PR #2 | Test infrastructure |
| 4 | orchestrate:ci | PR #3 | CI + security scanning |
| 5 | orchestrate:security | PR #4 | Governance files |
| 6 | orchestrate:replicate | PR #5 | Claude Code skills |
| 7 | orchestrate:review | -- | Review all orchestration PRs |

## Implementation Scope

### Files to create:
- `.claude/skills/orchestrate:review/SKILL.md` — new Phase 7 skill

### Files to modify:
- `.claude/skills/orchestrate:scan/SKILL.md` — enhanced test section
- `.claude/skills/orchestrate/SKILL.md` — add Phase 7 to router table

### No files to delete.
