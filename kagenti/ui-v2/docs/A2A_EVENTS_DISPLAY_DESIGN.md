# A2A Protocol Events Display - Design Proposal

## Overview

This document proposes a design for displaying intermediate A2A protocol events in the chat interface. Currently, the chat only shows the final response from agents. This enhancement will provide visibility into the agent's processing steps, improving user experience and debuggability.

## Current Architecture

### Frontend (AgentChat.tsx)
- Uses SSE streaming via `/api/v1/chat/{namespace}/{name}/stream`
- Parses SSE `data:` lines containing JSON with `content`, `session_id`, `done`, `error`
- Only displays accumulated `content` as the response
- Shows a blinking cursor during streaming

### Backend (chat.py)
- Receives A2A protocol events from the agent via SSE
- Processes several event types:
  - **TaskArtifactUpdateEvent**: Contains intermediate outputs (always forwarded)
  - **TaskStatusUpdateEvent**: Contains task state transitions (only final states forwarded)
  - **Task object**: Initial task response
  - **Direct messages**: Simple text responses
- Currently filters out non-final status updates (SUBMITTED, WORKING states)

### A2A Protocol Events

| Event Type | Structure | Current Handling |
|------------|-----------|------------------|
| TaskStatusUpdateEvent | `{taskId, status: {state, message}, final}` | Only `state=COMPLETED/FAILED` forwarded |
| TaskArtifactUpdateEvent | `{taskId, artifact: {parts}}` | Always forwarded |
| Task | `{id, status: {state, message}}` | Only final states forwarded |

**Task States**: `SUBMITTED` → `WORKING` → `COMPLETED` or `FAILED`

---

## Proposed Design

### 1. Data Model Changes

#### New Event Types (Frontend)
```typescript
interface A2AEvent {
  id: string;
  timestamp: Date;
  type: 'status' | 'artifact' | 'error';
  taskId?: string;
  state?: 'SUBMITTED' | 'WORKING' | 'COMPLETED' | 'FAILED';
  message?: string;
  artifact?: {
    name?: string;
    parts: Array<{ type: string; content: string }>;
  };
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  events?: A2AEvent[];  // NEW: Associated events for this message
  isComplete?: boolean; // NEW: Whether response is finalized
}
```

#### Extended SSE Payload (Backend → Frontend)
```typescript
interface SSEPayload {
  // Existing fields
  content?: string;
  session_id: string;
  done?: boolean;
  error?: string;

  // NEW: Event information
  event?: {
    type: 'status' | 'artifact';
    taskId: string;
    state?: string;
    message?: string;
    artifact?: object;
    final?: boolean;
  };
}
```

### 2. UI Components

#### 2.1 EventsPanel Component

A collapsible panel that appears within an assistant message bubble to show processing events.

```
┌─────────────────────────────────────────────────────┐
│  ▼ Processing Events (3)                    [×]    │
├─────────────────────────────────────────────────────┤
│  ● 10:23:45  Task submitted                        │
│  ● 10:23:46  Working: Analyzing request...         │
│  ● 10:23:47  Artifact: weather_data                │
│    └─ {"temp": 72, "conditions": "sunny"}          │
└─────────────────────────────────────────────────────┘
```

**Features:**
- Collapsible header with event count badge
- Expandable by default while processing
- Auto-collapses when final message received
- Optional manual expand/collapse
- Timestamp for each event
- Different icons/colors for event types:
  - `●` Blue: Status updates (SUBMITTED, WORKING)
  - `●` Green: COMPLETED
  - `●` Red: FAILED
  - `◆` Purple: Artifacts

#### 2.2 Integration with Message Bubble

```
┌─────────────────────────────────────────────────────┐
│  [Assistant Message Bubble]                         │
│                                                     │
│  ┌─ Processing Events ──────────────────────────┐  │
│  │  (collapsed or expanded panel)                │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  The weather in San Francisco is 72°F and sunny.   │
│                                                     │
│  10:23:48                                          │
└─────────────────────────────────────────────────────┘
```

### 3. Behavior Specification

#### 3.1 Event Collection Phase (While Streaming)
1. User sends message
2. Create placeholder assistant message with `isComplete: false`
3. Events panel appears **expanded** within the message bubble
4. As events arrive:
   - Add each event to `message.events[]`
   - Update events panel in real-time
   - Status events show state transitions
   - Artifact events show intermediate outputs (collapsible)
5. Content accumulates as usual

#### 3.2 Completion Phase
1. When `done: true` or final state received:
   - Set `message.isComplete = true`
   - **Auto-collapse** events panel with smooth animation
   - Final content is displayed prominently
2. User can manually expand events panel to review

#### 3.3 Error Handling
1. If `error` received or `state: FAILED`:
   - Keep events panel expanded
   - Highlight the error event in red
   - Show error message prominently

### 4. Backend Changes

#### 4.1 Modified SSE Response Format

Update `_stream_a2a_response()` to include event metadata:

```python
# For status updates (including non-final)
yield f"data: {json.dumps({
    'event': {
        'type': 'status',
        'taskId': result.get('taskId'),
        'state': status.get('state'),
        'message': status.get('message', {}).get('parts', [{}])[0].get('text', ''),
        'final': is_final,
    },
    'session_id': session_id
})}\n\n"

# For artifacts
yield f"data: {json.dumps({
    'content': content,  # Still include content for backwards compatibility
    'event': {
        'type': 'artifact',
        'taskId': result.get('taskId'),
        'artifact': {
            'name': artifact.get('name'),
            'index': artifact.get('index'),
        },
    },
    'session_id': session_id
})}\n\n"
```

