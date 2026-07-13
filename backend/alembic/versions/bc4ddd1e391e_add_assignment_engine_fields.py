"""add_assignment_engine_fields

Revision ID: bc4ddd1e391e
Revises: e6588038b774
Create Date: 2026-06-14 00:15:09.973463

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc4ddd1e391e'
down_revision: Union[str, Sequence[str], None] = 'e6588038b774'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Update users table
    op.add_column('users', sa.Column('late_cancel_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('no_show_count', sa.Integer(), nullable=False, server_default='0'))

    # 2. Update machines table
    op.add_column('machines', sa.Column('status', sa.String(), nullable=False, server_default='active'))
    op.add_column('machines', sa.Column('cooldown_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('machines', sa.Column('daily_failure_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('machines', sa.Column('daily_no_show_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('machines', sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('machines', sa.Column('no_show_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('machines', sa.Column('late_cancel_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('machines', sa.Column('penalty_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('machines', sa.Column('avg_speed', sa.Float(), nullable=False, server_default='40.0'))
    op.add_column('machines', sa.Column('lat', sa.Float(), nullable=True))
    op.add_column('machines', sa.Column('lng', sa.Float(), nullable=True))
    op.add_column('machines', sa.Column('cost_per_hour', sa.Float(), nullable=False, server_default='150.0'))

    # 3. Update labour_teams table
    op.add_column('labour_teams', sa.Column('status', sa.String(), nullable=False, server_default='active'))
    op.add_column('labour_teams', sa.Column('cooldown_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('labour_teams', sa.Column('daily_failure_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('labour_teams', sa.Column('daily_no_show_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('labour_teams', sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('labour_teams', sa.Column('no_show_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('labour_teams', sa.Column('late_cancel_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('labour_teams', sa.Column('penalty_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('labour_teams', sa.Column('avg_speed', sa.Float(), nullable=False, server_default='40.0'))
    op.add_column('labour_teams', sa.Column('lat', sa.Float(), nullable=True))
    op.add_column('labour_teams', sa.Column('lng', sa.Float(), nullable=True))
    op.add_column('labour_teams', sa.Column('cost_per_worker_per_hour', sa.Float(), nullable=False, server_default='50.0'))

    # 4. Update requests table
    # Add 'UNSERVICED' value to requeststatus enum
    op.execute("ALTER TYPE requeststatus ADD VALUE 'UNSERVICED'")

    op.add_column('requests', sa.Column('start_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('requests', sa.Column('end_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('requests', sa.Column('duration', sa.Integer(), nullable=True))
    op.add_column('requests', sa.Column('max_budget_per_hour', sa.Float(), nullable=True))
    op.add_column('requests', sa.Column('max_total_budget', sa.Float(), nullable=True))
    op.add_column('requests', sa.Column('work_size', sa.Float(), nullable=True))
    op.add_column('requests', sa.Column('quantity', sa.Integer(), nullable=True))
    op.add_column('requests', sa.Column('workers_required', sa.Integer(), nullable=True))
    op.add_column('requests', sa.Column('partial_allowed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('requests', sa.Column('reassignment_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('requests', sa.Column('estimated_cost', sa.Float(), nullable=True))

    # 5. Update assignments table
    op.add_column('assignments', sa.Column('start_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('assignments', sa.Column('end_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('assignments', sa.Column('duration', sa.Integer(), nullable=True))
    op.add_column('assignments', sa.Column('workers_assigned', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('assignments', sa.Column('final_cost', sa.Float(), nullable=True))
    op.add_column('assignments', sa.Column('cancelled_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_assignments_cancelled_by', 'assignments', 'users', ['cancelled_by_id'], ['id'])
    op.add_column('assignments', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('assignments', sa.Column('cancellation_reason', sa.String(), nullable=True))
    op.add_column('assignments', sa.Column('is_late_cancel', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('assignments', sa.Column('failure_logged', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('assignments', 'failure_logged')
    op.drop_column('assignments', 'is_late_cancel')
    op.drop_column('assignments', 'cancellation_reason')
    op.drop_column('assignments', 'cancelled_at')
    op.drop_constraint('fk_assignments_cancelled_by', 'assignments', type_='foreignkey')
    op.drop_column('assignments', 'cancelled_by_id')
    op.drop_column('assignments', 'final_cost')
    op.drop_column('assignments', 'workers_assigned')
    op.drop_column('assignments', 'duration')
    op.drop_column('assignments', 'end_time')
    op.drop_column('assignments', 'start_time')

    op.drop_column('requests', 'estimated_cost')
    op.drop_column('requests', 'reassignment_attempts')
    op.drop_column('requests', 'partial_allowed')
    op.drop_column('requests', 'workers_required')
    op.drop_column('requests', 'quantity')
    op.drop_column('requests', 'work_size')
    op.drop_column('requests', 'max_total_budget')
    op.drop_column('requests', 'max_budget_per_hour')
    op.drop_column('requests', 'duration')
    op.drop_column('requests', 'end_time')
    op.drop_column('requests', 'start_time')

    op.drop_column('labour_teams', 'cost_per_worker_per_hour')
    op.drop_column('labour_teams', 'lng')
    op.drop_column('labour_teams', 'lat')
    op.drop_column('labour_teams', 'avg_speed')
    op.drop_column('labour_teams', 'penalty_count')
    op.drop_column('labour_teams', 'late_cancel_count')
    op.drop_column('labour_teams', 'no_show_count')
    op.drop_column('labour_teams', 'failure_count')
    op.drop_column('labour_teams', 'daily_no_show_count')
    op.drop_column('labour_teams', 'daily_failure_count')
    op.drop_column('labour_teams', 'cooldown_until')
    op.drop_column('labour_teams', 'status')

    op.drop_column('machines', 'cost_per_hour')
    op.drop_column('machines', 'lng')
    op.drop_column('machines', 'lat')
    op.drop_column('machines', 'avg_speed')
    op.drop_column('machines', 'penalty_count')
    op.drop_column('machines', 'late_cancel_count')
    op.drop_column('machines', 'no_show_count')
    op.drop_column('machines', 'failure_count')
    op.drop_column('machines', 'daily_no_show_count')
    op.drop_column('machines', 'daily_failure_count')
    op.drop_column('machines', 'cooldown_until')
    op.drop_column('machines', 'status')

    op.drop_column('users', 'no_show_count')
    op.drop_column('users', 'late_cancel_count')
