"""Local operator provisioning: migration owner and application runtime are separate."""
import os

from psycopg import sql
from sentinel.db import engine

MUTABLE = ('deposit_records', 'documents', 'outbox_events', 'release_cases', 'holds',
           'instrument_relationships', 'extraction_corrections', 'discrepancies',
           'integration_requests', 'notification_deliveries')


def provision():
    password = os.environ.get('RUNTIME_DB_PASSWORD', '')
    if len(password) < 32:
        raise RuntimeError('Run bootstrap to generate the runtime database credential')
    with engine().begin() as connection:
        cursor = connection.connection.driver_connection.cursor()
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'sentinel_runtime'")
        if not cursor.fetchone():
            cursor.execute('CREATE ROLE sentinel_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION')
        cursor.execute(sql.SQL('ALTER ROLE sentinel_runtime PASSWORD {}').format(sql.Literal(password)))
        cursor.execute('SELECT current_database()')
        database = cursor.fetchone()[0]
        cursor.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO sentinel_runtime').format(sql.Identifier(database)))
        cursor.execute('GRANT USAGE ON SCHEMA public TO sentinel_runtime')
        cursor.execute('REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM sentinel_runtime')
        cursor.execute('GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO sentinel_runtime')
        cursor.execute('REVOKE INSERT ON alembic_version FROM sentinel_runtime')
        for table in MUTABLE:
            cursor.execute(sql.SQL('GRANT UPDATE ON TABLE {} TO sentinel_runtime').format(sql.Identifier(table)))
        cursor.execute('GRANT UPDATE(registry_status) ON institutions TO sentinel_runtime')
        cursor.execute("""
          CREATE OR REPLACE FUNCTION guard_runtime_scope_grants() RETURNS trigger LANGUAGE plpgsql AS $$
          BEGIN
            IF current_user = 'sentinel_runtime' AND (NEW.role != 'MAKER' OR NEW.scope_type != 'INSTITUTION'
              OR NOT EXISTS (SELECT 1 FROM institutions WHERE id = NEW.scope_id AND owner = NEW.subject)) THEN
              RAISE EXCEPTION 'Privileged scope grants require operator provisioning';
            END IF;
            RETURN NEW;
          END;
          $$;
          DROP TRIGGER IF EXISTS runtime_scope_grants ON role_bindings;
          CREATE TRIGGER runtime_scope_grants BEFORE INSERT ON role_bindings
          FOR EACH ROW EXECUTE FUNCTION guard_runtime_scope_grants();
        """)
        cursor.close()


if __name__ == '__main__':
    provision()
    print('Restricted runtime role provisioned; no DDL, deletion, privileged scope grants or history updates.')