#### 4.2 Forward All Events

Remove the filter that skips non-final status updates. Instead, forward all events but mark them appropriately:

```python
# Current: Skip non-final
if is_final or status.get("state") in ["COMPLETED", "FAILED"]:
    # process

# Proposed: Forward all, let frontend decide display
yield f"data: {json.dumps({
    'event': {...},
    'session_id': session_id
})}\n\n"
```

### 5. PatternFly Component Usage

| Component | Usage |
|-----------|-------|
| `ExpandableSection` | Collapsible events panel |
| `Label` | Event type badges with semantic colors |
| `Icon` | Event type icons (CheckCircleIcon, SpinnerIcon, etc.) |
| `List` / `DataList` | Event list display |
| `Timestamp` | Event timestamps |
| `CodeBlock` | Artifact content display |
| `Alert` (inline) | Error event highlighting |

### 6. State Management

```typescript
// In AgentChat component
const [messages, setMessages] = useState<Message[]>([]);
const [currentEvents, setCurrentEvents] = useState<A2AEvent[]>([]);
const [eventsExpanded, setEventsExpanded] = useState<Record<string, boolean>>({});

// When streaming starts
const handleStreamStart = () => {
  const messageId = `assistant-${Date.now()}`;
  setMessages(prev => [...prev, {
    id: messageId,
    role: 'assistant',
    content: '',
    timestamp: new Date(),
    events: [],
    isComplete: false,
  }]);
  setEventsExpanded({ [messageId]: true }); // Auto-expand
};

// When event received
const handleEvent = (event: A2AEvent, messageId: string) => {
  setMessages(prev => prev.map(msg =>
    msg.id === messageId
      ? { ...msg, events: [...(msg.events || []), event] }
      : msg
  ));
};

// When complete
const handleComplete = (messageId: string, finalContent: string) => {
  setMessages(prev => prev.map(msg =>
    msg.id === messageId
      ? { ...msg, content: finalContent, isComplete: true }
      : msg
  ));
  setEventsExpanded(prev => ({ ...prev, [messageId]: false })); // Auto-collapse
};
```

### 7. Visual Design

#### 7.1 Color Scheme (PatternFly tokens)

| Event Type | Color Token | Usage |
|------------|-------------|-------|
| SUBMITTED | `--pf-v5-global--info-color--100` | Blue |
| WORKING | `--pf-v5-global--info-color--100` | Blue (with spinner) |
| COMPLETED | `--pf-v5-global--success-color--100` | Green |
| FAILED | `--pf-v5-global--danger-color--100` | Red |
| Artifact | `--pf-v5-global--palette--purple-400` | Purple |

#### 7.2 Animation
- Smooth collapse animation (300ms ease-out)
- Fade-in for new events
- Spinner animation for WORKING state

### 8. Implementation Phases

#### Phase 1: Backend Updates
1. Modify `_stream_a2a_response()` to forward all events
2. Add event metadata to SSE payload
3. Maintain backward compatibility with `content` field

#### Phase 2: Frontend - Data Layer
1. Update `Message` interface with events support
2. Update SSE parser to extract events
3. Add event state management

#### Phase 3: Frontend - UI Components
1. Create `EventsPanel` component
2. Integrate into message bubble
3. Implement auto-expand/collapse behavior

#### Phase 4: Polish
1. Add animations
2. Ensure dark/light theme compatibility
3. Test with various agent types
4. Add loading states

---

## Design Decisions

1. **Event Retention**: Events are NOT persisted across page refreshes. They exist only in component state during the session.
2. **Event Limit**: No limit on number of displayed events. All events are shown.
3. **Artifact Display**: Large artifacts are truncated at 500 characters with a "Show more" toggle to expand.
4. **Non-streaming Agents**: Events panel is only shown for streaming responses where intermediate events are available.

---

## Mockups

### Expanded State (During Processing)
```
┌──────────────────────────────────────────────────────────────┐
│  Chat with weather-agent                         [Streaming] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [User] What's the weather in San Francisco?         10:23  │
│                                                              │
│  [Assistant]                                                 │
│  ┌─ Processing Events (3) ─────────────────────────────────┐│
│  │  ⬤ 10:23:45  SUBMITTED - Task received                 ││
│  │  ◐ 10:23:46  WORKING - Fetching weather data...        ││
│  │  ◆ 10:23:47  ARTIFACT - weather_api_response            ││
│  │    ▼ Show content                                       ││
│  │    {"location": "San Francisco", "temp_f": 72, ...}     ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  Getting weather information...█                             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Collapsed State (After Completion)
```
┌──────────────────────────────────────────────────────────────┐
│  [Assistant]                                                 │
│  ┌─ ▶ Processing Events (4) ───────────────────────────────┐│
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  The current weather in San Francisco is 72°F (22°C) with   │
│  clear skies. It's a beautiful day with light winds from    │
│  the west at 8 mph.                                          │
│                                                       10:23  │
└──────────────────────────────────────────────────────────────┘
```

---

## Acceptance Criteria

1. [ ] All A2A protocol events (SUBMITTED, WORKING, COMPLETED, FAILED, artifacts) are displayed
2. [ ] Events panel is expanded by default during processing
3. [ ] Events panel auto-collapses when final message received
4. [ ] User can manually expand/collapse events panel
5. [ ] Events show appropriate icons and colors by type
6. [ ] Timestamps are displayed for each event
7. [ ] Artifact content is expandable/collapsible
8. [ ] Error states are visually highlighted
9. [ ] Works with both light and dark themes
10. [ ] Backward compatible with agents that don't send intermediate events
