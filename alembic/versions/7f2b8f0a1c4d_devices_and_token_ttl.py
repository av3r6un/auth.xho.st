"""Add devices and bind refresh tokens to devices.

Revision ID: 7f2b8f0a1c4d
Revises: 241808c91694
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = '7f2b8f0a1c4d'
down_revision: Union[str, Sequence[str], None] = '241808c91694'
branch_labels = None
depends_on = None


def upgrade() -> None:
  op.create_table(
      'devices',
      sa.Column('id', sa.String(length=36), nullable=False),
      sa.Column('user_uid', sa.String(length=6), nullable=False),
      sa.Column('device_id', sa.String(length=128), nullable=False),
      sa.Column('name', sa.String(length=255), nullable=True),
      sa.Column('is_master', sa.Boolean(), nullable=False),
      sa.Column('revoked', sa.Boolean(), nullable=False),
      sa.Column('last_seen', sa.DateTime(), nullable=False),
      sa.Column('created', sa.DateTime(), nullable=False),
      sa.ForeignKeyConstraint(['user_uid'], ['users.uid']),
      sa.PrimaryKeyConstraint('id'),
      sa.UniqueConstraint('user_uid', 'device_id', name='uq_devices_user_device'),
  )
  op.create_index('ix_devices_user_uid', 'devices', ['user_uid'])
  op.add_column('refresh_tokens', sa.Column('device_id', sa.String(length=128), nullable=True))
  op.create_index('ix_refresh_tokens_device_id', 'refresh_tokens', ['device_id'])


def downgrade() -> None:
  op.drop_index('ix_refresh_tokens_device_id', table_name='refresh_tokens')
  op.drop_column('refresh_tokens', 'device_id')
  op.drop_index('ix_devices_user_uid', table_name='devices')
  op.drop_table('devices')
