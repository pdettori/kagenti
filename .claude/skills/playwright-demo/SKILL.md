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
- [Directory Structure](#directory-structure)
- [Output Conventions](#output-conventions)
- [Iterating on Narration](#iterating-on-narration)
- [Creating New Demo Scenarios](#creating-new-demo-scenarios)
- [Google Drive Sync](#google-drive-sync)
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
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX> --test walkthrough-demo
```

List available tests:

```bash
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX>
```

## How It Works

### Without OPENAI_API_KEY

Records a single fast video, saves all artifacts to the nested `demos/` directory.

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

## Directory Structure

Demos are organized in nested directories matching `TODO_VIDEOS.md` categories.
The mapping from test name to output directory is in `demo-map.json`.

```
local_experiments/
├── demo-map.json                       # Test name → output dir mapping
├── e2e/                                # Source test specs
│   ├── walkthrough-demo.spec.ts
│   ├── home-overview.spec.ts
│   ├── agent-chat.spec.ts
│   ├── agent-detail.spec.ts
│   └── ...
├── narrations/                         # Source narration text files
│   ├── walkthrough-demo.txt
│   ├── home-overview.txt
│   └── ...
├── demos/                              # Output: organized by category
│   ├── 01-existing/
│   │   └── full-platform-walkthrough/
│   ├── 02-ui-pages/
│   │   ├── home-overview/
│   │   ├── agent-detail/
│   │   ├── tool-detail-mcp/
│   │   ├── observability/
│   │   ├── admin-page/
│   │   └── ...
│   ├── 03-workflows/
│   │   ├── agent-chat/
│   │   ├── e2e-deploy/
│   │   └── ...
│   ├── 04-observability/
│   │   ├── mlflow-traces/
│   │   └── ...
│   └── 05-advanced/
│       └── ...
├── sync-to-gdrive.sh                  # Google Drive upload
└── run-playwright-demo.sh             # Main entry script
```

## Output Conventions

Each demo directory contains **all artifacts** needed to understand and regenerate
the video. Every recording creates **timestamped copies** plus **`_latest` copies**
that get overwritten on each run.

```
demos/02-ui-pages/home-overview/
├── home-overview.spec.ts                           # Test spec (copy)
├── home-overview.txt                               # Narration text (copy)
├── home-overview-timestamps.json                   # Step timings
├── home-overview-section-pauses.json               # Pause calculations
│
├── audio_segments/                                 # Individual TTS segments
│   ├── intro.mp3                                   # Cached per-section audio
│   ├── intro.hash                                  # MD5 of narration text
│   ├── login.mp3
│   ├── login.hash
│   └── ...                                         # One .mp3+.hash per markStep
│
├── home-overview_2026-02-11_10-22.webm             # Timestamped raw video
├── home-overview_2026-02-11_10-22_voiceover.mp4    # Timestamped narrated
├── home-overview_2026-02-11_10-22_narration.mp3    # Timestamped audio
│
├── home-overview_latest.webm                       # Latest raw (overwritten)
├── home-overview_latest_voiceover.mp4              # Latest narrated
└── home-overview_latest_narration.mp3              # Latest audio
```

### Artifact types

| File | Source | Purpose |
|------|--------|---------|
| `*.spec.ts` | Copied from `e2e/` | Test spec for regeneration |
| `*.txt` | Copied from `narrations/` | Narration text for TTS |
| `*-timestamps.json` | Generated by test | Step timings for sync |
| `*-section-pauses.json` | Generated by sync | Pause calculations |
| `audio_segments/*.mp3` | OpenAI TTS | Individual per-section audio |
| `audio_segments/*.hash` | MD5 of text | Cache invalidation — only regenerate if text changed |
| `*_YYYY-MM-DD_HH-MM.webm` | Playwright video | Raw recording (no audio) |
| `*_YYYY-MM-DD_HH-MM_voiceover.mp4` | FFmpeg composite | Video + narration |
| `*_YYYY-MM-DD_HH-MM_narration.mp3` | OpenAI TTS | Standalone narration |
| `*_latest.*` | Copy of most recent | Always-current version |

### Incremental regeneration

When narration text changes for a specific section:
1. Only that section's `audio_segments/<section>.mp3` is regenerated
2. The `.hash` file tracks whether the text changed (MD5)
3. Unchanged sections reuse cached audio — no API calls needed
4. Video is re-composited with the mix of cached + new segments

### demo-map.json

Maps test names to their nested output directories:

```json
{
  "home-overview": {
    "dir": "02-ui-pages/home-overview",
    "description": "Home page: stats, actions, theme, navigation"
  }
}
```

To add a new demo, add an entry to `demo-map.json` and create the directory.

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
python3 local_experiments/validate-alignment.py \
    --timestamps local_experiments/demos/<category>/<name>/<name>-timestamps.json \
    --narration local_experiments/narrations/<name>.txt
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

1. Add entry to `local_experiments/demo-map.json`:
   ```json
   "my-demo": {
     "dir": "02-ui-pages/my-demo",
     "description": "What this demo shows"
   }
   ```

2. Create test: `local_experiments/e2e/<name>.spec.ts`
   - Use `markStep('section_name')` at each visual transition
   - All `markStep()` calls MUST be outside conditional blocks
   - Use `demoClick()` for visible cursor movement
   - Use SPA navigation for Kagenti UI (sidebar clicks, not `page.goto`)
   - Use `page.goto()` for external apps (MLflow, Phoenix, Kiali)
   - Write timestamps to `<name>-timestamps.json`

3. Create narration: `local_experiments/narrations/<name>.txt`
   - One `[section]` per `markStep()` in the test
   - Text describes what's visible during that section

4. Run and iterate:

```bash
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX> --test <name>
```

See `playwright-demo:debug` for fixing failing steps.
See `playwright-research` for analyzing UI code to write correct selectors.

## Google Drive Sync

Upload demo videos to a shared Google Drive folder using a scoped service account.

### Step 1: Create Google Cloud project and enable Drive API

```bash
# Create project (or use existing)
gcloud projects create kagenti-demos --name="Kagenti Demos" 2>/dev/null || true
gcloud config set project kagenti-demos

# Enable the Drive API
gcloud services enable drive.googleapis.com
```

### Step 2: Create a scoped service account

The service account only has `drive.file` scope — it can only access files
it creates or files explicitly shared with it. No access to anything else.

```bash
# Create service account
gcloud iam service-accounts create kagenti-demo-sync \
    --display-name="Kagenti Demo Video Sync" \
    --description="Syncs demo videos to a single Google Drive folder"

# Get the service account email
SA_EMAIL=$(gcloud iam service-accounts list \
    --filter="email:kagenti-demo-sync" \
    --format="value(email)")
echo "Service account: $SA_EMAIL"

# Create and download the JSON key
gcloud iam service-accounts keys create \
    ~/.config/kagenti-gdrive-sa.json \
    --iam-account="$SA_EMAIL"

echo "Key saved to: ~/.config/kagenti-gdrive-sa.json"
```

### Step 3: Create a Google Drive folder and share with service account

1. Create a folder in Google Drive (e.g., "Kagenti Demos")
2. Right-click the folder → Share
3. Add the service account email (from step 2): `kagenti-demo-sync@<project>.iam.gserviceaccount.com`
4. Give it **Editor** access
5. Copy the folder ID from the URL:
   `https://drive.google.com/drive/folders/FOLDER_ID_HERE`

The service account can ONLY touch files inside this shared folder and its
subdirectories. It has no access to any other Drive content.

### Step 4: Configure environment

```bash
# Add to .env in the playwright worktree
cat >> .worktrees/playwright-demos/local_experiments/.env << 'EOF'
GDRIVE_FOLDER_ID=your-folder-id-here
GDRIVE_SA_KEY_FILE=~/.config/kagenti-gdrive-sa.json
EOF
```

### Step 5: Install Python dependency

```bash
uv pip install google-api-python-client google-auth
```

### Sync commands

```bash
# Show setup instructions (when not configured)
./local_experiments/sync-to-gdrive.sh

# Sync all demos
./local_experiments/sync-to-gdrive.sh --sync

# Sync only _latest files (smaller, faster)
./local_experiments/sync-to-gdrive.sh --sync --latest-only

# Sync a specific category
./local_experiments/sync-to-gdrive.sh --sync --category 02-ui-pages

# Dry run (show what would be synced)
./local_experiments/sync-to-gdrive.sh --sync --dry-run
```

### Security notes

- The service account uses `drive.file` scope (most restrictive)
- It can only access files it created or files in the shared folder
- No access to user's personal Drive, other folders, or org-wide data
- The JSON key should be kept in `~/.config/` (gitignored)
- Rotate keys: `gcloud iam service-accounts keys create` + delete old key

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

### Problem: Video goes to wrong directory
**Symptom**: Video saved to `demos/<test-name>/` instead of nested path
**Fix**: Add the test name to `demo-map.json` with the correct `dir` value.

## Related Skills

- `playwright-demo:debug` — Debug failing Playwright steps
- `playwright-research` — Analyze UI code, detect changes, plan videos
- `hypershift:cluster` — Create/manage test clusters
- `k8s:health` — Verify platform health before recording
- `test:write` — Patterns for writing test specs
