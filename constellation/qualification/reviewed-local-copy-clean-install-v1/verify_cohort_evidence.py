#!/usr/bin/env python3
"""Independently verify an exported cohort evidence bundle (alpha.6 shape).

QUALIFICATION-ONLY. The published alpha.6 verifier pins its evidence files by
digest, runs an independent checker over them, and requires a mismatched plan
digest to refuse. This does the same for a cohort bundle written by
`constellation_cohort.py evidence`, without trusting the bundle's JOIN.json:

- every file listed in SHA256SUMS has its digest;
- binding, occurrence and campaign agree across the Maude binding, the
  retained candidate and AG's spend and issuance;
- the accepted candidate is byte-identical to the retained one;
- AG's issuance is v2 with a signed not_after after the spend, and Docket's
  record carries the same issuance, custody, attempt and settlement;
- Docket's standing snapshot joins custody;
- exactly one spend, one Docket attempt and one settlement, outcome success;
- result.txt holds exactly the plan's reviewed bytes;
- the issuance identity recomputes under AG's digest law, and its Ed25519
  signature verifies (openssl) by a key the bundle's Docket trust names;
- the same checks with a substituted plan digest refuse.

Prints one JSON line and exits 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

SIGNATURE_PREFIX = b'ag-ng\x00governed-loop-issuance-signature\x00v1\x00'
SPKI_ED25519 = bytes.fromhex('302a300506032b6570032100')


def load(root: Path, name: str):
    return json.loads((root / name).read_bytes())


def sums(root: Path) -> list[str]:
    bad = []
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            bad.append(name)
    return bad


def jcs(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def ag_digest(domain: str, payload: bytes) -> str:
    digest = hashlib.sha256(b'ag-ng\x00digest\x00v1\x00')
    digest.update(len(domain).to_bytes(16, 'big') + domain.encode() + len(payload).to_bytes(16, 'big') + payload)
    return 'sha256:' + digest.hexdigest()


def b64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def issuance_checks(root: Path) -> dict:
    """AG issuance identity and signature, independent of the driver."""
    record = load(root, 'native/docket-inspect.json').get('record') or {}
    issuance, authentication = record.get('issuance', {}), record.get('authentication', {})
    basis = {name: issuance.get(name) for name in ('key', 'mandate', 'observation', 'program', 'proposal', 'scope',
                                                   'spend', 'standing_resolution', 'subject', 'work', 'work_schema',
                                                   'not_after_unix_ms')}
    identity = ag_digest('ag.governed-loop.issuance/v2', jcs(basis)) == issuance.get('issuance')
    trusted = any(entry.get('issuer_principal') == authentication.get('issuer_principal')
                  and entry.get('key_id') == authentication.get('signer_key_id')
                  and entry.get('public_key') == authentication.get('signer_public_key')
                  for entry in load(root, 'state/ports/docket-trust.json').get('issuers', []))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / 'k.der').write_bytes(SPKI_ED25519 + b64url(authentication.get('signer_public_key', '')))
        (work / 'm').write_bytes(SIGNATURE_PREFIX + jcs(issuance))
        (work / 's').write_bytes(b64url(authentication.get('signature', '')))
        done = subprocess.run(['openssl', 'pkeyutl', '-verify', '-pubin', '-inkey', str(work / 'k.der'), '-keyform', 'DER',
                               '-rawin', '-in', str(work / 'm'), '-sigfile', str(work / 's')], capture_output=True, check=False)
    return {'issuance_identity': identity, 'issuance_signature': trusted and done.returncode == 0}


def joins(root: Path, plan_digest_override: str | None = None) -> dict:
    binding = load(root, 'state/plan/binding.json')
    candidate_raw = (root / 'caller/review-001/record-review-input.json').read_bytes()
    candidate = json.loads(candidate_raw)
    accepted_raw = (root / 'caller/continuation-001/accepted-record-review-input.json').read_bytes()
    acceptance = load(root, 'caller/continuation-001/operator-acceptance.json')
    ag = load(root, 'native/ag-inspect.json')
    docket = load(root, 'native/docket-inspect.json')
    snapshot = load(root, 'native/standing-snapshot.json')
    executor = load(root, 'state/plan/executor-config.json')
    plan = json.loads(base64.b64decode(executor['executor_plan_base64'], validate=True))
    result = load(root, 'native/result-file.json')
    states = ag['current']['state']
    variant = next(iter(states)) if len(states) == 1 else None
    value = states.get(variant, {}) if variant else {}
    authorized = value.get('dispatch', {}).get('authorized', {})
    spend, issuance = authorized.get('spend', {}), authorized.get('issuance', {})
    custody, settlement = value.get('dispatch', {}).get('custody', {}), value.get('settlement', {})
    record = docket.get('record') or {}
    key = {'campaign': binding['campaign'], 'occurrence': binding['occurrence']}
    content = base64.b64decode(result.get('content_base64', ''))
    expected_plan = plan_digest_override or binding['plan_document_digest']
    return {
        'plan_document': binding['artifacts']['plan_document']['sha256'] == expected_plan == plan['plan_document_digest'],
        'binding': candidate['binding_id'] == binding['binding_id'] == candidate['review']['binding_id'],
        'occurrence': (spend.get('key') == key == issuance.get('key') and candidate['occurrence'] == key['occurrence']
                       and candidate['campaign'] == key['campaign'] and issuance.get('work') == binding['work']),
        'candidate_accepted': (accepted_raw == candidate_raw and acceptance.get('candidate_sha256')
                               == 'sha256:' + hashlib.sha256(candidate_raw).hexdigest()
                               and acceptance.get('human_attestation') is False),
        'issuance_v2_not_after': (issuance.get('schema') == 'ag.governed-loop.issuance/v2'
                                  and type(issuance.get('not_after_unix_ms')) is int
                                  and issuance['not_after_unix_ms'] > spend.get('consumed_at_unix_ms', 2**63)),
        'docket_record': (record.get('issuance') == issuance and record.get('custody') == custody
                          and custody.get('issuance') == issuance.get('issuance')
                          and docket.get('requested_issuance') == issuance.get('issuance')),
        'attempt': custody.get('attempt') is not None and record.get('settlement', {}).get('attempt') == custody['attempt'],
        'settlement': (variant == 'settled_observation_required' and record.get('settlement') == settlement
                       and record.get('status') == 'settled' and settlement.get('outcome') == 'success'),
        'standing': (snapshot.get('execution_standing') == custody.get('execution_standing')
                     and snapshot.get('currentness') == custody.get('standing_currentness')),
        'once': all(ag['replay'].get(name) == 1 for name in ('ag_spends', 'docket_attempts', 'settlements')),
        'result_bytes': ('sha256:' + hashlib.sha256(content).hexdigest() == plan['reviewed_text_digest']
                         and len(content) == plan['reviewed_text_byte_length'] and result.get('scratch_entries') == ['result.txt']),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    root = args.evidence.resolve()
    bad = sums(root)
    checks = {**joins(root), **issuance_checks(root)}
    refused = not all(joins(root, 'sha256:' + '0' * 64).values())
    passed = not bad and all(checks.values()) and refused
    binding = load(root, 'state/plan/binding.json')
    ag = load(root, 'native/ag-inspect.json')
    print(json.dumps({'schema': 'constellation.cohort-evidence-check/v1', 'result': 'passed' if passed else 'failed',
                      'digest_mismatches': bad, 'checks': checks, 'mismatched_plan_digest': 'refused' if refused else 'ACCEPTED',
                      'binding_id': binding['binding_id'], 'occurrence': binding['occurrence'],
                      'state_digest': ag['current'].get('state_digest'),
                      'sha256sums_sha256': 'sha256:' + hashlib.sha256((root / 'SHA256SUMS').read_bytes()).hexdigest()},
                     sort_keys=True, separators=(',', ':')))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
