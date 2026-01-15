"""Add owner namespace to published package storage."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260111_0008"
down_revision = "20260102_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    default_owner = "local"
    conn = op.get_bind()

    op.create_table(
        "package_index_new",
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("archive_path", sa.String(length=512), nullable=True),
        sa.Column("archive_sha256", sa.String(length=64), nullable=True),
        sa.Column("archive_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("owner_id", "name", "version", "source"),
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO package_index_new (
                owner_id,
                name,
                version,
                source,
                schema_version,
                description,
                manifest_json,
                manifest_hash,
                archive_path,
                archive_sha256,
                archive_size_bytes,
                status,
                created_at,
                updated_at,
                last_seen_at
            )
            SELECT
                COALESCE(owner_id, :owner_id) AS owner_id,
                name,
                version,
                source,
                schema_version,
                description,
                manifest_json,
                manifest_hash,
                archive_path,
                archive_sha256,
                archive_size_bytes,
                status,
                created_at,
                updated_at,
                last_seen_at
            FROM package_index
            """
        ),
        {"owner_id": default_owner},
    )
    op.drop_table("package_index")
    op.rename_table("package_index_new", "package_index")
    op.create_index("ix_package_index_name", "package_index", ["name"])
    op.create_index("ix_package_index_source", "package_index", ["source"])
    op.create_index("ix_package_index_owner_id", "package_index", ["owner_id"])
    op.create_index("ix_package_index_owner_name", "package_index", ["owner_id", "name"])

    op.create_table(
        "package_dist_tags_new",
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("owner_id", "name", "tag", "source"),
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO package_dist_tags_new (
                owner_id,
                name,
                tag,
                source,
                version,
                created_at,
                updated_at
            )
            SELECT
                :owner_id AS owner_id,
                name,
                tag,
                source,
                version,
                created_at,
                updated_at
            FROM package_dist_tags
            """
        ),
        {"owner_id": default_owner},
    )
    op.drop_table("package_dist_tags")
    op.rename_table("package_dist_tags_new", "package_dist_tags")
    op.create_index("ix_package_dist_tags_name", "package_dist_tags", ["name"])
    op.create_index("ix_package_dist_tags_source", "package_dist_tags", ["source"])
    op.create_index("ix_package_dist_tags_owner_id", "package_dist_tags", ["owner_id"])
    op.create_index("ix_package_dist_tags_owner_name", "package_dist_tags", ["owner_id", "name"])


def downgrade() -> None:
    conn = op.get_bind()

    op.create_table(
        "package_index_old",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("archive_path", sa.String(length=512), nullable=True),
        sa.Column("archive_sha256", sa.String(length=64), nullable=True),
        sa.Column("archive_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name", "version", "source"),
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO package_index_old (
                name,
                version,
                source,
                schema_version,
                description,
                manifest_json,
                manifest_hash,
                archive_path,
                archive_sha256,
                archive_size_bytes,
                status,
                created_at,
                updated_at,
                last_seen_at
            )
            SELECT
                name,
                version,
                source,
                schema_version,
                description,
                manifest_json,
                manifest_hash,
                archive_path,
                archive_sha256,
                archive_size_bytes,
                status,
                created_at,
                updated_at,
                last_seen_at
            FROM package_index
            """
        )
    )
    op.drop_table("package_index")
    op.rename_table("package_index_old", "package_index")
    op.create_index("ix_package_index_name", "package_index", ["name"])
    op.create_index("ix_package_index_source", "package_index", ["source"])

    op.create_table(
        "package_dist_tags_old",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name", "tag", "source"),
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO package_dist_tags_old (
                name,
                tag,
                source,
                version,
                created_at,
                updated_at
            )
            SELECT
                name,
                tag,
                source,
                version,
                created_at,
                updated_at
            FROM package_dist_tags
            """
        )
    )
    op.drop_table("package_dist_tags")
    op.rename_table("package_dist_tags_old", "package_dist_tags")
    op.create_index("ix_package_dist_tags_name", "package_dist_tags", ["name"])
    op.create_index("ix_package_dist_tags_source", "package_dist_tags", ["source"])
