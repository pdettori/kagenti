---
name: playwright-demo
description: Record narrated demo videos of the Kagenti platform using Playwright and OpenAI TTS
---

# Playwright Demo Recording

Record demo videos of the Kagenti platform with AI-generated voiceover narration.

## Table of Contents

- [When to Use](#when-to-use)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Iterating on Narration](#iterating-on-narration)
- [Creating New Demo Scenarios](#creating-new-demo-scenarios)
- [Task Tracking](#task-tracking)
- [Troubleshooting](#troubleshooting)
- [Related Skills](#related-skills)

## When to Use

- Creating a demo video of the Kagenti platform for presentations
- Recording a walkthrough of a new feature with voiceover
- Generating reproducible video documentation of platform workflows

## Prerequisites

- HyperShift or Kind cluster with Kagenti deployed
- The `playwright-demos` worktree: `.worktrees/playwright-demos/`
- `ffmpeg` and `ffprobe` installed
- `OPENAI_API_KEY` in `.env` for narration (optional — video-only without it)

## Quick Start

From the `playwright-demos` worktree:

```bash
cd .worktrees/playwright-demos
```

Video only (no narration):

```bash
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX> --test walkthrough-demo
```

Video + narration (set OPENAI_API_KEY first):

```bash
source .env
```

```bash
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX> --test walkthrough-demo
```

List available tests:

```bash
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX>
```

## How It Works

### Without OPENAI_API_KEY

Records a single fast video → saves to `demos/<testname>/`.

### With OPENAI_API_KEY (automatic 3-step pipeline)

```
Step 1: Fast run → measure video slot timing per markStep() section
        ↓
Step 2: Generate TTS for each [section] in narrations/<test>.txt
        Compare narration duration vs video slot:
        - narration < slot → validation: "add N chars to [section]"
        - narration ≥ slot → sync adds extra wait to match
        ↓
Step 3: Record narration-synced video → composite voiceover → validate
```

### Output files

```
demos/<testname>/
├── *_YYYY-MM-DD_HH-MM.webm              # Raw video (no audio)
├── *_YYYY-MM-DD_HH-MM_narration.mp3     # Standalone narration audio
└── *_YYYY-MM-DD_HH-MM_voiceover.mp4     # Final video with narration
```

## Iterating on Narration

After a run, the validation prints an action plan. Follow it:

1. Read the action plan — it says which sections need more text and how many chars
2. Edit `local_experiments/narrations/<testname>.txt`
3. Re-run the script — converges in 2 iterations max

### Narration file format

```
[section_name]
Narration text matching this markStep() in the test.
Must describe what's currently visible on screen.

[next_section]
Next section narration.
```

### Validation (run manually anytime)

```bash
python3 local_experiments/validate-alignment.py
```

### Voice options

```bash
TTS_VOICE=shimmer TTS_SPEED=0.9 ./local_experiments/run-playwright-demo.sh ...
```

Voices: `onyx` (default), `alloy`, `echo`, `fable`, `nova`, `shimmer`

### Pronunciation

OpenAI TTS has no SSML. Use spelling tricks in narration text:
- Kagenti → `Kay-jentee`
- A2A → `A-to-A`
- mTLS → `mutual TLS`

## Creating New Demo Scenarios

1. Create test: `local_experiments/e2e/<name>.spec.ts`
   - Use `markStep('section_name')` at each visual transition
   - All `markStep()` calls MUST be outside conditional blocks
   - Use `demoClick()` for visible cursor movement
   - Use SPA navigation for Kagenti UI (sidebar clicks, not `page.goto`)
   - Use `page.goto()` for external apps (MLflow, Phoenix, Kiali)

2. Create narration: `local_experiments/narrations/<name>.txt`
   - One `[section]` per `markStep()` in the test
   - Text describes what's visible during that section

3. Run and iterate:

```bash
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX> --test <name>
```

See `playwright-demo:debug` for fixing failing steps.

## Task Tracking

On invocation:
1. TaskList — check existing demo recording tasks
2. TaskCreate with naming: `playwright-demos | <cluster> | <plan> | demo | <phase> | <task>`
3. TaskUpdate as narration iterations progress

## Troubleshooting

### Problem: Validation shows IDLE gaps
**Symptom**: `[section] IDLE 5.0s — Add ~75 chars narration`
**Fix**: Add more narration text to `narrations/<test>.txt` for that section. Re-run.

### Problem: Narration overlaps next section
**Symptom**: `OVERLAP [a] ends at Xs but [b] starts at Ys`
**Fix**: The `--sync` pipeline adds extra waits automatically. Just re-run.

### Problem: Missing markStep timestamp
**Symptom**: `Section [name] has no markStep() timestamp`
**Fix**: Move `markStep('name')` outside any `if` block in the test.

### Problem: MLflow/Kiali login fails
**Symptom**: Auth error on external app
**Fix**: Script auto-discovers credentials. Check `kagenti-test-user` secret exists.
See `playwright-demo:debug` for detailed auth troubleshooting.

### Problem: Multiple voices overlapping in video
**Symptom**: Audio plays on top of each other
**Fix**: Missing timestamps cause wrong audio placement. Fix all `markStep()` calls first.

## Related Skills

- `playwright-demo:debug` — Debug failing Playwright steps
- `hypershift:cluster` — Create/manage test clusters
- `k8s:health` — Verify platform health before recording
- `test:write` — Patterns for writing test specs
