"""Build the `cohort-kit` release tarball from a clean checkout of this kit.

    python3 build_cohort_kit.py --output DIR

The tarball holds one top-level directory `cohort-kit-<version>/` with the
reviewed_local_copy caller glue, `setup/` (this driver and its helpers) and a
`BUILD-INFO.json` that binds every file's sha256 to the site commit. It is
deterministic: sorted entries, root:root, fixed mtime, gzip mtime 0. The
builder refuses a dirty kit directory, so the recorded commit is exact.

Two things differ from the checkout, both by rule:

- the released driver has the build commit stamped into its one
  `KIT_SOURCE_COMMIT = None` line, so it can refuse a manifest that names
  another kit commit (a source checkout stays unstamped and refuses to
  install);
- `README.md` is not in the kit. It is the published page that states the
  kit's and the manifest's digests, which a file inside the kit cannot do.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
MTIME = 1700000000
EXCLUDE_DIRS = {'__pycache__'}
EXCLUDE_FILES = {'build_cohort_kit.py', 'README.md'}
STAMP_LINE = b'\nKIT_SOURCE_COMMIT = None\n'
DRIVER = 'setup/constellation_cohort.py'


def stamp(driver: bytes, commit: str) -> bytes:
    if driver.count(STAMP_LINE) != 1:
        raise SystemExit(f'{DRIVER} must hold exactly one unstamped KIT_SOURCE_COMMIT line')
    return driver.replace(STAMP_LINE, f"\nKIT_SOURCE_COMMIT = '{commit}'\n".encode())


def git(*args: str) -> str:
    return subprocess.run(['git', '-C', str(KIT), *args], check=True, capture_output=True, text=True).stdout.strip()


def kit_files() -> list[Path]:
    tracked = git('ls-files', '--', '.').splitlines()
    files = []
    for name in sorted(tracked):
        path = KIT / name
        if any(part in EXCLUDE_DIRS for part in path.parts) or path.name in EXCLUDE_FILES or name.endswith('.pyc'):
            continue
        files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if git('status', '--porcelain', '--untracked-files=all', '--', '.'):
        raise SystemExit('the kit directory has uncommitted changes; commit before building')
    commit = git('rev-parse', 'HEAD')
    import sys
    sys.path.insert(0, str(HERE))
    import constellation_cohort as driver
    version = driver.DRIVER_VERSION
    top = f'cohort-kit-{version}'
    files = {str(path.relative_to(KIT)): path.read_bytes() for path in kit_files()}
    files[DRIVER] = stamp(files[DRIVER], commit)
    info = {'schema': 'constellation.cohort-kit-build-info/v1', 'component': 'cohort-kit', 'version': version,
            'source_commit': commit, 'source_repository': 'https://github.com/unpingable/unpingable-site',
            'source_path': 'constellation/examples/reviewed_local_copy', 'debug_assertions': False,
            'profile': 'release', 'files': {name: 'sha256:' + hashlib.sha256(raw).hexdigest() for name, raw in files.items()}}
    files['BUILD-INFO.json'] = (json.dumps(info, sort_keys=True, indent=1) + '\n').encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as tar:
        directories = sorted({str(Path(name).parent) for name in files if str(Path(name).parent) != '.'})
        for name in [''] + directories:
            entry = tarfile.TarInfo(f'{top}/{name}'.rstrip('/'))
            entry.type, entry.mode, entry.mtime, entry.uname, entry.gname = tarfile.DIRTYPE, 0o755, MTIME, 'root', 'root'
            tar.addfile(entry)
        for name, raw in sorted(files.items()):
            entry = tarfile.TarInfo(f'{top}/{name}')
            entry.size, entry.mtime, entry.uname, entry.gname = len(raw), MTIME, 'root', 'root'
            entry.mode = 0o755 if name == 'setup/constellation_cohort.py' else 0o644
            tar.addfile(entry, io.BytesIO(raw))
    compressed = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=compressed, mtime=0) as stream:
        stream.write(buffer.getvalue())
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / f'{top}.tar.gz'
    if target.exists():
        raise SystemExit(f'{target} exists')
    target.write_bytes(compressed.getvalue())
    digest = hashlib.sha256(compressed.getvalue()).hexdigest()
    print(json.dumps({'artifact': str(target), 'sha256': 'sha256:' + digest, 'component': 'cohort-kit',
                      'version': version, 'source_commit': commit}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
