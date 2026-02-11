---
name: playwright-research
description: Analyze UI code changes to plan, create, and maintain Playwright demo videos - change detection, test writing, video recording lifecycle
---

# Playwright Research - Demo Video Lifecycle Management

Analyze UI code to determine which demo videos need creation or regeneration,
write Playwright demo tests, validate them, and manage the full video lifecycle.

## Table of Contents

- [When to Use](#when-to-use)
- [Prerequisites](#prerequisites)
- [Workflow Overview](#workflow-overview)
- [Phase 1: UI Code Analysis](#phase-1-ui-code-analysis)
- [Phase 2: Change Detection](#phase-2-change-detection)
- [Phase 3: Test Writing](#phase-3-test-writing)
- [Phase 4: Test Validation](#phase-4-test-validation)
- [Phase 5: Video Recording](#phase-5-video-recording)
- [Phase 6: Narration](#phase-6-narration)
- [Architecture: How Segments Work](#architecture-how-segments-work)
- [File Layout](#file-layout)
- [TODO_VIDEOS.md Management](#todo_videosmd-management)
- [Task Tracking](#task-tracking)
- [Related Skills](#related-skills)

## When to Use

- **New feature added to UI** — Determine if a new demo video is needed
- **UI code changed** — Check if existing demos need regeneration
- **Planning demo coverage** — Analyze UI to find uncovered workflows
- **Writing new demo tests** — Create tests that match UI code patterns
- **Iterating on failing tests** — Debug and fix test selectors/flows
- **Managing TODO_VIDEOS.md** — Keep the video plan current with UI state

## Prerequisites

- Access to the `kagenti/ui-v2/src/` source code
- The `playwright-demos` worktree: `.worktrees/playwright-demos/`
- HyperShift or Kind cluster with Kagenti deployed (for test execution)
- Playwright installed: `cd kagenti/ui-v2 && npm install`

## Workflow Overview

```
┌─────────────────────────────────────────────────────┐
│  1. ANALYZE: Read UI code, identify pages/components│
│     └─ Compare against TODO_VIDEOS.md               │
├─────────────────────────────────────────────────────┤
│  2. DETECT: Check git diff for UI changes           │
│     └─ Map changed files to affected videos         │
├─────────────────────────────────────────────────────┤
│  3. WRITE: Create/update Playwright demo test       │
│     └─ Analyze UI selectors from source code        │
├─────────────────────────────────────────────────────┤
│  4. VALIDATE: Run test, fix failures, iterate       │
│     └─ Use playwright-demo:debug for issues         │
├─────────────────────────────────────────────────────┤
│  5. RECORD: Run demo with --no-narration first      │
│     └─ Use playwright-demo skill                    │
├─────────────────────────────────────────────────────┤
│  6. NARRATE: Add narration text, sync, record final │
│     └─ Iterate on alignment                         │
└─────────────────────────────────────────────────────┘
```

## Phase 1: UI Code Analysis

### Step 1: Inventory UI pages and components

Read the following files to understand the current UI structure:

```
kagenti/ui-v2/src/App.tsx              # Routes — all pages
kagenti/ui-v2/src/pages/               # Page components
kagenti/ui-v2/src/components/          # Shared components
kagenti/ui-v2/src/services/            # API service layer
```

### Step 2: Map UI features to demo candidates

For each page, identify:

| Question | Action |
|----------|--------|
| What user workflows does this page support? | Each workflow = potential demo |
| What interactive elements exist (forms, tables, buttons)? | These need selectors |
| What API calls does the page make? | Determines data dependencies |
| What state transitions happen? | Determines test flow |

### Step 3: Compare against TODO_VIDEOS.md

Check `.worktrees/playwright-demos/TODO_VIDEOS.md` for:
- Which videos already exist (marked DONE)
- Which are planned but not started (marked NEW)
- Which need regeneration due to code changes

## Phase 2: Change Detection

### Detecting UI changes that affect demos

Use the change detection mapping in `TODO_VIDEOS.md` section 10 to determine
which videos are affected by a code change.

### Quick check: what changed since last demo recording

```bash
# From main repo
git diff --name-only HEAD~10 -- kagenti/ui-v2/src/

# Or between branches
git diff --name-only main..HEAD -- kagenti/ui-v2/src/
```

### File-to-video mapping

| UI Source File | Affected Demo Videos |
|----------------|---------------------|
| `HomePage.tsx` | home-overview, e2e-deploy |
| `AgentCatalogPage.tsx` | walkthrough-demo, agent-detail, e2e-deploy |
| `AgentDetailPage.tsx` | walkthrough-demo, agent-detail, agent-chat |
| `AgentChat.tsx` | walkthrough-demo, agent-chat |
| `ImportAgentPage.tsx` | agent-import, e2e-deploy |
| `BuildProgressPage.tsx` | agent-build, e2e-deploy |
| `ToolCatalogPage.tsx` | tool-catalog, tool-integration |
| `ToolDetailPage.tsx` | tool-detail, tool-integration |
| `ImportToolPage.tsx` | tool-import, tool-integration |
| `MCPGatewayPage.tsx` | mcp-gateway |
| `ObservabilityPage.tsx` | observability |
| `AdminPage.tsx` | admin-page |
| `AppLayout.tsx` | ALL demos (navigation changes) |
| `NamespaceSelector.tsx` | Any demo with namespace selection |

### Analyzing component changes

When a component changes, check:

1. **Selector changes**: Did CSS classes, aria-labels, or test IDs change?
   - Search the test for selectors that reference the changed component
   - Update selectors in the test to match new DOM structure

2. **Layout changes**: Did the visual layout change?
   - The test may still pass but the video may look different
   - Mark the video for regeneration

3. **New features**: Were new UI elements added?
   - Consider adding new `markStep()` sections to cover them
   - Update narration text

4. **Removed features**: Were UI elements removed?
   - Tests using those selectors will fail
   - Remove or update corresponding `markStep()` sections

## Phase 3: Test Writing

### Analyzing UI code for selectors

Before writing a test, read the UI source to find the correct selectors.

**Pattern: Find clickable elements**

```typescript
// Read the page component to find element identifiers
// Look for: aria-label, data-testid, role, className, text content

// Example from AgentCatalogPage.tsx:
// <Button onClick={() => navigate('/agents/import')}>Import Agent</Button>
// → page.getByRole('button', { name: /Import Agent/i })

// <Select aria-label="Select namespace">
// → page.locator('[aria-label="Select namespace"]')

// <Tabs><Tab title="Chat">
// → page.getByRole('tab', { name: /Chat/i })
```

**Pattern: Find data elements**

```typescript
// Look for table columns, card content, status badges
// <Table><Td><Link to={`/agents/${ns}/${name}`}>{name}</Link>
// → page.locator('a').filter({ hasText: 'weather-service' })
```

### Test template

Every demo test follows this structure:

```typescript
import { test, expect } from '@playwright/test';

const PAUSE = 2000;
const LONG_PAUSE = 3000;

const stepTimestamps: { step: string; time: number }[] = [];
const demoStartTime = Date.now();
const markStep = (step: string) => {
  const elapsed = (Date.now() - demoStartTime) / 1000;
  stepTimestamps.push({ step, time: elapsed });
  console.log(`[demo-ts] ${elapsed.toFixed(1)}s — ${step}`);
};

const UI_URL = process.env.KAGENTI_UI_URL || '';
const KC_USER = process.env.KEYCLOAK_USER || 'admin';
const KC_PASS = process.env.KEYCLOAK_PASS || 'admin';

test.describe('Demo Name', () => {
  test.describe.configure({ mode: 'serial' });

  test('description', async ({ page }) => {
    test.setTimeout(300000);

    // Cursor injection (copy from walkthrough-demo.spec.ts)
    let lastCursorX = 960, lastCursorY = 540;
    const injectCursor = async () => { /* ... */ };
    const humanMove = async (toX: number, toY: number) => { /* ... */ };
    const demoClick = async (locator: any, description?: string) => { /* ... */ };

    // Navigation + login (copy auth handling from walkthrough-demo.spec.ts)
    await page.goto(UI_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await injectCursor();
    markStep('intro');
    // ... login steps ...

    // Demo-specific steps
    markStep('section_name');
    // ... test actions ...

    markStep('end');

    // Write timestamps
    const fs = require('fs');
    const path = require('path');
    const scriptDir = process.env.PLAYWRIGHT_OUTPUT_DIR || path.join(__dirname, '..');
    const tsFile = path.join(scriptDir, '..', '<name>-timestamps.json');
    fs.writeFileSync(tsFile, JSON.stringify(stepTimestamps, null, 2));

    await page.waitForTimeout(10000); // Final pause for narration
  });
});
```

### Critical rules for demo tests

1. **All `markStep()` calls MUST be outside conditional blocks**
   - The narration sync relies on every markStep firing
   - If a step is conditional, still call markStep outside the if/else

2. **Use SPA navigation for Kagenti UI pages**
   - Click sidebar links instead of `page.goto()` to preserve Keycloak tokens
   - Use `page.goto()` only for external apps (MLflow, Phoenix, Kiali)

3. **Re-inject cursor after `page.goto()`**
   - Full page navigation resets the DOM
   - Call `await injectCursor()` after every `page.goto()`

4. **Use `demoClick()` instead of `locator.click()`**
   - `demoClick()` moves the visible cursor to the element first
   - This creates a natural-looking mouse movement in the video

5. **Multiple selector strategies with fallbacks**
   - UI elements may render differently across versions
   - Try role-based > aria-label > text content > CSS class

6. **Section duration should be 3-15 seconds**
   - Shorter than 3s leaves no room for narration
   - Longer than 15s should be split into sub-sections

## Phase 4: Test Validation

### Running a test to verify it passes

```bash
cd .worktrees/playwright-demos

# Dry run — see available tests
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX>

# Run specific test (video-only, no narration)
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX> --test <name>

# Kind cluster
./local_experiments/run-playwright-demo.sh --kind --test <name>
```

### Debugging failures

1. Check `[demo]` log lines in output — which step failed?
2. Look at screenshots: `local_experiments/test-results/*/test-failed-1.png`
3. Use `playwright-demo:debug` skill for common issues
4. Common fixes:
   - **Selector not found**: Read the current UI source, update selector
   - **Auth timeout**: Check cluster health (`k8s:health`)
   - **Element behind overlay**: Add `.catch(() => {})` and fallback

### Iterative fixing

```
Run test → fails at step N
  → Read UI source for step N component
  → Update selector/flow in test
  → Re-run test
  → Repeat until all steps pass
```

## Phase 5: Video Recording

Once the test passes, record the video:

```bash
# No narration (fast)
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX> --test <name>
```

Review the video in `local_experiments/demos/<name>/`.

See `playwright-demo` skill for the full recording workflow.

## Phase 6: Narration

### Creating narration text

Create `local_experiments/narrations/<name>.txt` with one `[section]` per
`markStep()` in the test:

```
[intro]
Description of what's visible during the intro section.

[section_name]
Narration text describing this section's visuals.

[end]
Closing remarks.
```

### Narration guidelines

- Describe what's **visible on screen**, not implementation details
- Use pronunciation tricks: Kay-jentee, A-to-A, M-C-P, mutual TLS
- Keep sections under 15 seconds of speech (~150 words max)
- Match `markStep()` names exactly

### Recording with narration

```bash
source .env  # OPENAI_API_KEY
./local_experiments/run-playwright-demo.sh --cluster-suffix <SUFFIX> --test <name>
```

This triggers the 3-step pipeline: measure → sync → record + voiceover.

## Architecture: How Segments Work

### markStep() timing system

```
Test execution timeline:
  0.0s  markStep('intro')      ← Records timestamp
  4.8s  markStep('login')      ← Records timestamp
 15.2s  markStep('catalog')    ← Records timestamp
  ...

Output: <name>-timestamps.json
  [
    { "step": "intro", "time": 0.0 },
    { "step": "login", "time": 4.8 },
    { "step": "catalog", "time": 15.2 }
  ]
```

### Narration sync algorithm

```
For each [section] in narrations/<name>.txt:
  1. Generate TTS audio → measure duration (e.g., 8.3s)
  2. Calculate video slot = next_step_time - this_step_time (e.g., 4.8s)
  3. If narration > slot:
     extra_wait = narration_duration + 1.5s_buffer - slot
     → Inject: await page.waitForTimeout(extra_wait_ms)
  4. If narration < slot:
     → Validation says: "section X has idle time, add more narration"
```

### Video + audio compositing

```
sync-narration.py:
  narrations/<name>.txt → TTS audio files + e2e-narration/<name>.spec.ts

add-voiceover.py:
  video.webm + TTS audio files → composite MP4 with positioned audio

validate-alignment.py:
  Check for idle gaps and overlaps
```

## File Layout

```
.worktrees/playwright-demos/
├── TODO_VIDEOS.md                        # Master plan (this file)
├── local_experiments/
│   ├── run-playwright-demo.sh            # Main entry script
│   ├── sync-narration.py                 # Narration timing sync
│   ├── add-voiceover.py                  # TTS + FFmpeg compositing
│   ├── validate-alignment.py             # Alignment checker
│   ├── keycloak-auth-setup.ts            # Playwright auth setup
│   ├── e2e/                              # Source demo tests
│   │   ├── walkthrough-demo.spec.ts      # Full walkthrough
│   │   ├── home-overview.spec.ts         # Home page demo
│   │   ├── agent-chat.spec.ts            # Agent chat demo
│   │   └── <new-test>.spec.ts
│   ├── e2e-narration/                    # Generated (narration-synced tests)
│   ├── narrations/                       # Narration text files
│   │   ├── walkthrough-demo.txt
│   │   ├── home-overview.txt
│   │   ├── agent-chat.txt
│   │   └── <new-test>.txt
│   ├── demos/                            # Output videos
│   │   └── <test-name>/
│   │       ├── *_YYYY-MM-DD_HH-MM.webm
│   │       └── *_YYYY-MM-DD_HH-MM_voiceover.mp4
│   ├── test-results/                     # Playwright output (temp)
│   ├── *-timestamps.json                 # Step timings from last run
│   └── section-pauses.json              # Pause calculations
│
├── kagenti/ui-v2/                        # UI source (for analysis)
│   ├── src/pages/                        # Page components to analyze
│   ├── src/components/                   # Shared components
│   ├── e2e/                              # Repo e2e tests (basic)
│   └── playwright.config.ts             # Standard test config
│
└── .claude/skills/                       # Worktree-local skills
    └── playwright-demos*.md              # Demo workflow skills
```

## TODO_VIDEOS.md Management

### Adding a new video candidate

In `.worktrees/playwright-demos/TODO_VIDEOS.md`:

1. Add entry under the appropriate section
2. Set status: `[NEW]`
3. Set importance: `[P0]` through `[P3]`
4. List sections (markStep names)
5. Add to the priority order table
6. Add to the file-to-video mapping in section 10

### Updating video status

| Status | Meaning |
|--------|---------|
| `[NEW]` | Needs test + narration |
| `[WIP]` | Test exists, needs iteration |
| `[DONE]` | Test passes, video recorded |
| `[REGEN]` | UI changed, video needs re-recording |
| `[IDEA]` | Proposed, needs validation |

### Marking videos for regeneration

When UI code changes:
1. Run change detection (Phase 2)
2. Find affected videos using the mapping
3. Change their status from `[DONE]` to `[REGEN]`

## Task Tracking

On invocation:
1. `TaskList` — check existing video planning tasks
2. `TaskCreate` for each phase of work:
   - `playwright-research | analyze | <scope>`
   - `playwright-research | detect | <change description>`
   - `playwright-research | write-test | <test name>`
   - `playwright-research | validate | <test name>`
   - `playwright-research | record | <test name>`
   - `playwright-research | narrate | <test name>`
3. `TaskUpdate` as work progresses

## Related Skills

- `playwright-demo` — Record demo videos (Phase 5-6)
- `playwright-demo:debug` — Debug failing tests (Phase 4)
- `k8s:health` — Verify platform health before testing
- `hypershift:cluster` — Create test clusters
- `test:write` — General test writing patterns
- `kagenti:ui-debug` — Debug Kagenti UI issues
