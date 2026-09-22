"""Add canonical asset embedding records.

The original schema exposes ``embeddings_refs`` for the reconciliation
service.  The ingestion worker stores the generated vector in this table and
keeps the reference table for backwards compatibility.
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_asset_embeddings"
down_revision = "0003_add_reconcile_job"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("vector_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ready"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_embeddings_asset_id", "embeddings", ["asset_id"])


def downgrade():
    op.drop_index("ix_embeddings_asset_id", table_name="embeddings")
    op.drop_table("embeddings")
