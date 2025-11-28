# Scheduler �?Worker Control-Plane (Comm Protocol)

This document defines the message envelope, payload schemas, session lifecycle, reliability/ordering, security/tenancy, and observability for the AstraFlow scheduler–worker control-plane.

> All message payloads are separately validated against JSON Schema in `docs/schema/ws/*.json`. The envelope **must** be validated first.

---

## 1. Envelope & Message Types

All frames use a shared envelope; `type` selects the payload schema.

- Required envelope fields: `type`, `id`, `ts`, `tenant`, `sender`, `payload`
- Reserved for future use: `flags: string[]` (compression, tracing hints)

**Shared error codes (subset)**

- `E.AUTH.INVALID_TOKEN`, `E.AUTH.MTLS_REQUIRED`
- `E.SESSION.STALE_BINDING`, `E.SESSION.DENIED`
- `E.CMD.UNKNOWN`, `E.CMD.CONCURRENCY_VIOLATION`
- `E.RESULT.DUPLICATE`, `E.RESULT.SEQ_GAP`
- `E.PKG.INVALID`, `E.PKG.PERMISSION`
- `E.INTERNAL`, `E.TIMEOUT`

See: `docs/schema/ws/ws.envelope.schema.json`.

---

## 2. Session Lifecycle (Worker-side State Machine)

`NEW �?HANDSHAKING �?REGISTERED �?HEARTBEATING �?DRAINING �?CLOSED` (errors go to `BACKOFF`, then retry to `NEW`).

Key transitions

- **NEW** �?send `handshake` (token or mTLS)
- **HANDSHAKING** �?recv `ack` / `error`
- **REGISTERED** �?send `register` (capabilities, pkg inventory)
- **HEARTBEATING** �?periodic `heartbeat` (healthy true/false)
- **DRAINING** �?scheduler sends `cmd.drain` (stop taking new; finish in-flight)
- **CLOSED** �?graceful close or idle timeout / missed heartbeats
- **BACKOFF** �?auth/network error; exponential backoff (jitter) then reconnect

Reconnect reconciliation (§4.4): scheduler compares `worker_id` and last `session_id`; stale bindings (orphaned in-flight tasks) are resolved per policy.

---

## 3. Message Payload Schemas

- `handshake` -> `ws.handshake.schema.json`
- `register` -> `ws.register.schema.json`
- `ack` -> `ws.ack.schema.json`
- `heartbeat` -> `ws.heartbeat.schema.json`
- `cmd.dispatch` -> `ws.cmd.dispatch.schema.json`（含 middleware 链路元数据：`host_node_id`、`middleware_chain`、`chain_index`，可选）
- `feedback` -> `ws.feedback.schema.json`
- `result` -> `ws.result.schema.json`
- `error` -> `ws.error.schema.json`
- `pkg.install` / `pkg.uninstall` / `pkg.event` -> corresponding `ws.pkg.*.schema.json`

**Middleware trace 元数据**

- cmd.dispatch payload 可携带：`host_node_id`（宿主节点 id）、`middleware_chain`（挂载的 middleware id 数组）、`chain_index`（当前 middleware 在链路中的位置，宿主为 null）。
- node state/metadata 中会包含：
  - 对宿主：`middlewares: string[]`
  - 对 middleware：`host_node_id`、`chain_index`
  - 可由 UI 用于 trace 展示/过滤，不影响执行语义。

### 3.1 Dispatch resources and affinity

`cmd.dispatch` exposes two optional helpers:

- `resource_refs[]` &mdash; describes artifacts that must already exist on the selected worker. Each entry includes `resource_id`, `worker_id`, `type`, optional `scope`, `expires_at`, and metadata. Scheduling logic must respect these hints or fail fast.
- `affinity` &mdash; conveys sticky or preferred scheduling keys so follow-up commands stay on the worker that owns cached state (for example Playwright sessions or loaded models).

The free-form `parameters` object remains unchanged; packages can continue to inline light data alongside references.

### 3.2 Result artifacts

`result` payloads now support an optional `artifacts[]` array. Every artifact descriptor contains:

- `resource_id`, `worker_id`, `type`
- Optional `size_bytes`, `expires_at`, `inline` flag, and additional metadata

Workers set `inline=true` when the payload already contains the data body. Otherwise, consumers must resolve the reference via the worker resource registry (see `docs/resource-affinity-and-artifacts.md`).


### 3.3 Feedback streaming (adapter telemetry)

Workers may emit incremental execution telemetry through the `feedback` payload while a node is running:

