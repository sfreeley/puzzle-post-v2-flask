"""add is_automated to message model

Revision ID: 1a568826fcb1
Revises: 8c7563d35395
Create Date: 2024-07-10 19:53:59.702684

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a568826fcb1'
down_revision = '8c7563d35395'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_automated', sa.Boolean(), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.drop_column('is_automated')

    # ### end Alembic commands ###
