"""Add reconcile job status table.

Revision ID: 0003_add_reconcile_job
Revises: 0002_add_task_queue
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_add_reconcile_job"
down_revision = "0002_add_task_queue"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reconcile_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("total_refs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_refs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("errors", sa.JSON(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reconcile_jobs_status", "reconcile_jobs", ["status"])


def downgrade():
    op.drop_index("ix_reconcile_jobs_status", table_name="reconcile_jobs")
    op.drop_table("reconcile_jobs")
