"""One executed synthetic local-model sample; this is not a model quality benchmark."""
import json
import os
import time

import httpx
from sentinel.config import settings
from sentinel.local_ai import propose_fields

base_url = os.getenv('SMOKE_AI_URL', 'http://127.0.0.1:11434')
model = settings().ai_model
pages = [{'page': 1, 'text': 'SYNTHETIC FIXTURE. Amount paise: 350000000. '
          'Issue date: 2016-10-01. Maturity date: 2026-10-01.'}]
expected = {('amount_paise', '350000000'), ('issue_date', '2016-10-01'), ('maturity_date', '2026-10-01')}
started = time.perf_counter()
proposals, rejected = propose_fields(pages, base_url=base_url)
models = httpx.get(base_url.rstrip('/') + '/api/tags', timeout=5).json()['models']
model_digest = next((m.get('digest') for m in models if m['name'] == model), None)
observed = {(p['field'], p['value']) for p in proposals}
print(json.dumps({'samples': 1, 'expected_fields': 3, 'observed_fields': len(observed),
                  'correct_fields': len(observed & expected), 'unsupported_proposals_rejected': rejected,
                  'model': model, 'observed_model_digest': model_digest,
                  'original_model_quotes_validated': sum(p['model_quote_validated'] for p in proposals),
                  'source_relinked_fields': len(proposals), 'elapsed_seconds': round(time.perf_counter() - started, 3),
                  'proposals': proposals,
                  'limitations': 'One tiny synthetic sample; quotes independently relinked; no authenticity/production accuracy claim; human confirmation mandatory.'}, indent=2))
