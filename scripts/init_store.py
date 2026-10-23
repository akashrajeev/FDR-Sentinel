import time

from sentinel.config import settings
from sentinel.storage import storage

for attempt in range(60):
    try:
        if not storage().bucket_exists(settings().s3_bucket):
            storage().make_bucket(settings().s3_bucket)
        break
    except Exception:
        if attempt == 59:
            raise
        time.sleep(2)
print('Private bucket initialized; no anonymous policy.')
