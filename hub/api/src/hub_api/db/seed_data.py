"""Seed hub database with default accounts."""

from __future__ import annotations

import os
from uuid import uuid4

from sqlalchemy import select

from hub_api.repo.packages import publish_package_version, set_package_tag_record
from hub_api.repo.workflows import publish_workflow_version
from .models import (
    HubOrganization,
    HubOrganizationMember,
    HubPackage,
    HubToken,
    HubUser,
    HubWorkflow,
)
from .security import hash_password
from .session import SessionLocal

DEFAULT_USERS = [
    {"id": "hub-user", "username": "hub-user", "display_name": "Hub Publisher"},
    {"id": "astra-labs", "username": "astra-labs", "display_name": "Astra Labs"},
    {"id": "nebula-ops", "username": "nebula-ops", "display_name": "Nebula Ops"},
    {"id": "ion-forge", "username": "ion-forge", "display_name": "Ion Forge"},
    {"id": "nova-core", "username": "nova-core", "display_name": "Nova Core"},
]

OWNER_NAME_BY_ID = {user["id"]: user["display_name"] for user in DEFAULT_USERS}
DEFAULT_WORKFLOW_SCHEMA_VERSION = "2025-10"

DEFAULT_PACKAGES = [
    {
        "name": "orion.llm.chat",
        "latest": "1.4.2",
        "description": "Unified chat inference nodes with guardrails and retry policies.",
        "tags": ["chat", "guardrails", "providers"],
        "owner_id": "astra-labs",
        "owner_name": "Astra Labs",
        "versions": ["1.4.0", "1.4.1", "1.4.2"],
        "dist_tags": {"latest": "1.4.2", "stable": "1.4.2"},
        "readme": "Orion LLM Chat provides unified chat nodes across providers.",
    },
    {
        "name": "pulse.metrics.stream",
        "latest": "2.1.0",
        "description": "Stream metrics from workflow runs into your monitoring stack.",
        "tags": ["metrics", "streaming", "alerts"],
        "owner_id": "nebula-ops",
        "owner_name": "Nebula Ops",
        "versions": ["2.0.0", "2.0.3", "2.1.0"],
        "dist_tags": {"latest": "2.1.0"},
        "readme": "Pulse Metrics Stream exports workflow metrics in real time.",
    },
    {
        "name": "atlas.dispatch.router",
        "latest": "0.9.5",
        "description": "Route tasks across worker pools with adaptive backpressure.",
        "tags": ["routing", "workers", "scaling"],
        "owner_id": "ion-forge",
        "owner_name": "Ion Forge",
        "versions": ["0.9.0", "0.9.3", "0.9.5"],
        "dist_tags": {"latest": "0.9.5", "beta": "0.9.5"},
        "readme": "Atlas Dispatch Router optimizes worker selection and queueing.",
    },
    {
        "name": "vector.trace.kit",
        "latest": "1.2.0",
        "description": "High fidelity vector traces with anomaly markers.",
        "tags": ["search", "vector", "tracing"],
        "owner_id": "nova-core",
        "owner_name": "Nova Core",
        "versions": ["1.0.0", "1.1.1", "1.2.0"],
        "dist_tags": {"latest": "1.2.0"},
        "readme": "Vector Trace Kit helps analyze retrieval traces and drift.",
    },
]

DEFAULT_WORKFLOWS = [
    {
        "workflow_id": "wf-welcome-journey",
        "name": "Customer Welcome Journey",
        "summary": "Personalized onboarding workflow with multichannel notifications.",
        "description": "A multi-step onboarding flow with scheduling, content selection, and metrics.",
        "tags": ["crm", "notifications", "email"],
        "owner_id": "astra-labs",
        "version": "1.0.0",
        "dependencies": [{"name": "orion.llm.chat", "version": "1.4.2"}],
    },
    {
        "workflow_id": "wf-incident-drill",
        "name": "Incident Drill Auto-Responder",
        "summary": "Automated triage, escalation, and audit capture for incidents.",
        "description": "Simulates incident response with real-time dashboards and reporting.",
        "tags": ["incident", "ops", "audit"],
        "owner_id": "nebula-ops",
        "version": "1.2.0",
        "dependencies": [{"name": "pulse.metrics.stream", "version": "2.1.0"}],
    },
    {
        "workflow_id": "wf-content-reviewer",
        "name": "Realtime Content Reviewer",
        "summary": "Streams content through a multi-model moderation pipeline.",
        "description": "Includes policy checks, human review escalation, and reporting.",
        "tags": ["moderation", "stream", "compliance"],
        "owner_id": "ion-forge",
        "version": "0.9.1",
        "dependencies": [{"name": "atlas.dispatch.router", "version": "0.9.5"}],
    },
    {
        "workflow_id": "wf-growth-insights",
        "name": "Growth Insights Digest",
        "summary": "Weekly insight pack for product and growth teams.",
        "description": "Aggregates events, summarizes KPIs, and publishes a report.",
        "tags": ["analytics", "reporting", "growth"],
        "owner_id": "nova-core",
        "version": "1.0.0",
        "dependencies": [{"name": "vector.trace.kit", "version": "1.2.0"}],
    },
]


