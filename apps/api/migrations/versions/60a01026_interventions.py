"""Operational product policies and source-resolved follow-up episodes."""
import sqlalchemy as sa
from alembic import op

revision = '60a01026'
down_revision = '52b01026'
branch_labels = depends_on = None


def upgrade():
    op.alter_column('notifications', 'deposit_id', nullable=True)
    op.create_table('operations_policies',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('institution_id', sa.String(36), sa.ForeignKey('institutions.id'), nullable=False),
        sa.Column('revision', sa.Integer, nullable=False), sa.Column('configuration', sa.JSON, nullable=False),
        sa.Column('actor', sa.String(128), nullable=False), sa.Column('reason', sa.String(2000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('institution_id', 'revision'))
    op.create_index('ix_operations_policies_institution_id', 'operations_policies', ['institution_id'])
    op.execute('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON operations_policies '
               'FOR EACH ROW EXECUTE FUNCTION reject_history_change()')
    op.create_table('interventions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('institution_id', sa.String(36), sa.ForeignKey('institutions.id'), nullable=False),
        sa.Column('deposit_id', sa.String(36), sa.ForeignKey('deposit_records.id')),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('release_cases.id')),
        sa.Column('condition_key', sa.String(160), nullable=False), sa.Column('episode', sa.Integer, nullable=False),
        sa.Column('category', sa.String(40), nullable=False), sa.Column('state', sa.String(16), nullable=False),
        sa.Column('source_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('policy_revision', sa.Integer, nullable=False), sa.Column('detail', sa.JSON, nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True)), sa.Column('acknowledged_by', sa.String(128)),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True)), sa.Column('acknowledgement', sa.String(2000)),
        sa.UniqueConstraint('institution_id', 'condition_key', 'episode'),
        sa.CheckConstraint("state IN ('OPEN','RESOLVED')"))
    for name in ('institution_id', 'deposit_id', 'case_id', 'category', 'state', 'due_at'):
        op.create_index('ix_interventions_' + name, 'interventions', [name])
    op.execute("""
      CREATE FUNCTION guard_intervention() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF OLD.state='RESOLVED' OR (NEW.id,NEW.institution_id,NEW.deposit_id,NEW.case_id,
          NEW.condition_key,NEW.episode,NEW.category,NEW.source_at) IS DISTINCT FROM
          (OLD.id,OLD.institution_id,OLD.deposit_id,OLD.case_id,OLD.condition_key,OLD.episode,OLD.category,OLD.source_at)
        THEN RAISE EXCEPTION 'Intervention identity/resolved history is immutable'; END IF;
        RETURN NEW;
      END; $$;
      CREATE TRIGGER intervention_identity BEFORE UPDATE ON interventions
      FOR EACH ROW EXECUTE FUNCTION guard_intervention();
      CREATE UNIQUE INDEX one_open_intervention ON interventions(institution_id,condition_key) WHERE state='OPEN';
    """)


def downgrade():
    op.drop_table('interventions')
    op.execute('DROP FUNCTION guard_intervention()')
    op.drop_table('operations_policies')
