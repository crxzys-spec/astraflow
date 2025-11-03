# Worker-Scheduler Architecture

This document captures the backend positioning for AstraFlow, detailing the roles, communication channels, package lifecycle, runtime management, scheduling strategy, and rollout plan for the Scheduler and Worker services.

## 1. Roles & Responsibilities

### Scheduler Server
- **Persistent state**: WorkflowRun records, execution queue metadata, Worker bindings (via `ExecutionJobStore` and related tables).
- **Interfaces**:
  - REST: `POST /api/workers/register`, `POST /api/workers/heartbeat` for Worker lifecycle management.
  - Package management commands: install/uninstall node packages.
  - WebSocket control channel for dispatching scheduling directives and receiving execution feedback.
- **Scheduling workflow**:
  - Continue using `ExecutionDispatcher` to emit `RunTaskCommand`.
  - Select appropriate Workers based on Worker-package mappings and assign dedicated queues.
  - Monitor Worker health; trigger rebind or drain operations when anomalies are detected.

### Worker Server
- **Startup sequence**:
  - Load configuration (Scheduler endpoint, Worker ID, auth token).
  - Register with the Scheduler over WebSocket.
  - Install node packages as instructed.
  - Establish a persistent WebSocket session for task dispatch.
  - Send heartbeat reports covering status, resources, and installed packages.
- **Runtime modules**:
  - `PackageManager`: download `.cwx`, validate manifests, install Python dependencies, execute hooks.
  - `AdapterRegistry`: load `manifest.json` entrypoints and register adapters.
  - `Runner`: reuse `WorkflowRunner` to execute node tasks.
  - WebSocket handler: receive package/task commands and stream execution results and logs.

## 2. Communication Channels

### WebSocket Control Plane
- **Worker ->Scheduler**: registration, heartbeat updates, execution results, incremental task feedback (progress/logs/LLM tokens), package install acknowledgements.
- **Scheduler ->Worker**: package install/uninstall commands, manual controls (Drain/Rebind), task dispatch notifications.
- **Specification**: WebSocket frame structure is defined in `docs/comm-protocol.md`, with authoritative JSON Schema under `docs/schema/ws/`.
- **Message format** (JSON examples):
  ```json
  { "type": "register", "workerId": "...", "capabilities": [...] }
  { "type": "heartbeat", "status": { ... }, "packages": [ ... ] }
  { "type": "package.install", "package": "crawlerx_playwright", "version": "2025.10.0", "url": "...", "sha256": "..." }
  { "type": "task.dispatch", "runId": "...", "taskId": "...", "nodeId": "...", "package": {"name": "...", "version": "2025.10.0"}, "parameters": { ... } }
  { "type": "feedback", "runId": "...", "taskId": "...", "stage": "streaming", "progress": 0.42, "message": "LLM streaming", "chunks": [{ "channel": "llm", "text": "Hello" }] }
  { "type": "task.result", "runId": "...", "taskId": "...", "nodeId": "...", "status": "SUCCEEDED", "result": { ... } }
  ```
- **Reliability requirements**: ACK with retry, keepalive pings, resync state after reconnect.
  Task dispatch and execution acknowledgements ride exclusively on WebSocket frames; no separate message queue is involved.

## 3. Node Package Model

### 3.1 Adapter feedback example

Packages can stream execution telemetry back to the scheduler through the `FeedbackPublisher` exposed on the `ExecutionContext`. A typical async adapter might look like:

```python
from worker.agent.runner.context import ExecutionContext
from shared.models.ws.feedback import FeedbackChannel


class SummariseAdapter:
    async def async_run(self, ctx: ExecutionContext):
        reporter = ctx.feedback

        if reporter:
            await reporter.send(
                stage="running",
                progress=0.05,
                message="Downloading source articles…",
            )

        articles = await self._load_articles(ctx.params["urls"])

        if reporter:
            reporter.send_nowait(
                stage="streaming",
                message="Tokenising input",
                chunks=[{"channel": FeedbackChannel.log, "text": "Loaded %d articles" % len(articles)}],
            )

        summary_tokens = []
        async for token in self._llm_stream(articles):
            summary_tokens.append(token)
            if reporter:
                reporter.send_nowait(
                    stage="streaming",
                    chunks=[{"channel": FeedbackChannel.llm, "text": token}],
                    progress=min(0.95, 0.05 + len(summary_tokens) / 2000),  # crude heuristic
                )

        summary = "".join(summary_tokens)

        if reporter:
            await reporter.send(
                stage="finalising",
                progress=0.99,
                message="Streaming complete, packaging result",
            )

        return {
            "status": "SUCCEEDED",
            "outputs": {"summary": summary},
            "metadata": {"token_count": len(summary_tokens)},
        }
```

