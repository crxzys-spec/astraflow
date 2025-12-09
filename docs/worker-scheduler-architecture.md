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
                message="Downloading source articles¡­",
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
â”œâ”€â”€ manifest.json
â”œâ”€â”€ adapters/crawlerx_playwright/*.py
â”œâ”€â”€ resources/...
â”œâ”€â”€ scripts/install_extra.sh
â””â”€â”€ requirements.txt
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
      "name": "browser",
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
      "adapter": "browser",
      "handler": "open_page",
      "config": {
        "navigationStrategy": "default"
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
  - Download and verify archive; extract to `/var/astraflow/node-packages/<name>/<version>/` (or the configured packages root).
  - Install `python.dependencies` (pip/venv).
  - Run install hooks.
  - Refresh `AdapterRegistry`.
  - ACK result; on failure, rollback (remove dependencies, clean directories).
- `package.uninstall` triggers manifest uninstall hooks and deletes the package directory.
- Worker reports installed package versions in heartbeats; Scheduler uses this to decide upgrade/rollback.

## 3.5 Loop & Branch Execution Model

To support loops and conditional fan-out while keeping workflows as DAGs, the scheduler introduces two small extensions.

- **Loop nodes** reference other workflows by globally unique `workflowId`. When such a node is scheduled the run registry clones the referenced workflow, giving each cloned node a namespace such as `library.translator.step1`. Loop inputs/outputs still use `inputPorts/widgets/outputPorts`, but `binding.path` may include these namespaces so outer nodes can inject into / read from the loop body directly.
- **Namespace-aware bindings**: the registry maintains a `scope -> NodeState` index. Binding paths remain JSON Pointer style (`parameters.foo`, `results.bar`); if no prefix is supplied they continue to resolve against the current node. Optionally prepending `namespace.subgraphAlias.nodeId.` lets builders wire cross-workflow bindings by targeting the localized subgraphs they have embedded without introducing explicit parent/child syntax.
- **Versioning through ids**: publishing or copying a workflow simply creates a new `workflowId`. Loop nodes reference the exact id they depend on, so adopting a revised definition is an explicit action (swap the id) instead of an implicit upgrade.

### 3.6 Binding Scope Upgrade Plan

We are expanding bindings so a node can point at any other node¡¯s `parameters.*` / `results.*`, including nodes housed inside inline subgraphs or external workflows owned by the same user. The upgrade introduces explicit prefixes plus supporting metadata so resolution remains deterministic.

- **Prefix grammar**:
  - `@subgraphAlias(.childAlias)*(.nodeId)?` ¡ª hop into a localized subgraph declared in the current definition (imported workflows must be owned by the same tenant before localization). Example: `@welcomeJourney.stage2.#notifyCustomer.results.status`.
  - `#nodeId` ¡ª target another node within the current workflow scope before falling back to the JSON pointer root. Example: `#reader.parameters.tokenDelayMs`.
  - If no prefix is present, bindings stay local (legacy behaviour) and continue to resolve against the current node.
  - After the prefix, JSON pointer semantics still apply (`/parameters/message`, `/results/summary`), so existing tooling continues to parse the paths.

- **Data structures & indexes**:
- Workflow definitions gain `subgraphs[]` entries (each a localized snapshot of either a local draft or an imported workflow). Each alias becomes a resolvable scope id such as `scope:default/welcomeJourney/stage2`.
- At plan/build time we populate a hierarchical cache: `scopeId -> nodeId -> {parameters, results}` plus reverse maps (`subgraphAlias -> scopeId`, `nodeId -> inbound/outbound bindings`). Subgraphs inherit their parent scope so deeper nesting is just another level in the tree.
- Scheduler enforcement checks that `@` aliases map to localized subgraphs whose provenance (`referenceWorkflowId` / ownership) matches the tenant. During execution the run registry walks the scope tree before applying the JSON pointer to the resolved node payload.

- **Upgrade tasks**:
  1. **Schema & API** ¡ª extend `binding` objects (OpenAPI + manifest) with optional structured scope fields, regenerate SDKs, and document the string prefix shorthand for humans/editors.
  2. **Backend logic** ¡ª enhance workflow validation (ownership, alias lookup), update binding resolution utilities to parse prefixes, and persist the new scope metadata alongside run plans.
  3. **Runtime indexing** ¡ª teach the scheduler/run registry to hydrate the hierarchical index so SSE streams and dependency tracking continue to work with nested scopes.
  4. **Frontend/editor** ¡ª expose alias-aware pickers/autocomplete, serialize the structured fields, and surface the resolved scope in the inspector so authors can see when a widget targets another workflow.
  5. **Docs & rollout** ¡ª keep this section plus release notes updated, communicate the syntax change, and include migration guidance for teams who want to refactor existing bindings.

Legacy bindings do not need immediate changes; they omit the prefix and serialize with `scope.kind = local`. New bindings may mix both forms, letting teams adopt cross-workflow bindings gradually while the scheduler enforces tenant boundaries throughout the stack.

## 4. Workflow Definition Instance

The workflow definition serves as the contract between the drag-and-connect editor and the Scheduler runtime. The UI persists the JSON, and the Scheduler consumes the same payload to orchestrate tasks. Global context is no longer exchanged; instead, node parameters contain fully resolved values or expressions local to each node, and widgets can also bind to `results.*` paths for read-only display of execution outputs. **All workflow IDs and node IDs must be UUIDs** so they remain globally unique across imports and Scheduler executions.

### 4.1 Subgraphs & Container Nodes

Workflows can now embed **subgraphs** to encapsulate reusable logic. Subgraphs are defined once per workflow and then referenced by container nodes:

```json
{
  "subgraphs": [
    {
      "id": "sg_local_a",
      "definition": { "...complete workflow JSON..." },
      "metadata": {
        "label": "Local enrichment",
        "description": "Shared data prep stage"
      }
    },
    {
      "id": "sg_external_template",
      "definition": { "...external workflow snapshot..." },
      "metadata": {
        "label": "Customer Onboarding",
        "referenceWorkflowId": "wf_onboarding_2025_03"
      }
    }
  ]
}
```
Adapters register handlers once via `adapters[]`, and every catalogued node picks the adapter plus handler combo it needs (`adapter: "browser"`, `handler: "open_page"`). This mirrors the `node-packages/<package>/<version>/manifest.json` layout so execution routing no longer depends on runtime buckets.

- All subgraphs are ¡°localized¡± when the workflow is saved/published: even external references are stored as a copy of the referenced workflow so Scheduler does not need to fetch anything at runtime.
- Each container node references one of these subgraphs through a reserved parameter bucket: `parameters.__container.subgraphId`. The node itself keeps the standard schema (`parameters`, `results`, `ui.inputPorts`, `ui.outputPorts`, `ui.widgets`). The `__container` parameter holds the subgraph link and any execution policies:

```json
{
  "id": "node_container_a",
  "type": "workflow.container",
  "label": "Enrich Customer Profile",
  "ui": {
    "inputPorts": [
      { "key": "profile", "label": "Profile", "binding": { "path": "/parameters/profile" } }
    ],
    "outputPorts": [
      { "key": "result", "label": "Result", "binding": { "path": "/results/result" } }
    ],
    "widgets": [
      { "key": "loopToggle", "label": "Loop", "component": "checkbox", "binding": { "path": "/parameters/loopEnabled" } }
    ]
  },
  "parameters": {
    "__container": {
      "subgraphId": "sg_local_a",
      "loop": {
        "enabled": true,
        "maxIterations": 5,
        "condition": "results.status != 'done'"
      },
      "timeoutSeconds": 600
    },
    "loopEnabled": false
  },
  "results": {}
}
```

- Bindings from container ports/widgets to the subgraph internals use the same prefix syntax described in ¡ì3.6. For example, `/parameters/profile` may be wired to the subgraph¡¯s entry node by binding with `@sg_local_a.#entryNode.parameters.profile`.
- Loop/retry/timeout semantics live under the reserved `parameters.__container` namespace so Scheduler can treat the subgraph invocation like any other node task while still honoring the extra policies.

This approach keeps container nodes structurally identical to other nodes while allowing them to encapsulate entire sub-workflows that can be reused, looped, or imported from other definitions.\r\n\r\nThe dashboard ships with a built-in system@1.0.0 package whose manifest defines the canonical workflow.container node. Its schema establishes the parameters.__container contract (subgraphId, loop.*, 	imeoutSeconds, etc.) and its UI widgets drive the subgraph picker / loop controls via the regular widget registry, so container behaviour stays declarative instead of hard-coded in the builder.

#### Additional design notes

- **Subgraphs are always localized**: regardless of origin, `workflow.subgraphs[]` stores a complete `Workflow` definition. Reference metadata (original workflow id/owner/name) can live inside the subgraph¡¯s `metadata` block for UI display, but Scheduler never re-fetches the source at runtime.
- **Top-level metadata stays local**: `workflow.metadata.*` always reflects the currently edited workflow (namespace, originId, owner, etc.). Imported snapshots only record their provenance inside their own subgraph `metadata`, so referencing another workflow never overwrites the parent¡¯s metadata.
- **Containers reuse the existing node schema**: they still expose `label`, `position`, `parameters`, `results`, and `ui.*`. The only convention is the reserved `parameters.__container` bucket, which records `subgraphId` plus optional orchestration settings (loop/retry/timeout). No custom handler development is required¡ªcontainers are platform-provided control nodes.
- **Bindings bridge container <-> subgraph**: widgets and ports continue to bind to `/parameters/...` or `/results/...`. When a binding needs to reach into the subgraph, it uses the same prefix syntax (`@subgraphAlias.#node.parameters.foo`). The Scheduler¡¯s scope index resolves these prefixes, so data injection/extraction works just like any other node.
- **Execution flow**: before dispatching the subgraph, the container copies relevant `parameters` into the subgraph definition; once the subgraph run completes, specified `results` are copied back to the container node. Loop/retry policies defined in `parameters.__container` control how many times the subgraph is invoked or when to stop.

#### Containers vs. Subgraphs at a glance

- **Placement**: `workflow.subgraphs[]` exists at the workflow root (peer to `nodes[]`/`edges[]`) and stores localized workflow snapshots, while containers remain regular `workflow.nodes[]` entries with an extra `parameters.__container` bucket.
- **Execution contract**: containers inherit every standard node field and merely add optional orchestration hooks (`loop`, `retry`, `timeoutSeconds`). Subgraphs never execute by themselves¡ªthey are invoked only through containers referencing their `subgraphId`.
- **Authoring flow**: builders create/import subgraphs once, then reuse them across multiple containers. Adjusting a container¡¯s `subgraphId` or policies changes behavior without rewriting the subgraph JSON.

Below is a representative instance of the top-level workflow wiring two Playwright adapters plus a containerized subgraph:

### 4.2 Upgrade Plan Snapshot

To roll out subgraphs/containers end-to-end we¡¯re tackling the work in four coordinated streams:

1. **Schema & docs** ¨C finalize the OpenAPI/manifest models for `workflow.subgraphs[]`, `workflow.container` nodes, and binding prefixes; regenerate SDKs; keep this document + frontend builder docs current so builders know how to author new structures.
2. **Scheduler backend** ¨C teach plan building + `RunRegistry` to hydrate subgraph definitions, resolve container bindings via the scope index, and honor `parameters.__container` policies (loop/retry/timeout). Add validation for subgraph IDs, tenant ownership, and prefixed bindings.
3. **Dashboard builder** ¨C add subgraph management UI (create/import, alias metadata), container-node inspectors (subgraph picker, execution policy controls), and ensure draft ? API converters round-trip `subgraphs[]` / `parameters.__container`.
4. **Runtime validation & tests** ¨C extend unit/integration coverage for container execution, SSE updates, and cross-workflow bindings; document migration steps for existing workflows and monitor the rollout.

Each phase is tracked in the upgrade checklist so we can land schema, backend, frontend, and QA changes in lockstep.

**Execution pipeline upgrades**

1. **Planner expansion**:
   - Clone subgraphs referenced by containers during plan build: assign scoped node ids (`<containerId>::<nodeId>`), merge edges, and tag each cloned node with its alias chain.
   - Validate `parameters.__container` (loop/retry/timeout) plus any subgraph-level constraints (ownership, version).
   - Persist the expanded plan so API consumers see a single DAG with metadata describing which nodes belong to which container frame.
2. **Stack-based runtime**:
   - Update the dispatcher to push container frames onto a stack (frame = cloned subgraph DAG + policy state). While a frame is active, scheduling/dispatch works exactly like the top-level DAG.
   - When the frame completes, pop back to the parent container, propagate child results into the container node, and continue the parent DAG.
   - Support recursion by allowing a frame to push another frame (container inside container) without special casing.
3. **Binding scope enforcement**:
   - Extend `WorkflowScopeIndex` and `BindingScopeHint` so nested alias chains resolve to the proper scoped node ids inside the active frame.
   - When bindings reference subgraph outputs (`@sg_alias.#node.results.*`), automatically copy those values back into the parent container when the frame returns.
4. **Loop/retry/timeout integration**:
   - Implement loop state per frame: evaluate exit conditions after each iteration, requeue the frame with updated parameters when the loop continues.
   - Implement retry policies per frame: on failure, re-run the entire frame up to `maxAttempts` with configurable backoff.
   - Enforce `timeoutSeconds` by canceling/discarding frames that exceed their allotted time and surfacing a container-level failure.
5. **Observability**:
   - Aggregate child stage/progress metrics so container nodes report meaningful status (e.g., `running (2/5 child nodes complete)`).
   - Emit SSE events and audit logs annotated with the frame stack (`["node_container_debug","sg_node_normalise"]`) so operators can trace into subgraphs.
   - Update dashboard views to display stacked breadcrumbs when inspecting nested nodes.

- `metadata.namespace` provides a logical grouping (default `default`) that bindings can reference when targeting nodes in other workflows.
- `metadata.originId` links versions of the same workflow. When a workflow is cloned/published, a new `id` is issued but `originId` remains stable so loop nodes can reference a specific revision on purpose.

> **Tip:** The bundled `example.pkg.feedback_demo` node demonstrates the feedback contract: the worker emits incremental updates via `metadata.results`, for example `{"results": {"summary": "HELLO"}}`. The scheduler merges those keys into `results.*`, publishes `node.result.delta`, and the builder's `summaryPreview` widget (bound to `/results/summary`, `mode: "read"`) renders the stream live. Reuse the same convention for any other result fields you want to surface incrementally.

Example welcome journey:
- **Load Welcome Config** ¡ª parses the JSON definition, expands the template into a ready-to-send message, and exposes derived fields (recipient, timing, channel).
- **Personalise Message** ¡ª formats the message, forwards routing metadata (`recipient`, `subject`, `delaySeconds`, `tokenDelayMs`) to downstream nodes, and provides the stream source for the feedback node.
- **Stream Feedback** ¡ª emits the formatted message token-by-token so the builder shows live progress.
- **Schedule Delivery** ¡ª waits for the configured delay, modelling long-running work.
- **Send Welcome Notification** ¡ª simulates dispatch, returns a `notificationId`, and summarises the action.
- **Audit Delivery** ¡ª records the outcome (including the notification ID) for traceability.

```json
{
  "id": "ba55c67a-9ad4-4b6f-a719-b84e774c2d11",
  "schemaVersion": "2025-10",
  "metadata": {
    "name": "Playwright Smoke Check",
    "description": "Open a target page and click the login button to verify availability.",
    "tags": ["playwright", "smoke-test"],
    "environment": "staging",
    "namespace": "default",
    "originId": "ba55c67a-9ad4-4b6f-a719-b84e774c2d11"
  },
  "subgraphs": [
    {
      "id": "sg_welcome_stage",
      "definition": {
        "id": "883d0c5f-53a8-487b-91fc-7d7f4e5d5b1b",
        "schemaVersion": "2025-10",
        "metadata": {
          "name": "Welcome Journey Snapshot",
          "namespace": "default",
          "originId": "7c1f3d77-7017-4f41-90f7-7f7ac0eaa901"
        },
        "nodes": [{ "...": "subgraph workflow JSON omitted for brevity" }],
        "edges": []
      },
      "metadata": {
        "label": "Welcome Journey v3",
        "referenceWorkflowId": "7c1f3d77-7017-4f41-90f7-7f7ac0eaa901",
        "referenceWorkflowName": "Customer Welcome Journey",
        "ownerId": "team-success"
      }
    }
  ],
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
    },
    {
      "id": "fa112d74-8cb6-497c-9a53-8f6cbd8c3e7a",
      "type": "workflow.container",
      "label": "Run Welcome Subgraph",
      "package": {
        "name": "system",
        "version": "1.0.0"
      },
      "position": { "x": 620, "y": 180 },
      "parameters": {
        "customerId": "{{results.notificationId}}",
        "__container": {
          "subgraphId": "sg_welcome_stage",
          "loop": { "enabled": false },
          "timeoutSeconds": 900
        }
      },
      "results": {},
      "ui": {
        "inputPorts": [
          {
            "key": "customer",
            "label": "Customer Record",
            "binding": {
              "path": "/parameters/customerId",
              "mode": "two_way"
            }
          }
        ],
        "outputPorts": [
          {
            "key": "welcomeResult",
            "label": "Welcome Result",
            "binding": {
              "path": "/results/welcomeSummary",
              "mode": "read",
              "prefix": "@sg_welcome_stage.#final_stage"
            }
          }
        ]
      },
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
    },
    {
      "id": "c79957bc-e371-4c60-a6c5-682a1cf726a4",
      "source": { "node": "8f5dea1f-6a13-4e43-843f-5361c40f8f5a", "port": "done" },
      "target": { "node": "fa112d74-8cb6-497c-9a53-8f6cbd8c3e7a", "port": "customer" }
    }
  ],
  "tags": ["web", "smoke"]
}
```
> **Debug harness:** `docs/examples/debug-workflow.json` contains a second, richer workflow that exercises `workflow.container` nodes, localized subgraphs, and the new `example.pkg.collect_metrics` / `example.pkg.debug_gate` adapters so engineers can validate binding prefixes end-to-end. Persist it via `python scripts/persist_workflow.py --token <Bearer token> --endpoint http://<scheduler-host>/api/v1/workflows` (all arguments are optional; defaults target the bundled demo).
Each entry under `workflow.nodes[]` may include a `state` object populated by the scheduler during execution. The schema mirrors `WorkflowNodeState` from the public API and supplies the latest stage, progress, and failure details so the builder can surface live feedback without mutating package-controlled `parameters` or `results`.

This payload is stored alongside the manifest-driven catalog. When a run is triggered, the Scheduler selects adapters by `type` and dispatches `RunTaskCommand` messages per node following the defined edges. Per-node parameters are passed through exactly as authored in the workflow JSON.

### Package Registry & Adapter Resolution

- Workers install packages into versioned directories under the shared root (e.g. `/var/astraflow/node-packages/<name>/<version>/` or `./node-packages/<name>/<version>/`) so multiple revisions can coexist.
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
   Package versions reported in the register frame are sourced from the local `node-packages/<name>/<version>/` directories (or the configured packages root) maintained by the worker `PackageManager`.
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





## 11. Workflow Persistence Refresh (Phase 1)

- **Structured metadata columns**: `schema_version`, `namespace`, `origin_id`, `description`, `environment`, and `tags` now live directly on `WorkflowRecord`. The JSON `definition` payload only contains runtime graph/state so reads remain lightweight and writes can query metadata without reparsing.
- **DTO compatibility layer**: API responses hydrate the stored structure back into the legacy shape (`id`, `schemaVersion`, `metadata`) so both the dashboard and SDK continue to receive the same contract while the database benefits from proper columns and indexes.
- **Ownership & authorship**: Workflow metadata now carries `ownerId`, `createdBy`, and `updatedBy`. The DB columns (`owner_id`, `created_by`, `updated_by`) are populated from the authenticated token and surfaced to the UI for auditing.
- **Audit metadata**: `created_by` and `updated_by` capture the authenticated user responsible for each insert/update. The values currently power basic auditing and will feed the versioning/history UI later.
- **Migration behavior**: Alembic revision `20251105_0003` parses existing workflow JSON, hydrates the new columns, strips metadata from `definition`, and stores tags as JSON text. Downgrades reverse the process so backups remain portable.

## 12. Authentication & Authorization Bootstrap

- **Domain model**: Added `users`, `roles`, and `user_roles` tables plus the corresponding SQLAlchemy models. Passwords are stored as bcrypt hashes and linked to simple RBAC roles (`admin`, `workflow.editor`, `workflow.viewer`, `run.viewer`).
- **Seed admin**: Migration `20251105_0004` inserts an `admin` account whose password comes from `SCHEDULER_ADMIN_PASSWORD` (default `changeme`). Rotate that env var in every deployment before exposing the API.
- **JWT issuance**: `/api/v1/auth/login` exchanges username/password for a Bearer token signed with `SCHEDULER_JWT_SECRET` (algorithm `SCHEDULER_JWT_ALGORITHM`, default HS256). Expiry is controlled by `SCHEDULER_JWT_ACCESS_MINUTES` (default `525600`, i.e. 1 year) and returned as `expiresIn` for the UI.
- **Request flow**: Every REST/SSE route except `/auth/login` now requires the Bearer token. `security_api.get_token_bearerAuth` decodes the JWT, raises 401 on failure, and publishes the token to `scheduler_api.auth.context` so business logic (e.g., workflow persistence) can access the current user id.
- **Dashboard UX**: Added a login page, Zustand-powered auth store, and guarded routes. Tokens persist in `localStorage`, axios/EventSource automatically attach the header, and a dev escape hatch (`VITE_SCHEDULER_TOKEN`) remains available until we wire OIDC/SAML.
- **Audit trail**: The `audit_events` table records key state transitions (currently workflow create/update, run.start, auth attempts) with actor, target, and structured metadata to support later compliance reporting. `/api/v1/audit-events` exposes filterable/paginated access for admins in both API and dashboard.
- **RBAC enforcement**: Workflows, runs, packages, and SSE firehose endpoints enforce `workflow.viewer/editor`, `run.viewer`, or `admin` as appropriate. The dashboard surfaces role-aware controls so read-only users can inspect resources without mutating them.
- **Ops tooling**: Use `python scheduler/scripts/manage_users.py` to create users, rotate passwords, and assign roles without touching the database directly.
- **Next steps**: Provide CLI/management APIs for creating users + assigning roles, wire optional `DEV_AUTH_BYPASS`, and plan for IdP integration so this bootstrap layer can federate with enterprise auth once ready.

## 13. Workflow Draft & Store Upgrade

### 13.1 Goals
- Keep `/workflows` as the home for personal, executable drafts; remove any publish badge or blocking reminder because every run executes from the caller's draft copy regardless of publish status.
- Introduce a first-class catalog (the "Store") that surfaces published workflows as reusable packages with semantic versions, search, and ownership metadata.
- Allow authors to publish/clone workflows without changing the runtime surface for drafts; publishing only affects discoverability.

### 13.2 Data Model
- Reuse the existing `workflows` table for drafts. Records retain `owner_id`, `origin_id`, and `definition`, and no publish metadata is written back to these rows.
- Add `workflow_packages` (id, slug, display name, summary, tags, visibility, owner_id, created_by, updated_by) and `workflow_package_versions` (package_id, semver, changelog, definition_snapshot, published_at, publisher_id) tables. A publish action snapshots the draft JSON into `workflow_package_versions` and updates package metadata.
- Publishing does not mutate the draft record; the draft id remains stable so executions and edits stay local. Cloning a package version creates a new draft row with `origin_id` pointing to the version snapshot.

### 13.3 API Surface
- `/api/v1/workflows` continues to serve draft CRUD. The handler now always filters by `owner_id = current_user` so callers only see their personal copies, and no publish fields appear in the response.
- New catalog endpoints:
  - `GET /api/v1/workflow-packages`: paginated search over published workflows (filters for owner, visibility, tags, updatedAfter, text query).
  - `GET /api/v1/workflow-packages/{packageId}` and `/versions`: retrieve package metadata plus version history.
  - `POST /api/v1/workflow-packages/{packageId}/clone`: copies a selected version into the caller's drafts via the `/api/v1/workflows` persistence path.
  - `POST /api/v1/workflows/{workflowId}/publish`: snapshots the workflow into `workflow_package_versions`, creating or updating the package as needed. Optional `PATCH /api/v1/workflow-packages/{packageId}/visibility` handles unpublish/private toggles.
- RBAC: drafts require `workflow.editor` as today; publishing/cloning requires `workflow.publisher` (subset of admin-able roles). Each publish/clone writes to `audit_events`.

### 13.4 Dashboard UX
- Sidebar order: `Workflows` before `Runs`, plus a new top-level `Store` (or `Packages`) route.
- Workflows page: list + builder focus strictly on drafts; UI drops publish chips and warnings. Actions stay edit, run, duplicate, delete.
- Store page: queries `/workflow-packages`, shows owner, description, last update, and prominent "Clone to My Workflows" action. Detail drawer exposes version changelog and clone button per version.
- Builder publish action: available via a "Publish to Store" button that opens a modal (name, summary, version bump, visibility). Successful publish navigates to the package detail or displays a toast with deep link. Draft header includes a passive banner showing whether the latest published version lags behind, without blocking runs.

### 13.5 Migration & Rollout
- Migration script seeds `workflow_packages` and `workflow_package_versions` from any workflow currently marked as shared/public. All drafts remain untouched.
- Backend deploy order: (1) schema migration + models, (2) API handlers guarded by feature flags, (3) dashboard Store route + publish/clone UX, (4) remove legacy publish reminders.
- Update `docs/api/v1/openapi.yaml` plus individual path/component files to document the new catalog endpoints once implemented.
- Provide operational runbook: `manage_users.py` already supports `activate/deactivate`; extend it (or a new CLI) with `publish-workflow` helper for seed data and automated tests.










