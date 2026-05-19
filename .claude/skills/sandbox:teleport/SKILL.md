# Teleport: Local Claude Code → Kagenti Sandbox

Package your local Claude Code context (CLAUDE.md, skills, settings) and deploy
it into a Kagenti OpenShell sandbox with full isolation (Landlock, seccomp, netns).
Execute instructions remotely and retrieve results.

## Prerequisites

- Kagenti cluster with OpenShell gateway deployed (Kind or HyperShift)
- Sandbox CRD installed (`kubectl get crd sandboxes.agents.x-k8s.io`)
- LiteLLM proxy running in the target namespace
- `litellm-virtual-keys` secret with `api-key`

## Quick Start (all-in-one)

```bash
scripts/openshell/teleport-session.sh --full "What project is this? Summarize CLAUDE.md"
```

This packages context, deploys a sandbox, sends the prompt, prints the result,
and cleans up — all in one command.

## Step-by-Step Usage

### 1. Package context into a ConfigMap

```bash
SESSION_ID=$(scripts/openshell/teleport-session.sh --package)
echo "Session: $SESSION_ID"
```

What gets packaged:
- `CLAUDE.md` from repo root
- `.claude/skills/*/SKILL.md` files (directory names encoded for ConfigMap keys)
- `.claude/settings.json` (sensitive fields stripped)

Size limit: 900KB total (ConfigMap max ~1MB).

### 2. Deploy sandbox with context

```bash
scripts/openshell/teleport-session.sh --deploy --session $SESSION_ID
```

Creates a Sandbox CR with:
- Base image: `ghcr.io/nvidia/openshell-community/sandboxes/base:latest`
- Claude CLI pre-installed
- Context mounted and unpacked into `/workspace/`
- LiteLLM credentials injected via K8s secret

### 3. Send instruction

```bash
scripts/openshell/teleport-session.sh --prompt --session $SESSION_ID \
  "Review the skills in .claude/skills/ and list the top 5 most useful ones"
```

Executes `claude --print --bare` inside the sandbox pod. The remote Claude Code
has access to the teleported CLAUDE.md and skills.

### 4. Clean up

```bash
scripts/openshell/teleport-session.sh --cleanup --session $SESSION_ID
```

Deletes the Sandbox CR, ConfigMap, and waits for pod termination.

## What Gets Teleported

| Item | Source | Destination in sandbox |
|------|--------|----------------------|
| CLAUDE.md | `$REPO_ROOT/CLAUDE.md` | `/workspace/CLAUDE.md` |
| Skills | `.claude/skills/*/SKILL.md` | `/workspace/.claude/skills/*/SKILL.md` |
| Settings | `.claude/settings.json` | `/workspace/.claude/settings.json` |

## What Does NOT Get Teleported (MVP)

- Conversation history
- Git state / working tree files
- Memory files (user-specific, may contain sensitive data)
- Local environment variables
- Running processes or background tasks

## Options

```
--namespace <ns>    Target namespace (default: team1)
--session <id>      Session ID (auto-generated for --package)
--timeout <secs>    Prompt timeout (default: 120)
```

## Limitations

- **One-shot execution**: each `--prompt` is a single Claude Code invocation
  (`claude --print --bare`). No multi-turn or persistent sessions yet.
- **ConfigMap size**: context must be under 900KB. For larger bundles, PVC
  support is planned.
- **No result sync**: changes made by Claude Code inside the sandbox are not
  synced back to your local machine. Use `--prompt` to ask for specific outputs.
