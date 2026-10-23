"""Backwards-compatible defaults and explicit current authority boundaries."""
import sqlalchemy as sa
from alembic import op

revision = '021_processing_guards'
down_revision = 'c0ab3227de0d'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('documents', 'processing_metadata', server_default=sa.text("'{}'::json"))
    op.alter_column('outbox_events', 'processing_attempts', server_default='0')
    op.create_check_constraint('ck_local_verification_authority', 'deposit_records',
                               "verification_status IN ('INSTITUTION_DECLARED','MANUALLY_REVIEWED','DISPUTED','UNAVAILABLE')")
    op.create_check_constraint('ck_no_synthetic_settlement', 'deposit_records',
                               "lifecycle_status IN ('RECORDED','ACTIVE','APPROACHING_MATURITY','MATURED','REPLACED')")
    op.create_check_constraint('ck_correction_status', 'extraction_corrections',
                               "status IN ('PROPOSED','CONFIRMED','REJECTED') AND page > 0")
    op.execute("""
      CREATE FUNCTION protect_correction_identity() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF OLD.status != 'PROPOSED' OR
          (NEW.document_id, NEW.field, NEW.value, NEW.page, NEW.bounds::text, NEW.quote, NEW.reason, NEW.maker)
          IS DISTINCT FROM
          (OLD.document_id, OLD.field, OLD.value, OLD.page, OLD.bounds::text, OLD.quote, OLD.reason, OLD.maker) THEN
          RAISE EXCEPTION 'Correction identity or decided transcription is immutable';
        END IF;
        RETURN NEW;
      END;
      $$;
      CREATE TRIGGER correction_identity BEFORE UPDATE ON extraction_corrections
      FOR EACH ROW EXECUTE FUNCTION protect_correction_identity();
    """)


def downgrade():
    op.execute('DROP TRIGGER correction_identity ON extraction_corrections')
    op.execute('DROP FUNCTION protect_correction_identity()')
    op.drop_constraint('ck_correction_status', 'extraction_corrections')
    op.drop_constraint('ck_no_synthetic_settlement', 'deposit_records')
    op.drop_constraint('ck_local_verification_authority', 'deposit_records')
    op.alter_column('outbox_events', 'processing_attempts', server_default=None)
    op.alter_column('documents', 'processing_metadata', server_default=None)
