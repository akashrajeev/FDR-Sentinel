"""Cancel source-resolved or no-longer-authorized operational delivery."""
from alembic import op

revision = '60b01026'
down_revision = '60a01026'
branch_labels = depends_on = None


def upgrade():
    op.execute('ALTER TABLE notification_deliveries DROP CONSTRAINT notification_deliveries_state_check')
    op.create_check_constraint('notification_deliveries_state_check', 'notification_deliveries',
                              "state IN ('PENDING','SENT','DEAD_LETTER','CANCELLED')")


def downgrade():
    raise RuntimeError('Retain cancellation history; use forward-only operational migrations')
