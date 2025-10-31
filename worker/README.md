# Worker Service

The worker process reads its configuration via `worker.agent.config.get_settings()`.  
Configuration sources are merged in the following priority order:

1. explicit arguments provided by the caller (reserved for future bootstrap hooks);
2. YAML/JSON file referenced by `ASTRA_WORKER_CONFIG_FILE`, or the first available file in:
   - `/etc/astraflow/worker.yaml`
   - `/etc/astraflow/worker.yml`
   - `./config/worker.yaml`
   - `./config/worker.yml`
3. environment variables prefixed with `ASTRA_WORKER_` (e.g. `ASTRA_WORKER_SCHEDULER_WS_URL`);
4. values declared in a `.env` file located in the current working directory;
5. internal defaults defined in `WorkerSettings`.

Paths such as `packages_dir` and `data_dir` are expanded to absolute locations during bootstrap.

Key configuration fields include:

- `scheduler_ws_url`, `auth_token`, `tenant`: identify the scheduler endpoint and tenancy scope.
- `transport`: selects the control-plane transport (`websocket` for real integration, `dummy` for offline testing).
- `heartbeat_interval_seconds` / `heartbeat_jitter_seconds`: control the cadence of health reports.

### Control-plane scaffold

- Use `worker.agent.runtime.build_connection()` to obtain a `ControlPlaneConnection`
  configured with current settings and the transport dictated by `WorkerSettings.transport`.
- Optional `command_handler` / `package_handler` callables can be supplied to `build_connection`
  to integrate with task runners and package management code; handlers receive the raw envelope
  for future parsing logic.
- `start_control_plane()` performs the sequence `handshake -> register -> heartbeat`
  and launches the periodic heartbeat loop.
- When `transport=websocket`, the runtime uses the async WebSocket client stub; `dummy`
  remains available for local smoke tests without a scheduler.
- Extensive debug logging (enable via `ASTRA_WORKER_LOG_LEVEL=DEBUG`) traces outbound frames,
  retries, ACK resolution, and inbound command routing for quick verification.

### Package management

- `AdapterRegistry` keeps `(package, version, handler)` mappings and dynamically imports
  handler entrypoints defined in `manifest.json`.
- `PackageManager` installs archives (download, extract, validate manifest, register handlers)
  into a package-specific directory inside `packages_dir`, keeping the manifest and adapters
  colocated for runtime discovery.
- Default package command handler is wired automatically: `package.install` triggers install
  and emits `pkg.event` with status `installed`; failures emit `status=failed` and include details.
  `package.uninstall` removes the specific version and reports completion.

### Node execution

- `Runner` resolves dispatch commands via the registry and invokes the appropriate package handler,
  passing an `ExecutionContext` with run/task identifiers, parameters, tenant info, and a dedicated
  data directory.
- Results are wrapped into `result` frames (with duration, optional metadata); exceptions yield
  `command.error` containing `E.RUNNER.FAILURE`.
- Consumers may inject custom `command_handler` implementations, but the bundled default covers the
  happy-path for manifest-compliant packages.

### Concurrency

- A built-in `ConcurrencyGuard` enforces single-flight semantics per `concurrency_key`. Duplicate
  dispatches for the same key receive `E.CMD.CONCURRENCY_VIOLATION` errors without invoking the
  handler.
