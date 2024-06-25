"""fix is_deleted_by_recipient column issue

Revision ID: bf5adda06d95
Revises: 0246b0794948
Create Date: 2024-06-24 15:42:10.931045

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf5adda06d95'
down_revision = '0246b0794948'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_deleted_by_recipient', sa.Boolean(), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.drop_column('is_deleted_by_recipient')

    # ### end Alembic commands ###