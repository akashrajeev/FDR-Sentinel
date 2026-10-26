"""Clean source export, new credentials and fresh isolated volumes; preserves the live stack."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', help='Optional recent signed Debian snapshot; signature/expiry checks stay enabled')
    args = parser.parse_args()
    if args.snapshot and not re.fullmatch(r'20\d{6}T\d{6}Z', args.snapshot):
        parser.error('snapshot must be YYYYMMDDTHHMMSSZ')
    root = Path(__file__).resolve().parents[1]
    suffix = uuid4().hex[:8]
    destination = root / '.local' / ('fresh-acceptance-' + suffix)
    destination.mkdir(parents=True, exist_ok=False)
    project = 'sentinel-acceptance-' + suffix
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root)
    tree_hash = hashlib.sha256()
    count = 0
    for name in sorted(set(names.decode().split('\0')) - {''}):
        source = (root / name).resolve()
        if not source.is_relative_to(root) or source.is_symlink():
            raise RuntimeError('Refusing source outside the project')
        if not source.is_file():
            continue
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        tree_hash.update(name.encode() + b'\0' + source.read_bytes())
        count += 1
    subprocess.run([sys.executable, 'scripts/bootstrap.py'], cwd=destination, check=True, capture_output=True)
    environment = {**os.environ, **{k: v for k, v in dotenv_values(destination / '.env').items() if v is not None}}
    environment.pop('COMPOSE_PROFILES', None)
    environment['AI_ASSIST_ENABLED'] = 'false'
    # Every service is on its own network/volumes, with no host ports. The fresh backend
    # suite reaches its own IdP/sandbox/mailbox through real internal network APIs.
    app_services = ('api', 'worker', 'beat', 'migrate', 'storage-init', 'test', 'sandbox', 'idp-init')
    lines = ['services:']
    for service in app_services:
        lines += [f'  {service}:', f'    image: fdr-sentinel-acceptance-api:{suffix}']
        if service == 'sandbox':
            lines += ['    ports: !reset []']
    lines += ['  web:', f'    image: fdr-sentinel-acceptance-web:{suffix}', '    ports: !reset []']
    for service in ('postgres', 'redis', 'objectstore', 'keycloak', 'clamav', 'mailpit', 'ollama'):
        lines += [f'  {service}:', '    ports: !reset []']
    override = destination / 'isolated.compose.yml'
    override.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    command = ['docker', 'compose', '--project-directory', str(destination), '-p', project,
               '-f', str(destination / 'docker-compose.yml'), '-f', str(override)]
    started = time.monotonic()
    report = {'project': project, 'source_files': count, 'source_tree_sha256': tree_hash.hexdigest(),
              'isolated_directory': str(destination), 'new_credentials': True, 'host_ports': [],
              'fresh_application_volumes': True, 'live_stack_untouched': True}

    def run(label, arguments):
        print(label + ' (isolated project ' + project + ')', flush=True)
        with (destination / (label + '.log')).open('wb') as output:
            result = subprocess.run(command + arguments, cwd=destination, env=environment, stdout=output,
                                    stderr=subprocess.STDOUT, timeout=900)
        if result.returncode:
            raise RuntimeError(f'{label} failed; inspect ignored {destination / (label + ".log")}')

    try:
        run('config', ['config', '--quiet'])
        build_args = ['--build-arg', 'DEBIAN_SNAPSHOT=' + args.snapshot] if args.snapshot else []
        run('build', ['build', *build_args, 'api', 'web'])
        run('startup', ['up', '-d', '--no-build'])
        run('backend-tests', ['--profile', 'test', 'run', '--rm', '--no-deps', 'test'])
        run('health', ['exec', '-T', 'api', 'python', '-c',
            "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/health/ready'); "
            "assert r.status_code==200 and r.json()['processing']=='available',r.text; print(r.json())"])
        result_text = (destination / 'backend-tests.log').read_text(encoding='utf-8', errors='replace')
        summary = re.findall(r'\d+ passed[^\n]*', result_text)
        report.update(status='PASSED', backend_summary=summary[-1] if summary else 'Exit status 0',
                      elapsed_seconds=round(time.monotonic() - started, 2),
                      limit='Fresh isolated source export/backend network acceptance; browser suite runs separately against the live demo')
    finally:
        # Stops only this generated project; no volume resets, recursive deletes or live-stack operations.
        with (destination / 'stop.log').open('wb') as output:
            subprocess.run(command + ['stop'], cwd=destination, env=environment, stdout=output,
                           stderr=subprocess.STDOUT, timeout=120)
        report.setdefault('status', 'FAILED')
        (destination / 'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
