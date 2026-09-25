"""Add annotation review metadata."""

from alembic import op
import sqlalchemy as sa

revision = "0006_add_annotation_review_fields"
down_revision = "0005_add_auth_ownership"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("annotations") as batch_op:
        batch_op.add_column(sa.Column("reviewed_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("uq_annotations_asset_version", ["asset_id", "version"], unique=True)


def downgrade():
    with op.batch_alter_table("annotations") as batch_op:
        batch_op.drop_index("uq_annotations_asset_version")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by_id")
