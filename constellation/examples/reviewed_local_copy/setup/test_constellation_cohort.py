"""Unit tests for the cohort setup driver: manifest validation and fail-closed pins.

Run with the target interpreter (-I implies -P, so run the file itself):

    python3.11 -I -S -B test_constellation_cohort.py -v

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

# The qualified cohort this driver release ships.
SHIPPED = 'alpha-exit-rc'


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
        entry['component']: {key: entry[key] for key in cc.PIN_FIELDS}
        for entry in value['components']}}}


def shipped_manifest(kit_commit=None, kit_digest=None, kit_version=None):
    """A manifest naming exactly the shipped qualified cohort."""
    pins = cc.QUALIFIED_COHORTS[cc.PROFILE][SHIPPED]
    components = []
    for name, pin in sorted(pins.items()):
        entry = {'component': name, **pin}
        if name == 'cohort-kit':
            entry.update(package_version=kit_version or cc.DRIVER_VERSION, source_commit=kit_commit or commit('kit'),
                         artifact_sha256=kit_digest or 'sha256:' + hashlib.sha256(b'kit').hexdigest())
        components.append(entry)
    return {'schema': cc.MANIFEST_SCHEMA, 'profile': cc.PROFILE, 'components': components}


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

    def test_shipped_table_refuses_other_commits(self):
        detail = self.refuses(None)
        self.assertIn(SHIPPED, detail)

    def test_shipped_cohort_matches_with_any_kit_commit_but_its_own_version(self):
        manifest = cc.load_manifest(raw(shipped_manifest()))
        self.assertEqual(cc.check_cohort_pins(manifest), SHIPPED)
        with self.assertRaises(cc.Refusal) as caught:
            cc.check_cohort_pins(cc.load_manifest(raw(shipped_manifest(kit_version='0.1.0'))))
        self.assertIn('cohort-kit.package_version', caught.exception.detail)

    def test_shipped_cohort_refuses_another_artifact_digest(self):
        value = shipped_manifest()
        for entry in value['components']:
            if entry['component'] == 'docket':
                entry['artifact_sha256'] = 'sha256:' + hashlib.sha256(b'rebuilt').hexdigest()
        with self.assertRaises(cc.Refusal) as caught:
            cc.check_cohort_pins(cc.load_manifest(raw(value)))
        self.assertEqual(caught.exception.code, 'pin.incompatible')
        self.assertIn('docket.artifact_sha256', caught.exception.detail)

    def test_shipped_table_binds_the_lane_reports(self):
        pins = cc.QUALIFIED_COHORTS[cc.PROFILE][SHIPPED]
        self.assertEqual(set(pins), set(cc.COMPONENTS))
        self.assertEqual(pins['maude']['source_commit'], '75d4dc1df1934cfc797c48c528d314804938eaae')
        self.assertEqual(pins['nightshift']['source_commit'], pins['pulse']['source_commit'])
        self.assertNotEqual(pins['nightshift']['artifact_sha256'], pins['pulse']['artifact_sha256'])
        self.assertTrue(pins['nq']['artifact_sha256'].startswith('sha256:9e953e88'))
        # AG revision 2: keyless read-only verification (G3 D-1 fixed).
        self.assertEqual(pins['ag']['source_commit'], '58122cec1ca8de35a1d146bf7987f8e69f49a040')
        self.assertTrue(pins['ag']['artifact_sha256'].startswith('sha256:bc53b836'))
        for name, pin in pins.items():
            if name != 'cohort-kit':
                self.assertRegex(pin['source_commit'], cc.COMMIT)
                self.assertRegex(pin['artifact_sha256'], cc.DIGEST)

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


    def test_receipt_identity_binds_the_executable_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'bin').mkdir()
            (root / 'bin/codex-app-server').write_bytes(b'\x7fELF app server')
            info = self.info(component='codex-app-server', profile='release',
                             executable_sha256=cc.sha256_file(root / 'bin/codex-app-server'))
            (root / 'build-info.json').write_text(json.dumps(info, indent=1) + '\n')
            cc.check_receipt_identity('app-server', root, 'bin/codex-app-server', self.pin)
            (root / 'bin/codex-app-server').write_bytes(b'\x7fELF a different build')
            with self.assertRaises(cc.Refusal) as caught:
                cc.check_receipt_identity('app-server', root, 'bin/codex-app-server', self.pin)
            self.assertEqual(caught.exception.code, 'build_info.executable_digest')


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

    def test_verify_manifest_fails_closed_on_unqualified_pins(self):
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



KIT_COMMIT = commit('kit')


def kit_tarball(files=None, info_changes=None, extra=(), driver=None, top=None):
    """A cohort-kit tarball laid out like build_cohort_kit.py's, in memory."""
    top = top or f'cohort-kit-{cc.DRIVER_VERSION}'
    files = dict(files or {'setup/constellation_cohort.py': cc.RUNNING_DRIVER if driver is None else driver,
                           'setup/verify_cohort_evidence.py': b'# verifier\n', 'prepare_plan.py': b'# plan\n'})
    info = {'schema': 'constellation.cohort-kit-build-info/v1', 'component': 'cohort-kit',
            'version': cc.DRIVER_VERSION, 'source_commit': KIT_COMMIT, 'debug_assertions': False,
            'profile': 'release', 'files': {name: cc.digest_bytes(raw) for name, raw in files.items()}}
    info.update(info_changes or {})
    members = [member(f'{top}/', kind=tarfile.DIRTYPE), member(f'{top}/setup/', kind=tarfile.DIRTYPE),
               member(f'{top}/BUILD-INFO.json', json.dumps(info).encode(), mode=0o644)]
    members += [member(f'{top}/{name}', raw, mode=0o644) for name, raw in sorted(files.items())]
    members += list(extra)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        for info_member, data in members:
            tar.addfile(info_member, io.BytesIO(data) if data is not None else None)
    return buffer.getvalue()


KIT_PIN = {'package_version': cc.DRIVER_VERSION, 'source_commit': KIT_COMMIT}


