"""Unit tests for the in-kit evidence verifier.

Run with the target interpreter (-I implies -P, so run the file itself):

    /usr/bin/python3.11 -I -S -B test_verify_cohort_evidence.py -v

Each test builds a small synthetic evidence bundle in the exported layout and
signs its issuance with a throwaway Ed25519 key made by /usr/bin/openssl. No
root, network, component artifact or real cohort is needed.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_cohort_evidence as v  # noqa: E402

REVIEWED = b'synthetic reviewed text for the verifier\n'


def digest(raw: bytes) -> str:
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


def openssl(*args: str, data: bytes | None = None) -> bytes:
    return subprocess.run([v.OPENSSL, *args], input=data, capture_output=True, check=True).stdout


class Bundle:
    """A synthetic, internally consistent evidence export."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.key = root.parent / 'issuer.pem'
        openssl('genpkey', '-algorithm', 'ed25519', '-out', str(self.key))
        self.public = openssl('pkey', '-in', str(self.key), '-pubout', '-outform', 'DER')[-32:]
        key = {'campaign': digest(b'campaign'), 'occurrence': digest(b'occurrence')}
        plan_document = digest(b'plan document')
        self.binding = {'binding_id': digest(b'binding'), **key, 'work': digest(b'work'),
                        'plan_document_digest': plan_document,
                        'artifacts': {'plan_document': {'sha256': plan_document}}}
        self.candidate = json.dumps({'binding_id': self.binding['binding_id'], **key,
                                     'review': {'binding_id': self.binding['binding_id']}}).encode()
        self.spend = {'key': key, 'consumed_at_unix_ms': 1_000}
        issuance = {'schema': 'ag.governed-loop.issuance/v2', 'key': key, 'mandate': digest(b'mandate'),
                    'observation': digest(b'observation'), 'program': digest(b'program'),
                    'proposal': digest(b'proposal'), 'scope': digest(b'scope'), 'spend': digest(b'spend'),
                    'standing_resolution': digest(b'standing'), 'subject': digest(b'subject'),
                    'work': self.binding['work'], 'work_schema': 'maude.reviewed-local-copy/v1',
                    'not_after_unix_ms': 2_000}
        self.issuance = self.identify(issuance)
        self.custody = {'issuance': self.issuance['issuance'], 'attempt': digest(b'attempt'),
                        'execution_standing': digest(b'execution standing'), 'standing_currentness': 'current'}
        self.settlement = {'attempt': self.custody['attempt'], 'outcome': 'success'}
        self.trust = {'issuers': [{'issuer_principal': 'synthetic-issuer', 'key_id': 'synthetic-issuer-k1',
                                   'public_key': b64url(self.public)}]}
        self.replay = {'ag_spends': 1, 'docket_attempts': 1, 'settlements': 1}
        self.result = REVIEWED

    def identify(self, issuance: dict) -> dict:
        basis = {name: issuance[name] for name in ('key', 'mandate', 'observation', 'program', 'proposal', 'scope',
                                                   'spend', 'standing_resolution', 'subject', 'work', 'work_schema',
                                                   'not_after_unix_ms')}
        return dict(issuance, issuance=v.ag_digest('ag.governed-loop.issuance/v2', v.jcs(basis)))

    def sign(self, issuance: dict) -> str:
        message = self.root.parent / 'message'
        message.write_bytes(v.SIGNATURE_PREFIX + v.jcs(issuance))
        return b64url(openssl('pkeyutl', '-sign', '-inkey', str(self.key), '-rawin', '-in', str(message)))

    def write(self, signed_issuance: dict | None = None) -> Path:
        """Write the bundle; `signed_issuance` is what the signature covers."""
        signature = self.sign(signed_issuance or self.issuance)
        state = {'settled_observation_required': {
            'dispatch': {'authorized': {'spend': self.spend, 'issuance': self.issuance}, 'custody': self.custody},
            'settlement': self.settlement}}
        plan = {'plan_document_digest': self.binding['plan_document_digest'], 'reviewed_text_digest': digest(REVIEWED),
                'reviewed_text_byte_length': len(REVIEWED)}
        files = {
            'state/plan/binding.json': self.binding,
            'caller/review-001/record-review-input.json': self.candidate,
            'caller/continuation-001/accepted-record-review-input.json': self.candidate,
            'caller/continuation-001/operator-acceptance.json': {'candidate_sha256': digest(self.candidate),
                                                                 'human_attestation': False},
            'native/ag-inspect.json': {'current': {'state': state, 'state_digest': digest(b'state')},
                                       'replay': self.replay},
            'native/docket-inspect.json': {'requested_issuance': self.issuance['issuance'], 'record': {
                'issuance': self.issuance, 'custody': self.custody, 'settlement': self.settlement, 'status': 'settled',
                'authentication': {'issuer_principal': 'synthetic-issuer', 'signer_key_id': 'synthetic-issuer-k1',
                                   'signer_public_key': b64url(self.public), 'signature': signature}}},
            'native/standing-snapshot.json': {'execution_standing': self.custody['execution_standing'],
                                              'currentness': 'current'},
            'state/plan/executor-config.json': {
                'executor_plan_base64': base64.b64encode(json.dumps(plan).encode()).decode()},
            'native/result-file.json': {'content_base64': base64.b64encode(self.result).decode(),
                                        'scratch_entries': ['result.txt']},
            'state/ports/docket-trust.json': self.trust,
        }
        lines = []
        for name, value in sorted(files.items()):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
            lines.append(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}\n')
        (self.root / 'SHA256SUMS').write_text(''.join(lines))
        return self.root


