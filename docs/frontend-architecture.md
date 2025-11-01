- `src/features/workflow/components/NodeInspector.tsx`: inspector panel that resolves widget bindings and writes updates back into the store.
- `src/features/workflow/constants.ts`: shared DnD payload identifiers.
- `src/pages/WorkflowBuilderPage.tsx`: route-level integration that fetches a workflow via Orval hooks, hydrates the store, and orchestrates palette/canvas/inspector.

The dashboard is the control-plane UI for orchestrating and monitoring AstraFlow
workflows. Two main personas are supported:

- **Designers / Operators** use the **Workflow Builder** to compose, version, and
  publish workflow definitions.
- **Schedulers / Observers** use the **Runs, Workflows, Workers panels** to
  inspect executions, worker health, and events.

The application is built with **React + Vite + TypeScript**. React Flow powers
the workflow canvas, TanStack Query handles server state, and the HTTP contract
is generated automatically from the OpenAPI specification.

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?React Router鈹傗攢鈹€鈹€鈹€鈹€鈻垛攤 Feature Pages鈹傗攢鈹€鈹€鈹€鈹€鈻垛攤 UI Components鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?        鈹?                   鈹?                    鈹?        鈻?                   鈻?                    鈻?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?State Layer                                              鈹?鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?鈹?鈹?React Query (server  鈹? 鈹?Workflow Store            鈹?鈹?鈹?鈹?cache + requests)    鈹? 鈹?(Zustand/Jotai, domain)   鈹?鈹?鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?        鈹?                   鈹?                    鈹?        鈻?                   鈻?                    鈻?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?Orval SDK  鈹傗攢鈹€鈹€鈹€鈹€鈻垛攤 Axios Client 鈹傗攢鈹€鈹€鈹€鈹€鈻垛攤 Scheduler API鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?```

## 2. Technology Stack

- **Build / Tooling**: Vite, npm scripts, TypeScript strict mode.
- **UI**: React 19, React Router 6, React Flow (for workflow canvas).
- **State**:
  - TanStack Query for server state (runs, workers, workflow definitions).
  - A dedicated Zustand/Jotai store (to be implemented) for workflow editing
    state (`WorkflowDraft`, `WorkflowNodeDraft`, etc.).
- **HTTP Client**: Axios, configured via `src/lib/httpClient.ts`. Base URL is
  injected through `VITE_API_BASE_URL`.
- **API SDK**: `npm run generate:api` uses swagger-cli + orval to bundle the
  multi-file OpenAPI spec and generate typed React Query hooks under `src/api/`.
- **Styling**: Lightweight custom styles (`App.css`, `index.css`) with BEM-like
  class names; can be replaced with a design system later.

## 3. API Integration

- `docs/api/v1/openapi.yaml` is the source of truth. Multi-file references are
  bundled to `tmp/openapi.bundle.yaml` before generation.
- Orval creates Axios-based clients and React Query hooks (e.g.
  `useListRuns`, `useGetRun`).
- All Axios requests share configuration defined in
  `src/lib/httpClient.ts`. Future cross-cutting concerns (auth tokens, tracing,
  error logging) should be wired in here.
- Regeneration workflow:
  ```bash
  npm run generate:api
  # tmp/openapi.bundle.yaml, src/api/endpoints.ts, src/api/models/** are rebuilt
  ```
  Generated files are git-ignored (except README) to avoid manual edits.

## 4. State Management

### 4.1 TanStack Query

Server-side resources (runs, workers, workflow definitions) are fetched through
orval-generated hooks. Query options (retry, stale time, refetch behaviour) are
centralised in `src/lib/queryClient.ts`. The app is wrapped by
`QueryClientProvider` and includes React Query Devtools for debugging.

### 4.2 Workflow Editing Store

Workflow editing requires local mutable state that should not trigger React Flow
re-renders on every change. A dedicated Zustand store
(`src/features/workflow/store.ts`) now owns the builder session and exposes a
minimal API for the canvas and inspector to consume:

- `workflow`: the current `WorkflowDraft` with metadata, tags, runtimes, and a
  `dirty` flag.
- Node registry keyed by `nodeId` with parameters, results, dependencies,
  resources, affinity, etc.
- Flat edge list plus helpers to add/update/remove edges while keeping
  dependencies in sync.
- UI state such as `selectedNodeId`; undo/redo stacks can be layered on later.

React Flow receives derived node/edge arrays from
`utils/flowTransforms.ts`, keeping node data lightweight (`nodeId`, `label`,
status hints) so parameter edits do not re-render the entire canvas.

## 5. Workflow Builder Design

### 5.1 Data Conversion

Utilities under `src/features/workflow/utils/` manage translation between the
scheduler schema and editable state:

```
API WorkflowDefinitionInstance
    -> workflowDefinitionToDraft()        // converters.ts
         -> WorkflowDraft                 // maintained in store.ts
              -> buildFlowNodes()/buildFlowEdges()  // flowTransforms.ts
                   -> React Flow canvas
              -> workflowDraftToDefinition()        // converters.ts
                   -> API WorkflowDefinitionInstance (save)
