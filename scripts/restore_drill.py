"""Consistent PostgreSQL snapshot + protected objects restored into isolated targets."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sentinel.config import settings
from sentinel.db import engine
from sentinel.storage import read_original, storage
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


def main():
    config = settings()
    source = make_url(config.database_url)
    if source.database not in ('sentinel', 'sentinel_test') or source.host not in ('localhost', '127.0.0.1', 'postgres'):
        raise RuntimeError('Restore drill is restricted to the dedicated local synthetic databases')
    suffix = uuid4().hex[:10]
    destination = 'sentinel_restore_' + suffix
    restored_bucket = 'sentinel-restore-' + suffix
    output = Path(__file__).resolve().parents[1] / '.local/backups' / suffix
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc)
    with engine().connect().execution_options(isolation_level='REPEATABLE READ') as connection:
        with connection.begin():
            snapshot = connection.scalar(text('SELECT pg_export_snapshot()'))
            tables = sorted(inspect(connection).get_table_names())
            quote = connection.dialect.identifier_preparer.quote
            counts = {name: connection.scalar(text(f'SELECT count(*) FROM {quote(name)}')) for name in tables}
            objects = connection.execute(text('SELECT id, object_key, sha256, processing_metadata FROM documents')).all()
            dump = subprocess.run(['docker', 'compose', 'exec', '-T', 'postgres', 'pg_dump', '-U', 'sentinel',
                                   '-d', source.database, '--snapshot', snapshot, '-Fc'],
                                  check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90).stdout
            (output / 'database.dump').write_bytes(dump)
    admin = create_engine(source.set(database='postgres'), isolation_level='AUTOCOMMIT')
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE {destination}'))  # generated alphanumeric name, never overwrites
    subprocess.run(['docker', 'compose', 'exec', '-T', 'postgres', 'pg_restore', '-U', 'sentinel',
                    '-d', destination, '--no-owner', '--no-privileges'], input=dump,
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    target = create_engine(source.set(database=destination))
    with target.connect() as connection:
        quote = connection.dialect.identifier_preparer.quote
        restored_counts = {name: connection.scalar(text(f'SELECT count(*) FROM {quote(name)}')) for name in tables}
        assert counts == restored_counts, 'Snapshot row counts differ after restore'
        assert connection.scalar(text('SELECT version_num FROM alembic_version'))
    storage().make_bucket(restored_bucket)
    object_count = 0
    for document_id, key, sha, metadata in objects:
        references = [(key, sha, 'application/pdf')]
        references += [(f'previews/{document_id}/{page}.png', digest, 'image/png')
                       for page, digest in metadata.get('preview_hashes', {}).items()]
        for object_key, expected, mime in references:
            data = read_original(object_key)
            assert hashlib.sha256(data).hexdigest() == expected
            import io
            storage().put_object(restored_bucket, object_key, io.BytesIO(data), len(data), content_type=mime)
            response = storage().get_object(restored_bucket, object_key)
            try:
                assert hashlib.sha256(response.read()).hexdigest() == expected
            finally:
                response.close()
                response.release_conn()
            object_count += 1
    report = {'mode': 'LOCAL_SYNTHETIC_RESTORE_DRILL', 'source_database': source.database,
              'restored_database': destination, 'restored_private_bucket': restored_bucket,
              'tables_verified': len(tables), 'rows_verified': sum(counts.values()),
              'audit_rows_verified': counts.get('audit_events'), 'object_hashes_verified': object_count,
              'database_dump_sha256': hashlib.sha256(dump).hexdigest(),
              'elapsed_seconds': round((datetime.now(timezone.utc) - started).total_seconds(), 2),
              'source_untouched': True, 'limits': 'Local snapshot restore; no production PITR/RPO/RTO or encrypted off-site backup qualification'}
    (output / 'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    target.dispose()
    admin.dispose()


if __name__ == '__main__':
    main()