For synchronous adapters, call `ctx.feedback.send_nowait(...)` (or `emit_text`) to avoid blocking the handler. The reporter takes care of serialising payloads to `task.feedback` frames; packages do not have to manage WebSocket details.

### Package Layout Example
```
crawlerx_playwright/
鈹溾攢鈹€ manifest.json
鈹溾攢鈹€ adapters/crawlerx_playwright/*.py
鈹溾攢鈹€ resources/...
鈹溾攢鈹€ scripts/install_extra.sh
鈹斺攢鈹€ requirements.txt
 manifest.json
 adapters/crawlerx_playwright/*.py
 resources/...
 scripts/install_extra.sh
 requirements.txt
```


### Manifest Instance Example
```jsonc
{
  "name": "playwright",
  "version": "2025.10.0",
  "schemaVersion": "1.0.0",
  "description": "...",
  "adapters": [
    {
      "name": "playwright",
      "runtime": "playwright",
      "entrypoint": "playwright.adapter:PlaywrightAdapter",
      "capabilities": [
        "playwright.open_page",
        "playwright.click",
        "playwright.input",
        "... etc"
      ],
      "idempotency": "per_request",
      "metadata": {
        "disable_ssl_verify": false
      }
    }
  ],
  "python": {
    "requires": ">=3.10,<3.12",
    "dependencies": [
      "playwright==1.47.2",
      "...other dependencies"
    ]
  },
  "nodes": [
    {
      "type": "playwright.open_page",
      "status": "published",
      "category": "Page Actions",
      "label": "Open Page",
      "description": "Navigate to a specific URL with configurable wait conditions.",
      "tags": ["playwright", "navigation"],
      "runtimes": {
        "playwright": {
          "config": {
            "navigationStrategy": "default"
          },
          "handler": "open_page"
        }
      },
      "schema": {
        "parameters": {
          "type": "object",
          "properties": {
            "url": {
              "type": "string",
              "format": "uri",
              "description": "Page URL opened by the node.",
              "default": "https://example.com"
            },
            "waitFor": {
              "type": "string",
              "enum": ["domcontentloaded", "load", "networkidle"],
              "default": "domcontentloaded"
            },
            "timeoutMs": {
              "type": "integer",
              "minimum": 0,
              "maximum": 120000,
              "default": 30000
            }
          },
          "required": ["url"]
        },
        "results": {
          "type": "object",
          "properties": {
            "status": {
              "type": "string",
              "enum": ["PENDING", "RUNNING", "SUCCEEDED", "FAILED"],
              "default": "PENDING"
            },
            "page": {
              "type": "object",
              "default": {}
            },
            "done": {
              "type": "boolean",
              "default": false
            }
          },
          "required": ["status"],
          "additionalProperties": true
        }
      },
      "ui": {
        "inputPorts": [
          {
            "key": "trigger",
            "label": "Trigger",
            "binding": {
              "path": "parameters.trigger",
              "mode": "write"
            }
          }
        ],
        "widgets": [
          {
            "key": "url",
            "label": "Target URL",
            "component": "string",
            "binding": {
              "path": "parameters.url",
              "mode": "two_way"
            },
            "options": {
              "placeholder": "https://example.com",
              "helpText": "Page URL to open.",
              "required": true
            }
          },
          {
            "key": "waitFor",
            "label": "Wait Strategy",
            "component": "enum",
            "binding": {
              "path": "parameters.waitFor",
              "mode": "two_way"
            },
            "options": {
              "helpText": "Playwright wait-until behaviour.",
              "options": [
                { "label": "DOM Content Loaded", "value": "domcontentloaded" },
                { "label": "Page Load", "value": "load" },
                { "label": "Network Idle", "value": "networkidle" }
              ]
            }
          },
          {
            "key": "timeoutMs",
            "label": "Timeout (ms)",
            "component": "number",
            "binding": {
              "path": "parameters.timeoutMs",
              "mode": "two_way"
            },
            "options": {
              "helpText": "Abort after this timeout.",
              "min": 0,
              "max": 120000,
              "step": 500
            }
          },
          {
            "key": "executionStatus",
            "label": "Execution Status",
            "component": "string",
            "binding": {
              "path": "results.status",
              "mode": "read"
            },
            "options": {
              "helpText": "Most recent execution status from the Worker.",
              "readOnly": true
            }
          },
          {
            "key": "pageContext",
            "label": "Page Context",
            "component": "json",
            "binding": {
              "path": "results.page",
              "mode": "read"
            },
            "options": {
              "helpText": "Page handle metadata returned by the Worker.",
              "readOnly": true,
              "collapsed": true
            }
          }
        ],
        "outputPorts": [
          {
            "key": "page",
            "label": "Page Context",
            "binding": {
              "path": "results.page",
              "mode": "read"
            }
          },
          {
            "key": "done",
            "label": "Done",
            "binding": {
              "path": "results.done",
              "mode": "read"
            }
          }
        ]
      },
      "conditions": {},
      "extensions": {},
      "metadata": {}
    },
    "...other nodes..."
  ],
  "resources": [
    { "path": "resources/chromium", "type": "download", "sha256": "..." }
  ],
  "hooks": {
    "install": ["scripts/install_extra.sh"],
    "uninstall": ["scripts/cleanup.sh"]
  },
  "signature": {
    "sha256": "...",
    "signedAt": "...",
    "signedBy": "..."
  }
}
```