class KitArchive(unittest.TestCase):
    """F1: the kit tarball is bound exhaustively to this running driver."""

    def check(self, raw, pin=KIT_PIN, stamped=KIT_COMMIT):
        return cc.check_kit_archive(raw, dict(pin), stamped=stamped)

    def refuses(self, raw, code, **kwargs):
        with self.assertRaises(cc.Refusal) as caught:
            self.check(raw, **kwargs)
        self.assertEqual(caught.exception.code, code, caught.exception.detail)
        return caught.exception.detail

    def test_released_kit_with_the_running_driver_passes(self):
        observed = self.check(kit_tarball())
        self.assertEqual((observed['source_commit'], observed['files'], observed['stamped_commit']),
                         (KIT_COMMIT, 3, KIT_COMMIT))

    def test_planted_unlisted_module_is_refused(self):
        planted = member(f'cohort-kit-{cc.DRIVER_VERSION}/setup/json.py', b'raise SystemExit("shadow")\n', mode=0o644)
        detail = self.refuses(kit_tarball(extra=[planted]), 'kit.unlisted_member')
        self.assertIn('setup/json.py', detail)

    def test_unlisted_directory_is_refused(self):
        extra = member(f'cohort-kit-{cc.DRIVER_VERSION}/hidden/', kind=tarfile.DIRTYPE)
        self.refuses(kit_tarball(extra=[extra]), 'kit.unlisted_member')

    def test_symlink_or_special_member_is_refused(self):
        link = member(f'cohort-kit-{cc.DRIVER_VERSION}/setup/json.py', kind=tarfile.SYMTYPE, link='/tmp/x.py')
        self.refuses(kit_tarball(extra=[link]), 'artifact.unsafe_member')
        fifo = member(f'cohort-kit-{cc.DRIVER_VERSION}/setup/pipe', kind=tarfile.FIFOTYPE)
        self.refuses(kit_tarball(extra=[fifo]), 'artifact.unsafe_member')

    def test_listed_file_missing_or_changed_is_refused(self):
        files = {'setup/constellation_cohort.py': cc.RUNNING_DRIVER, 'prepare_plan.py': b'# plan\n'}
        raw = kit_tarball(files=files, info_changes={'files': {**{k: cc.digest_bytes(v) for k, v in files.items()},
                                                               'setup/gone.py': cc.digest_bytes(b'x')}})
        self.refuses(raw, 'kit.missing_member')
        raw = kit_tarball(files=files, info_changes={'files': {'setup/constellation_cohort.py': cc.digest_bytes(
            cc.RUNNING_DRIVER), 'prepare_plan.py': cc.digest_bytes(b'# other\n')}})
        self.refuses(raw, 'kit.member_digest')

    def test_kit_whose_driver_differs_from_the_running_one_is_refused(self):
        self.refuses(kit_tarball(driver=b'# another driver\n'), 'kit.driver_differs')

    def test_build_info_commit_must_equal_the_manifest(self):
        self.refuses(kit_tarball(info_changes={'source_commit': commit('other')}), 'build_info.commit')

    def test_placeholder_commit_is_refused(self):
        for placeholder in ('0' * 40, 'f' * 40):
            self.refuses(kit_tarball(info_changes={'source_commit': placeholder}), 'pin.kit_commit',
                         pin={**KIT_PIN, 'source_commit': placeholder}, stamped=placeholder)

    def test_unreleased_driver_refuses_and_a_foreign_commit_refuses(self):
        self.refuses(kit_tarball(), 'kit.unreleased_driver', stamped=None)
        self.refuses(kit_tarball(), 'pin.kit_commit', stamped=commit('another release'))
        if b'\nKIT_SOURCE_COMMIT = None\n' in cc.RUNNING_DRIVER:
            self.assertIsNone(cc.KIT_SOURCE_COMMIT)  # a source checkout
        else:
            self.assertRegex(cc.KIT_SOURCE_COMMIT, cc.COMMIT)  # the released kit copy

    def test_verify_manifest_refuses_an_altered_kit_bundle(self):
        """The hostile review's k1 shape, end to end through verify-manifest."""
        planted = member(f'cohort-kit-{cc.DRIVER_VERSION}/setup/json.py', b'raise SystemExit("shadow")\n', mode=0o644)
        with tempfile.TemporaryDirectory() as tmp, patched(cc, KIT_SOURCE_COMMIT=KIT_COMMIT):
            directory = Path(tmp)
            raw_kit = kit_tarball(extra=[planted])
            (directory / 'cohort-kit-x.tar.gz').write_bytes(raw_kit)
            manifest = cc.load_manifest(raw(shipped_manifest(kit_commit=KIT_COMMIT,
                                                             kit_digest=cc.digest_bytes(raw_kit))))
            with self.assertRaises(cc.Refusal) as caught:
                pin = manifest['components']['cohort-kit']
                cc.check_artifact_bytes('cohort-kit', cc.load_artifact(directory / 'cohort-kit-x.tar.gz',
                                                                       pin['artifact_sha256']), pin)
            self.assertEqual(caught.exception.code, 'kit.unlisted_member')


class KitImportPath(unittest.TestCase):
    """F1: a kit file can never shadow the standard library."""

    def test_no_kit_module_is_named_like_a_standard_module(self):
        kit = Path(__file__).resolve().parent.parent
        names = {path.stem for path in list(kit.glob('*.py')) + list(kit.glob('setup/*.py'))}
        self.assertTrue(names)
        self.assertEqual(sorted(names & set(sys.stdlib_module_names)), [])

    def test_planted_json_module_is_never_imported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'setup').mkdir()
            marker = root / 'shadow-marker'
            (root / 'setup/json.py').write_text(f'open({str(marker)!r}, "a").write("imported\\n")\n'
                                                'raise SystemExit(99)\n')
            (root / 'setup/probe_module.py').write_text(
                'import json, sys\n'
                'def main(argv):\n'
                '    sys.stdout.write(json.dumps({"json": json.__file__, "argv": argv}))\n')
            argv = cc.kit_module([root / 'setup', root], 'probe_module', ['x'])
            self.assertEqual(argv[:4], [str(cc.PYTHON), '-I', '-S', '-c'])
            argv[0] = sys.executable
            done = __import__('subprocess').run(argv, capture_output=True, check=False, env={'PATH': '/usr/bin:/bin'})
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertFalse(marker.exists(), 'the planted setup/json.py was imported')
            self.assertNotIn(str(root), json.loads(done.stdout)['json'])
            # The pre-fix form (prepend) would have imported it: the test bites.
            prepend = (f'import sys; sys.path[:0]={[str(root / "setup"), str(root)]!r}; import probe_module; '
                       'probe_module.main(sys.argv[1:])')
            done = __import__('subprocess').run([argv[0], '-I', '-S', '-c', prepend, 'x'], capture_output=True,
                                                check=False, env={'PATH': '/usr/bin:/bin'})
            self.assertTrue(marker.exists(), prepend)


