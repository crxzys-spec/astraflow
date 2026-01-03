"""Runtime entrypoint that layers custom behaviour on the generated FastAPI app."""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware

from hub_api import main as generated_main
from hub_api.db.migrations import upgrade_database
from hub_api.db.seed_data import seed_default_accounts, seed_sample_catalog

app = generated_main.app

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    upgrade_database()
    seed_default_accounts()
    seed_sample_catalog()
