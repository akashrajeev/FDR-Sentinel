"""Package only the built browser demo for a static Vercel deployment.

Run npm run build:demo --prefix apps/web first. No secrets, source uploads,
backend runtime, database dumps or user-uploaded documents enter this package.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'apps' / 'web' / 'dist-demo'


def package():
    if not (BUILD / 'index.html').is_file():
        raise SystemExit('Build the demo first: npm run build:demo --prefix apps/web')
    files = []
    for path in sorted(BUILD.rglob('*')):
        if path.is_dir():
            continue
        relative = path.relative_to(BUILD).as_posix()
        if path.is_symlink() or path.suffix not in {'.html', '.js', '.css', '.svg', '.png'}:
            raise SystemExit(f'Unexpected build artifact: {relative}')
        if relative not in {'index.html', 'favicon.svg', 'brand/fdr-sentinel-monogram-v1.png'} and not relative.startswith('assets/'):
            raise SystemExit(f'Unexpected build path: {relative}')
        files.append((relative, path.read_bytes()))
    config = {
        'version': 2,
        'framework': None,
        'buildCommand': None,
        'rewrites': [{'source': '/((?!assets/|brand/|favicon.svg|api/).*)', 'destination': '/index.html'}],
        'headers': [{'source': '/(.*)', 'headers': [
            {'key': 'X-Content-Type-Options', 'value': 'nosniff'},
            {'key': 'Referrer-Policy', 'value': 'strict-origin-when-cross-origin'},
        ]}],
    }
    files.append(('vercel.json', json.dumps(config, indent=2).encode()))
    digest = hashlib.sha256()
    for name, data in files:
        digest.update(name.encode() + b'\0' + data)
    target = ROOT / '.local' / 'vercel-demo' / digest.hexdigest()[:16]
    target.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, data in files:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        manifest.append({'file': name, 'size': len(data), 'sha': hashlib.sha1(data).hexdigest(),
                         'sha256': hashlib.sha256(data).hexdigest(), 'path': str(destination)})
    result = {'snapshot_sha256': digest.hexdigest(), 'directory': str(target), 'files': manifest}
    (target / 'manifest.local.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    package()
