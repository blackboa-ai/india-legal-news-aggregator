"""v2.1 Phase 1: Content Classification Engine & DB Migration

Revision ID: 0004_v2_1_content_classification
Revises: 0003_add_feedback_table
Create Date: 2026-11-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_v2_1_content_classification"
down_revision: str | None = "0003_add_feedback_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        # Offline SQL generation
        op.add_column(
            "judgments",
            sa.Column(
                "content_type",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'unknown'"),
            ),
        )
        op.add_column(
            "judgments",
            sa.Column(
                "content_type_confidence",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0.0"),
            ),
        )
        op.create_index(
            "idx_judgments_content_type",
            "judgments",
            ["content_type"],
            unique=False,
        )
        op.execute(
            """
            UPDATE judgments 
            SET content_type = 'judgment', content_type_confidence = 1.0 
            WHERE source IN ('sci', 'indiankanoon');
            """
        )
        op.execute(
            """
            UPDATE judgments 
            SET content_type = 'unknown', content_type_confidence = 0.5 
            WHERE source IN ('livelaw', 'barandbench');
            """
        )
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "judgments" in tables:
        columns = [c["name"] for c in inspector.get_columns("judgments")]
        indexes = [idx["name"] for idx in inspector.get_indexes("judgments")]

        # 1. Add content_type column if not present
        if "content_type" not in columns:
            op.add_column(
                "judgments",
                sa.Column(
                    "content_type",
                    sa.String(length=20),
                    nullable=False,
                    server_default=sa.text("'unknown'"),
                ),
            )

        # 2. Add content_type_confidence column if not present
        if "content_type_confidence" not in columns:
            op.add_column(
                "judgments",
                sa.Column(
                    "content_type_confidence",
                    sa.Float(),
                    nullable=False,
                    server_default=sa.text("0.0"),
                ),
            )

        # 3. Create index idx_judgments_content_type if not present
        if "idx_judgments_content_type" not in indexes:
            op.create_index(
                "idx_judgments_content_type",
                "judgments",
                ["content_type"],
                unique=False,
            )

        # 4. Immediate SQL Backfill:
        # Step 4A: Rule A - Authoritative sources (sci, indiankanoon)
        op.execute(
            """
            UPDATE judgments 
            SET content_type = 'judgment', content_type_confidence = 1.0 
            WHERE source IN ('sci', 'indiankanoon');
            """
        )

        # Step 4B: LiveLaw and Bar & Bench classification
        try:
            from app.services.legal_classifier import classify_content_type

            rows = conn.execute(
                sa.text(
                    "SELECT id, title, excerpt, full_text, source, url "
                    "FROM judgments WHERE source IN ('livelaw', 'barandbench')"
                )
            ).fetchall()

            for row in rows:
                row_id = row[0]
                title = row[1] or ""
                excerpt = row[2] or ""
                full_text = row[3] or ""
                source = row[4] or ""
                url = row[5] or ""
                c_type, c_conf = classify_content_type(
                    title=title,
                    text=full_text or excerpt,
                    source=source,
                    url=url,
                )
                conn.execute(
                    sa.text(
                        "UPDATE judgments "
                        "SET content_type = :ctype, content_type_confidence = :cconf "
                        "WHERE id = :id"
                    ),
                    {"ctype": c_type, "cconf": float(c_conf), "id": row_id},
                )
        except Exception:
            # Fallback to default unknown with 0.5 confidence as specified
            op.execute(
                """
                UPDATE judgments 
                SET content_type = 'unknown', content_type_confidence = 0.5 
                WHERE source IN ('livelaw', 'barandbench') AND (content_type IS NULL OR content_type = 'unknown');
                """
            )

        # Step 4C: Any remaining rows default to 'unknown' with 0.5 confidence
        op.execute(
            """
            UPDATE judgments 
            SET content_type = 'unknown', content_type_confidence = 0.5 
            WHERE content_type = 'unknown' AND content_type_confidence = 0.0;
            """
        )


def downgrade() -> None:
    if context.is_offline_mode():
        op.drop_index("idx_judgments_content_type", table_name="judgments")
        op.drop_column("judgments", "content_type_confidence")
        op.drop_column("judgments", "content_type")
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "judgments" in tables:
        indexes = [idx["name"] for idx in inspector.get_indexes("judgments")]
        if "idx_judgments_content_type" in indexes:
            op.drop_index("idx_judgments_content_type", table_name="judgments")

        columns = [c["name"] for c in inspector.get_columns("judgments")]
        if "content_type_confidence" in columns:
            op.drop_column("judgments", "content_type_confidence")
        if "content_type" in columns:
            op.drop_column("judgments", "content_type")
