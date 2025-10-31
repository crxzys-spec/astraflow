# AstraFlow Resource, Affinity, and Artifact Design

## 1. Objectives

- Avoid shipping large artifacts (video, model weights, browser sessions, GPU tensors) across the control-plane wire.
- Keep tasks that rely on the same state on the same worker whenever possible.
- Let package authors return lightweight references, while the platform enforces guardrails (size limits, required types, TTL).
- Provide a single resource management layer in the worker so files and in-memory assets share lifecycle code.

## 2. Terminology

| Term | Meaning |
|------|---------|
| Resource / Artifact | Any reusable output: file on disk, browser session, loaded torch model, GPU context. |
| ResourceHandle | Reference object with `resourceId`, `type`, `workerId`, `scope` (run or session), `state`, and metadata. |
| Affinity Key | Scheduler-side identifier, for example `(tenant, package, version, sessionId)` or `(runtime, modelId)`. |
| Lease / TTL | Time-bounded claim on a resource. Prevents stale state from living forever. |

## 3. Worker Resource Registry

### API sketch

```python
class ResourceRegistry:
    def register(self, scope, resource_id, type, metadata) -> ResourceHandle: ...
    def register_file(self, resource_id, file_path, scope=None, metadata=None) -> ResourceHandle: ...
    def lease(self, resource_id) -> ResourceHandle: ...
    def release(self, resource_id, *, reason=None) -> None: ...
    def release_scope(self, scope) -> None: ...
    def touch(self, resource_id, *, expires_at=None) -> None: ...
    def list(self, *, scope=None, type=None) -> list[ResourceHandle]: ...
    def gc(self) -> None: ...
    def to_artifact_descriptor(self, resource_id, inline=None) -> dict: ...
```

### Storage backends

- **FileBackend**  
  Stores data under `settings.data_dir / run_id / session_id / ...`. Metadata includes file size, checksum, created_at.

- **MemoryBackend**  
  Wraps long-lived objects such as Playwright browser contexts, torch models, or GPU tensors. Tracks memory usage and eviction policy.

Both backends share:

- metadata persistence (JSON or sqlite for v1, Redis later),
- reference counts (`lease` increments, `release` decrements),
- eviction policy (LRU, explicit release, watermarks).

### Cleanup loop

Worker runs a background coroutine that:

1. scans handles with `in_use_count == 0` and `expires_at` in the past,
2. deletes files, closes sessions, frees GPU state,
3. reports reclaimed bytes in logs and heartbeat metrics.

When disk or memory watermarks are exceeded, the loop can promote eligible resources to `evicting` state and delete them early.

### Handler workflow

- **Inputs**: `ExecutionContext.resource_refs` contains the references sent by the scheduler. The worker pre-leases them and exposes the actual handles via `ExecutionContext.leased_resources` (a mapping from `resource_id` to `ResourceHandle`). Handlers can read metadata such as file paths or session IDs directly.
- **Outputs**: After producing large artifacts, handlers call `resource_registry.register(...)` or `register_file(...)` and return an `artifacts` list from `Runner` (e.g. `{"resource_id": "...", "type": "file", ...}`). Smaller values can remain inline in `outputs`.
- **Cleanup**: When a handler finishes, the worker releases all leases. Package code can voluntarily extend TTL (`touch`) or mark resources for eviction when they are no longer useful.

The `ExecutionContext.resource_registry` field is optional; packages should guard for `None` so unit tests or dummy transports keep working.

#### Example handler

```python
from datetime import timedelta

async def async_run(context):
    registry = context.resource_registry
    leased = context.leased_resources or {}

    # Reuse upstream artifact if present.
    video_handle = leased.get("run123/sessionA/frame001")
    if video_handle:
        local_path = video_handle.metadata.get("path")
        process_video(local_path)

    # Produce a new artifact.
    output_path = context.data_dir / "processed.mp4"
    render_video_to(output_path)

    artifact_id = f"{context.run_id}/{context.task_id}/processed"
    registry.register_file(
        resource_id=artifact_id,
        file_path=output_path,
        scope=context.run_id,
        metadata={"mime": "video/mp4"},
        expires_at=(
            video_handle.expires_at + timedelta(hours=1)
            if video_handle and video_handle.expires_at
            else None
        ),
    )

    return {
        "status": "succeeded",
        "outputs": {"message": "video processed"},
        "artifacts": [
            registry.to_artifact_descriptor(artifact_id, inline=False),
        ],
    }
```

## 4. Scheduler Affinity Registry

### API sketch

```python
class AffinityRegistry:
    def acquire(self, tenant, key, worker_id, *, ttl) -> bool: ...
    def lookup(self, tenant, key) -> AffinityRecord | None: ...
    def touch(self, tenant, key, *, ttl=None) -> None: ...
    def release(self, tenant, key, *, reason=None) -> None: ...
```

`AffinityRecord` keeps `worker_id`, `acquired_at`, `expires_at`, `inflight_count`, `metadata`, and a `state` flag (active, stale, draining).

### Dispatch flow

