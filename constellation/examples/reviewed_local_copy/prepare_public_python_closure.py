#!/usr/bin/env python3
"""Build the bounded, isolated public Python closure for reviewed local-copy.

The one permitted network transition is the explicit wheel download.  It is
followed by a generated, hash-pinned lock and every installation is offline.
This tool has no provider, grant, or executor command.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile


SWITCHYARD_REVISION = '1c82e719cf358728d0262ae11138fb13fefe0cae'
MAUDE_REVISION = '0d5b6c91102b1088818d0493c687f9f23db7684e'
ALLOCATION_LIMIT = 512 * 1024 * 1024
# jsonschema 4.10.3's declared ``format`` extra, plus the exact build tools.
WHEEL_REQUIREMENTS = (
    'arrow==1.3.0', 'attrs==23.2.0', 'fqdn==1.5.1', 'idna==3.7',
    'isoduration==20.11.0', 'jsonpointer==3.0.0', 'jsonschema==4.10.3',
    'python-dateutil==2.9.0.post0', 'pyrsistent==0.20.0',
    'rfc3339-validator==0.1.4', 'rfc3987==1.3.8', 'setuptools==68.1.2',
    'six==1.16.0', 'types-python-dateutil==2.9.0.20250822', 'uri-template==1.3.0',
    'webcolors==24.6.0', 'wheel==0.42.0',
)
PUBLIC_LOCK = Path(__file__).with_name('requirements-public.lock')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n'


def write_once(path, value):
    raw = value if isinstance(value, bytes) else canonical(value)
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def digest(path):
    with path.open('rb') as stream:
        return 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()


def regular(path, limit=128 * 1024 * 1024):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit, 'input type/size refused: ' + str(path))
        actual = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'input content changed: ' + str(path))
    return actual


def clean_revision(source, revision):
    actual = subprocess.check_output(['git', '-C', source, 'rev-parse', 'HEAD'], text=True).strip()
    require(actual == revision, 'source revision differs: ' + source)
    require(not subprocess.check_output(['git', '-C', source, 'status', '--porcelain'], text=True), 'source dirty: ' + source)


def command(argv, *, cwd=None):
    subprocess.run([str(item) for item in argv], cwd=cwd, check=True,
        env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'}, timeout=120)


def lock_from_wheelhouse(wheelhouse):
    wheels = sorted(wheelhouse.glob('*.whl'))
    require(len(wheels) == len(WHEEL_REQUIREMENTS), 'wheel download did not produce the closed requirement set')
    names = set()
    lines = []
    for wheel in wheels:
        name, version = wheel.name.split('-', 2)[:2]
        normalized = name.replace('_', '-').lower()
        names.add(normalized)
        lines.append(f'{normalized}=={version} --hash={digest(wheel)}')
    expected = {item.split('==', 1)[0] for item in WHEEL_REQUIREMENTS}
    require(names == expected, 'wheelhouse names differ from frozen requirement set')
    return ('\n'.join(sorted(lines)) + '\n').encode()


def allocation(root):
    return sum(item.lstat().st_blocks * 512 for item in (root, *root.rglob('*')) if not item.is_symlink())


def build(args):
    require(os.environ.get('INVOCATION_ID'), 'durable manager required')
    owner, switchyard, maude = Path(args.owner), Path(args.switchyard), Path(args.maude)
    require(owner.is_absolute() and not owner.exists(), 'fresh absolute owner root required')
    clean_revision(str(switchyard), SWITCHYARD_REVISION); clean_revision(str(maude), MAUDE_REVISION)
    owner.mkdir(mode=0o700)
    stages = owner / 'stages'; stages.mkdir(mode=0o700)
    write_once(stages / 'checkpoint.json', {'unit': args.unit, 'invocation_id': os.environ['INVOCATION_ID'],
        'owner': str(owner), 'sources': {'switchyard': SWITCHYARD_REVISION, 'maude': MAUDE_REVISION},
        'allocation_limit_bytes': ALLOCATION_LIMIT, 'network_transition': 'bounded wheel download only',
        'next': 'inspect this original owner and manager records; do not reinstall or refresh it'})
    wheelhouse = owner / 'wheelhouse'; wheelhouse.mkdir(mode=0o700)
    requested = owner / 'wheel-requirements.txt'; write_once(requested, ('\n'.join(WHEEL_REQUIREMENTS) + '\n').encode())
    command([args.python, '-m', 'pip', 'download', '--disable-pip-version-check', '--isolated', '--retries', '0',
        '--timeout', '30', '--no-cache-dir', '--no-deps', '--only-binary=:all:', '--dest', wheelhouse,
        '--requirement', requested])
    lock = owner / 'requirements.lock'; write_once(lock, lock_from_wheelhouse(wheelhouse))
    require(PUBLIC_LOCK.read_bytes() == lock.read_bytes(), 'downloaded wheel lock differs from reviewed public lock')
    venv = owner / 'venv'
    command([args.python, '-m', 'venv', '--copies', venv])
    python = venv / 'bin/python'
    command([python, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-index', '--find-links', wheelhouse,
        '--require-hashes', '--no-cache-dir', '--ignore-installed', '--requirement', lock])
    exported = owner / 'switchyard-source'; exported.mkdir(mode=0o700)
    archive = subprocess.check_output(['git', '-C', switchyard, 'archive', SWITCHYARD_REVISION])
    with tarfile.open(fileobj=__import__('io').BytesIO(archive)) as bundle:
        bundle.extractall(exported, filter='data')
    built = owner / 'built'; built.mkdir(mode=0o700)
    command([python, '-m', 'pip', 'wheel', '--no-index', '--no-deps', '--no-build-isolation', '--wheel-dir', built, exported])
    switchyard_wheels = sorted(built.glob('switchyard_codex_foreman-*.whl'))
    require(len(switchyard_wheels) == 1, 'Switchyard wheel build ambiguous')
    command([python, '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-cache-dir', switchyard_wheels[0]])
    command([python, '-m', 'pip', 'check'])
    code = """import jsonschema, pathlib, switchyard, sys
root=pathlib.Path(sys.prefix).resolve()
for module in (jsonschema, switchyard):
    assert pathlib.Path(module.__file__).resolve().is_relative_to(root), module.__file__
assert not any('dist-packages' in item for item in sys.path if item and not item.startswith(sys.prefix))
"""
    command([python, '-I', '-c', code])
    command([venv / 'bin/switchyard-review-verifier', '--help'])
    command([venv / 'bin/switchyard-provider-runner', '--help'])
    write_once(stages / 'closure.json', {'wheel_lock_sha256': digest(lock), 'wheel_count': len(WHEEL_REQUIREMENTS),
        'switchyard_wheel_sha256': digest(switchyard_wheels[0]), 'python': str(python),
        'system_site_packages': False, 'pip_check': 'passed', 'provider_calls': 0, 'grants': 0, 'executor_calls': 0})
    require(allocation(owner) <= ALLOCATION_LIMIT, 'qualification allocation exceeded 512MiB')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True); parser.add_argument('--switchyard', required=True)
    parser.add_argument('--maude', required=True); parser.add_argument('--python', default='/usr/bin/python3.12')
    parser.add_argument('--unit', default='constellation-reviewed-copy-python-001.service')
    args = parser.parse_args(argv)
    build(args)


if __name__ == '__main__':
    main()