def run_cli(root: Path) -> tuple[int, dict]:
    done = subprocess.run([sys.executable, '-I', '-S', '-B', str(HERE / 'verify_cohort_evidence.py'), '--evidence',
                           str(root)], capture_output=True, check=False)
    return done.returncode, json.loads(done.stdout)


@unittest.skipUnless(Path(v.OPENSSL).is_file(), 'needs /usr/bin/openssl')
class Verifier(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bundle = Bundle(Path(self.tmp.name) / 'evidence')

    def tearDown(self):
        self.tmp.cleanup()

    def failed(self, *checks: str) -> dict:
        code, value = run_cli(self.bundle.write())
        self.assertEqual((code, value['result']), (1, 'failed'), value)
        for name in checks:
            self.assertIs(value['checks'][name], False, name)
        return value

    def test_genuine_bundle_passes_and_a_substituted_plan_digest_refuses(self):
        code, value = run_cli(self.bundle.write())
        self.assertEqual((code, value['result']), (0, 'passed'), value)
        self.assertEqual(value['digest_mismatches'], [])
        self.assertEqual(value['mismatched_plan_digest'], 'refused')
        self.assertTrue(all(value['checks'].values()))
        self.assertEqual(value['sha256sums_sha256'], digest((self.bundle.root / 'SHA256SUMS').read_bytes()))

    def test_changed_byte_is_a_digest_mismatch(self):
        root = self.bundle.write()
        with (root / 'native/ag-inspect.json').open('ab') as stream:
            stream.write(b' ')
        code, value = run_cli(root)
        self.assertEqual((code, value['digest_mismatches']), (1, ['native/ag-inspect.json']))

    def test_missing_or_escaping_listed_file_fails(self):
        root = self.bundle.write()
        (root / 'native/standing-snapshot.json').unlink()
        self.assertIn('native/standing-snapshot.json', v.sums(root))
        with (root / 'SHA256SUMS').open('a') as stream:
            stream.write('0' * 64 + '  ../outside\n')
        self.assertIn('../outside', v.sums(root))

    def test_extended_not_after_breaks_identity_and_signature(self):
        signed = self.bundle.issuance
        self.bundle.issuance = dict(signed, not_after_unix_ms=signed['not_after_unix_ms'] + 1)
        self.bundle.custody['issuance'] = signed['issuance']
        code, value = run_cli(self.bundle.write(signed_issuance=signed))
        self.assertEqual(code, 1)
        self.assertFalse(value['checks']['issuance_identity'])
        self.assertFalse(value['checks']['issuance_signature'])

    def test_signature_over_other_bytes_fails(self):
        other = self.bundle.identify(dict(self.bundle.issuance, mandate=digest(b'other mandate')))
        code, value = run_cli(self.bundle.write(signed_issuance=other))
        self.assertEqual(code, 1)
        self.assertFalse(value['checks']['issuance_signature'])
        self.assertTrue(value['checks']['issuance_identity'])

    def test_key_absent_from_the_docket_trust_fails(self):
        self.bundle.trust = {'issuers': [dict(self.bundle.trust['issuers'][0], key_id='another-key')]}
        self.failed('issuance_signature')

    def test_result_bytes_must_equal_the_reviewed_bytes(self):
        self.bundle.result = REVIEWED.replace(b'text', b'TEXT')
        self.failed('result_bytes')

    def test_more_than_one_spend_or_a_failed_settlement_fails(self):
        self.bundle.replay = dict(self.bundle.replay, ag_spends=2)
        self.failed('once')
        self.bundle.replay['ag_spends'] = 1
        self.bundle.settlement = dict(self.bundle.settlement, outcome='failure')
        self.failed('settlement')

    def test_not_after_before_the_spend_fails(self):
        self.bundle.spend = dict(self.bundle.spend, consumed_at_unix_ms=5_000)
        self.failed('issuance_v2_not_after')

    def test_other_accepted_candidate_fails(self):
        root = self.bundle.write()
        accepted = root / 'caller/continuation-001/accepted-record-review-input.json'
        accepted.write_bytes(accepted.read_bytes() + b' ')
        self.assertFalse(v.joins(root)['candidate_accepted'])

    def test_incomplete_bundle_fails_with_the_reason(self):
        root = self.bundle.write()
        (root / 'state/plan/binding.json').unlink()
        code, value = run_cli(root)
        self.assertEqual((code, value['result']), (1, 'failed'))
        self.assertIn('binding.json', value['error'])

    def test_joins_are_computed_without_the_bundle_join(self):
        root = self.bundle.write()
        (root / 'JOIN.json').write_text(json.dumps({'complete': False}))
        self.assertTrue(all(v.joins(root).values()))
        broken = copy.deepcopy(self.bundle.binding)
        broken['binding_id'] = digest(b'another binding')
        (root / 'state/plan/binding.json').write_text(json.dumps(broken))
        self.assertFalse(v.joins(root)['binding'])


if __name__ == '__main__':
    unittest.main()
