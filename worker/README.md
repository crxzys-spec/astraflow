# Worker Service

The worker process reads its configuration via `worker.config.get_settings()`.  
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

Paths such as `packages_dir` and `data_dir` are expanded to absolute locations during bootstrap; by default `packages_dir` points at `node-packages` (override via `ASTRA_PACKAGES_ROOT` or `ASTRA_WORKER_PACKAGES_DIR`).

Key configuration fields include:

- `scheduler_ws_url`, `auth_token`, `tenant`: identify the scheduler endpoint and tenancy scope.
- `transport`: selects the control-plane transport (`websocket` for real integration, `dummy` for offline testing).
- `heartbeat_interval_seconds` / `heartbeat_jitter_seconds`: control the cadence of health reports.

### Control-plane scaffold

- Call `worker.bootstrap.setup()` to initialise and start the `NetworkClient`
  with current settings and the transport dictated by `WorkerSettings.transport`.
- When `transport=websocket`, the runtime uses the async WebSocket client stub; `dummy`
  remains available for local smoke tests without a scheduler.
- Extensive debug logging (enable via `ASTRA_WORKER_LOG_LEVEL=DEBUG`) traces outbound frames,
  retries, ACK resolution, and inbound command routing for quick verification.

### Package management

- `AdapterRegistry` keeps `(package, version, handler)` mappings and dynamically imports
  handler entrypoints defined in `manifest.json`.
- `PackageManager` installs archives (download, extract, validate manifest, register handlers)
  into a package-specific directory inside `packages_dir` (e.g. `node-packages/<name>/<version>`),
  keeping the manifest and adapters colocated for runtime discovery.
- Default package command handler is wired automatically: `package.install` triggers install
  and emits `pkg.event` with status `installed`; failures emit `status=failed` and include details.
  `package.uninstall` removes the specific version and reports completion.

### Node execution

- `Runner` resolves dispatch commands via the registry and invokes the appropriate package handler,
  passing an `ExecutionContext` with run/task identifiers, parameters, tenant info, and a dedicated
  data directory.
- Results are wrapped into `result` frames (with duration, optional metadata); exceptions yield
  `command.error` containing `E.RUNNER.FAILURE`.
- Handler execution mode can be set per node via `nodes[].config.exec_mode` or per adapter via
  `adapters[].metadata.exec_mode` (`auto`, `inline`, `thread`). The worker default comes from
  `ASTRA_WORKER_HANDLER_EXEC_MODE_DEFAULT` (`auto` runs sync handlers in a thread and async inline).

### Concurrency

- A built-in `ConcurrencyGuard` enforces single-flight semantics per `concurrency_key`. Duplicate
  dispatches for the same key receive `E.CMD.CONCURRENCY_VIOLATION` errors without invoking the
  handler.
- Queue limits can be configured to apply backpressure when handlers fall behind:
  `ASTRA_WORKER_TRANSPORT_RECV_QUEUE_MAX` and `ASTRA_WORKER_SESSION_APP_QUEUE_MAX`
  (set to `0` for unbounded). Overflow policy for the session queue is controlled by
  `ASTRA_WORKER_SESSION_APP_QUEUE_OVERFLOW` (`block`, `drop_new`, `drop_oldest`).
- `ASTRA_WORKER_HANDLER_DISPATCH_MAX_INFLIGHT` caps concurrent biz handler tasks
  (`0` keeps sequential dispatch).
- `ASTRA_WORKER_HANDLER_DISPATCH_QUEUE_MAX` caps per-type dispatch queue depth
  (`0` keeps queues unbounded). Overflow policy is controlled by
  `ASTRA_WORKER_HANDLER_DISPATCH_QUEUE_OVERFLOW`.
- `ASTRA_WORKER_HANDLER_DISPATCH_QUEUE_IDLE_SECONDS` retires per-type dispatch
  queues after idle time to avoid unbounded type growth.
- `ASTRA_WORKER_HANDLER_DISPATCH_TIMEOUT_SECONDS` applies a timeout per handler
  invocation. Use `ASTRA_WORKER_HANDLER_DISPATCH_MAX_FAILURES` +
  `ASTRA_WORKER_HANDLER_DISPATCH_FAILURE_COOLDOWN_SECONDS` to enable cooldown
  after consecutive failures.
- `ASTRA_WORKER_RECONNECT_ABORT_ON_AUTH_ERROR` and
  `ASTRA_WORKER_RECONNECT_ABORT_ON_PROTOCOL_ERROR` can stop reconnect loops
  when failures are non-recoverable.
