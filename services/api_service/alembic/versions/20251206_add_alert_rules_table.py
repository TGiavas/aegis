"""add alert_rules table

Revision ID: a1b2c3d4e5f6
Revises: 372ab04c6328
Create Date: 2025-12-06 12:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '372ab04c6328'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create alert_rules table
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('field', sa.String(length=50), nullable=False),
        sa.Column('operator', sa.String(length=10), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('alert_level', sa.String(length=20), nullable=False),
        sa.Column('message_template', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Index for fetching rules by project
    op.create_index('ix_alert_rules_project_id', 'alert_rules', ['project_id'], unique=False)
    
    # Unique constraint for project-specific rules (name + project_id)
    op.create_index(
        'uq_alert_rules_name_project',
        'alert_rules',
        ['name', 'project_id'],
        unique=True,
        postgresql_where=sa.text('project_id IS NOT NULL'),
    )
    
    # Unique constraint for global rules (name only, where project_id IS NULL)
    op.create_index(
        'uq_alert_rules_name_global',
        'alert_rules',
        ['name'],
        unique=True,
        postgresql_where=sa.text('project_id IS NULL'),
    )
    
    # Seed default global rules (migrating from hardcoded rules)
    op.execute("""
        INSERT INTO alert_rules (name, project_id, field, operator, value, alert_level, message_template, enabled)
        VALUES 
            ('critical_event', NULL, 'severity', '==', 'CRITICAL', 'HIGH', 
             'Critical event from {source}: {event_type}', true),
            ('high_latency', NULL, 'latency_ms', '>', '5000', 'MEDIUM', 
             'High latency detected: {latency_ms}ms from {source}', true),
            ('error_event', NULL, 'severity', '==', 'ERROR', 'MEDIUM', 
             'Error event from {source}: {event_type}', true)
    """)


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index('uq_alert_rules_name_global', table_name='alert_rules')
    op.drop_index('uq_alert_rules_name_project', table_name='alert_rules')
    op.drop_index('ix_alert_rules_project_id', table_name='alert_rules')
    op.drop_table('alert_rules')