`schema.parameters` / `schema.results` mirror the workflow schema: they validate per-node `parameters` / `results` payloads and supply defaults that the editor seeds when a node is dropped onto the canvas.

### Package Lifecycle
- Scheduler publishes `.cwx` (zip) packages to a repository, recording version and checksum in the database.
- When required, Scheduler issues `package.install` over WebSocket.
- Worker `PackageManager`:
  - Download and verify archive; extract to `/var/crawlerx/packages/<name>/<version>/`.
  - Install `python.dependencies` (pip/venv).
  - Run install hooks.
  - Refresh `AdapterRegistry`.
  - ACK result; on failure, rollback (remove dependencies, clean directories).
- `package.uninstall` triggers manifest uninstall hooks and deletes the package directory.
- Worker reports installed package versions in heartbeats; Scheduler uses this to decide upgrade/rollback.

## 4. Workflow Definition Instance

The workflow definition serves as the contract between the drag-and-connect editor and the Scheduler runtime. The UI persists the JSON, and the Scheduler consumes the same payload to orchestrate tasks. Global context is no longer exchanged; instead, node parameters contain fully resolved values or expressions local to each node, and widgets can also bind to `results.*` paths for read-only display of execution outputs. **All workflow IDs and node IDs must be UUIDs** so they remain globally unique across imports and Scheduler executions. Below is a representative instance that wires two Playwright adapters from the package example above.

> **Tip:** The bundled `example.pkg.feedback_demo` node demonstrates the feedback contract: the worker emits incremental updates via `metadata.results`, for example `{"results": {"summary": "HELLO"}}`. The scheduler merges those keys into `results.*`, publishes `node.result.delta`, and the builder's `summaryPreview` widget (bound to `/results/summary`, `mode: "read"`) renders the stream live. Reuse the same convention for any other result fields you want to surface incrementally.

Example welcome journey:
- **Load Welcome Config** — parses the JSON definition, expands the template into a ready-to-send message, and exposes derived fields (recipient, timing, channel).
- **Personalise Message** — formats the message, forwards routing metadata (`recipient`, `subject`, `delaySeconds`, `tokenDelayMs`) to downstream nodes, and provides the stream source for the feedback node.
- **Stream Feedback** — emits the formatted message token-by-token so the builder shows live progress.
- **Schedule Delivery** — waits for the configured delay, modelling long-running work.
- **Send Welcome Notification** — simulates dispatch, returns a `notificationId`, and summarises the action.
- **Audit Delivery** — records the outcome (including the notification ID) for traceability.

