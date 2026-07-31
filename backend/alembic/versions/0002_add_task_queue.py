"""Add task queue table.

Revision ID: 0002_add_task_queue
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_task_queue"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "task_queue",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True
        ),

        sa.Column(
            "task_type",
            sa.String(255),
            nullable=False
        ),

        sa.Column(
            "payload",
            sa.JSON(),
            nullable=False
        ),

        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="queued"
        ),

        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),

        sa.Column(
            "error",
            sa.Text(),
            nullable=True
        ),

        sa.Column(
            "result",
            sa.JSON(),
            nullable=True
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP")
        ),

        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True
        ),

        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True
        )
    )


def downgrade():
    op.drop_table("task_queue")