class HostPlumbing(unittest.TestCase):
    def test_nq_config_correlates_subject_and_scope_under_nq_directories(self):
        ids = cc.synthetic_identities('qual-a', 'fixture-review')
        text = cc.nq_config_text('qual-a', ids).decode()
        self.assertIn('subject = "host:cohort-qual-a-host"', text)
        self.assertIn('value = { id = "cohort-qual-a-host" }', text)
        self.assertIn('execution_account = "nq-helper"', text)
        self.assertIn('database_path = "/var/lib/nq/cohort-qual-a/nq.db"', text)
        self.assertNotIn('allow_same_identity_in_debug', text)

    def test_nq_unit_is_the_documented_capability_unit(self):
        argv = cc.nq_unit(['--config', '/etc/nq/x.toml', 'diagnostics', 'execute', 'h'])
        self.assertEqual(argv[:5], ['/usr/bin/systemd-run', '--quiet', '--wait', '--pipe', '--collect'])
        self.assertIn('--property=User=nq', argv)
        self.assertIn('--property=AmbientCapabilities=CAP_SETUID CAP_SETGID CAP_CHOWN CAP_KILL', argv)
        self.assertIn('--property=ReadWritePaths=/var/lib/nq /run/nq', argv)
        self.assertEqual(argv[argv.index('--') + 1:], ['/usr/bin/nq', '--config', '/etc/nq/x.toml', 'diagnostics',
                                                         'execute', 'h'])

    def test_children_drop_to_the_service_account_without_new_privileges(self):
        argv = cc.as_user('constellation', ['/bin/true'])
        self.assertEqual(argv[0], '/usr/bin/setpriv')
        self.assertIn('--reuid=constellation', argv)
        self.assertIn('--no-new-privs', argv)
        self.assertEqual(argv[-2:], ['--', '/bin/true'])

    def test_kit_modules_run_isolated_without_site_and_with_an_explicit_path(self):
        argv = cc.kit_module([Path('/opt/x/lib/maude-plan.pyz'), Path('/opt/kit')], 'prepare_plan', ['--output', Path('/o')])
        self.assertEqual(argv[:4], ['/usr/bin/python3.11', '-I', '-S', '-c'])
        # Appended after the standard library, never prepended (F1).
        self.assertIn("sys.path.extend(['/opt/x/lib/maude-plan.pyz', '/opt/kit'])", argv[4])
        self.assertNotIn('sys.path[:0]', argv[4])
        self.assertEqual(argv[5:], ['--output', '/o'])

    def test_transition_claims_are_create_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = {'records': Path(tmp)}
            cc.claim(paths, 'accept', {'at': 'now'})
            with self.assertRaises(cc.Refusal) as caught:
                cc.claim(paths, 'accept', {'at': 'later'})
            self.assertEqual(caught.exception.code, 'accept.exists')

    def test_unit_entry_always_leaves_one_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            class Args:
                records = tmp
            def refuse(args, records):
                raise cc.Refusal('observation.condition', 'present')
            self.assertEqual(cc.unit_entry(refuse, Args), 2)
            result = json.loads((Path(tmp) / 'unit-result.json').read_bytes())
            self.assertEqual((result['result'], result['code']), ('refused', 'observation.condition'))

    def test_identities_are_fresh_per_cohort_and_bound_to_the_cohort(self):
        first = cc.synthetic_identities('qual-a', 'fixture-review')
        second = cc.synthetic_identities('qual-a', 'fixture-review')
        self.assertNotEqual(first['occurrence'], second['occurrence'])
        self.assertNotEqual(first['draft_id'], second['draft_id'])
        self.assertEqual(first['campaign'], second['campaign'])
        self.assertRegex(first['draft_id'], r'draft_[0-9a-f]{32}\Z')
        self.assertEqual(first['run_id'], 'cohort-qual-a-review-001')


def join_fixture(root):
    """A settled occurrence in the native shapes (AG inspect, Docket inspect)."""
    binding = {'binding_id': 'sha256:' + 'b' * 64, 'campaign': 'sha256:' + 'c' * 64,
               'occurrence': '00000000-0000-4000-8000-000000000001', 'work': 'sha256:' + 'e' * 64}
    candidate = {'schema': 'ag.governed-loop.review-record-input/v1', 'campaign': binding['campaign'],
                 'occurrence': binding['occurrence'], 'binding_id': binding['binding_id'],
                 'review': {'binding_id': binding['binding_id'], 'result_digest': 'sha256:' + 'f' * 64}}
    candidate_raw = json.dumps(candidate).encode()
    key = {'campaign': binding['campaign'], 'occurrence': binding['occurrence']}
    issuance = {'schema': 'ag.governed-loop.issuance/v2', 'issuance': 'sha256:' + '1' * 64, 'key': key,
                'work': binding['work'], 'not_after_unix_ms': 2000}
    custody = {'issuance': issuance['issuance'], 'attempt': 'sha256:' + '2' * 64,
               'execution_standing': 'sha256:' + '3' * 64, 'standing_currentness': 'sha256:' + '4' * 64}
    settlement = {'settlement': 'sha256:' + '5' * 64, 'issuance': issuance['issuance'], 'attempt': custody['attempt'],
                  'outcome': 'success'}
    native = {
        'program_counter': 'settled_observation_required',
        'ag_inspect': {'current': {'state_digest': 'sha256:' + '6' * 64, 'state': {'settled_observation_required': {
            'dispatch': {'authorized': {'spend': {'spend': 'sha256:' + '7' * 64, 'key': key, 'consumed_at_unix_ms': 1000},
                                        'issuance': issuance}, 'custody': custody},
            'settlement': settlement}}},
            'replay': {'ag_spends': 1, 'docket_attempts': 1, 'settlements': 1}},
        'docket_inspect': {'requested_issuance': issuance['issuance'],
                           'record': {'status': 'settled', 'issuance': issuance, 'custody': custody, 'settlement': settlement}},
        'standing_snapshot': {'execution_standing': custody['execution_standing'],
                              'currentness': custody['standing_currentness']},
    }
    paths = {'plan': root / 'plan', 'review_output': root / 'review', 'continuation': root / 'continuation'}
    for directory in paths.values():
        directory.mkdir()
    (paths['plan'] / 'binding.json').write_text(json.dumps(binding))
    (paths['review_output'] / 'record-review-input.json').write_bytes(candidate_raw)
    (paths['continuation'] / 'accepted-record-review-input.json').write_bytes(candidate_raw)
    (paths['continuation'] / 'operator-acceptance.json').write_text(json.dumps(
        {'candidate_sha256': 'sha256:' + hashlib.sha256(candidate_raw).hexdigest()}))
    return native, paths


