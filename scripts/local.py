"""Run a Python command against loopback-only Compose services (no secret echo)."""
import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
environment = dict(os.environ)
environment.update({k: v for k, v in dotenv_values(root / '.env').items() if v is not None})
arguments = sys.argv[1:]
database = 'sentinel'
if arguments and arguments[0] == '--test':
    database = 'sentinel_test'
    arguments = arguments[1:]
environment.update({
    'DATABASE_URL': f"postgresql+psycopg://sentinel:{environment['POSTGRES_PASSWORD']}@localhost:55432/{database}",
    'REDIS_URL': 'redis://localhost:56379/0', 'S3_ENDPOINT': 'localhost:59000',
    'OIDC_JWKS_URL': 'http://localhost:8081/realms/sentinel/protocol/openid-connect/certs',
    'CLAMAV_HOST': 'localhost', 'CLAMAV_PORT': '53310', 'TEST_SERVICES': '1',
    'TEST_OIDC_URL': 'http://localhost:8081/realms/sentinel/protocol/openid-connect/token',
    'BROWSER_CHANNEL': os.getenv('BROWSER_CHANNEL', 'chrome'),
})
raise SystemExit(subprocess.call([sys.executable, *arguments], env=environment, cwd=root))
