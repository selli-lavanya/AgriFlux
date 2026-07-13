"""add_locking_and_infraction_fields

Revision ID: f09d85387690
Revises: bc4ddd1e391e
Create Date: 2026-06-14 01:14:56.854885

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f09d85387690'
down_revision: Union[str, Sequence[str], None] = 'bc4ddd1e391e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Update machines and labour_teams tables
    op.add_column('machines', sa.Column('last_infraction_date', sa.Date(), nullable=True))
    op.add_column('labour_teams', sa.Column('last_infraction_date', sa.Date(), nullable=True))

    # 2. Update availability_calendar table
    op.add_column('availability_calendar', sa.Column('temp_lock_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('availability_calendar', sa.Column('locked_by_request_id', sa.Integer(), nullable=True))

    # 3. Apply performance indexes
    op.create_index('ix_assignments_scheduled_date_status', 'assignments', ['scheduled_date', 'status'])
    op.create_index('ix_availability_calendar_date_status', 'availability_calendar', ['date', 'status'])
    op.create_index('ix_requests_status_priority_score', 'requests', ['status', 'priority_score'])

    # 4. Perform uppercase data backfill updates
    op.execute("UPDATE assignments SET status = UPPER(status) WHERE status IS NOT NULL")
    op.execute("UPDATE requests SET status = UPPER(status::text)::requeststatus WHERE status IS NOT NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Revert uppercase status backfills for assignments
    op.execute("UPDATE assignments SET status = LOWER(status) WHERE status IS NOT NULL")

    # 2. Drop performance indexes
    op.drop_index('ix_requests_status_priority_score', table_name='requests')
    op.drop_index('ix_availability_calendar_date_status', table_name='availability_calendar')
    op.drop_index('ix_assignments_scheduled_date_status', table_name='assignments')

    # 3. Drop columns from availability_calendar
    op.drop_column('availability_calendar', 'locked_by_request_id')
    op.drop_column('availability_calendar', 'temp_lock_until')

    # 4. Drop columns from machines and labour_teams
    op.drop_column('labour_teams', 'last_infraction_date')
    op.drop_column('machines', 'last_infraction_date')