class EvidenceJoin(unittest.TestCase):
    def test_complete_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            native, paths = join_fixture(Path(tmp))
            join = cc.evidence_join(native, paths)
            self.assertTrue(join['complete'], join['checks'])
            self.assertEqual(join['not_after_unix_ms'], 2000)

    def test_each_broken_link_is_reported(self):
        cases = {
            'issuance_v2_not_after': lambda n: n['ag_inspect']['current']['state']['settled_observation_required']
            ['dispatch']['authorized']['issuance'].update(schema='ag.governed-loop.issuance/v1'),
            'issuance_ag_docket': lambda n: n['docket_inspect']['record']['issuance'].update(work='sha256:' + '9' * 64),
            'attempt_ag_docket': lambda n: n['docket_inspect']['record']['settlement'].update(attempt='sha256:' + '9' * 64),
            'standing_join': lambda n: n['standing_snapshot'].update(currentness='sha256:' + '9' * 64),
            'replay_once': lambda n: n['ag_inspect']['replay'].update(docket_attempts=2),
        }
        for check, damage in cases.items():
            with self.subTest(check), tempfile.TemporaryDirectory() as tmp:
                native, paths = join_fixture(Path(tmp))
                native = json.loads(json.dumps(native))
                damage(native)
                join = cc.evidence_join(native, paths)
                self.assertFalse(join['complete'])
                self.assertFalse(join['checks'][check])

    def test_not_after_must_follow_the_spend(self):
        with tempfile.TemporaryDirectory() as tmp:
            native, paths = join_fixture(Path(tmp))
            native['ag_inspect']['current']['state']['settled_observation_required']['dispatch']['authorized'][
                'issuance']['not_after_unix_ms'] = 1000
            self.assertFalse(cc.evidence_join(native, paths)['checks']['issuance_v2_not_after'])

    def test_other_accepted_candidate_breaks_the_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            native, paths = join_fixture(Path(tmp))
            (paths['continuation'] / 'accepted-record-review-input.json').write_bytes(b'{}')
            self.assertFalse(cc.evidence_join(native, paths)['checks']['candidate_accepted'])



# AG conformance vector v2-current (constellation-ag
# conformance/governed-loop-issuance/v2-vectors.json, mirrored by Docket).
VECTOR_BODY = (
    '{"issuance":"sha256:178d3f9b60ff4052535cf0984c5c26234b9f7ac648576d5056d4c48287375d49",'
    '"key":{"campaign":"sha256:1111111111111111111111111111111111111111111111111111111111111111",'
    '"occurrence":"00000000-0000-4000-8000-0000000000e1"},'
    '"mandate":"sha256:9999999999999999999999999999999999999999999999999999999999999999",'
    '"not_after_unix_ms":1790000060000,'
    '"observation":"sha256:7777777777777777777777777777777777777777777777777777777777777777",'
    '"program":"sha256:2222222222222222222222222222222222222222222222222222222222222222",'
    '"proposal":"sha256:3333333333333333333333333333333333333333333333333333333333333333",'
    '"schema":"ag.governed-loop.issuance/v2",'
    '"scope":"sha256:6666666666666666666666666666666666666666666666666666666666666666",'
    '"spend":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
    '"standing_resolution":"sha256:8888888888888888888888888888888888888888888888888888888888888888",'
    '"subject":"sha256:5555555555555555555555555555555555555555555555555555555555555555",'
    '"work":"sha256:4444444444444444444444444444444444444444444444444444444444444444",'
    '"work_schema":"conformance.exact-work/v1"}')
VECTOR_AUTHENTICATION = {
    'issuer_principal': 'conformance.ag-issuer',
    'signature': 'fcBIZs0NoZmmYqphD6EcJh5MPKbRI7-dos085YpTmfnkLSxBjektFswyKSR-CenBvmhvMjqxzJWQiWotF-rVDA',
    'signer_key_id': 'conformance.ag-issuer.v2-vectors',
    'signer_public_key': 'sllKLbsqnYtcVIRHSoWzizsv1p_ng46_Sb22IvtYLD0'}
VECTOR_TRUST = {'issuers': [{'issuer_principal': 'conformance.ag-issuer', 'key_id': 'conformance.ag-issuer.v2-vectors',
                             'public_key': 'sllKLbsqnYtcVIRHSoWzizsv1p_ng46_Sb22IvtYLD0'}]}


class RetainedIssuance(unittest.TestCase):
    def setUp(self):
        self.issuance = json.loads(VECTOR_BODY)
        self.record = {'issuance': self.issuance, 'authentication': dict(VECTOR_AUTHENTICATION)}

    def test_identity_is_the_ag_law(self):
        self.assertEqual(cc.issuance_identity(self.issuance), self.issuance['issuance'])
        extended = dict(self.issuance, not_after_unix_ms=self.issuance['not_after_unix_ms'] + 1)
        self.assertNotEqual(cc.issuance_identity(extended), self.issuance['issuance'])

    def test_not_after_shape_must_match_the_schema(self):
        for changed in (dict(self.issuance, not_after_unix_ms=None),
                        dict(self.issuance, schema='ag.governed-loop.issuance/v1')):
            with self.assertRaises(cc.Refusal) as caught:
                cc.issuance_identity(changed)
            self.assertEqual(caught.exception.code, 'evidence.issuance_identity')

    def test_canonical_body_is_the_signed_body(self):
        self.assertEqual(cc.canonical(self.issuance), VECTOR_BODY.encode())
        envelope = json.loads(cc.signed_issuance_envelope(self.record))
        self.assertEqual(envelope['schema'], 'ag.governed-loop.signed-issuance/v1')
        self.assertEqual(cc.b64url(envelope['body_b64']), VECTOR_BODY.encode())

    @unittest.skipUnless(cc.OPENSSL.is_file(), 'needs /usr/bin/openssl')
    def test_signature_verifies_and_a_changed_body_or_untrusted_key_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in 'abc':
                (Path(tmp) / name).mkdir()
            good = cc.verify_issuance_signature(self.record, VECTOR_TRUST, Path(tmp) / 'a')
            self.assertTrue(good['signature_valid'] and good['trusted_by_retained_trust'])
            changed = {'issuance': dict(self.issuance, not_after_unix_ms=self.issuance['not_after_unix_ms'] + 1),
                       'authentication': self.record['authentication']}
            self.assertFalse(cc.verify_issuance_signature(changed, VECTOR_TRUST, Path(tmp) / 'b')['signature_valid'])
            other = cc.verify_issuance_signature(self.record, {'issuers': []}, Path(tmp) / 'c')
            self.assertFalse(other['trusted_by_retained_trust'])


