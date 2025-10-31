# AstraFlow

## Schema-driven code generation

Install tooling:

```bash
pip install -r requirements-dev.txt
```

Generate WebSocket models (Pydantic) from JSON Schema:

```bash
python scripts/generate_ws_models.py
```

Generated modules land in `shared/models/ws/` and should be committed.

Generate Scheduler FastAPI stubs from OpenAPI:

```bash
export OPENAPI_GENERATOR_CLI=openapi-generator-cli  # optional if CLI on PATH
python scripts/generate_scheduler_api.py
```

The generated server package will appear under `scheduler/generated_api/`.
