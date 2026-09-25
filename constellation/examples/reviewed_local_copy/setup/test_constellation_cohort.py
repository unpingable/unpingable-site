"""Unit tests for the cohort setup driver: manifest validation and fail-closed pins.

Run from this directory with the target interpreter:

    python3 -B -m unittest -v test_constellation_cohort

No root, network, component artifact or VM is needed.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parent))
import constellation_cohort as cc  # noqa: E402


def commit(seed):
    return hashlib.sha1(seed.encode()).hexdigest()


def artifact_bytes(name):
    return f'artifact for {name}\n'.encode()


def manifest_value():
    return {
        'schema': cc.MANIFEST_SCHEMA,
        'profile': cc.PROFILE,
        'components': [
            {'component': name, 'package_version': '0.1.0',
             'source_commit': commit(name),
             'artifact_sha256': 'sha256:' + hashlib.sha256(artifact_bytes(name)).hexdigest()}
            for name in sorted(cc.COMPONENTS)
        ],
    }


def raw(value):
    return json.dumps(value).encode()


def qualified_for(value):
    return {cc.PROFILE: {'test-cohort': {
        entry['component']: {'package_version': entry['package_version'], 'source_commit': entry['source_commit']}
        for entry in value['components']}}}


class ManifestValidation(unittest.TestCase):
    def refuses(self, value, code):
        with self.assertRaises(cc.Refusal) as caught:
            cc.load_manifest(value if isinstance(value, bytes) else raw(value))
        self.assertEqual(caught.exception.code, code, caught.exception.detail)

    def test_valid_manifest_is_indexed_by_component_and_digested(self):
        data = raw(manifest_value())
        manifest = cc.load_manifest(data)
        self.assertEqual(set(manifest['components']), set(cc.COMPONENTS))
        self.assertEqual(manifest['manifest_sha256'], 'sha256:' + hashlib.sha256(data).hexdigest())

    def test_not_json(self):
        self.refuses(b'{not json', 'manifest.not_json')

    def test_duplicate_json_key(self):
        self.refuses(b'{"schema":"a","schema":"b","profile":"p","components":[]}', 'manifest.not_json')

    def test_extra_top_level_field(self):
        value = manifest_value()
        value['review_route'] = 'fixture-review'
        self.refuses(value, 'manifest.shape')

    def test_wrong_schema(self):
        value = manifest_value()
        value['schema'] = 'constellation.cohort-manifest/v2'
        self.refuses(value, 'manifest.schema')

    def test_other_profile(self):
        value = manifest_value()
        value['profile'] = 'reviewed-local-copy-evidence-read/v1'
        self.refuses(value, 'manifest.profile')

    def test_extra_component_field(self):
        value = manifest_value()
        value['components'][0]['artifact_name'] = 'x.tar.gz'
        self.refuses(value, 'manifest.component_shape')

    def test_unknown_component(self):
        value = manifest_value()
        value['components'].append(dict(value['components'][0], component='phosphor'))
        self.refuses(value, 'manifest.unknown_component')

    def test_duplicate_component(self):
        value = manifest_value()
        value['components'].append(copy.deepcopy(value['components'][0]))
        self.refuses(value, 'manifest.duplicate_component')

    def test_missing_component(self):
        value = manifest_value()
        value['components'] = [e for e in value['components'] if e['component'] != 'docket']
        self.refuses(value, 'manifest.missing_component')

    def test_short_or_uppercase_commit(self):
        for bad in ('8ab64ed', commit('x').upper(), commit('x') + '0'):
            value = manifest_value()
            value['components'][0]['source_commit'] = bad
            self.refuses(value, 'manifest.commit')

    def test_bad_digest(self):
        for bad in ('0' * 64, 'sha512:' + '0' * 64, 'sha256:' + 'G' * 64):
            value = manifest_value()
            value['components'][0]['artifact_sha256'] = bad
            self.refuses(value, 'manifest.digest')

    def test_bad_version(self):
        for bad in ('', ' 0.1', 'v/1', 1):
            value = manifest_value()
            value['components'][0]['package_version'] = bad
            self.refuses(value, 'manifest.version')

    def test_two_components_cannot_share_one_artifact(self):
        value = manifest_value()
        value['components'][1]['artifact_sha256'] = value['components'][0]['artifact_sha256']
        self.refuses(value, 'manifest.shared_artifact')


class CohortPins(unittest.TestCase):
    def setUp(self):
        self.value = manifest_value()
        self.manifest = cc.load_manifest(raw(self.value))

    def refuses(self, table):
        with self.assertRaises(cc.Refusal) as caught:
            cc.check_cohort_pins(self.manifest, table)
        self.assertEqual(caught.exception.code, 'pin.incompatible')
        return caught.exception.detail

    def test_exact_match_names_the_qualified_cohort(self):
        self.assertEqual(cc.check_cohort_pins(self.manifest, qualified_for(self.value)), 'test-cohort')

    def test_shipped_table_is_pending_and_refuses_every_manifest(self):
        detail = self.refuses(None)
        self.assertIn('PENDING', detail)

    def test_one_commit_differs(self):
        table = qualified_for(self.value)
        table[cc.PROFILE]['test-cohort']['nightshift']['source_commit'] = commit('9e592cb')
        self.assertIn('nightshift', self.refuses(table))

    def test_version_differs(self):
        table = qualified_for(self.value)
        table[cc.PROFILE]['test-cohort']['nq']['package_version'] = '0.1.0-1'
        self.assertIn('nq', self.refuses(table))

    def test_component_set_differs(self):
        table = qualified_for(self.value)
        del table[cc.PROFILE]['test-cohort']['cohort-kit']
        self.assertIn('component set differs', self.refuses(table))

    def test_no_qualified_cohort_for_profile(self):
        self.refuses({})

    def test_newer_commit_is_not_compatible(self):
        # No ranges: a descendant commit is a different pin.
        table = qualified_for(self.value)
        self.manifest['components']['maude']['source_commit'] = commit('c1fce17')
        self.assertIn('maude', self.refuses(table))


class Artifacts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.manifest = cc.load_manifest(raw(manifest_value()))
        for name, spec in cc.COMPONENTS.items():
            suffix = '.deb' if spec['kind'] == 'deb' else '.tar.gz'
            (self.dir / f'{name}{suffix}').write_bytes(artifact_bytes(name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_located_by_digest(self):
        located = cc.locate_artifacts(self.manifest, self.dir)
        self.assertEqual(located['nq'].name, 'nq.deb')

    def test_missing_artifact(self):
        (self.dir / 'docket.tar.gz').write_bytes(b'rebuilt with different bytes\n')
        with self.assertRaises(cc.Refusal) as caught:
            cc.locate_artifacts(self.manifest, self.dir)
        self.assertEqual(caught.exception.code, 'artifact.missing')

    def test_ambiguous_artifact(self):
        (self.dir / 'docket-copy.tar.gz').write_bytes(artifact_bytes('docket'))
        with self.assertRaises(cc.Refusal) as caught:
            cc.locate_artifacts(self.manifest, self.dir)
        self.assertEqual(caught.exception.code, 'artifact.ambiguous')

    def test_wrong_kind(self):
        os.rename(self.dir / 'nq.deb', self.dir / 'nq.tar.gz')
        with self.assertRaises(cc.Refusal) as caught:
            cc.locate_artifacts(self.manifest, self.dir)
        self.assertEqual(caught.exception.code, 'artifact.kind')

    def test_symlink_is_not_an_artifact(self):
        os.rename(self.dir / 'ag.tar.gz', self.dir.parent / f'{self.dir.name}-ag.tar.gz')
        os.symlink(self.dir.parent / f'{self.dir.name}-ag.tar.gz', self.dir / 'ag.tar.gz')
        try:
            with self.assertRaises(cc.Refusal) as caught:
                cc.locate_artifacts(self.manifest, self.dir)
            self.assertEqual(caught.exception.code, 'artifact.missing')
        finally:
            os.unlink(self.dir.parent / f'{self.dir.name}-ag.tar.gz')


def tarball(path, members):
    with tarfile.open(path, 'w:gz') as tar:
        for info, data in members:
            tar.addfile(info, io.BytesIO(data) if data is not None else None)


def member(name, data=b'', mode=0o755, kind=tarfile.REGTYPE, link=''):
    info = tarfile.TarInfo(name)
    info.type = kind
    info.mode = mode
    info.linkname = link
    info.size = len(data) if kind == tarfile.REGTYPE else 0
    return info, (data if kind == tarfile.REGTYPE else None)


class SafeExtract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def refuses(self, members, code):
        tarball(self.dir / 'a.tar.gz', members)
        with self.assertRaises(cc.Refusal) as caught:
            cc.safe_extract(self.dir / 'a.tar.gz', self.dir / 'out')
        self.assertEqual(caught.exception.code, code)
        self.assertFalse((self.dir / 'out').exists(), 'nothing extracted after a refusal')

    def test_extracts_one_root(self):
        tarball(self.dir / 'a.tar.gz', [member('ag-0.1.0/', kind=tarfile.DIRTYPE),
                                        member('ag-0.1.0/bin/ag-loopctl', b'\x7fELF')])
        names = cc.safe_extract(self.dir / 'a.tar.gz', self.dir / 'out')
        self.assertEqual(names, ['ag-0.1.0/bin/ag-loopctl'])
        root = cc.artifact_root(self.dir / 'out')
        self.assertTrue(os.access(root / 'bin/ag-loopctl', os.X_OK))

    def test_absolute_member(self):
        self.refuses([member('/etc/passwd', b'x')], 'artifact.unsafe_member')

    def test_parent_escape(self):
        self.refuses([member('ag/../../x', b'x')], 'artifact.unsafe_member')

    def test_symlink_member(self):
        self.refuses([member('ag/bin/x', kind=tarfile.SYMTYPE, link='/usr/bin/python3')], 'artifact.unsafe_member')

    def test_setuid_member(self):
        self.refuses([member('ag/bin/x', b'x', mode=0o4755)], 'artifact.unsafe_mode')

    def test_group_writable_member(self):
        self.refuses([member('ag/bin/x', b'x', mode=0o775)], 'artifact.unsafe_mode')

    def test_destination_exists(self):
        (self.dir / 'out').mkdir()
        tarball(self.dir / 'a.tar.gz', [member('ag/x', b'x')])
        with self.assertRaises(cc.Refusal) as caught:
            cc.safe_extract(self.dir / 'a.tar.gz', self.dir / 'out')
        self.assertEqual(caught.exception.code, 'artifact.destination_exists')

    def test_two_roots_refuse_layout(self):
        tarball(self.dir / 'a.tar.gz', [member('a/x', b'x'), member('b/y', b'y')])
        cc.safe_extract(self.dir / 'a.tar.gz', self.dir / 'out')
        with self.assertRaises(cc.Refusal) as caught:
            cc.artifact_root(self.dir / 'out')
        self.assertEqual(caught.exception.code, 'artifact.layout')


class BuildInfo(unittest.TestCase):
    pin = {'package_version': '0.2.0', 'source_commit': commit('nq')}

    def info(self, **changes):
        value = {'schema': 'nq.build_info.v2', 'component': 'nq', 'version': '0.2.0',
                 'source_commit': commit('nq'), 'debug_assertions': False}
        value.update(changes)
        return value

    def refuses(self, info, code):
        with self.assertRaises(cc.Refusal) as caught:
            cc.check_build_info('nq', '/usr/bin/nq', info, self.pin)
        self.assertEqual(caught.exception.code, code)

    def test_matching_release_build(self):
        observed = cc.check_build_info('nq', '/usr/bin/nq', self.info(), self.pin)
        self.assertEqual(observed['source_commit'], self.pin['source_commit'])

    def test_version_mismatch(self):
        self.refuses(self.info(version='0.1.0'), 'build_info.version')

    def test_commit_mismatch_or_absent(self):
        self.refuses(self.info(source_commit=commit('other')), 'build_info.commit')
        self.refuses(self.info(source_commit=None), 'build_info.commit')

    def test_debug_build_refused(self):
        self.refuses(self.info(debug_assertions=True), 'build_info.debug_build')
        self.refuses(self.info(profile='dev'), 'build_info.debug_build')

    def test_component_absent(self):
        self.refuses(self.info(component=''), 'build_info.component')

    def test_parse_requires_one_json_line(self):
        self.assertEqual(cc.parse_build_info(b'{"a":1}\n'), {'a': 1})
        for bad in (b'{"a":1}', b'{"a":1}\n{}\n', b'nq 0.2.0\n', b'[1]\n'):
            with self.assertRaises(cc.Refusal) as caught:
                cc.parse_build_info(bad)
            self.assertEqual(caught.exception.code, 'build_info.format')

    def test_probe_program_through_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            program = Path(tmp) / 'nq'
            line = json.dumps(self.info())
            program.write_text(f'#!/bin/sh\nprintf \'%s\\n\' \'{line}\'\n')
            program.chmod(0o755)
            records = cc.Records(Path(tmp) / 'records', 'test')
            done = records.call('build-info-nq', [program, '--build-info'])
            cc.check_build_info('nq', str(program), cc.parse_build_info(done.stdout), self.pin)
            files = sorted(p.name for p in records.run.iterdir())
            self.assertEqual(files, ['001-build-info-nq.finished.json', '001-build-info-nq.started.json',
                                     '001-build-info-nq.stderr', '001-build-info-nq.stdout'])


class Records(unittest.TestCase):
    def test_create_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            records = cc.Records(Path(tmp), 'test')
            records.write('a.json', {'x': 1})
            with self.assertRaises(FileExistsError):
                records.write('a.json', {'x': 2})

    def test_failed_child_is_a_refusal_with_retained_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            records = cc.Records(Path(tmp), 'test')
            with self.assertRaises(cc.Refusal) as caught:
                records.call('false', ['/bin/sh', '-c', 'echo no >&2; exit 3'])
            self.assertEqual(caught.exception.code, 'child.failed')
            self.assertEqual((records.run / '001-false.stderr').read_bytes(), b'no\n')


class Identities(unittest.TestCase):
    def test_reviewer_is_never_the_author_and_fixture_is_labelled(self):
        for route in cc.REVIEW_ROUTES:
            ids = cc.synthetic_identities('rc1-a', route)
            self.assertNotEqual(ids['reviewer_id'], ids['author_principal'])
        self.assertEqual(cc.synthetic_identities('rc1-a', 'fixture-review')['reviewer_id'],
                         'fixture-deterministic-reviewer-not-independent')
        self.assertNotIn('fixture', cc.synthetic_identities('rc1-a', 'real')['reviewer_id'])

    def test_real_route_never_writes_a_credential(self):
        self.assertEqual(set(cc.codex_home_files('real', None)), {'config.toml'})

    def test_fixture_route_is_loopback_with_a_dummy_key(self):
        files = cc.codex_home_files('fixture-review', 23459)
        self.assertIn(b'http://127.0.0.1:23459/v1', files['config.toml'])
        self.assertTrue(json.loads(files['auth.json'])['OPENAI_API_KEY'].startswith('fixture-not-a-credential-'))
        with self.assertRaises(cc.Refusal):
            cc.codex_home_files('fixture-review', None)

    def test_cohort_id(self):
        for bad in ('A', '../x', 'x' * 41, 'has space'):
            with self.assertRaises(cc.Refusal):
                cc.cohort_paths(bad)


class CommandLine(unittest.TestCase):
    def run_main(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            status = cc.main(argv)
        return status, json.loads(out.getvalue())

    def test_verify_manifest_fails_closed_on_pending_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'manifest.json'
            path.write_bytes(raw(manifest_value()))
            status, result = self.run_main(['verify-manifest', '--manifest', str(path), '--artifacts', tmp])
        self.assertEqual(status, 2)
        self.assertEqual(result['code'], 'pin.incompatible')

    def test_accept_requires_an_exact_candidate_digest(self):
        status, result = self.run_main(['accept', '--cohort', 'rc1-a', '--candidate-sha256', 'latest'])
        self.assertEqual((status, result['code']), (2, 'accept.candidate'))

    def test_no_automatic_acceptance_option_exists(self):
        help_text = cc.parser().format_help() + ''.join(
            action.format_help() for action in cc.parser()._subparsers._group_actions[0].choices.values())
        for word in ('auto-accept', 'yes', 'synthetic'):
            self.assertNotIn('--' + word, help_text)


if __name__ == '__main__':
    unittest.main()
