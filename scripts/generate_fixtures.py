"""Create synthetic PDF fixtures in ignored .local/fixtures, with separate labels."""
from pathlib import Path

from sentinel.synthetic import fixture_pdf

target = Path(__file__).resolve().parents[1] / '.local/fixtures'
target.mkdir(parents=True, exist_ok=True)
for name in ('digital-a', 'digital-b', 'scanned', 'adversarial'):
    (target / f'{name}.pdf').write_bytes(fixture_pdf(name))
print('Created four visibly synthetic PDFs in ignored .local/fixtures.')