def seed_default_accounts() -> None:
    with SessionLocal() as session:
        for user in DEFAULT_USERS:
            existing = session.get(HubUser, user["id"])
            if existing:
                continue
            session.add(
                HubUser(
                    id=user["id"],
                    username=user["username"],
                    display_name=user["display_name"],
                    email=None,
                    password_hash=hash_password(user["username"]),
                )
            )
        session.commit()

        for user in DEFAULT_USERS:
            if user["id"] == "hub-user":
                continue
            existing_org = session.get(HubOrganization, user["id"])
            if existing_org:
                continue
            org = HubOrganization(
                id=user["id"],
                name=user["display_name"],
                slug=user["id"],
                owner_id=user["id"],
            )
            session.add(org)
            session.add(
                HubOrganizationMember(
                    org_id=user["id"],
                    user_id=user["id"],
                    role="owner",
                )
            )
        session.commit()

        token_exists = session.execute(
            select(HubToken).where(HubToken.owner_id == "hub-user")
        ).scalar_one_or_none()
        if not token_exists:
            session.add(
                HubToken(
                    id="hub-default-token",
                    owner_id="hub-user",
                    label="default-dev",
                    scopes=["read", "publish", "admin"],
                    package_name=None,
                    token="hub-user-token",
                )
            )
            session.commit()


def _env_flag(name: str, default: str | None = None) -> bool:
    value = os.getenv(name)
    if value is None:
        value = default
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_primary_dependency(workflow: dict[str, object]) -> tuple[str, str]:
    dependencies = workflow.get("dependencies")
    if isinstance(dependencies, list):
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            name = dependency.get("name")
            version = dependency.get("version")
            if isinstance(name, str) and name and isinstance(version, str) and version:
                return name, version
    return "hub.placeholder", "0.0.0"


def _build_workflow_definition(workflow: dict[str, object]) -> dict[str, object]:
    name = workflow.get("name")
    if not isinstance(name, str) or not name.strip():
        name = str(workflow.get("workflow_id") or "Hub Workflow")
    summary = workflow.get("summary")
    description = workflow.get("description")
    if not isinstance(description, str) or not description.strip():
        description = summary if isinstance(summary, str) else None
    tags = workflow.get("tags") if isinstance(workflow.get("tags"), list) else []
    owner_id = workflow.get("owner_id") if isinstance(workflow.get("owner_id"), str) else None
    owner_name = OWNER_NAME_BY_ID.get(owner_id or "")
    package_name, package_version = _resolve_primary_dependency(workflow)
    workflow_definition_id = str(uuid4())
    node_id = str(uuid4())

    metadata = {
        "name": name,
        "description": description,
        "tags": tags or None,
        "namespace": "default",
        "originId": workflow_definition_id,
        "ownerId": owner_id,
        "ownerName": owner_name,
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}

    return {
        "id": workflow_definition_id,
        "schemaVersion": DEFAULT_WORKFLOW_SCHEMA_VERSION,
        "metadata": metadata,
        "nodes": [
            {
                "id": node_id,
                "type": f"{package_name}.entry",
                "package": {"name": package_name, "version": package_version},
                "status": "published",
                "category": "hub",
                "label": "Entry",
                "position": {"x": 0, "y": 0},
                "parameters": {},
                "results": {},
            }
        ],
        "edges": [],
        "tags": tags,
    }


def seed_sample_catalog() -> None:
    enabled = _env_flag(
        "HUB_SEED_SAMPLE_DATA",
        os.getenv("ASTRAFLOW_HUB_SEED_SAMPLE_DATA", "false"),
    )
    if not enabled:
        return

    with SessionLocal() as session:
        has_packages = session.execute(select(HubPackage.name).limit(1)).first()
        has_workflows = session.execute(select(HubWorkflow.id).limit(1)).first()
        if has_packages or has_workflows:
            return

    for package in DEFAULT_PACKAGES:
        for version in package["versions"]:
            publish_package_version(
                name=package["name"],
                version=version,
                description=package["description"],
                readme=package["readme"],
                tags=package["tags"],
                visibility="public",
                owner_id=package["owner_id"],
                owner_name=package["owner_name"],
                publisher_id=package["owner_id"],
                archive_bytes=None,
                archive_sha256=None,
                archive_size_bytes=None,
            )
        for tag, tagged_version in package["dist_tags"].items():
            if tag == "latest":
                continue
            set_package_tag_record(package["name"], tag, tagged_version)

    for workflow in DEFAULT_WORKFLOWS:
        definition = _build_workflow_definition(workflow)
        publish_workflow_version(
            workflow_id=workflow["workflow_id"],
            name=workflow["name"],
            version=workflow["version"],
            summary=workflow["summary"],
            description=workflow["description"],
            tags=workflow["tags"],
            visibility="public",
            preview_image=None,
            dependencies=workflow["dependencies"],
            definition=definition,
            publisher_id=workflow["owner_id"],
        )
