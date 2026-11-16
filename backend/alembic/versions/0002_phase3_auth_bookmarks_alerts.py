"""Phase 3 schema: users, bookmarks enhancements (notes, tags), and personalized alerts

Revision ID: 0002_phase3_auth_bookmarks_alerts
Revises: 0001_initial_phase2_schema
Create Date: 2026-11-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_phase3_auth_bookmarks_alerts"
down_revision: str | None = "0001_initial_phase2_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE varchar(128);")
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create users table
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=True),
            sa.Column("full_name", sa.String(length=255), nullable=True),
            sa.Column("google_id", sa.String(length=255), nullable=True, unique=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        )
        op.create_index("idx_users_email", "users", ["email"])
        op.create_index("idx_users_google_id", "users", ["google_id"])
    else:
        existing_user_indexes = [idx["name"] for idx in inspector.get_indexes("users")]
        if "idx_users_email" not in existing_user_indexes:
            op.create_index("idx_users_email", "users", ["email"])
        if "idx_users_google_id" not in existing_user_indexes:
            op.create_index("idx_users_google_id", "users", ["google_id"])

    # 2. Add notes and tags to bookmarks table
    if "bookmarks" in tables:
        existing_cols = [c["name"] for c in inspector.get_columns("bookmarks")]
        if "notes" not in existing_cols:
            op.add_column("bookmarks", sa.Column("notes", sa.Text(), nullable=True))
        if "tags" not in existing_cols:
            op.add_column(
                "bookmarks",
                sa.Column("tags", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
            )

    # 3. Create alerts table
    if "alerts" not in tables:
        op.create_table(
            "alerts",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("user_id", sa.String(length=100), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=True),
            sa.Column("court_code", sa.String(length=50), nullable=True),
            sa.Column("keywords", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
            sa.Column("query", sa.String(length=300), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_alerts_user_id", "alerts", ["user_id"])
        op.create_index("idx_alerts_category", "alerts", ["category"])
        op.create_index("idx_alerts_court_code", "alerts", ["court_code"])
    else:
        existing_alert_indexes = [idx["name"] for idx in inspector.get_indexes("alerts")]
        if "idx_alerts_user_id" not in existing_alert_indexes:
            op.create_index("idx_alerts_user_id", "alerts", ["user_id"])
        if "idx_alerts_category" not in existing_alert_indexes:
            op.create_index("idx_alerts_category", "alerts", ["category"])
        if "idx_alerts_court_code" not in existing_alert_indexes:
            op.create_index("idx_alerts_court_code", "alerts", ["court_code"])


def downgrade() -> None:
    # Drop alerts
    op.drop_index("idx_alerts_court_code", table_name="alerts")
    op.drop_index("idx_alerts_category", table_name="alerts")
    op.drop_index("idx_alerts_user_id", table_name="alerts")
    op.drop_table("alerts")

    # Revert bookmarks columns
    op.drop_column("bookmarks", "tags")
    op.drop_column("bookmarks", "notes")

    # Drop users
    op.drop_index("idx_users_google_id", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
