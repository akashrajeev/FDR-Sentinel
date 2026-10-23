import json
from pathlib import Path

from sentinel.main import app

target = Path(__file__).resolve().parents[1] / 'openapi' / 'openapi.json'
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(app.openapi(), indent=2) + '\n', encoding='utf-8')
print('Exported API schema; run npm run contracts --prefix apps/web.')