1. During workflow planning, extract affinity keys from node metadata (for example resource references or explicit session markers).  
2. Call `lookup` before selecting a worker. If the record is active and the worker is online, use that worker.  
3. When `resource_refs` specify a `workerId`, the scheduler pins dispatch to that worker; conflicting hints return HTTP 409, and an unavailable worker surfaces HTTP 503.  
4. On successful dispatch, call `acquire` (or `touch`) to refresh the lease.  
5. When the run or session ends, or the worker reports the resource freed, call `release`.
The runtime dispatcher reads the registry's ready queue, resolves pinned workers before fallback selection, and pushes commands via the WebSocket control-plane. Retry/backoff logic handles temporary worker unavailability; exceeding retry thresholds results in a transport error that closes the run.

### Failure handling

- Worker disconnects → mark the record `stale`. Retry for a grace period, then fail the node/run if the worker does not return.  
- Too many consecutive failures → remove the record so the next dispatch can rebuild state on a different worker (future extension).

## 5. Protocol extensions

### 5.1 Result payload

```json
{
  "run_id": "run-123",
  "task_id": "node-1",
  "status": "SUCCEEDED",
  "result": {
    "summary": "...",
    "artifacts": [
      {
        "resourceId": "run-123/session-A/frame-001",
        "workerId": "worker-playwright-1",
        "type": "file",
        "sizeBytes": 52428800,
        "expiresAt": "2025-11-01T12:00:00Z",
        "inline": false,
        "metadata": {
          "mime": "video/mp4"
        }
      }
    ]
  }
}
```

- `inline=true` means the payload already contains the data body.  
- `inline=false` indicates the consumer must resolve the reference through the worker resource registry.  
- Schema updates will add the `artifacts` array and metadata contract.

### 5.2 Dispatch parameters

```json
{
  "parameters": {
    "sourceVideo": {
      "resourceRef": {
        "resourceId": "run-123/session-A/frame-001",
        "workerId": "worker-playwright-1",
        "type": "file"
      }
    },
    "browserSession": {
      "resourceRef": {
        "resourceId": "run-123/playwright-session",
        "workerId": "worker-playwright-1",
        "type": "browserSession"
      }
    }
  }
}
```

The scheduler enforces allocation to `worker-playwright-1`. If the worker rejects the request (resource missing), the scheduler treats it as a hard failure in the current design.

## 6. Platform guardrails and package guidance

### Guardrails controlled by the platform

- `inline_payload_limit_bytes` (for example 2 MiB). Above the limit the scheduler rejects inline responses.  
- `forced_reference_types` (set of artifact types that must be references).  
- `default_resource_ttl_seconds`.  
- Worker-level watermarks for disk and memory usage that trigger cleanup commands.

### Package developer guidance

- Use SDK helpers such as `artifact.store_file(path)`, `artifact.store_bytes(data)`, `resource.lease("session-id")`.  
- Declare default behavior in the package manifest:

```json
{
  "resources": {
    "defaults": {
      "inlineThresholdBytes": 131072,
      "type": "file"
    }
  }
}
```

- Document typical patterns (Playwright session reuse, torch model warm caches) so handler authors know when to return references.

## 7. Lifecycle

1. **Create**: handler stores output via `ResourceRegistry.register` and returns a reference.  
2. **Dispatch**: scheduler reads the reference, locks affinity to the worker, and ships the command.  
3. **Consume**: worker leases the resource; handler uses the handle.  
4. **Release**: handler (or context manager) calls `release`.  
5. **Keep-alive**: long-running sessions call `touch` to extend TTL.  
6. **Cleanup**: when the run or session ends, scheduler sends a cleanup command; worker releases the entire scope.  
7. **Faults**: if a worker times out or runs out of resources, it marks the handle `evicted` and reports via heartbeat; the scheduler fails the node or rebuilds state in a future revision.

## 8. Heartbeat metrics

Workers add the following fields to heartbeat payloads:

- `metrics.resource.disk_bytes_in_use`
- `metrics.resource.mem_bytes_in_use`
- `metrics.resource.sessions_active`
- `metrics.resource.eviction_candidates`
- `metrics.resource.last_gc_seconds`

These metrics let the scheduler apply back-pressure or issue cleanup commands.

## 9. Sample worker configuration

```
ASTRA_WORKER_DATA_DIR=/var/astraflow/data
ASTRA_WORKER_RESOURCE_MAX_DISK_BYTES=21474836480      # 20 GiB
ASTRA_WORKER_RESOURCE_MAX_MEM_BYTES=8589934592        # 8 GiB
ASTRA_WORKER_RESOURCE_GC_INTERVAL_SECONDS=60
ASTRA_WORKER_INLINE_RESULT_LIMIT_BYTES=2097152        # 2 MiB
ASTRA_WORKER_RESOURCE_DEFAULT_TTL_SECONDS=3600
```

## 10. Open items

- Update the JSON Schemas (`ws.result`, `ws.cmd.dispatch`) to add `artifacts` and `resourceRef`.  
- Persist `AffinityRegistry` (in-memory now, move to Redis or a SQL table).  
- Worker restart recovery: scan `data_dir` and rebuild the registry.  
- Tenant isolation: quotas per tenant for disk, memory, and active sessions.  
- Security: signed URLs or encrypted blobs when references point to shared storage.  
- Cross-worker fallback (future): optional second storage URI in the handle, or orchestrated copy.

This document captures the agreed design so implementation across scheduler, worker, and package SDK can follow the same contracts.