class RetainedTree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'export'
        (self.root / 'native').mkdir(parents=True)
        (self.root / 'JOIN.json').write_bytes(b'{"complete":true}\n')
        (self.root / 'native' / 'ag-inspect.json').write_bytes(b'{}\n')
        sums = ''.join(f'{hashlib.sha256((self.root / n).read_bytes()).hexdigest()}  {n}\n'
                       for n in ('JOIN.json', 'native/ag-inspect.json'))
        (self.root / 'SHA256SUMS').write_text(sums)

    def tearDown(self):
        self.tmp.cleanup()

    def refuses(self, code):
        with self.assertRaises(cc.Refusal) as caught:
            cc.check_tree(self.root, cc.read_sums(self.root, 'export'), 'export')
        self.assertEqual(caught.exception.code, code, caught.exception.detail)

    def test_intact_tree_verifies(self):
        cc.check_tree(self.root, cc.read_sums(self.root, 'export'), 'export')

    def test_changed_byte(self):
        (self.root / 'JOIN.json').write_bytes(b'{"complete":false}\n')
        self.refuses('export.digest_mismatch')

    def test_missing_file(self):
        (self.root / 'native' / 'ag-inspect.json').unlink()
        self.refuses('export.missing')

    def test_unlisted_file(self):
        (self.root / 'native' / 'extra.json').write_bytes(b'{}')
        self.refuses('export.unlisted')

    def test_symlink(self):
        (self.root / 'link').symlink_to(self.root / 'JOIN.json')
        self.refuses('export.unsafe')

    def test_malformed_or_escaping_sums(self):
        for line in ('xyz  JOIN.json\n', f'{"0" * 64}  ../etc/passwd\n', f'{"0" * 64}  SHA256SUMS\n'):
            (self.root / 'SHA256SUMS').write_text(line)
            with self.assertRaises(cc.Refusal) as caught:
                cc.read_sums(self.root, 'export')
            self.assertEqual(caught.exception.code, 'export.sums')

    def test_retained_copy_is_sealed_and_a_partial_copy_is_never_retained(self):
        entries = cc.read_sums(self.root, 'export')
        digest = cc.sha256_file(self.root / 'SHA256SUMS')
        attempt = Path(self.tmp.name) / 'upgrades' / 'qual-a-to-qual-b' / 'attempt-001'
        attempt.mkdir(parents=True)
        with patched(cc, RETAINED_ROOT=Path(self.tmp.name) / 'retained'):
            target = cc.retained_path('qual-a', digest)
            # An interrupted attempt's partial copy stays, and is not the target.
            (target.parent).mkdir(parents=True)
            (target.parent / '.partial-qual-a-to-qual-b-attempt-000').mkdir()
            self.assertEqual(cc.retain_copy(self.root, entries, target, attempt, digest, 'qual-a'), 'retained')
            self.assertEqual(stat_mode(target), 0o500)
            self.assertEqual(stat_mode(target / 'JOIN.json'), 0o400)
            marker = json.loads((target / 'RETAINED.json').read_text())
            self.assertEqual((marker['cohort'], marker['sha256sums']), ('qual-a', digest))
            cc.check_tree(target, entries, 'retained', extra_allowed=('SHA256SUMS', 'RETAINED.json'))
            self.assertEqual(cc.retain_copy(self.root, entries, target, attempt, digest, 'qual-a'), 'already_retained')
            self.assertTrue((target.parent / '.partial-qual-a-to-qual-b-attempt-000').is_dir())
            os.chmod(target, 0o700)
            os.chmod(target / 'JOIN.json', 0o600)
            (target / 'JOIN.json').write_bytes(b'{"complete":false}\n')
            with self.assertRaises(cc.Refusal) as caught:
                cc.retain_copy(self.root, entries, target, attempt, digest, 'qual-a')
            self.assertEqual(caught.exception.code, 'retained.digest_mismatch')


def stat_mode(path):
    return os.stat(path).st_mode & 0o777


class patched:
    """Temporarily replace module attributes (roots) for one test."""

    def __init__(self, module, **values):
        self.module, self.values, self.saved = module, values, {}

    def __enter__(self):
        for name, value in self.values.items():
            self.saved[name] = getattr(self.module, name)
            setattr(self.module, name, value)

    def __exit__(self, *exc):
        for name, value in self.saved.items():
            setattr(self.module, name, value)


UNAVAILABLE = {'schema': 'ag.governed-loop.read-only-verification/v1', 'status': 'enrolled-file-unavailable',
               'unavailable': [{'identity': 'sha256:' + '1' * 64, 'path': '/opt/x/validator.pyz',
                                'role': 'shared_admission.plan_validator'}]}
INSPECTED = {'current': {'state': {'settled_observation_required': {}}, 'state_digest': 'sha256:' + '2' * 64}}


class AgReadOnly(unittest.TestCase):
    """AG 58122ce read-only exits: 0 verified, 3 verified except named files."""

    def outcome(self, code, stdout=INSPECTED, stderr=b''):
        out = stdout if isinstance(stdout, bytes) else json.dumps(stdout).encode()
        return cc.ag_read_only_outcome(code, out, stderr)

    def report(self, value=UNAVAILABLE):
        return b'warning: other line\n' + cc.AG_UNAVAILABLE_PREFIX.encode() + json.dumps(value).encode() + b'\n'

    def test_exit_zero_is_verified(self):
        value = self.outcome(0)
        self.assertEqual((value['status'], value['json'], value['unavailable']), ('verified', INSPECTED, None))

    def test_exit_three_names_the_files_and_is_not_verified(self):
        value = self.outcome(3, stderr=self.report())
        self.assertEqual(value['status'], 'verified_except_unavailable')
        self.assertEqual(value['unavailable'], UNAVAILABLE['unavailable'])
        self.assertEqual(value['json'], INSPECTED)

    def test_exit_three_without_a_typed_report_is_refused(self):
        for stderr in (b'', b'enrolled file unavailable: not json\n',
                       self.report(dict(UNAVAILABLE, schema='other')), self.report(dict(UNAVAILABLE, unavailable=[]))):
            self.assertEqual(self.outcome(3, stderr=stderr)['status'], 'refused', stderr)
        self.assertEqual(self.outcome(3, stdout=b'', stderr=self.report())['status'], 'refused')

    def test_other_exits_are_refused(self):
        for code in (1, 2, 4, -9):
            self.assertEqual(self.outcome(code, stderr=self.report())['status'], 'refused')
        self.assertEqual(self.outcome(0, stdout=b'not json')['status'], 'refused')

    def test_status_refuses_a_live_cohort_with_an_unavailable_enrolled_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            deployment = Path(tmp)
            (deployment / 'ag.sqlite').write_bytes(b'')
            programs = type('P', (), {'ag': Path('/opt/ag-loopctl'), 'docket': Path('/opt/docket')})()
            done = __import__('subprocess').CompletedProcess([], 3, json.dumps(INSPECTED).encode(), self.report())
            with patched(cc.subprocess, run=lambda *a, **k: done):
                with self.assertRaises(cc.Refusal) as caught:
                    cc.native_read(programs, {'deployment': deployment, 'ports': deployment})
        self.assertEqual(caught.exception.code, 'ag.enrolled_file_unavailable')
        self.assertIn('shared_admission.plan_validator', caught.exception.detail)


