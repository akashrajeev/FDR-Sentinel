"""Independent sandbox schema and durable integration/delivery work.

Revision ID: 52a01026
Revises: 339cf1735fc9
"""
import sqlalchemy as sa
from alembic import op

revision = '52a01026'
down_revision = '339cf1735fc9'
branch_labels = depends_on = None


def upgrade():
    op.execute('CREATE SCHEMA sandbox')
    op.execute('CREATE TABLE sandbox.registry (id varchar(64) PRIMARY KEY, data jsonb NOT NULL)')
    op.execute("CREATE TABLE sandbox.ledger (id varchar(64) PRIMARY KEY, data jsonb NOT NULL, "
               "release_case_id varchar(36), CHECK (id LIKE 'SB-%'))")
    op.execute("CREATE TABLE sandbox.requests (id varchar(36) PRIMARY KEY, client_key varchar(128) UNIQUE NOT NULL, "
               "fingerprint varchar(64) NOT NULL, payload jsonb NOT NULL, result jsonb NOT NULL, "
               "ready_at timestamptz NOT NULL, fault_remaining integer NOT NULL DEFAULT 0, "
               "created_at timestamptz NOT NULL DEFAULT now())")
    op.create_table('integration_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('institution_id', sa.String(36), sa.ForeignKey('institutions.id'), nullable=False),
        sa.Column('deposit_id', sa.String(36), sa.ForeignKey('deposit_records.id')),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('release_cases.id')),
        sa.Column('operation', sa.String(24), nullable=False), sa.Column('state', sa.String(20), nullable=False),
        sa.Column('requested_by', sa.String(128), nullable=False), sa.Column('input_revision', sa.Integer, nullable=False),
        sa.Column('payload', sa.JSON, nullable=False), sa.Column('trace_context', sa.JSON, nullable=False),
        sa.Column('remote_id', sa.String(36)), sa.Column('attempts', sa.Integer, nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=False), sa.Column('last_error', sa.String(80)),
        sa.Column('result', sa.JSON), sa.Column('signature', sa.String(64)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint("operation IN ('BANK_VERIFY','REGISTRY_LOOKUP','CASE_SYNC','RELEASE_ACK')"),
        sa.CheckConstraint("state IN ('PENDING','WAITING','SUCCEEDED','STALE','DEAD_LETTER')"))
    for column in ('institution_id', 'deposit_id', 'case_id', 'state', 'next_attempt_at'):
        op.create_index('ix_integration_requests_' + column, 'integration_requests', [column])
    op.create_table('notification_deliveries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('notification_id', sa.String(36), sa.ForeignKey('notifications.id'), nullable=False, unique=True),
        sa.Column('state', sa.String(20), nullable=False), sa.Column('attempts', sa.Integer, nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=False), sa.Column('last_error', sa.String(80)),
        sa.Column('message_id', sa.String(128), unique=True, nullable=False), sa.Column('delivered_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint("state IN ('PENDING','SENT','DEAD_LETTER')"))
    for constraint in sa.inspect(op.get_bind()).get_check_constraints('role_bindings'):
        if 'MAKER' in constraint['sqltext']:
            op.drop_constraint(constraint['name'], 'role_bindings')
    op.create_check_constraint('ck_role_bindings_roles', 'role_bindings',
        "role IN ('MAKER','REVIEWER','AUDITOR','CLEARANCE','APPROVER','ISSUER','OPERATOR')")


def downgrade():
    raise RuntimeError('Forward migration only; preserve sandbox/integration evidence')
