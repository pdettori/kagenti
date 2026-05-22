# Teleport: Remote Claude Code Execution in OpenShell Sandboxes

Teleport packages your local Claude Code context (CLAUDE.md, skills, settings)
into a Kagenti OpenShell sandbox and executes prompts remotely with full
isolation (Landlock, seccomp, network namespace, OPA policy).

## Prerequisites

- **kubectl** configured for your Kind or HyperShift cluster
- **Sandbox CRD** installed (`agents.x-k8s.io/v1alpha1`)
- **OpenShell gateway** running (`openshell-server` pod in target namespace)
- **LiteLLM proxy** running for LLM access (`litellm-model-proxy` in target namespace)

Check readiness:

```bash
# Sandbox CRD installed?
kubectl api-resources | grep sandboxes

# Gateway running?
kubectl get pods -n team1 -l app.kubernetes.io/name=openshell --no-headers

# LiteLLM running?
kubectl get pods -n team1 -l app=litellm-model-proxy --no-headers
```

## Quick Start

One command — packages context, deploys sandbox, sends prompt, cleans up:

```bash
scripts/openshell/teleport-session.sh --full "What project is described in CLAUDE.md?"
```

## Step-by-Step Usage

### 1. Package context

Bundles CLAUDE.md, settings.json, and selected skills into a ConfigMap:

```bash
scripts/openshell/teleport-session.sh --package
# Output: 8-char session ID (e.g., a3da31dd)
```

To include specific skills:

```bash
TELEPORT_SKILLS="sandbox:teleport,graph-loop" \
  scripts/openshell/teleport-session.sh --package
```

### 2. Deploy sandbox

Creates a Sandbox CR with the packaged context mounted:

```bash
scripts/openshell/teleport-session.sh --deploy --session a3da31dd
```

This creates:
- A Sandbox CR named `teleport-a3da31dd`
- A pod with the OpenShell base image (`ghcr.io/nvidia/openshell-community/sandboxes/base`)
- ConfigMap mounted at `/workspace/.claude-context`
- Context unpacked to `$HOME` (CLAUDE.md, .claude/skills/, .claude/settings.json)
- `ANTHROPIC_BASE_URL` pointing to LiteLLM proxy
- `ANTHROPIC_AUTH_TOKEN` from `litellm-virtual-keys` secret

### 3. Send prompts

```bash
scripts/openshell/teleport-session.sh --session a3da31dd \
  --prompt "List the Kubernetes namespaces mentioned in CLAUDE.md"
```

Claude Code runs inside the sandbox with:
- `claude --print --bare --model claude-sonnet-4-20250514`
- Read-only access to the teleported context
- Network isolated (OPA egress policy)
- Filesystem isolated (Landlock)

### 4. Cleanup

Deletes the Sandbox CR, pod, and ConfigMap:

```bash
scripts/openshell/teleport-session.sh --cleanup --session a3da31dd
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--namespace <ns>` | Target K8s namespace | `team1` |
| `--session <id>` | Session ID (auto-generated for `--package`) | — |
| `--timeout <secs>` | Prompt timeout | `120` |

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEPORT_NS` | Target namespace | `team1` |
| `TELEPORT_SKILLS` | Comma-separated skill names to include | — (none) |

## What Gets Teleported

| Item | Source | Destination in sandbox |
|------|--------|-----------------------|
| CLAUDE.md | Repo root | `$HOME/CLAUDE.md` |
| settings.json | `.claude/settings.json` (secrets stripped) | `$HOME/.claude/settings.json` |
| Skills | `.claude/skills/<name>/SKILL.md` (selected via `TELEPORT_SKILLS`) | `$HOME/.claude/skills/<name>/SKILL.md` |

**Size limit**: 800 KB total (ConfigMap max ~1 MB). If exceeded, reduce skills
or use fewer context files.

**Not teleported**: memory files, conversation history, workspace files,
git state. This is a one-shot context transfer, not a session migration.

## How It Works

```
Local machine                     Kind/HyperShift cluster
─────────────                     ──────────────────────
CLAUDE.md ─┐
skills/  ──┼─→ ConfigMap ──→ Sandbox CR ──→ Pod
settings ──┘      │              │            │
                  │              │            ├─ supervisor (Landlock, seccomp)
                  │              │            ├─ claude --print --bare
                  │              │            └─ ANTHROPIC_BASE_URL → LiteLLM
                  │              │
                  └──────────────┴─→ cleanup deletes both
```

The sandbox pod runs Claude Code via `claude --print --bare`, which:
- Skips CLAUDE.md auto-discovery (context loaded via `--bare`)
- Uses the LiteLLM proxy as the LLM backend
- Has no network access except to LiteLLM (OPA policy)
- Runs as non-root user (uid 998) in the sandbox container

## Claude Code Skill

Use `/sandbox:teleport` in Claude Code for guided teleport workflow.

## Testing

Run T7 teleport tests:

```bash
# Without LLM (infrastructure only):
uv run pytest kagenti/tests/e2e/openshell/test_T7_1_teleport.py -v

# With LLM (full lifecycle including prompt):
OPENSHELL_LLM_AVAILABLE=true \
  uv run pytest kagenti/tests/e2e/openshell/test_T7_1_teleport.py -v
```

Test coverage:

| Test | What it validates |
|------|-------------------|
| `test_teleport__script_exists` | Script exists and is executable |
| `test_teleport__package_creates_configmap` | ConfigMap created with session ID |
| `test_teleport__cleanup_removes_resources` | ConfigMap deleted after cleanup |
| `test_teleport__full_lifecycle` | Package → deploy → verify CLAUDE.md → prompt → cleanup |
| `test_teleport__full_mode` | `--full` flag runs entire lifecycle |
| `test_teleport__skills_packaged` | `TELEPORT_SKILLS` includes skills in ConfigMap |
| `test_teleport__no_action` | Script fails without action flag |
| `test_teleport__deploy_without_session` | Deploy requires `--session` |
| `test_teleport__prompt_without_session` | Prompt requires `--session` |
| `test_teleport__cleanup_without_session` | Cleanup requires `--session` |

## Limitations

- **One-shot only**: no multi-turn conversation, no streaming
- **No session persistence**: pod deletion loses all state
- **CLI output includes tool calls**: `claude --print` outputs tool-call
  text alongside the answer
- **No workspace sync**: files created in the sandbox are lost on cleanup
- **ConfigMap size limit**: 800 KB for all context combined