- `stage` - optional scheduler hint such as `running`, `streaming`, `waiting_inputs`.
- `progress` - normalized 0-1 progress for progress bars.
- `message` - human friendly status text exposed to dashboards.
- `chunks[]` - ordered fragments per channel (`stdout`, `stderr`, `log`, `llm`, etc.) carrying either UTF-8 text or base64 data along with MIME type and metadata.
- `metrics` - ad-hoc numeric gauges (loss, iterations, throughput).

Feedback is incremental; workers must still emit a terminal `result` payload when execution completes. The scheduler can translate feedback into SSE notifications (`node.state`, `node.result.delta`) for UI consumption.

---

## 4. Reliability & Ordering

### 4.1 ACK & Retry
- Any control message can request per-message ACKs (`ack.request=true` in envelope).
- Sender retries unacked messages with **exponential backoff + jitter** (base 200 ms, max 5 s, 6 attempts).
- Scheduler `RunOrchestrator` keeps a 5 second ack deadline per dispatch; if the ack does not arrive it resets the run state and requeues the command before ultimately surfacing `E.DISPATCH.UNAVAILABLE`.
- **Idempotency** by `(id, corr)`; receivers must no-op duplicates (and may resend ack).

### 4.2 Sequence Numbers
- Maintain **per-run** stream: `seq` strictly increases for `cmd.dispatch` and `result`.
- On gap �?respond `E.RESULT.SEQ_GAP`; sender retries from last acked `seq`.

### 4.3 Duplicate Policy
- **Result duplicates**: accept **first**; subsequent with same `(task_id, seq)` drop & ack.
- **Command duplicates**: re-emit ack; **must not** start duplicate execution; guard via `concurrency_key`.

### 4.4 Reconnect & Stale Reconciliation
- Worker reconnects with `handshake` + `register`.
- Scheduler checks orphaned tasks for that `worker_id`:
  - Lease **expired** �?requeue (replay).
  - Lease **valid** but new session �?mark old session lost, rebind tasks; late duplicate results are dropped via idempotency.

---

## 5. Concurrency Rules

- Default worker parallelism = `capabilities.concurrency.max_parallel`.
- `concurrency_key` enforces single-flight within a worker (e.g., one task per `run_id`).
- Scheduler may enforce **cross-worker** single-flight with queue/lease semantics.

---

## 6. Security & Tenancy

- Auth modes: **token** (short-lived bearer, tenant-bound) or **mTLS** (preferred in prod).
- Envelope **must** include `tenant`; server binds connection to tenant.
- **Audit**: log who/when/what for `pkg.install/uninstall` and `cmd.dispatch` with `sender.id`, `tenant`, `corr`, outcome code.
- Support token rotation and connection-level revoke (server may kick with `E.AUTH.INVALID_TOKEN`).

---

## 7. Observability (Baseline)

**Scheduler metrics**
- `ws_conn_active{tenant}`
- `ws_heartbeat_miss_total{tenant,worker}`
- `cmd_dispatch_total{tenant,node_type}`, `cmd_retry_total{reason}`
- `result_latency_ms_bucket{tenant,node_type}`
- `ws_conn_active{tenant}`, `ws_frame_bytes_total{tenant,dir}`
- `pkg_ops_total{tenant,op,status}`

**Worker metrics**
- `inflight_tasks`
- `task_duration_ms_bucket{node_type}`
- `heartbeat_sent_total`, `heartbeat_degraded_total`

**Logs**
- Structured JSON with `tenant`, `sender.id`, `type`, `id`, `corr`, `code`, `seq`.

**Threshold guidance (defaults; per-tenant overrides)**
- `mem_pct �?90%` or `disk_pct �?95%` �?auto-drain
- `inflight_tasks �?max_parallel` & sustained �?consider scaling/rebinding
- Missed heartbeats: 1× WARN, 2× DEGRADED, 3× UNHEALTHY �?mark lost & rebind

---

## 8. Example Exchange

1. Worker �?`handshake` (`ack.request=true`)
2. Scheduler �?`ack {for: handshake.id}`
3. Worker �?`register`
4. Scheduler �?`cmd.dispatch` (`corr=task_id, seq=1, ack.request=true`)
5. Worker �?`ack {for: cmd.id}`
6. Worker �?`result` (`corr=task_id, seq=1`)
7. Scheduler �?`ack {for: result.id}`
8. Worker �?periodic `heartbeat`

---

## 9. CI Integration

- Validate **envelope** then **payload** schema on both ends before handling.
- Enforce idempotency cache keyed by `(id, corr)` and per-run `seq` counters.
- Unit tests must cover dupes, gaps, retries, reconnection reconciliation.