class VerifiedBytes(unittest.TestCase):
    """F3: hash and use the same bytes; check every extracted file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / 'sources').mkdir()
        self.genuine = self.dir / 'sources' / 'genuine.tar.gz'
        tarball(self.genuine, [member('docket-0.1.0/', kind=tarfile.DIRTYPE),
                               member('docket-0.1.0/bin/docket', b'\x7fELF genuine'),
                               member('docket-0.1.0/SHA256SUMS',
                                      (hashlib.sha256(b'\x7fELF genuine').hexdigest() + '  bin/docket\n').encode(),
                                      mode=0o644)])
        self.evil = self.dir / 'sources' / 'evil.tar.gz'
        tarball(self.evil, [member('docket-0.1.0/', kind=tarfile.DIRTYPE),
                            member('docket-0.1.0/bin/docket', b'#!/bin/sh\necho forged build info\n')])
        self.expected = cc.sha256_file(self.genuine)

    def tearDown(self):
        self.tmp.cleanup()

    def test_substitution_between_locate_and_use_is_refused(self):
        artifact = self.dir / 'docket.tar.gz'
        artifact.write_bytes(self.genuine.read_bytes())
        manifest = {'components': {'docket': {'artifact_sha256': self.expected}}}
        with patched(cc, COMPONENTS={'docket': cc.COMPONENTS['docket']}):
            located = cc.locate_artifacts(manifest, self.dir)
        self.assertEqual(located['docket'], artifact)
        os.replace(self.evil, artifact)  # the swap lands after the check
        with self.assertRaises(cc.Refusal) as caught:
            cc.load_artifact(located['docket'], self.expected)
        self.assertEqual(caught.exception.code, 'artifact.changed')

    def test_substitution_after_the_read_changes_nothing(self):
        artifact = self.dir / 'docket.tar.gz'
        artifact.write_bytes(self.genuine.read_bytes())
        raw = cc.load_artifact(artifact, self.expected)
        os.replace(self.evil, artifact)
        digests = {}
        cc.safe_extract(raw, self.dir / 'out', digests)
        cc.verify_extracted(self.dir / 'out', digests)
        self.assertEqual((self.dir / 'out/docket-0.1.0/bin/docket').read_bytes(), b'\x7fELF genuine')
        root = cc.artifact_root(self.dir / 'out')
        relative = {key.split('/', 1)[1]: value for key, value in digests.items()}
        self.assertEqual(cc.check_component_receipt('docket', root, relative), 'SHA256SUMS')

    def test_extracted_tree_changed_afterwards_is_refused(self):
        digests = {}
        cc.safe_extract(self.genuine.read_bytes(), self.dir / 'out', digests)
        (self.dir / 'out/docket-0.1.0/bin/docket').write_bytes(b'#!/bin/sh\n')
        with self.assertRaises(cc.Refusal) as caught:
            cc.verify_extracted(self.dir / 'out', digests)
        self.assertEqual(caught.exception.code, 'artifact.extracted_mismatch')
        (self.dir / 'out/docket-0.1.0/bin/docket').write_bytes(b'\x7fELF genuine')
        (self.dir / 'out/docket-0.1.0/bin/extra').write_bytes(b'x')
        with self.assertRaises(cc.Refusal):
            cc.verify_extracted(self.dir / 'out', digests)
        os.unlink(self.dir / 'out/docket-0.1.0/bin/extra')
        os.symlink('/bin/sh', self.dir / 'out/docket-0.1.0/bin/link')
        with self.assertRaises(cc.Refusal):
            cc.verify_extracted(self.dir / 'out', digests)

    def test_component_receipt_must_list_every_file_with_its_digest(self):
        root = self.dir / 'r'
        (root / 'bin').mkdir(parents=True)
        digests = {'bin/docket': cc.digest_bytes(b'a'), 'README.md': cc.digest_bytes(b'b')}
        (root / 'SHA256SUMS').write_text(hashlib.sha256(b'a').hexdigest() + '  bin/docket\n')
        with self.assertRaises(cc.Refusal) as caught:
            cc.check_component_receipt('docket', root, digests)
        self.assertEqual(caught.exception.code, 'artifact.receipt_mismatch')
        (root / 'SHA256SUMS').unlink()
        (root / 'BUILD-INFO.json').write_text(json.dumps({'binaries': {'nightshift': {
            'path': 'bin/docket', 'sha256': hashlib.sha256(b'other').hexdigest()}}}))
        with self.assertRaises(cc.Refusal) as caught:
            cc.check_component_receipt('nightshift', root, digests)
        self.assertEqual(caught.exception.code, 'artifact.receipt_mismatch')


def build_deb(root, *, conffile=True, readme=b'nq readme\n'):
    """A small nq-ng .deb, or None when dpkg-deb is unavailable."""
    import shutil as _shutil
    import subprocess as _subprocess
    if _shutil.which('dpkg-deb') is None:
        return None
    tree = root / 'deb-tree'
    (tree / 'DEBIAN').mkdir(parents=True)
    (tree / 'usr/bin').mkdir(parents=True)
    (tree / 'usr/share/doc/nq-ng').mkdir(parents=True)
    (tree / 'etc/nq').mkdir(parents=True)
    (tree / 'usr/bin/nq').write_bytes(b'\x7fELF nq\n')
    os.chmod(tree / 'usr/bin/nq', 0o755)
    (tree / 'usr/share/doc/nq-ng/README.md').write_bytes(readme)
    (tree / 'etc/nq/defaults.toml').write_bytes(b'schema = "nq.config.v1"\n')
    os.symlink('nq', tree / 'usr/bin/nq-link')
    (tree / 'DEBIAN/control').write_text('Package: nq-ng\nVersion: 0.2.0\nArchitecture: amd64\n'
                                         'Maintainer: test\nDescription: test package\n')
    if conffile:
        (tree / 'DEBIAN/conffiles').write_text('/etc/nq/defaults.toml\n')
    target = root / 'nq-ng.deb'
    _subprocess.run(['dpkg-deb', '--root-owner-group', '-Zgzip', '--build', str(tree), str(target)], check=True,
                    capture_output=True)
    return target


class NqPackage(unittest.TestCase):
    """F2: an installed nq-ng must equal the pinned package file by file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        deb = build_deb(self.dir)
        if deb is None:
            self.skipTest('dpkg-deb is not available')
        self.raw = deb.read_bytes()
        self.contents = cc.deb_contents(self.raw)
        self.root = self.dir / 'host'
        with tarfile.open(fileobj=io.BytesIO(__import__('subprocess').run(
                ['dpkg-deb', '--fsys-tarfile', str(deb)], capture_output=True, check=True).stdout)) as tar:
            if hasattr(tarfile, 'data_filter'):
                tar.extractall(self.root, filter='data')
            else:
                tar.extractall(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_contents_are_read_from_the_verified_bytes(self):
        self.assertEqual((self.contents['package'], self.contents['version'], self.contents['architecture']),
                         ('nq-ng', '0.2.0', 'amd64'))
        self.assertEqual(self.contents['conffiles'], ['/etc/nq/defaults.toml'])
        self.assertEqual(self.contents['files']['/usr/bin/nq']['sha256'], cc.digest_bytes(b'\x7fELF nq\n'))
        self.assertEqual(self.contents['files']['/usr/bin/nq-link'], {'type': 'symlink', 'target': 'nq'})

    def test_identical_installation_passes(self):
        self.assertEqual(cc.installed_package_mismatches(self.contents, self.root), [])

    def test_edited_file_conffile_and_link_are_each_refused(self):
        (self.root / 'usr/share/doc/nq-ng/README.md').write_bytes(b'nq readme\nappended\n')
        (self.root / 'etc/nq/defaults.toml').write_bytes(b'edited\n')
        os.unlink(self.root / 'usr/bin/nq-link')
        os.symlink('/bin/sh', self.root / 'usr/bin/nq-link')
        os.unlink(self.root / 'usr/bin/nq')
        mismatches = cc.installed_package_mismatches(self.contents, self.root)
        self.assertEqual(len(mismatches), 4, mismatches)
        self.assertTrue(any('(conffile)' in line for line in mismatches))

    def test_forged_package_is_refused_although_dpkg_verify_is_clean(self):
        forged_dir = self.dir / 'forged'
        forged_dir.mkdir()
        forged = cc.deb_contents(build_deb(forged_dir, readme=b'nq readme\nforged\n').read_bytes())
        forged_root = self.dir / 'forged-host'
        (forged_root / 'usr/share/doc/nq-ng').mkdir(parents=True)
        # The host holds the forged package; the pin is the genuine one.
        for path, entry in self.contents['files'].items():
            source, target = self.root / path.lstrip('/'), forged_root / path.lstrip('/')
            if entry['type'] == 'dir':
                target.mkdir(parents=True, exist_ok=True)
            elif entry['type'] == 'symlink':
                os.symlink(entry['target'], target)
            else:
                target.write_bytes(source.read_bytes())
        (forged_root / 'usr/share/doc/nq-ng/README.md').write_bytes(b'nq readme\nforged\n')
        self.assertEqual(cc.installed_package_mismatches(forged, forged_root), [])
        state = {'status': 'install ok installed', 'version': '0.2.0', 'architecture': 'amd64'}
        clean = __import__('subprocess').CompletedProcess([], 0, b'', b'')
        with patched(cc.subprocess, run=lambda *a, **k: clean):
            with self.assertRaises(cc.Refusal) as caught:
                cc.check_installed_nq(self.contents, state, forged_root)
            self.assertEqual(caught.exception.code, 'nq.installed_mismatch')
            self.assertIn('README.md', caught.exception.detail)
            self.assertEqual(cc.check_installed_nq(self.contents, state, self.root)['dpkg_verify_lines'], 0)

    def test_dpkg_verify_output_is_parsed_not_its_exit_status(self):
        state = {'status': 'install ok installed', 'version': '0.2.0', 'architecture': 'amd64'}
        tampered = __import__('subprocess').CompletedProcess(
            [], 0, b'??5?????? c /usr/share/doc/nq-ng/copyright\n', b'')
        self.assertEqual(cc.dpkg_verify_lines(tampered.stdout), ['??5?????? c /usr/share/doc/nq-ng/copyright'])
        with patched(cc.subprocess, run=lambda *a, **k: tampered):
            with self.assertRaises(cc.Refusal) as caught:
                cc.check_installed_nq(self.contents, state, self.root)
        self.assertEqual(caught.exception.code, 'nq.installed_mismatch')
        self.assertIn('copyright', caught.exception.detail)

    def test_other_version_or_half_installed_is_refused(self):
        for state in ({'status': 'install ok installed', 'version': '0.1.0', 'architecture': 'amd64'},
                      {'status': 'install ok half-configured', 'version': '0.2.0', 'architecture': 'amd64'}):
            with self.assertRaises(cc.Refusal) as caught:
                cc.check_installed_nq(self.contents, state, self.root)
            self.assertEqual(caught.exception.code, 'nq.installed_mismatch')


def acceptance_fixture(root, expires_in_ms, route='fixture-review'):
    paths = {'records': root / 'driver', 'plan': root / 'plan', 'review_output': root / 'review'}
    for directory in paths.values():
        directory.mkdir()
    text = b'Constellation cohort qual-a reviewed copy.\n'
    (paths['records'] / 'identities.json').write_text(json.dumps(
        {'reviewed_text_base64': __import__('base64').b64encode(text).decode(), 'review_route': route}))
    plan = {'scratch_root': '/var/lib/constellation/cohorts/qual-a/scratch',
            'reviewed_text_digest': cc.digest_bytes(text), 'reviewed_text_byte_length': len(text)}
    (paths['plan'] / 'executor-config.json').write_text(json.dumps(
        {'executor_plan_base64': __import__('base64').b64encode(json.dumps(plan).encode()).decode()}))
    result = {'verdict': 'accepted', 'findings': [{'code': 'fixture.accepted', 'summary': 'scripted verdict'}]}
    now = cc.now_ms()
    candidate = {'review': {'verdict': 'accepted', 'reviewer_id': 'fixture-deterministic-reviewer-not-independent',
                            'reviewed_at_unix_ms': now - 1000, 'expires_at_unix_ms': now + expires_in_ms},
                 'artifacts': {'result_bytes_base64': __import__('base64').b64encode(json.dumps(result).encode()).decode()}}
    (paths['review_output'] / 'record-review-input.json').write_text(json.dumps(candidate))
    return paths, text


class Acceptance(unittest.TestCase):
    """Newcomer fixes: a readable acceptance, its deadline, and clean refusals."""

    def test_view_shows_text_destination_bytes_and_time_left(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, text = acceptance_fixture(Path(tmp), 240_000)
            view = cc.acceptance_view(paths, 'qual-a')
        will = view['will_write']
        self.assertEqual((will['path'], will['bytes'], will['text']),
                         ('/var/lib/constellation/cohorts/qual-a/scratch/result.txt', len(text), text.decode()))
        self.assertTrue(will['bound_by_plan'])
        self.assertEqual(view['review']['findings'], ['scripted verdict'])
        self.assertIn('scripted', view['review']['note'])
        self.assertFalse(view['deadline']['expired'])
        self.assertTrue(230 <= view['deadline']['seconds_remaining'] <= 240)
        self.assertTrue(view['deadline']['accept_before'].endswith('Z'))
        self.assertIn('--candidate-sha256 ' + view['candidate_sha256'], view['accept_command'])

    def test_expired_review_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = acceptance_fixture(Path(tmp), -5000)
            view = cc.acceptance_view(paths, 'qual-a')
        self.assertTrue(view['deadline']['expired'])
        self.assertEqual(view['deadline']['seconds_remaining'], 0)
        self.assertIn('fresh cohort', cc.status_next({'review': {'exit_code': 0}, 'accept': 'not_started',
                                                      'acceptance': view, 'result_file': {}}))

    @unittest.skipIf(os.geteuid() == 0, 'runs as an unprivileged account')
    def test_unprivileged_status_is_a_clean_refusal(self):
        out = io.StringIO()
        with redirect_stdout(out):
            status = cc.main(['status', '--cohort', 'qual-a'])
        self.assertEqual((status, json.loads(out.getvalue())['code']), (2, 'host.not_root'))

    def test_permission_error_is_one_json_refusal(self):
        def denied(args):
            raise PermissionError(13, 'Permission denied', '/var/lib/constellation/cohorts/qual-a/driver')
        out = io.StringIO()
        with patched(cc, COMMANDS={**cc.COMMANDS, 'evidence': denied}), redirect_stdout(out):
            status = cc.main(['evidence', '--cohort', 'qual-a', '--output', '/tmp/x'])
        value = json.loads(out.getvalue())
        self.assertEqual(status, 2)
        self.assertIn(value['code'], ('host.not_root', 'host.permission'))


class Help(unittest.TestCase):
    def test_help_hides_the_unit_entry_points_and_documents_every_option(self):
        top = cc.parser()
        text = top.format_help()
        self.assertNotIn('SUPPRESS', text)
        self.assertNotIn('_review-unit', text)
        self.assertNotIn('_accept-unit', text)
        for name, sub in top._subparsers._group_actions[0].choices.items():
            if name.startswith('_'):
                continue
            self.assertIn(name, text)
            for action in sub._actions:
                if action.option_strings and action.dest != 'help':
                    self.assertTrue(action.help, f'{name} {action.option_strings} has no help')


class UpgradeJournal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        me = __import__('pwd').getpwuid(os.getuid()).pw_name
        self.patch = patched(cc, UPGRADE_ROOT=base / 'upgrades', RETAINED_ROOT=base / 'retained',
                             QUARANTINE_ROOT=base / 'quarantine', STATE_ROOT=base / 'cohorts',
                             NQ_STATE_DIR=base / 'nq', NQ_CONFIG_DIR=base / 'etc-nq', NQ_ACCOUNT=me)
        self.patch.__enter__()
        for directory in (cc.STATE_ROOT / 'qual-a' / 'ports', cc.NQ_STATE_DIR / 'cohort-qual-a', cc.NQ_CONFIG_DIR):
            directory.mkdir(parents=True)
        (cc.STATE_ROOT / 'qual-a' / 'ports' / 'issuer.pk8').write_bytes(b'synthetic')
        (cc.NQ_CONFIG_DIR / 'cohort-qual-a.toml').write_bytes(b'# synthetic\n')

    def tearDown(self):
        self.patch.__exit__()
        self.tmp.cleanup()

    def attempt(self, name='attempt-001'):
        path = cc.upgrade_dir('qual-a', 'qual-b') / name
        path.mkdir(parents=True)
        cc.journal_write(path, 'begin', {'from': 'qual-a', 'to': 'qual-b'})
        return path

    def test_an_interrupted_upgrade_blocks_the_successor_init_and_retires_the_source_id(self):
        self.attempt()
        [journal] = cc.journals()
        self.assertEqual((journal['from'], journal['to'], journal['interrupted']), ('qual-a', 'qual-b', ['attempt-001']))
        with self.assertRaises(cc.Refusal) as caught:
            cc.upgrade_into('qual-b')
        self.assertEqual(caught.exception.code, 'upgrade.interrupted')
        with self.assertRaises(cc.Refusal) as caught:
            cc.check_not_retired('qual-a')
        self.assertEqual(caught.exception.code, 'cohort.retired')
        cc.check_not_retired('qual-b')

    def test_a_completed_upgrade_is_the_successor_predecessor(self):
        path = self.attempt()
        cc.journal_write(path, 'completed', {'from': 'qual-a', 'to': 'qual-b', 'retained': '/r',
                                             'retained_sha256sums': 'sha256:' + '0' * 64})
        self.assertEqual(cc.upgrade_into('qual-b')['from'], 'qual-a')
        self.assertIsNone(cc.upgrade_into('qual-c'))

    def test_quarantine_moves_never_delete_and_leave_a_tombstone(self):
        path = self.attempt()
        moved = cc.quarantine('qual-a', path, Path('/retained'))
        self.assertEqual([entry['moved_by'] for entry in moved], ['attempt-001'] * 3)
        self.assertEqual((cc.QUARANTINE_ROOT / 'qual-a' / 'state' / 'ports' / 'issuer.pk8').read_bytes(), b'synthetic')
        self.assertTrue((cc.NQ_STATE_DIR / 'quarantine-cohort-qual-a' / 'cohort-qual-a.toml').is_file())
        marker = cc.STATE_ROOT / 'qual-a'
        self.assertTrue(marker.is_file())
        self.assertEqual(json.loads(marker.read_text())['schema'], cc.TOMBSTONE_SCHEMA)
        self.assertEqual(cc.retired_state('qual-a'), cc.QUARANTINE_ROOT / 'qual-a' / 'state')
        # A resumed attempt finds everything already moved.
        again = cc.quarantine('qual-a', cc.upgrade_dir('qual-a', 'qual-b') / 'attempt-002', Path('/retained'))
        self.assertEqual([entry['moved_by'] for entry in again], ['an earlier attempt'] * 3)

    def test_quarantine_refuses_a_conflict_or_a_loss(self):
        path = self.attempt()
        (cc.QUARANTINE_ROOT / 'qual-a' / 'state').mkdir(parents=True)
        with self.assertRaises(cc.Refusal) as caught:
            cc.quarantine('qual-a', path, Path('/retained'))
        self.assertEqual(caught.exception.code, 'upgrade.quarantine_conflict')
        os.rmdir(cc.QUARANTINE_ROOT / 'qual-a' / 'state')
        __import__('shutil').rmtree(cc.STATE_ROOT / 'qual-a')
        with self.assertRaises(cc.Refusal) as caught:
            cc.quarantine('qual-a', path, Path('/retained'))
        self.assertEqual(caught.exception.code, 'upgrade.quarantine_lost')

    def test_restored_view_is_private_and_read_only(self):
        argv = cc.restored_view(Path('/q/state'), 'qual-a', Path('/s/stage'), ['/bin/true'])
        self.assertEqual(argv[:5], ['/usr/bin/unshare', '--mount', '--propagation', 'private', '--'])
        self.assertIn('remount,bind,ro', argv[7])
        self.assertEqual(argv[-5:], ['/q/state', '/s/stage', str(cc.STATE_ROOT), 'qual-a', '/bin/true'])

    def test_upgrade_needs_an_export_and_names_no_automatic_resume(self):
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()), __import__('contextlib').redirect_stderr(io.StringIO()):
                cc.parser().parse_args(['upgrade', '--from-cohort', 'qual-a', '--to-cohort', 'qual-b'])
        options = {action.dest for action in cc.parser()._subparsers._group_actions[0].choices['upgrade']._actions}
        self.assertEqual(options, {'help', 'from_cohort', 'to_cohort', 'export', 'after_interrupted'})


if __name__ == '__main__':
    unittest.main()
