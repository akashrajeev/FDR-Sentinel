"""Owner-only grants and independent immutable fictional registry/ledger fixtures."""
import json
import os

from psycopg import sql
from sentinel.db import engine


def provision():
    password = os.environ.get('SANDBOX_DB_PASSWORD', '')
    if len(password) < 32:
        raise RuntimeError('Bootstrap must generate the sandbox database credential')
    with engine().begin() as connection:
        cursor = connection.connection.driver_connection.cursor()
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='sentinel_sandbox'")
        if not cursor.fetchone():
            cursor.execute('CREATE ROLE sentinel_sandbox LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION')
        cursor.execute(sql.SQL('ALTER ROLE sentinel_sandbox PASSWORD {}').format(sql.Literal(password)))
        cursor.execute('GRANT USAGE ON SCHEMA sandbox TO sentinel_sandbox')
        cursor.execute('GRANT SELECT,INSERT ON ALL TABLES IN SCHEMA sandbox TO sentinel_sandbox')
        cursor.execute('REVOKE UPDATE ON sandbox.ledger,sandbox.requests FROM sentinel_sandbox')
        cursor.execute('GRANT UPDATE(release_case_id) ON sandbox.ledger TO sentinel_sandbox')
        cursor.execute('GRANT UPDATE(fault_remaining) ON sandbox.requests TO sentinel_sandbox')
        cursor.execute('REVOKE ALL ON SCHEMA sandbox FROM sentinel_runtime')
        registry = {'id': 'SYNTHETIC-001', 'legal_name': 'Sentinel Institute of Technology (Synthetic)',
                    'programme': 'ENGINEERING_UG', 'governance': 'PRIVATE', 'approval_from': '2024-07-01',
                    'approval_until': '2027-06-30', 'approval_status': 'ACTIVE'}
        cursor.execute('INSERT INTO sandbox.registry(id,data) VALUES (%s,%s::jsonb) ON CONFLICT DO NOTHING',
                       (registry['id'], json.dumps(registry)))
        for identity, suffix, issue, maturity, deposited, kind, status in (
            ('SB-FDR-001', '0001', '2016-10-01', '2026-10-01', None, 'FDR', 'ACTIVE'),
            ('SB-FDR-RENEWAL', '0002', '2026-10-01', '2036-10-01', None, 'FDR', 'ACTIVE'),
            ('SB-FDR-HOLD', '9001', '2016-10-01', '2026-10-01', None, 'FDR', 'HOLD'),
            ('SB-RTGS-001', '1001', None, None, '2016-10-01', 'RTGS', 'ACTIVE')):
            row = {'id': identity, 'institution_external_id': 'SYNTHETIC-001', 'bank_code': 'SYN-BANK',
                   'reference_last4': suffix, 'deposit_type': kind, 'amount_paise': 350000000,
                   'issue_date': issue, 'maturity_date': maturity, 'deposited_on': deposited, 'status': status}
            cursor.execute('INSERT INTO sandbox.ledger(id,data) VALUES (%s,%s::jsonb) ON CONFLICT DO NOTHING',
                           (identity, json.dumps(row)))
        cursor.close()


if __name__ == '__main__':
    provision()
    print('Independent synthetic sandbox schema/role and immutable example fixtures provisioned.')
