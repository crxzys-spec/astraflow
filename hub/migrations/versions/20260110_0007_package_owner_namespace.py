"""Namespace hub packages by owner."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260110_0007"
down_revision = "20260106_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("PRAGMA foreign_keys=OFF")

    conn = op.get_bind()
    def _table_exists(name: str) -> bool:
        return name in sa.inspect(conn).get_table_names()

    def _table_has_rows(name: str) -> bool:
        try:
            result = conn.execute(sa.text(f"SELECT 1 FROM {name} LIMIT 1")).fetchone()
        except Exception:
            return False
        return result is not None

    def _index_exists(table: str, name: str) -> bool:
        result = conn.execute(
            sa.text("SELECT 1 FROM sqlite_master WHERE type='index' AND name=:name"),
            {"name": name},
        ).fetchone()
        if result is not None:
            return True
        return any(idx.get("name") == name for idx in sa.inspect(conn).get_indexes(table))

    if not _table_exists("hub_packages_old") and _table_exists("hub_packages"):
        op.rename_table("hub_packages", "hub_packages_old")
    if not _table_exists("hub_package_versions_old") and _table_exists("hub_package_versions"):
        op.rename_table("hub_package_versions", "hub_package_versions_old")
    if not _table_exists("hub_package_permissions_old") and _table_exists("hub_package_permissions"):
        op.rename_table("hub_package_permissions", "hub_package_permissions_old")

    if not _table_exists("hub_packages"):
        op.create_table(
            "hub_packages",
            sa.Column("owner_id", sa.String(length=64), primary_key=True),
            sa.Column("name", sa.String(length=255), primary_key=True),
            sa.Column("name_normalized", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("readme", sa.Text(), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("dist_tags", sa.JSON(), nullable=True),
            sa.Column("latest_version", sa.String(length=64), nullable=True),
            sa.Column("owner_name", sa.String(length=128), nullable=True),
            sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "owner_id",
                "name_normalized",
                name="uq_hub_package_owner_name",
            ),
        )
    if _table_exists("hub_packages") and not _index_exists("hub_packages", "ix_hub_packages_name_normalized"):
        op.create_index("ix_hub_packages_name_normalized", "hub_packages", ["name_normalized"])
    if _table_exists("hub_packages") and not _index_exists("hub_packages", "ix_hub_packages_owner_id"):
        op.create_index("ix_hub_packages_owner_id", "hub_packages", ["owner_id"])

    if _table_exists("hub_packages_old") and not _table_has_rows("hub_packages"):
        op.execute(
            """
            INSERT INTO hub_packages (
                owner_id,
                name,
                name_normalized,
                description,
                readme,
                tags,
                dist_tags,
                latest_version,
                owner_name,
                visibility,
                created_at,
                updated_at
            )
            SELECT
                owner_id,
                name,
                name_normalized,
                description,
                readme,
                tags,
                dist_tags,
                latest_version,
                owner_name,
                visibility,
                created_at,
                updated_at
            FROM hub_packages_old
            """
        )

    if not _table_exists("hub_package_versions"):
        op.create_table(
            "hub_package_versions",
            sa.Column("owner_id", sa.String(length=64), nullable=False),
            sa.Column("package_name", sa.String(length=255), nullable=False),
            sa.Column("version", sa.String(length=64), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("readme", sa.Text(), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("archive_sha256", sa.String(length=64), nullable=True),
            sa.Column("archive_size_bytes", sa.Integer(), nullable=True),
            sa.Column("archive_path", sa.String(length=512), nullable=True),
            sa.Column("owner_name", sa.String(length=128), nullable=True),
            sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public"),
            sa.Column(
                "published_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(
                ["owner_id", "package_name"],
                ["hub_packages.owner_id", "hub_packages.name"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("owner_id", "package_name", "version"),
        )
    if _table_exists("hub_package_versions") and not _index_exists(
        "hub_package_versions",
        "ix_hub_package_versions_owner_id",
    ):
        op.create_index(
            "ix_hub_package_versions_owner_id",
            "hub_package_versions",
            ["owner_id"],
        )

    if _table_exists("hub_package_versions_old") and not _table_has_rows("hub_package_versions"):
        op.execute(
            """
            INSERT INTO hub_package_versions (
                owner_id,
                package_name,
                version,
                description,
                readme,
                tags,
                archive_sha256,
                archive_size_bytes,
                archive_path,
                owner_name,
                visibility,
                published_at,
                updated_at
            )
            SELECT
                owner_id,
                package_name,
                version,
                description,
                readme,
                tags,
                archive_sha256,
                archive_size_bytes,
                archive_path,
                owner_name,
                visibility,
                published_at,
                updated_at
            FROM hub_package_versions_old
            """
        )

    if not _table_exists("hub_package_permissions"):
        op.create_table(
            "hub_package_permissions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("owner_id", sa.String(length=64), nullable=False),
            sa.Column("package_name", sa.String(length=255), nullable=False),
            sa.Column("subject_type", sa.String(length=32), nullable=False),
            sa.Column("subject_id", sa.String(length=64), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(
                ["owner_id", "package_name"],
                ["hub_packages.owner_id", "hub_packages.name"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "owner_id",
                "package_name",
                "subject_type",
                "subject_id",
                name="uq_hub_package_permission",
            ),
        )
    if _table_exists("hub_package_permissions") and not _index_exists(
        "hub_package_permissions",
        "ix_hub_package_permissions_owner_id",
    ):
        op.create_index(
            "ix_hub_package_permissions_owner_id",
            "hub_package_permissions",
            ["owner_id"],
        )
    if _table_exists("hub_package_permissions") and not _index_exists(
        "hub_package_permissions",
        "ix_hub_package_permissions_package_name",
    ):
        op.create_index(
            "ix_hub_package_permissions_package_name",
            "hub_package_permissions",
            ["package_name"],
        )

    if _table_exists("hub_package_permissions_old") and not _table_has_rows("hub_package_permissions"):
        op.execute(
            """
            INSERT INTO hub_package_permissions (
                id,
                owner_id,
                package_name,
                subject_type,
                subject_id,
                role,
                created_at
            )
            SELECT
                perm.id,
                pkg.owner_id,
                perm.package_name,
                perm.subject_type,
                perm.subject_id,
                perm.role,
                perm.created_at
            FROM hub_package_permissions_old AS perm
            JOIN hub_packages AS pkg
                ON perm.package_name = pkg.name
            """
        )

    if _table_exists("hub_package_permissions_old"):
        op.drop_table("hub_package_permissions_old")
    if _table_exists("hub_package_versions_old"):
        op.drop_table("hub_package_versions_old")
    if _table_exists("hub_packages_old"):
        op.drop_table("hub_packages_old")

    op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    op.execute("PRAGMA foreign_keys=OFF")

    op.rename_table("hub_packages", "hub_packages_old")
    op.rename_table("hub_package_versions", "hub_package_versions_old")
    op.rename_table("hub_package_permissions", "hub_package_permissions_old")

    op.create_table(
        "hub_packages",
        sa.Column("name", sa.String(length=255), primary_key=True),
        sa.Column("name_normalized", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("readme", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("dist_tags", sa.JSON(), nullable=True),
        sa.Column("latest_version", sa.String(length=64), nullable=True),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("owner_name", sa.String(length=128), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_hub_packages_name_normalized",
        "hub_packages",
        ["name_normalized"],
        unique=True,
    )
    op.create_index("ix_hub_packages_owner_id", "hub_packages", ["owner_id"])

    op.execute(
        """
        INSERT INTO hub_packages (
            name,
            name_normalized,
            description,
            readme,
            tags,
            dist_tags,
            latest_version,
            owner_id,
            owner_name,
            visibility,
            created_at,
            updated_at
        )
        SELECT
            name,
            name_normalized,
            description,
            readme,
            tags,
            dist_tags,
            latest_version,
            owner_id,
            owner_name,
            visibility,
            created_at,
            updated_at
        FROM hub_packages_old
        """
    )

    op.create_table(
        "hub_package_versions",
        sa.Column("package_name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("readme", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("archive_sha256", sa.String(length=64), nullable=True),
        sa.Column("archive_size_bytes", sa.Integer(), nullable=True),
        sa.Column("archive_path", sa.String(length=512), nullable=True),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("owner_name", sa.String(length=128), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public"),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["package_name"], ["hub_packages.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("package_name", "version"),
    )
    op.create_index(
        "ix_hub_package_versions_owner_id",
        "hub_package_versions",
        ["owner_id"],
    )

    op.execute(
        """
        INSERT INTO hub_package_versions (
            package_name,
            version,
            description,
            readme,
            tags,
            archive_sha256,
            archive_size_bytes,
            archive_path,
            owner_id,
            owner_name,
            visibility,
            published_at,
            updated_at
        )
        SELECT
            package_name,
            version,
            description,
            readme,
            tags,
            archive_sha256,
            archive_size_bytes,
            archive_path,
            owner_id,
            owner_name,
            visibility,
            published_at,
            updated_at
        FROM hub_package_versions_old
        """
    )

    op.create_table(
        "hub_package_permissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("package_name", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["package_name"], ["hub_packages.name"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "package_name",
            "subject_type",
            "subject_id",
            name="uq_hub_package_permission",
        ),
    )
    op.create_index(
        "ix_hub_package_permissions_package_name",
        "hub_package_permissions",
        ["package_name"],
    )

    op.execute(
        """
        INSERT INTO hub_package_permissions (
            id,
            package_name,
            subject_type,
            subject_id,
            role,
            created_at
        )
        SELECT
            perm.id,
            perm.package_name,
            perm.subject_type,
            perm.subject_id,
            perm.role,
            perm.created_at
        FROM hub_package_permissions_old AS perm
        """
    )

    op.drop_table("hub_package_permissions_old")
    op.drop_table("hub_package_versions_old")
    op.drop_table("hub_packages_old")

    op.execute("PRAGMA foreign_keys=ON")
