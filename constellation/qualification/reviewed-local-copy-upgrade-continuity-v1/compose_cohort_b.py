#!/usr/bin/env python3
"""Compose the QUALIFICATION-ONLY cohort B bundle for the A -> B upgrade harness.

Cohort B is cohort A (the qualified alpha-exit-rc bundle) with two components
replaced by their own committed builders' outputs:

  - docket: a version-bumped rebuild (`packaging/release/build_release.py`,
    two clean builds, byte-equal) from a local qual commit;
  - cohort-kit: `build_cohort_kit.py` from the site qual/ branch whose driver
    qualifies only the cohort B entry.

Every other artifact is copied from bundle A after `sha256sum --check`. The
result is never a release: its manifest names a `-qual` Docket version and a
`-qual` kit version, and nothing here is published.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sums(directory: Path) -> dict:
    out = {}
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        digest, _, name = line.partition('  ')
        out[name] = digest
    for name, digest in out.items():
        if sha256(directory / name) != digest:
            raise SystemExit(f'{directory}/{name} does not match its SHA256SUMS')
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--bundle-a', type=Path, required=True)
    parser.add_argument('--docket-build', type=Path, required=True, help='build_release.py output directory')
    parser.add_argument('--kit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    listed_a = sums(args.bundle_a)
    manifest_a = json.loads((args.bundle_a / 'cohort-manifest.json').read_text())
    listed_d = sums(args.docket_build)
    receipt = json.loads((args.docket_build / 'build-receipt.v1.json').read_text())
    if receipt.get('reproduction', {}).get('byte_equal') is not True:
        raise SystemExit('the Docket build is not a byte-equal reproduction')
    [docket_name] = [name for name in listed_d if name.endswith('.tar.gz')]
    docket_info = receipt['binaries']['docket']['build_info']
    with tarfile.open(args.kit, 'r:gz') as tar:
        top = tar.getmembers()[0].name.split('/')[0]
        kit_info = json.loads(tar.extractfile(f'{top}/BUILD-INFO.json').read())
    args.output.mkdir(parents=True, exist_ok=False)
    components = []
    by_digest = {digest: name for name, digest in listed_a.items()}
    for entry in manifest_a['components']:
        name = entry['component']
        if name == 'docket':
            shutil.copyfile(args.docket_build / docket_name, args.output / docket_name)
            entry = {'component': 'docket', 'package_version': docket_info['version'],
                     'source_commit': docket_info['source_commit'],
                     'artifact_sha256': 'sha256:' + sha256(args.output / docket_name)}
        elif name == 'cohort-kit':
            shutil.copyfile(args.kit, args.output / args.kit.name)
            entry = {'component': 'cohort-kit', 'package_version': kit_info['version'],
                     'source_commit': kit_info['source_commit'], 'artifact_sha256': 'sha256:' + sha256(args.kit)}
        else:
            source = by_digest[entry['artifact_sha256'].removeprefix('sha256:')]
            shutil.copyfile(args.bundle_a / source, args.output / source)
        components.append(entry)
    (args.output / 'qualification-only').mkdir()
    fixture = [name for name in listed_a if name.startswith('qualification-only/')]
    for name in fixture:
        shutil.copyfile(args.bundle_a / name, args.output / name)
    manifest = {'schema': manifest_a['schema'], 'profile': manifest_a['profile'],
                'components': sorted(components, key=lambda entry: entry['component'])}
    (args.output / 'cohort-manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
    names = sorted(p.name for p in args.output.iterdir() if p.is_file())
    text = ''.join(f'{sha256(args.output / name)}  {name}\n' for name in names)
    text += ''.join(f'{listed_a[name]}  {name}\n' for name in fixture)
    (args.output / 'SHA256SUMS').write_text(text)
    print(json.dumps({'bundle': str(args.output), 'manifest_sha256': 'sha256:' + sha256(args.output / 'cohort-manifest.json'),
                      'qualification_only': True,
                      'components': {entry['component']: [entry['package_version'], entry['artifact_sha256']]
                                     for entry in components}}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
