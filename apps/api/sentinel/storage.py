import io
import socket
import struct
from functools import lru_cache

from minio import Minio
from urllib3 import PoolManager, Timeout

from sentinel.config import settings


@lru_cache
def storage():
    c = settings()
    return Minio(c.s3_endpoint, access_key=c.s3_access_key, secret_key=c.s3_secret_key,
                 secure=c.s3_secure, http_client=PoolManager(timeout=Timeout(connect=3, read=10), retries=0))


def put_original(key: str, data: bytes):
    storage().put_object(settings().s3_bucket, key, io.BytesIO(data), len(data), content_type='application/pdf')


def read_original(key: str) -> bytes:
    response = storage().get_object(settings().s3_bucket, key)
    try:
        return response.read(settings().max_upload_bytes + 1)
    finally:
        response.close()
        response.release_conn()


def scan_bytes(data: bytes) -> str:
    """ClamAV INSTREAM; actual scanner, never a success fallback."""
    c = settings()
    with socket.create_connection((c.clamav_host, c.clamav_port), timeout=10) as conn:
        conn.settimeout(45)
        conn.sendall(b'zINSTREAM\0')
        for offset in range(0, len(data), 64 * 1024):
            chunk = data[offset:offset + 64 * 1024]
            conn.sendall(struct.pack('!I', len(chunk)) + chunk)
        conn.sendall(struct.pack('!I', 0))
        result = b''
        while b'\0' not in result and len(result) < 1024:
            part = conn.recv(1024)
            if not part:
                break
            result += part
    message = result.rstrip(b'\0').decode('utf-8', errors='replace')
    if message.endswith(' FOUND'):
        return 'INFECTED'
    if message == 'stream: OK':
        return 'CLEAN'
    raise RuntimeError('Scanner returned an indeterminate result')
