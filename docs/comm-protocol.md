# Scheduler → Worker Control-Plane Protocol

This document describes the control-plane envelope, session lifecycle, reliability/ordering rules, security/identity, and observability for scheduler ↔ worker communication. Business payloads are explicitly out of scope here.

> All control/session payloads are validated against JSON Schema in `docs/schema/session/*.json`. The envelope **must** be validated first.

---

## 1. Envelope & Message Types

All frames use a shared envelope; `type` selects the payload schema.

- Required envelope fields: `type`, `id`, `ts`, `tenant`, `sender`, `payload`
- `sender.id` is the **worker instance id** (issued/persisted locally in `var/worker_instance_id`), not a friendly name.
- Reserved for future use: `flags: string[]` (compression, tracing hints)
- Naming: `control.*` = control/session frames; `biz.*` = first‑party business; `ext.vendor.*` = third‑party extensions. Control layer only parses `control.*`; others are reliably transported but opaque.

Common error codes (subset): `E.AUTH.INVALID_TOKEN`, `E.AUTH.MTLS_REQUIRED`, `E.SESSION.STALE_BINDING`, `E.SESSION.DENIED`, `E.CMD.UNKNOWN`, `E.RESULT.DUPLICATE`, `E.RESULT.SEQ_GAP`, `E.PKG.INVALID`, `E.INTERNAL`, `E.TIMEOUT`.

Envelope schema: `docs/schema/session/ws.envelope.schema.json`.

---

## 2. Session Lifecycle (Worker-side state machine)

`NEW → HANDSHAKING → REGISTERED → READY → DRAINING → CLOSED` (errors go to `BACKOFF`, then retry to `NEW`).

- **NEW** → send `control.handshake` (auth token or mTLS)
- **HANDSHAKING** → recv `control.ack` / `control.reset`
- **REGISTERED** → send `control.register` (capabilities, runtimes, features, payload_types)
- **READY** → after `control.session.accept`, begin heartbeats (`control.heartbeat`) and business traffic
- **DRAINING** → scheduler sends `control.drain` (stop taking new; finish in-flight)
- **CLOSED** → graceful close or idle timeout / missed heartbeats
- **BACKOFF** → auth/network error; exponential backoff (jitter) then reconnect

Reconnect reconciliation: scheduler binds the connection to `worker_instance_id`. A reconnect presenting the same instance id resumes the session (or issues `control.reset` to force fresh handshake/register). No reconciliation by worker name.

---

## 3. Control Payload Schemas

- `control.handshake` -> `session/handshake.schema.json`
- `control.register` -> `session/register.schema.json` (capabilities only; no business inventory)
- `control.session.accept` -> `session/session.accept.schema.json` (contains `session_id` + `session_token`)
- `control.resume` -> `session/session.resume.schema.json`
- `control.reset` -> `session/session.reset.schema.json`
- `control.drain` -> `session/session.drain.schema.json`
- `control.ack` -> `session/ack.schema.json` (see §4 for fields)
- `control.heartbeat` -> `session/heartbeat.schema.json`

Business/extension payloads live under `biz.*` / `ext.vendor.*` and define their own schemas; the control layer only enforces envelope validity and reliability.

---

## 4. Reliability & Ordering (Sliding Window)

Per-direction ordered streams with sliding windows; duplex directions use independent sequences.

- **Sequence**: `seq` starts at 0 per direction and monotonically increases. Window size configured on both sides (see settings).
- **ACK payload**: `ack_seq` (highest contiguous received), `ack_bitmap` (bitset for the next window span), `recv_window` (current window size).
- **Send window**: sender tracks unacked frames within window; retries with exponential backoff + jitter until acked or max attempts reached.
- **Receive window**: buffer out-of-order frames within window; deliver to upper layer in-order; drop frames outside window as late/duplicate.
- **Idempotency**: `(id, corr)` guard at business layer; window/bitmap covers transport duplicates.
- **Late/duplicate ACKs**: ignored if outside sender window; no state corruption.

---

## 5. Security & Identity

- Auth modes: bearer token (preferred for dev), mTLS (preferred for prod). Envelope must include `tenant`; server binds connection to tenant.
- **Identity**: `worker_instance_id` is the authoritative peer identifier, persisted locally and presented in `sender.id` and in `control.handshake`.
- **Session token**: issued in `control.session.accept`, signed with scheduler secret; payload `{sid, wid, tenant, exp}` where `wid` = worker instance id. Worker includes it on subsequent resumes; `worker_name` is display-only and not part of the signature.
- Token rotation and connection-level revoke are supported (`control.reset` with `E.AUTH.INVALID_TOKEN`).

---

## 6. Observability (baseline)

Scheduler metrics: `ws_conn_active{tenant}`, `ws_frame_bytes_total{tenant,dir}`, `ws_heartbeat_miss_total{tenant,worker}`, `cmd_dispatch_total{tenant,node_type}`, `cmd_retry_total{reason}`, `result_latency_ms_bucket{tenant,node_type}`, `pkg_ops_total{tenant,op,status}`.

Worker metrics: `inflight_tasks`, `task_duration_ms_bucket{node_type}`, `heartbeat_sent_total`, `heartbeat_degraded_total`.

Logs: structured JSON with `tenant`, `sender.id`, `type`, `id`, `corr`, `code`, `seq`.

Threshold guidance (defaults; per-tenant overrides): `mem_pct ≥ 90%` or `disk_pct ≥ 95%` → auto-drain; missed heartbeats: 1× WARN, 2× DEGRADED, 3× UNHEALTHY → mark lost & rebind.

---

## 7. Example Exchange

1) Worker → `control.handshake` (`ack.request=true`)
2) Scheduler → `control.ack {for: handshake.id}`
3) Worker → `control.register` (`ack.request=true`)
4) Scheduler → `control.ack {for: register.id}`
5) Scheduler → `control.session.accept` (`session_id`, `session_token`, window params)
6) Worker → periodic `control.heartbeat`
7) Scheduler ↔ Worker exchange business frames (`biz.*`) with ordered `seq` and `control.ack` carrying `ack_seq`/`ack_bitmap`

---

## 8. CI Integration

- Validate envelope then payload schema on both ends before handling.
- Enforce idempotency cache keyed by `(id, corr)` and per-direction `seq` counters within the sliding window.
- Tests must cover duplicates, gaps, retries, and reconnect with preserved `worker_instance_id`.
