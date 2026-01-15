"""Runtime entrypoint that layers custom behaviour on the generated FastAPI app."""

from __future__ import annotations

from fastapi import HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware

from scheduler_api import main as generated_main
from scheduler_api.apis.packages_api_base import BasePackagesApi
from scheduler_api.infra.catalog import catalog
from scheduler_api.infra.network.ws import router as control_router
from scheduler_api.db.migrations import upgrade_database
from scheduler_api.db.seed_data import seed_demo_workflow
from scheduler_api.models.extra_models import TokenModel
from scheduler_api.models.package_detail import PackageDetail
from scheduler_api.security_api import get_token_bearerAuth

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

@app.get(
    "/api/v1/packages/{owner}/{name}",
    response_model=PackageDetail,
    response_model_by_alias=True,
    tags=["Packages"],
    summary="Get package detail by owner/name",
)
async def get_package_by_owner(
    owner: str,
    name: str,
    version: str | None = Query(
        None,
        description="Specific package version to retrieve. Defaults to the latest available version.",
    ),
    token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> PackageDetail:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().get_package(f"{owner}/{name}", version)


@app.on_event("startup")
async def _startup() -> None:
    upgrade_database()
    catalog.reload()
    seed_demo_workflow()
