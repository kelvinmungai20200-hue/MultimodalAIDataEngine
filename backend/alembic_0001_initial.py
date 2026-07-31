"""
Initial database schema for SQLite.

Compatible with:
- SQLite (development)
- SQLAlchemy 2.x
- Alembic
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # -----------------------------
    # DATASETS
    # -----------------------------
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # -----------------------------
    # ASSETS
    # -----------------------------
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("s3_url", sa.String(length=1024), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("annotations", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_index(
        "ix_assets_dataset_status",
        "assets",
        ["dataset_id", "status"],
    )

    # -----------------------------
    # ANNOTATIONS
    # -----------------------------
    op.create_table(
        "annotations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("annotator_id", sa.Integer(), nullable=True),
        sa.Column("annotation", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_index(
        "ix_annotations_asset_status",
        "annotations",
        ["asset_id", "status"],
    )

    # -----------------------------
    # LLM RECORDS
    # -----------------------------
    op.create_table(
        "llm_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("responses", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("rlhf_feedback", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # -----------------------------
    # EMBEDDINGS
    # -----------------------------
    op.create_table(
        "embeddings_refs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "llm_record_id",
            sa.Integer(),
            sa.ForeignKey("llm_records.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("vector_db_id", sa.String(length=255), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("dimension", sa.Integer(), nullable=True),
        sa.Column("normalized", sa.Boolean(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_index(
        "ix_embeddings_vector_db_id",
        "embeddings_refs",
        ["vector_db_id"],
    )

    # -----------------------------
    # USERS
    # -----------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="annotator"),
        sa.Column("api_key_hash", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # -----------------------------
    # AUDIT LOGS
    # -----------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("target_type", sa.String(length=255), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade():
    op.drop_table("audit_logs")
    op.drop_table("users")

    op.drop_index(
        "ix_embeddings_vector_db_id",
        table_name="embeddings_refs",
    )
    op.drop_table("embeddings_refs")

    op.drop_table("llm_records")

    op.drop_index(
        "ix_annotations_asset_status",
        table_name="annotations",
    )
    op.drop_table("annotations")

    op.drop_index(
        "ix_assets_dataset_status",
        table_name="assets",
    )
    op.drop_table("assets")

    op.drop_table("datasets")