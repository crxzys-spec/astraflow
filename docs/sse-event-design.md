# SSE Messaging Design

This note captures the proposed Server-Sent Events (SSE) contract between the scheduler and dashboard.  
The intent is to decouple UI-facing event semantics from the internal WebSocket control channel while
retaining a single source of truth for payload shapes in the OpenAPI specification.

## 1. Goals

- Stream run and node progress to browsers with minimal polling.
- Deliver both incremental updates (LLM tokens, diffusion previews) and final snapshots.
- Support resumable subscriptions via `Last-Event-ID`.
- Keep platform state (`stage`, `progress`, errors) separate from package-defined `results`.

## 2. Envelope

Every SSE frame carries a JSON payload wrapped in a standard envelope. The same structure is exposed
through OpenAPI to generate backend and frontend helpers.

| Field           | Type        | Description                                                   |
|-----------------|-------------|---------------------------------------------------------------|
| `version`       | `string`    | Protocol version, currently `"v1"`.                          |
| `id`            | `string`    | Monotonic identifier for resume (`Last-Event-ID`).           |
| `type`          | `UiEventType` | Event classification (see 搂3).                            |
| `occurredAt`    | `date-time` | Timestamp of the underlying transition.                      |
| `scope`         | `UiEventScope` | Tenant/run/worker context.                               |
| `replayed`      | `boolean?`  | True when event was resent during catch-up.                  |
| `correlationId` | `string?`   | Links back to scheduler dispatch/result identifiers.         |
| `meta`          | `object?`   | Optional diagnostic hints (attempt, source, etc.).           |
| `data`          | `UiEventPayload` | Event-specific content.                               |

Example envelope:

```json
:event node.state
:id evt-00153928
:data {
  "version": "v1",
  "id": "evt-00153928",
  "type": "node.state",
  "occurredAt": "2025-11-02T15:21:33.412Z",
  "scope": { "tenant": "acme-labs", "runId": "run-8c94f7aa", "workerId": "worker-17" },
  "data": { ... }
}
```

## 3. Event Taxonomy