```json
{
  "id": "ba55c67a-9ad4-4b6f-a719-b84e774c2d11",
  "schemaVersion": "2025-10",
  "metadata": {
    "name": "Playwright Smoke Check",
    "description": "Open a target page and click the login button to verify availability.",
    "tags": ["playwright", "smoke-test"],
    "environment": "staging"
  },
  "nodes": [
    {
      "id": "2b2c3fcb-9c18-4ca2-9b5a-8ad4deb1f164",
      "type": "playwright.open_page",
      "package": {
        "name": "crawlerx_playwright",
        "version": "2025.10.0"
      },
      "label": "Open Base Page",
      "position": { "x": 100, "y": 160 },
      "parameters": {
        "url": "https://example.com",
        "waitFor": "domcontentloaded",
        "timeoutMs": 30000
      },
      "results": {
        "status": "PENDING",
        "page": {},
        "done": false
      },
      "ui": {
        "inputPorts": [
          {
            "key": "trigger",
            "label": "Trigger",
            "binding": {
              "path": "parameters.trigger",
              "mode": "write"
            }
          }
        ],
        "widgets": [
          {
            "key": "url",
            "label": "Target URL",
            "component": "string",
            "binding": {
              "path": "parameters.url",
              "mode": "two_way"
            },
            "options": {
              "helpText": "Page URL to open.",
              "required": true,
              "placeholder": "https://example.com"
            }
          },
          {
            "key": "waitFor",
            "label": "Wait Strategy",
            "component": "enum",
            "binding": {
              "path": "parameters.waitFor",
              "mode": "two_way"
            },
            "options": {
              "helpText": "Playwright wait-until behaviour.",
              "options": [
                { "label": "DOM Content Loaded", "value": "domcontentloaded" },
                { "label": "Page Load", "value": "load" },
                { "label": "Network Idle", "value": "networkidle" }
              ]
            }
          },
          {
            "key": "timeoutMs",
            "label": "Timeout (ms)",
            "component": "number",
            "binding": {
              "path": "parameters.timeoutMs",
              "mode": "two_way"
            },
            "options": {
              "helpText": "Abort after this timeout.",
              "min": 0,
              "max": 120000,
              "step": 500
            }
          },
          {
            "key": "executionStatus",
            "label": "Execution Status",
            "component": "string",
            "binding": {
              "path": "results.status",
              "mode": "read"
            },
            "options": {
              "helpText": "Most recent execution status from the Worker.",
              "readOnly": true
            }
          },
          {
            "key": "pageContext",
            "label": "Page Context",
            "component": "json",
            "binding": {
              "path": "results.page",
              "mode": "read"
            },
            "options": {
              "helpText": "Latest page handle metadata returned by the Worker.",
              "readOnly": true,
              "collapsed": true
            }
          }
        ],
        "outputPorts": [
          {
            "key": "page",
            "label": "Page Context",
            "binding": {
              "path": "results.page",
              "mode": "read"
            }
          },
          {
            "key": "done",
            "label": "Done",
            "binding": {
              "path": "results.done",
              "mode": "read"
            }
          }
        ]
      }
    },
    {
      "id": "8f5dea1f-6a13-4e43-843f-5361c40f8f5a",
      "type": "playwright.click",
      "package": {
        "name": "crawlerx_playwright",
        "version": "2025.10.0"
      },
      "label": "Click Login",
      "position": { "x": 360, "y": 160 },
      "parameters": {
        "selector": "#login-button",
        "waitFor": "visible",
        "button": "left",
        "delay": 0
      },
      "results": {
        "status": "PENDING",
        "done": false,
        "metadata": {}
      },
      "schema": {
        "parameters": {
          "type": "object",
          "properties": {
            "selector": {
              "type": "string",
              "description": "Element selector Playwright clicks.",
              "default": "#login-button"
            },
            "waitFor": {
              "type": "string",
              "enum": ["visible", "attached", "stable", "enabled"],
              "default": "visible"
            },
            "button": {
              "type": "string",
              "enum": ["left", "right", "middle"],
              "default": "left"
            },
            "delay": {
              "type": "integer",
              "minimum": 0,
              "default": 0
            }
          },
          "required": ["selector"]
        },
        "results": {
          "type": "object",
          "properties": {
            "status": {
              "type": "string",
              "enum": ["PENDING", "RUNNING", "SUCCEEDED", "FAILED"],
              "default": "PENDING"
            },
            "done": {
              "type": "boolean",
              "default": false
            },
            "metadata": {
              "type": "object",
              "default": {}
            }
          },
          "required": ["status"],
          "additionalProperties": true
        }
      },
      "ui": {
        "inputPorts": [
          {
            "key": "trigger",
            "label": "Trigger",
            "binding": {
              "path": "parameters.trigger",
              "mode": "write"
            }
          },
          {
            "key": "page",
            "label": "Page Context",
            "binding": {
              "path": "parameters.page",
              "mode": "write"
            }
          }
        ],
        "widgets": [
          {
            "key": "selector",
            "label": "Resolved Selector",
            "component": "string",
            "binding": {
              "path": "parameters.selector",
              "mode": "two_way"
            },
            "options": {
              "placeholder": "#login-button",
              "helpText": "Element to click.",
              "required": true
            }
          },
          {
            "key": "button",
            "label": "Mouse Button",
            "component": "enum",
            "binding": {
              "path": "parameters.button",
              "mode": "two_way"
            },
            "options": {
              "helpText": "Mouse button to use for the click.",
              "options": [
                "left",
                "right",
                "middle"
              ]
            }
          },
          {
            "key": "delay",
            "label": "Delay (ms)",
            "component": "number",
            "binding": {
              "path": "parameters.delay",
              "mode": "two_way"
            },
            "options": {
              "helpText": "Delay before performing the click."
            }
          },
          {
            "key": "executionStatus",
            "label": "Execution Status",
            "component": "string",
            "binding": {
              "path": "results.status",
              "mode": "read"
            },
            "options": {
              "helpText": "Most recent execution status.",
              "readOnly": true
            }
          },
          {
            "key": "resultMetadata",
            "label": "Result Metadata",
            "component": "json",
            "binding": {
              "path": "results.metadata",
              "mode": "read"
            },
            "options": {
              "helpText": "Worker-provided metadata payload.",
              "readOnly": true,
              "collapsed": true
            }
          }
        ],
        "outputPorts": [
          {
            "key": "done",
            "label": "Done",
            "binding": {
              "path": "results.done",
              "mode": "read"
            }
          }
        ]
      }
    }
  ],
  "edges": [
    {
      "id": "d2e8b74f-2a31-4f9f-a8c4-2a88dcb3f7b0",
      "source": { "node": "2b2c3fcb-9c18-4ca2-9b5a-8ad4deb1f164", "port": "done" },
      "target": { "node": "8f5dea1f-6a13-4e43-843f-5361c40f8f5a", "port": "trigger" }
    },
    {
      "id": "a36f5d7c-4c4d-4c46-9a8f-21d612f0b143",
      "source": { "node": "2b2c3fcb-9c18-4ca2-9b5a-8ad4deb1f164", "port": "page" },
      "target": { "node": "8f5dea1f-6a13-4e43-843f-5361c40f8f5a", "port": "page" }
    }
  ],
  "runtimes": {
    "playwright": {
      "workerHints": {
        "package": "crawlerx_playwright",
        "minVersion": "2025.10.0"
      }
    }
  },
  "tags": ["web", "smoke"]
}
```
Each entry under `workflow.nodes[]` may include a `state` object populated by the scheduler during execution. The schema mirrors `WorkflowNodeState` from the public API and supplies the latest stage, progress, and failure details so the builder can surface live feedback without mutating package-controlled `parameters` or `results`.

