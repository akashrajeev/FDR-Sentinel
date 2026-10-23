"""Protect clearance history and immutable document identities."""
from alembic import op

revision = '020_history_guards'
down_revision = '1ea39bee04cb'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON clearance_decisions '
               'FOR EACH ROW EXECUTE FUNCTION reject_history_change()')
    op.execute("""
      CREATE FUNCTION protect_original_identity() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF (NEW.object_key, NEW.sha256, NEW.size, NEW.deposit_id, NEW.institution_id, NEW.uploader,
            NEW.category, NEW.supersedes_id, NEW.release_case_id)
           IS DISTINCT FROM
           (OLD.object_key, OLD.sha256, OLD.size, OLD.deposit_id, OLD.institution_id, OLD.uploader,
            OLD.category, OLD.supersedes_id, OLD.release_case_id) THEN
          RAISE EXCEPTION 'Original document identity is immutable';
        END IF;
        RETURN NEW;
      END;
      $$;
      CREATE TRIGGER immutable_original BEFORE UPDATE ON documents
      FOR EACH ROW EXECUTE FUNCTION protect_original_identity();
    """)


def downgrade():
    op.execute('DROP TRIGGER immutable_original ON documents')
    op.execute('DROP FUNCTION protect_original_identity()')
    op.execute('DROP TRIGGER immutable_history ON clearance_decisions')
