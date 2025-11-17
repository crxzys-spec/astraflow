"""Store workflow metadata fields separately from runtime definition."""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "20251105_0003"
down_revision = "20251105_0002"
branch_labels = None
depends_on = None


WORKFLOW_TABLE = "workflows"


def _extract_metadata(payload: dict[str, object], workflow_id: str) -> tuple[str, str, str, str | None, str | None, str | None, dict[str, object]]:
    schema_version = str(payload.get("schemaVersion") or "2025-10")
    metadata = payload.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    name = str(metadata.get("name") or workflow_id)
    namespace = str(metadata.get("namespace") or "default")
    origin_id = str(metadata.get("originId") or workflow_id)
    description = metadata.get("description")
    environment = metadata.get("environment")
    tags = metadata.get("tags")
    if description is not None:
        description = str(description)
    if environment is not None:
        environment = str(environment)
    tags_value = None
    if isinstance(tags, list):
        tags_value = json.dumps(tags)
    structure = {k: v for k, v in payload.items() if k not in {"id", "schemaVersion", "metadata"}}
    return schema_version, name, namespace, origin_id, description, environment, tags_value, structure


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns(WORKFLOW_TABLE)}

    if "schema_version" not in existing_columns:
        op.add_column(WORKFLOW_TABLE, sa.Column("schema_version", sa.String(length=32), nullable=False, server_default="2025-10"))
    if "namespace" not in existing_columns:
        op.add_column(WORKFLOW_TABLE, sa.Column("namespace", sa.String(length=128), nullable=False, server_default="default"))
    if "origin_id" not in existing_columns:
        op.add_column(WORKFLOW_TABLE, sa.Column("origin_id", sa.String(length=128), nullable=False, server_default=""))
    if "description" not in existing_columns:
        op.add_column(WORKFLOW_TABLE, sa.Column("description", sa.Text(), nullable=True))
    if "environment" not in existing_columns:
        op.add_column(WORKFLOW_TABLE, sa.Column("environment", sa.String(length=64), nullable=True))
    if "tags" not in existing_columns:
        op.add_column(WORKFLOW_TABLE, sa.Column("tags", sa.Text(), nullable=True))

    rows = bind.execute(sa.text(f"SELECT id, name, definition FROM {WORKFLOW_TABLE}")).fetchall()
    update_stmt = sa.text(
        f"""
        UPDATE {WORKFLOW_TABLE}
        SET
            name = :name,
            schema_version = :schema_version,
            namespace = :namespace,
            origin_id = :origin_id,
            description = :description,
            environment = :environment,
            tags = :tags,
            definition = :definition
        WHERE id = :id
        """
    )
    for row in rows:
        payload = json.loads(row.definition)
        schema_version, name, namespace, origin_id, description, environment, tags_value, structure = _extract_metadata(payload, row.id)
        bind.execute(
            update_stmt,
            {
                "id": row.id,
                "name": name,
                "schema_version": schema_version,
                "namespace": namespace,
                "origin_id": origin_id,
                "description": description,
                "environment": environment,
                "tags": tags_value,
                "definition": json.dumps(structure, ensure_ascii=False),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"SELECT id, schema_version, name, namespace, origin_id, description, environment, tags, definition FROM {WORKFLOW_TABLE}")).fetchall()
    update_stmt = sa.text(
        f"""
        UPDATE {WORKFLOW_TABLE}
        SET definition = :definition
        WHERE id = :id
        """
    )
    for row in rows:
        metadata = {
            "name": row.name,
            "description": row.description,
            "environment": row.environment,
            "namespace": row.namespace,
            "originId": row.origin_id or row.id,
        }
        if row.tags:
            try:
                metadata["tags"] = json.loads(row.tags)
            except json.JSONDecodeError:
                pass
        structure = json.loads(row.definition)
        structure["id"] = row.id
        structure["schemaVersion"] = row.schema_version or "2025-10"
        structure["metadata"] = metadata
        bind.execute(
            update_stmt,
            {
                "id": row.id,
                "definition": json.dumps(structure, ensure_ascii=False),
            },
        )

    op.drop_column(WORKFLOW_TABLE, "tags")
    op.drop_column(WORKFLOW_TABLE, "environment")
    op.drop_column(WORKFLOW_TABLE, "description")
    op.drop_column(WORKFLOW_TABLE, "origin_id")
    op.drop_column(WORKFLOW_TABLE, "namespace")
    op.drop_column(WORKFLOW_TABLE, "schema_version")