This payload is stored alongside the manifest-driven catalog. When a run is triggered, the Scheduler selects adapters by `type` and dispatches `RunTaskCommand` messages per node following the defined edges. Per-node parameters are passed through exactly as authored in the workflow JSON.

### Package Registry & Adapter Resolution

- Workers install packages into versioned directories (e.g. `/var/worker/packages/<name>/<version>/`) so multiple revisions can coexist.
- During install, `PackageManager` parses `manifest.json`, validates adapters, and dynamically imports each `entrypoint`. Handlers are registered as `(package_name, package_version, capability|handler_key) -> callable` in the `AdapterRegistry`.
- `cmd.dispatch` payloads must include `package.name`, `package.version` (or satisfy `minVersion` hints) so the Worker can locate the exact handler for execution. Missing handlers return a `command.error`.
- Worker heartbeat/registration frames list installed package versions; Scheduler uses this inventory to bind runs to compatible Workers and initiate targeted upgrades/rollbacks.
- Uninstall commands remove only the referenced version and prune associated handler mappings; other versions remain intact to support gradual rollout.
- At runtime, `AdapterRegistry` exposes lookups (`(package, version, handler)` -> callable) for the execution engine; missing entries produce protocol-compliant `command.error` responses with `E.CMD.CONCURRENCY_VIOLATION` or similar error codes.
- `Runner` constructs an `ExecutionContext` (`run_id`, `task_id`, node params, tenant, dedicated data dir) and invokes the handler; results are wrapped into `result` frames, while exceptions are normalized to `E.RUNNER.FAILURE`.
- Default package commands (`pkg.install`, `pkg.uninstall`) are handled asynchronously: downloads happen off the event loop, success emits `pkg.event{status=installed}`, failures emit `status=failed` with error details; uninstall emits a terminal `pkg.event` so the Scheduler can mark cleanup complete.
- Workers maintain a lightweight cache of handler metadata (runtime, node type, capabilities) to accelerate dispatch resolution and to surface inventory via diagnostics APIs.