| Type (`UiEventType`)    | Purpose                                             |
|-------------------------|-----------------------------------------------------|
| `run.status`            | Run lifecycle state changes.                        |
| `run.snapshot`          | Full run definition/state snapshots.                |
| `run.metrics`           | Metric samples (latency, queue size, etc.).         |
| `node.state`            | Platform-owned node stage/progress/error hints.     |
| `node.status`           | High-level status transitions (queued, running鈥?.   |
| `node.result.snapshot`  | Complete node outputs/artifacts at a revision.      |
| `node.result.delta`     | Incremental result updates (LLM tokens, previews).  |
| `node.error`            | Fatal node errors with codes/messages.              |
| `artifact.ready`        | Artifact available for download.                    |
| `artifact.removed`      | Artifact expired/removed.                           |
| `command.ack`           | Control-plane command acknowledged.                 |
| `command.error`         | Control-plane command failed.                       |
| `worker.heartbeat`      | Worker health/queue info.                           |
| `worker.package`        | Worker package install/uninstall events.            |

Additional event families can be added without altering the envelope.

## 4. Payload Schemas

The OpenAPI spec exposes the payload variants via a `UiEventPayload` `oneOf`. Key definitions:

### 4.1 NodeStateEvent

```yaml
NodeStateEvent:
  type: object
  required: [kind, runId, nodeId, state]
  properties:
    kind: { const: "node.state" }
    runId: { type: string }
    nodeId: { type: string }
    state: { $ref: '#/WorkflowNodeState' } # stage/progress/message/error
```

### 4.2 NodeResultSnapshotEvent

Full results for a given revision. `complete=true` signals terminal state.

```yaml
NodeResultSnapshotEvent:
  type: object
  required: [kind, runId, nodeId, revision, content]
  properties:
    kind: { const: "node.result.snapshot" }
    runId: { type: string }
    nodeId: { type: string }
    revision: { type: integer, minimum: 0 }
    format: { type: string, enum: [json, binary, text], default: json }
    content: { type: object, additionalProperties: true }
    artifacts:
      type: array
      items: { $ref: '#/RunArtifact' }
    summary: { type: string, nullable: true }
    complete: { type: boolean, default: false }
```

### 4.3 NodeResultDeltaEvent

Represents incremental updates. `operation` defines how to apply `payload` / `patches`.

```yaml
NodeResultDeltaEvent:
  type: object
  required: [kind, runId, nodeId, revision, sequence, operation]
  properties:
    kind: { const: "node.result.delta" }
    runId: { type: string }
    nodeId: { type: string }
    revision: { type: integer, minimum: 0 }
    sequence: { type: integer, minimum: 0 }
    operation: { type: string, enum: [append, replace, patch] }
    path: { type: string, pattern: '^(/[^/]+)*$' }
    payload: { type: object, additionalProperties: true }
    patches:
      type: array
      items: { $ref: '#/JsonPatchOperation' }
    chunkMeta: { type: object, additionalProperties: true }
    terminal: { type: boolean, default: false }
```

### 4.4 Other Payloads

- `RunStatusEvent` (`kind: "run.status"`): wraps `RunStatus`, start/end timestamps, optional reason.
- `RunSnapshotEvent`: includes `Run` plus optional `RunNodeStatus[] (including each node's state snapshot)`.
- `RunMetricsEvent`: metric name/value plus tags.
- `NodeErrorEvent`: error code/message/metadata.
- `ArtifactEvent`: `artifact.ready` / `artifact.removed`.
- `CommandAckEvent` / `CommandErrorEvent`.
- `WorkerHeartbeatEvent`: queue load and capacity samples.
- `WorkerPackageEvent`: install/remove progress.

Each payload includes the minimal fields required to update the UI without leaking internal WS envelopes.

## 5. Ordering & Replay

- Scheduler assigns strictly monotonic `id` values (per tenant) to support graceful resume via `Last-Event-ID`.
- `revision` and `sequence` order deltas for a given `(runId, nodeId)`; consumers merge in order and may discard
  stale revisions.
- When replaying missed events, producer sets `replayed=true`; clients may suppress duplicate UI updates.

## 6. Publishing Guidelines

1. Emit `node.state` when dispatching, receiving ACK, starting execution, streaming outputs, and completing.
2. Stream `node.result.delta` for incremental outputs; mark `terminal=true` on the final chunk per revision.
3. Emit `node.result.snapshot` once complete (or periodically for checkpoints) with `complete=true` at the end.
4. Include artifacts and summary fields in snapshots for download links and UI badges.
5. Persist events (or at least recent history) so reconnecting clients can replay from their `Last-Event-ID`.

## 7. Consumption Guidelines

- Use the browser鈥檚 `EventSource`, listening to specific event types (`addEventListener('node.result.delta', 鈥?`).
- Maintain per-node state keyed by `(runId,nodeId)`:
  - Apply deltas in `sequence` order; treat `terminal=true` as a signal to expect the next revision or snapshot.
  - Replace stored results when a higher `revision` snapshot arrives.
  - Update builder canvas by writing `WorkflowNodeDraft.state` (`stage`, `progress`, etc.) instead of overloading `results`.
- On disconnect, reconnect with `Last-Event-ID`. When `replayed=true`, guard against duplicate UI updates.
- **Persist client identity across reloads**: generate a stable `clientSessionId` and store it in `localStorage` so every tab/refresh for that browser instance shares the same identifier (until explicitly cleared). A simple helper:
  ```ts
  const key = 'astraflow.clientSessionId';
  const clientSessionId =
    localStorage.getItem(key) ?? (() => {
      const value = crypto.randomUUID();
      localStorage.setItem(key, value);
      return value;
    })();
  ```
  Pass this value when starting runs and when opening the SSE connection; back-end should echo it in `UiEventScope.clientSessionId`. If finer granularity (per tab) is needed later, layer an additional `clientInstanceId` using `sessionStorage` or in-memory IDs.

## 8. System Architecture (Frontend 鈫?Backend)

### 8.1 Backend Responsibilities

- **Endpoint**: `/api/v1/events` returns `text/event-stream`. Each connection is authed (Bearer token) and registered with `{tenant, clientSessionId, clientInstanceId, filters}`.
- **Run Initiation Metadata**: When a run is created (REST, GraphQL, etc.), capture the caller鈥檚 `clientSessionId` (from token) and optional `clientInstanceId` (passed via request header/query). Persist on the run so subsequent node events inherit it.
- **Event Pipeline**:
  1. Worker / orchestrator emits domain events (dispatch, node result, metrics鈥?.
  2. Scheduler maps domain events 鈫?`UiEventEnvelope` (using schema in 搂4).
  3. Determine intended recipients: match tenant and apply filters (`runId`, `workerId`, etc.). If an event is tied to the initiating instance, compare `scope.clientInstanceId` to active connections鈥攐ptionally suppress duplicates for other tabs.
  4. Serialize envelope, emit SSE frame:
     ```
     id: evt-12345
     event: node.result.delta
     data: {...UiEventEnvelope JSON...}
     ```
  5. Maintain monotonic `id` per tenant (e.g., Snowflake or persisted counter). Persist events or at least recent windows for replay.
- **Reconnect Handling**: On `Last-Event-ID`, look up stored events 鈮?that id, re-deliver with `replayed=true`. Clean up connections on timeout/close.

### 8.2 Frontend Responsibilities

- **Client Instance Tracking**: On app load, ensure `clientInstanceId` exists in `sessionStorage` (refreshed tabs reuse the same value; new tabs generate new IDs). Provide an accessor to share across feature modules.
- **SSE Subscription**:
  ```ts
  const source = new EventSource(`${base}/api/v1/events?runId=${runId}&clientInstanceId=${clientInstanceId}`, { withCredentials: true });
  ```
  Attach `Authorization` via cookies or query depending on infra.
- **Typed Handling**: Use generated types (`UiEventEnvelope`, `NodeStateEvent`, etc.). Parse JSON, switch on `event.type` (and `data.kind`) to update relevant stores.
- **State Management**:
  - Maintain per-run map: `workflow.nodes[nodeId].state` (for `node.state`) and `workflow.nodes[nodeId].results` (apply deltas / snapshots).
  - Respect revisions/sequence numbers; discard stale or out-of-order messages.
  - If `scope.clientInstanceId` differs from current tab, decide whether to apply or treat as read-only (depending on UX requirements).
- **Resilience**: On `onerror`, backoff + reconnect with stored `lastEventId`. Use `replayed` flag to avoid double-applying state. Optionally share SSE-derived state across tabs via `BroadcastChannel`.

### 8.3 Multi-User / Multi-Tab Considerations

- `clientSessionId` ensures events stay within the authenticated user session.
- `clientInstanceId` differentiates concurrent tabs/windows of the same user. Server can choose to:
  - Route instance-specific reactions only to the originating tab.
  - Broadcast run-level events to all tabs but annotate `scope.clientInstanceId` so receivers can filter.
- Schema in 搂4 includes both IDs in `UiEventScope`, enabling clients to introspect origin.
- If fine-grained subscriptions are needed, extend query params (`runId`, `workspace`) or handshake payload to reduce broadcast noise.

## 9. Schema Integration

To integrate with OpenAPI:

1. Add `UiEventEnvelope`, `UiEventType`, `UiEventScope`, `UiEventPayload`, and individual payload schemas to `components.schemas`.
2. Update `/api/v1/events` response documentation to note: the `data:` line is a JSON `UiEventEnvelope`.
3. Regenerate:
   - Scheduler FastAPI stubs (`python scripts/generate_scheduler_api.py`).
   - Dashboard TypeScript models (`npm run generate:api`).
4. Refactor the scheduler鈥檚 SSE emitter to serialise these payloads and set `event:` to the same value as `type`.
5. Adjust the dashboard SSE consumer to parse `UiEventEnvelope` (using generated types) and update the workflow store.

With this design the SSE stream becomes first-class in the API, keeping UI and scheduler in lockstep while
supporting advanced streaming scenarios.




