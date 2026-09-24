"""Add password authentication and dataset ownership."""

from alembic import op
import sqlalchemy as sa

revision = "0005_add_auth_ownership"
down_revision = "0004_add_asset_embeddings"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("password_hash", sa.String(length=512), nullable=True))
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.create_index("ix_datasets_owner_id", ["owner_id"])
        batch_op.create_foreign_key(
            "fk_datasets_owner_id_users", "users", ["owner_id"], ["id"], ondelete="SET NULL"
        )


def downgrade():
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.drop_constraint("fk_datasets_owner_id_users", type_="foreignkey")
        batch_op.drop_index("ix_datasets_owner_id")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_hash")
