"""empty message

Revision ID: 994bc4f80420
Revises: 
Create Date: 2020-03-25 16:52:32.185023

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '994bc4f80420'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('machine_group',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.add_column('machine', sa.Column('group_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'machine', 'machine_group', ['group_id'], ['id'])
    op.drop_column('machine', 'group')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('machine', sa.Column('group', sa.VARCHAR(), nullable=True))
    op.drop_constraint(None, 'machine', type_='foreignkey')
    op.drop_column('machine', 'group_id')
    op.drop_table('machine_group')
    # ### end Alembic commands ###
