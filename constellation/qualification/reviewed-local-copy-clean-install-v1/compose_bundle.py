#!/usr/bin/env python3
"""Compose the reviewed-local-copy/v1 cohort release bundle for qualification.

QUALIFICATION-ONLY. It copies exactly the cohort artifacts (verified against
each lane's SHA256SUMS and the expected digests below), the cohort-kit tarball
and the loopback fixture tooling into a fresh directory, writes
`cohort-manifest.json` (constellation.cohort-manifest/v1) and `SHA256SUMS`.
Nothing is rebuilt.

The fixture tooling is a named qualification dependency of the harness, not a
manifest component: the newcomer's real route never uses it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

CAMPAIGN = Path('/data/git/.campaign-artifacts/alpha-exit-closure-20260925')
# component: (artifact path relative to the campaign, package version, commit, sha256)
COHORT = {
    'nq': ('nq-0.2.0/download/nq-ng_0.2.0_amd64.deb', '0.2.0', 'dbe29d81ba84061b08fec285f1218ec2145c65bc',
           '9e953e88d1f79cffd03e97b530199459b5e45ead55ea4ba7d5066e0851008d7b'),
    'maude': ('artifacts/maude/maude-reviewed-local-copy-0.1.0.tar.gz', '0.1.0', '75d4dc1df1934cfc797c48c528d314804938eaae',
              'f88b5823f6a7bc6ff1c9645daff6312eec5234559bb735d25db589e1904f7357'),
    'nightshift': ('artifacts/nightshift/nightshift-0.1.0-30c89fe-linux-amd64.tar.gz', '0.1.0',
                   '30c89fe17723a7b9d77b19fd650aadb0a784748d', 'cffbea38c4718c480fd9c0b5c41c28331d52132205a3e16f2fda2e572467a254'),
    'pulse': ('artifacts/pulse/pulse-nq-load-support-0.1.0-30c89fe-linux-amd64.tar.gz', '0.1.0',
              '30c89fe17723a7b9d77b19fd650aadb0a784748d', '51e85b97f44504240044f3b666d6fb3602270939102676e65798f4cecd405c61'),
    'ag': ('artifacts/ag/ag-0.1.0-linux-amd64.tar.gz', '0.1.0', '58122cec1ca8de35a1d146bf7987f8e69f49a040',
           'bc53b836d7207493bbe35f0b380475641603caf3aedea6e8bcd3c9c0dea6ab5c'),
    'docket': ('artifacts/docket/docket-0.1.0-linux-amd64.tar.gz', '0.1.0', '3093def030a5151d2e7b956eafb73d0c16f8c735',
               '6596315fcdb92fd881d6c0f2159eb912ee9c96b99a58fdc5ddea5e11a192c81b'),
    'switchyard': ('artifacts/switchyard/switchyard-0.2.0-1c82e719cf35.tar.gz', '0.2.0',
                   '1c82e719cf358728d0262ae11138fb13fefe0cae', 'be418f76e9f5f8239d457137b19ff771d562d89a85ccda5b4ccfdc0049f665c1'),
    'app-server': ('artifacts/app-server/codex-app-server-97b0acd5ce2c-linux-amd64.tar.gz', '0.0.0',
                   '97b0acd5ce2ccb3c87a763606696c35a450947f6', '9999bd8e75607071e1e43d9829fea253593f95323dff3a6e690b9d52433e2cd9'),
}
FIXTURE = ('artifacts/fixture-review-tooling/fixture-review-tooling-7b04e8d8cf99.tar.gz',
           '168c4e57a7cb3d431ee2f9cb3b546c0d51f97a4781313522fa28f42b39964b8a')


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def lane_sums(path: Path) -> dict:
    sums = path.parent / 'SHA256SUMS'
    return {line.split('  ', 1)[1]: line.split('  ', 1)[0] for line in sums.read_text().splitlines() if line}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--kit', type=Path, required=True, help='cohort-kit-<version>.tar.gz from build_cohort_kit.py')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    components = []
    for name, (relative, version, commit, expected) in sorted(COHORT.items()):
        source = CAMPAIGN / relative
        actual = sha256(source)
        if actual != expected or lane_sums(source).get(source.name) != expected:
            raise SystemExit(f'{name}: {source} does not match its expected digest and lane SHA256SUMS')
        shutil.copyfile(source, args.output / source.name)
        components.append({'component': name, 'package_version': version, 'source_commit': commit,
                           'artifact_sha256': 'sha256:' + actual})
    with tarfile.open(args.kit, 'r:gz') as tar:
        top = tar.getmembers()[0].name.split('/')[0]
        info = json.loads(tar.extractfile(f'{top}/BUILD-INFO.json').read())
    shutil.copyfile(args.kit, args.output / args.kit.name)
    components.append({'component': 'cohort-kit', 'package_version': info['version'],
                       'source_commit': info['source_commit'], 'artifact_sha256': 'sha256:' + sha256(args.kit)})
    fixture = CAMPAIGN / FIXTURE[0]
    if sha256(fixture) != FIXTURE[1] or lane_sums(fixture).get(fixture.name) != FIXTURE[1]:
        raise SystemExit('fixture tooling does not match its expected digest')
    fixture_dir = args.output / 'qualification-only'
    fixture_dir.mkdir()
    shutil.copyfile(fixture, fixture_dir / fixture.name)
    manifest = {'schema': 'constellation.cohort-manifest/v1', 'profile': 'reviewed-local-copy/v1',
                'components': sorted(components, key=lambda entry: entry['component'])}
    (args.output / 'cohort-manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
    names = sorted(p.name for p in args.output.iterdir() if p.is_file())
    sums = ''.join(f'{sha256(args.output / name)}  {name}\n' for name in names)
    sums += f'{FIXTURE[1]}  qualification-only/{fixture.name}\n'
    (args.output / 'SHA256SUMS').write_text(sums)
    print(json.dumps({'bundle': str(args.output), 'manifest_sha256': 'sha256:' + sha256(args.output / 'cohort-manifest.json'),
                      'components': {entry['component']: entry['artifact_sha256'] for entry in components}}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