## 4. Worker Environment Management

- Each Worker maintains its own virtualenv (e.g. `/var/crawlerx/env`).
- `PackageManager` exposes helpers `install_python_dependencies(list[str])` and `run_hook(script_path)` (trusted scripts/whitelisted commands).
- Resources declared in `manifest.resources` are downloaded and placed as specified.
- Worker runtime monitors CPU/Mem/Disk and includes metrics in heartbeat payloads.

## 5. Scheduling Strategy & State Management

- Scheduler tracks `ExecutionWorkerBinding` mapping `(run, package) -> (worker, channel)` in the database.
- On successful execution, Worker calls `record_worker_affinity` to refresh bindings.
- If a Worker is offline, Scheduler leverages heartbeat lapse or failure notifications to trigger `ExecutionDispatcher` rebound logic.
- Manual rebind: `POST /api/v1/scheduler/runs/{run_id}/rebind` sends WebSocket instructions to switch or drain.
- Scheduler selects target Workers based on installed packages, load, and health.
- When dispatching, Scheduler includes `package.name` and `package.version` (or resolves via `minVersion`) so Workers fetch the precise handler; Workers respond with `result` or `command.error` payloads, tagging `corr` with the original `taskId` for idempotency tracking.
- Worker-side concurrency guard enforces single-flight per `concurrency_key`; duplicate inflight commands are rejected with `E.CMD.CONCURRENCY_VIOLATION`, allowing Scheduler to requeue or delay retries.

## 6. Security & Operations (Initial Phase)

- Deploy within secured networks or VPN; Redis/MQ remain private.
- WebSocket runs over `wss`; handshake includes token or mTLS auth to block unauthorized Workers.
- Gradually introduce manifest signing, package verification, and command auditing.
- **Logging & metrics**:
  - Scheduler: Worker status (online/offline, heartbeat latency), queue depth, package install telemetry.
  - Worker: package install/uninstall logs, task execution logs.
  - Alerts tie to exceptional conditions.
- Version strategy: keep at least N previous versions of critical packages deployed to Workers so rollbacks are one command away; Scheduler tracks which Workers hold which versions to orchestrate phased upgrades and drains.

## 7. Implementation Roadmap

