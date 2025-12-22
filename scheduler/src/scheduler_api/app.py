"""Runtime entrypoint that layers custom behaviour on the generated FastAPI app."""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware

from scheduler_api import main as generated_main
from scheduler_api.catalog import catalog
from scheduler_api.control_plane import router as control_router
from scheduler_api.db.migrations import upgrade_database
from scheduler_api.db.seed_data import seed_demo_workflow

app = generated_main.app

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://10.0.35.8:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(control_router)


@app.on_event("startup")
def _startup() -> None:
    upgrade_database()
    catalog.reload()
    seed_demo_workflow()