```

- `workflowDefinitionToDraft` normalises nodes/edges, applies schema defaults via
  `buildDefaultsFromSchema`, and derives dependency lists.
- `createNodeDraftFromTemplate` bootstraps drops from the manifest palette with
  schema-driven parameter/result defaults.
- `workflowDraftToDefinition` deep-clones draft data back into the API contract
  for saves or previews.
### 5.2 Manifest Node Templates

Nodes on the palette are created from **Manifest Instance Example** entries.
Each manifest node contains:

- `type` / `package.{name, version}` / `label` / `description`
- `schema.parameters` & `schema.results` (JSON Schema with defaults, required
  fields, enums, etc.)
- `ui.inputPorts`, `ui.outputPorts`, `ui.widgets` (with bindings and widget
  components)
- Optional extras: `resources`, `conditions`, `extensions`, metadata

When a manifest node is dropped onto the canvas:

1. Generate a unique `nodeId` (UUID).
2. Capture the drop position `{x, y}`.
3. Copy structural metadata (`nodeKind`, package info, UI config).
4. Initialise `parameters` / `results` using the schema defaults. A helper
   `buildDefaults(schema)` walks the JSON schema and produces initial values.
5. Seed `dependencies`, `resources`, `affinity`, `concurrencyKey` (empty by
   default, or bring over manifest hints).
6. Insert into the workflow store as a `WorkflowNodeDraft`; create the light
   React Flow node referencing that id.
7. Mark the workflow `dirty`.

### 5.3 Ports & Data Binding

- `ui.inputPorts[]` / `ui.outputPorts[]` are rendered as React Flow handles.
  Each handle id matches the manifest port key, so connecting edges knows which
  port was used.
- Ports can carry metadata (accepted types, optional flags). Handle `data`
  stores this so edge creation can validate compatibility.
- Widgets/fields inside `ui.widgets[]` describe UI components and their binding:
  - `binding.path`: JSON pointer into `parameters.*` or `results.*`.
  - `binding.mode`:
    - `write` / `input`: widget writes data into `parameters`.
    - `read`: widget displays data from `results` (read-only).
    - `two_way` / `bidirectional`: editable widget that both reads and writes.
- Node components render widgets via the registry (see 5.4) and interact with
  the workflow store to read/write bound values. React Flow node data remains
  lightweight (typically just `nodeId`, `label`, `status`) to avoid rerenders
  when parameters change.
- When edges are created, the source/target handle ids let us look up the
  corresponding binding paths. Edge metadata can capture the mapping from
  source `results.*` to target `parameters.*`, so saving the workflow retains
  the data-flow semantics.

### 5.4 Widget Registry

`src/features/workflow/widgets/registry.tsx` implements a lightweight registry.
`WidgetRegistryProvider` exposes a resolver through context, while the global
singleton (`widgetRegistry`) allows feature code to register new renderers.

`src/features/workflow/widgets/builtin/registerBuiltinWidgets.ts` wires up the
built-in editors (`text`, `textarea`, `number`, `checkbox`, `json`) defined
under `widgets/components/`. Calling `registerBuiltinWidgets()` ensures
registrations occur (idempotently) before the inspector renders.

Renderers receive `{ node, widget, value, readOnly, onChange }` and can decide
how to present the bundle. Additional widget types can be registered by feature
code or package-specific extensions without touching the core builder.

### 5.5 Editing Flow

1. **Selection**: clicking a node sets `selectedNodeId` in store.
2. **Inspector Panel**: reads `WorkflowNodeDraft` from store, renders forms based
   on widget/parameter schema.
3. **Canvas Moves**: drag events update `node.position` in store and call
   `setNodes`.
4. **Edges**: creation/removal updates `dependencies` and `WorkflowEdgeDraft`.
5. **Validation**: before save, ensure no cycles, required ports are connected,
   parameters conform to schema.
6. **Persistence**: call `fromWorkflowDraft`, then POST/PUT to API; clear `dirty`
   flag on success.

### 5.6 Read-Only Mode

Runs or workflow list pages can open the builder in read-only mode:

- Load `WorkflowDefinitionInstance` via `useGetRunDefinition`/`useGetWorkflow`.
- Populate canvas + store but disable editing actions.
- Optionally overlay run results (node status, artifacts, durations).

### 5.7 Implementation Snapshot (Oct 2025)

- `src/features/workflow/types.ts`: domain models mapping manifest data to the
  builder store (`WorkflowDraft`, `WorkflowNodeDraft`, etc.).
- `src/features/workflow/utils/schemaDefaults.ts`: JSON-schema walker that
  seeds parameters/results defaults for new nodes.
- `src/features/workflow/utils/converters.ts`: conversions between API
  definitions and drafts, plus manifest template bootstrap.
- `src/features/workflow/utils/flowTransforms.ts`: derivations that convert the
  store into React Flow node/edge arrays.
- `src/features/workflow/store.ts`: Zustand store with helpers for loading,
  adding/removing nodes and edges, and tracking `selectedNodeId`.
- `src/features/workflow/widgets/registry.tsx`: global registry + provider for
  node widgets.
- `src/features/workflow/widgets/builtin/registerBuiltinWidgets.ts`: built-in
  widget registrations backed by components under `widgets/components/`.
- `src/features/workflow/components/WorkflowCanvas.tsx`: canvas shell binding
  React Flow callbacks to store actions; shows overlay when empty.
- src/features/workflow/components/WorkflowPalette.tsx: catalog UI that groups node definitions\n  and emits drag payloads for the canvas.\n- src/features/workflow/components/NodeInspector.tsx: inspector panel that\n  resolves widget bindings and writes updates back into the store.
- src/features/workflow/constants.ts: shared DnD payload identifiers.\n- src/pages/WorkflowBuilderPage.tsx: route-level integration that fetches a\n  workflow via Orval hooks, hydrates the store, and orchestrates palette/canvas/inspector.

## 6. Panels & Navigation

- **Runs Page** (`/runs`): table with status, timestamps; detail page shows
  metadata, run definition JSON, link to workflow builder.
- **Workflows Page** (`/workflows`): list of definitions and versions; open in
  builder.
- **Workers Page** (`/workers`): health overview, capabilities, concurrency.
- React Router handles navigation; layout component provides sidebar and
  responsive behaviour.

## 7. Styling & Components

- CSS uses BEM-like classes. Layout is a two-column grid (sidebar + workspace).
- `StatusBadge`, `Card`, `DataTable`, etc. provide reusable UI patterns.
- Toast/snackbar system pending (recommend `sonner` or `react-hot-toast`).

## 8. Scripts & Environment

```bash
npm install              # install dependencies
npm run generate:api     # regenerate SDK after schema changes
npm run dev -- --host    # start dev server (0.0.0.0:5173)
npm run build            # type check + production build
npm run preview          # serve build output
```

Environment variables:

- `VITE_API_BASE_URL`: Scheduler API base endpoint (dev/staging/prod).
  Provide via `.env.local`, `.env.development`, etc.

## 9. Testing & Quality

- **Unit/Component Tests**: Jest + Testing Library (to be configured) for
  component and store logic.
- **E2E Tests**: Playwright/Cypress for run list, workflow builder interactions.
- **CI**: run `npm run generate:api`, `npm run lint`, `npm run build`, tests.
  Flag when generated API outputs drift from committed state.

## 10. Next Steps

1. Implement widget registry + inspector panel to edit parameters/results without
   forcing React Flow re-renders.
2. Build manifest palette UI that surfaces `ManifestInstanceExample` data and
   wires drag/drop into `createNodeDraftFromTemplate`.
3. Add workflow persistence (save/publish) by invoking
   `workflowDraftToDefinition` and calling the scheduler API.
4. Introduce validation utilities (port compatibility, cycle detection,
   required bindings) before save/dispatch.
5. Establish unit/E2E coverage for schema defaults, converters, store actions,
   and core canvas flows.

This architecture enables incremental development while keeping workflow schema
parsing, editing, and persistence aligned with backend definitions.



- `src/features/workflow/components/WorkflowPalette.tsx`: catalog UI that groups node definitions and emits drag payloads for the canvas.