1. **Control plane**: add Scheduler WebSocket server with ACK protocol; build Worker client with heartbeat, reconnection, and task dispatch handling.
2. **Package management**: implement manifest parser, download/install/uninstall pipeline, Adapter registration; design `.cwx` packaging tool.
3. **Dispatch orchestration**: update `ExecutionDispatcher` to stream commands over WebSocket; retire Celery queue dependencies; enforce concurrency via WS sequencing.
4. **State sync**: consolidate Worker registration and heartbeat schema; persist `ExecutionWorkerBinding`; surface APIs for queries and manual operations.
5. **Monitoring & tooling**: CLI/API for Worker status, package management, forced rebind; add metrics and logs.
6. **Security hardening (future)**: introduce package signing, command ACLs, mTLS, and audit trails.

## 8. Contract & SDK Generation

- Adopt `openapi-generator` as the standard tooling for producing Scheduler REST client/server stubs from `docs/api/v1/openapi.yaml`, and wire the generation step into local dev tasks and CI.
- For WebSocket payloads, continue sourcing types from `docs/schema/ws/*.json`; reuse the same generation pipeline to emit language-specific models so Scheduler and Worker share a single contract surface.

## 9. Manual WS Loop Validation

1. Regenerate shared WS models if schemas changed: `python scripts/generate_ws_models.py`.
2. Launch the scheduler (e.g. `uvicorn scheduler_api.main:app --host 0.0.0.0 --port 8080`) so `/ws/worker` and REST `/api/v1/runs` are reachable.
3. Start a worker with WebSocket transport enabled (`ASTRA_WORKER_TRANSPORT=websocket` or config file) so it handshakes, registers, and heartbeats against the scheduler. Populate the control-plane metadata via env vars or config, for example:
   ```env
   ASTRA_WORKER_WORKER_VERSION=0.1.0
   ASTRA_WORKER_HANDSHAKE_PROTOCOL_VERSION=1
   ASTRA_WORKER_AUTH_MODE=token
   ASTRA_WORKER_AUTH_TOKEN=dev-token
   ASTRA_WORKER_CONCURRENCY_MAX_PARALLEL=2
   ASTRA_WORKER_RUNTIME_NAMES='["python","playwright"]'
   ASTRA_WORKER_FEATURE_FLAGS='["pkg.install","pkg.uninstall"]'
   ```
   Package versions reported in the register frame are sourced from the local `packages/<name>/<version>/` directories maintained by the worker `PackageManager`.
4. Trigger a run dispatch via REST:
   ```bash
   curl -X POST http://localhost:8080/api/v1/runs \
     -H "Authorization: Bearer dev-token" \
     -H "Content-Type: application/json" \
     -d @docs/examples/run-request.json
   ```
5. Observe scheduler logs: `cmd.dispatch` should be sent with `ack.request=true`, followed by `result` or `command.error` frames. The in-memory run registry powers `/api/v1/runs` so you can confirm status transitions (`running` ->`succeeded`/`failed`).
6. If the worker emits `command.error`, verify the scheduler responds with an ACK and the run status changes to `failed` with error metadata.


## 10. Resource & Affinity Design Snapshot

See `docs/resource-affinity-and-artifacts.md` for the full design of artifact references, worker-side resource management, and scheduler affinity. Highlights:

- Workers expose a unified `ResourceRegistry` to store large files, browser sessions, torch models, and other reusable assets, reporting their state via heartbeat metrics.
- Result payloads can return lightweight references (`resourceId`, `workerId`, `type`, metadata) instead of inlining large data, while dispatch parameters support `resourceRef` to enforce worker affinity.
- The scheduler maintains an affinity registry so follow-up tasks stick to the worker that owns the required resource; platform-level guardrails control inline size limits, TTL, and eviction policies.
- Lifecycle hooks (register ->lease ->touch ->release ->cleanup) coordinate between packages, worker runtime, and scheduler to reclaim resources safely.
- `/api/v1/runs` responses now include per-node state and aggregated artifacts so UIs can inspect which worker handled each step and which resources are available for reuse. Each node also exposes `pendingAck`, `dispatchId`, and `ackDeadline` so operators can spot dispatch retries or stalled acknowledgements directly from the REST view.
inate between packages, worker runtime, and scheduler to reclaim resources safely.

Use that document as the authoritative blueprint when implementing resource-aware dispatch, artifact storage, and session/model reuse.






