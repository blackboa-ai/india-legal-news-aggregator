"""Initial Phase 2 schema: judgments, bookmarks, topics, pgvector, and hybrid indexes

Revision ID: 0001_initial_phase2_schema
Revises: None
Create Date: 2026-11-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_phase2_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Enable pgvector and pgcrypto extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE varchar(128);")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION immutable_array_to_string(text[], text) 
        RETURNS text AS $$
            SELECT array_to_string($1, $2);
        $$ LANGUAGE sql IMMUTABLE;
        """
    )

    # 2. Create judgments table
    if "judgments" not in tables:
        op.create_table(
            "judgments",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("external_id", sa.String(length=128), nullable=False, unique=True),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("short_title", sa.String(length=500), nullable=True),
            sa.Column("court_code", sa.String(length=50), nullable=False),
            sa.Column("court_name", sa.String(length=120), nullable=False),
            sa.Column("court_level", sa.Integer(), nullable=False, server_default=sa.text("2")),
            sa.Column("judgment_date", sa.Date(), nullable=False),
            sa.Column("subject_category", sa.String(length=50), nullable=False),
            sa.Column("excerpt", sa.Text(), nullable=False),
            sa.Column("full_text", sa.Text(), nullable=True),
            sa.Column("url", sa.Text(), nullable=False),
            sa.Column("parties", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("tags", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
            sa.Column("source", sa.String(length=50), nullable=False),
            sa.Column("is_archived", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("classification_confidence", sa.Float(), server_default=sa.text("0.0"), nullable=False),
            sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
            sa.Column("search_tsv", postgresql.TSVECTOR(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        )

    # Convert embedding column to native VECTOR(384) in PostgreSQL
    op.execute("ALTER TABLE judgments ALTER COLUMN embedding TYPE vector(384) USING embedding::vector(384);")

    # Add search_tsv generated column or trigger-backed column for full-text search across title, excerpt & tags
    op.execute("ALTER TABLE judgments DROP COLUMN IF EXISTS search_tsv;")
    op.execute(
        """
        ALTER TABLE judgments ADD COLUMN search_tsv tsvector GENERATED ALWAYS AS (
            to_tsvector('english'::regconfig, coalesce(title, '') || ' ' || coalesce(excerpt, '') || ' ' || coalesce(immutable_array_to_string(tags, ' '), ''))
        ) STORED;
        """
    )

    # 3. Create bookmarks table
    if "bookmarks" not in tables:
        op.create_table(
            "bookmarks",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("user_id", sa.String(length=100), nullable=False),
            sa.Column(
                "judgment_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("judgments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            sa.UniqueConstraint("user_id", "judgment_id", name="uq_user_judgment_bookmark"),
        )

    # 4. Create topics table
    if "topics" not in tables:
        op.create_table(
            "topics",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("user_id", sa.String(length=100), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        )

    # 5. Create topic_judgments association table
    if "topic_judgments" not in tables:
        op.create_table(
            "topic_judgments",
            sa.Column(
                "topic_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("topics.id", ondelete="CASCADE"),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "judgment_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("judgments.id", ondelete="CASCADE"),
                primary_key=True,
                nullable=False,
            ),
            sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        )

    # 6. Create indexes
    existing_indexes = []
    if "judgments" in tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("judgments")]

    if "idx_judgments_category" not in existing_indexes:
        op.create_index("idx_judgments_category", "judgments", ["subject_category"])
    if "idx_judgments_court" not in existing_indexes:
        op.create_index("idx_judgments_court", "judgments", ["court_code"])
    if "idx_judgments_date" not in existing_indexes:
        op.create_index("idx_judgments_date", "judgments", [sa.text("judgment_date DESC")])

    if "bookmarks" in tables:
        bm_indexes = [idx["name"] for idx in inspector.get_indexes("bookmarks")]
        if "idx_bookmarks_user" not in bm_indexes:
            op.create_index("idx_bookmarks_user", "bookmarks", ["user_id"])
    elif "bookmarks" not in tables:
        op.create_index("idx_bookmarks_user", "bookmarks", ["user_id"])

    if "topics" in tables:
        tp_indexes = [idx["name"] for idx in inspector.get_indexes("topics")]
        if "idx_topics_user" not in tp_indexes:
            op.create_index("idx_topics_user", "topics", ["user_id"])
    elif "topics" not in tables:
        op.create_index("idx_topics_user", "topics", ["user_id"])

    # High-speed GIN index on search_tsv for fast BM25 / keyword retrieval
    op.execute("CREATE INDEX IF NOT EXISTS idx_judgments_tsv ON judgments USING GIN(search_tsv);")

    # High-speed HNSW cosine similarity index on embedding (VECTOR(384))
    op.execute("CREATE INDEX IF NOT EXISTS idx_judgments_embedding ON judgments USING HNSW (embedding vector_cosine_ops);")


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_judgments_embedding;")
    op.execute("DROP INDEX IF EXISTS idx_judgments_tsv;")
    op.drop_index("idx_topics_user", table_name="topics")
    op.drop_index("idx_bookmarks_user", table_name="bookmarks")
    op.drop_index("idx_judgments_date", table_name="judgments")
    op.drop_index("idx_judgments_court", table_name="judgments")
    op.drop_index("idx_judgments_category", table_name="judgments")

    # Drop tables
    op.drop_table("topic_judgments")
    op.drop_table("topics")
    op.drop_table("bookmarks")
    op.drop_table("judgments")
