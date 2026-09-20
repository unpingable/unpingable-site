#!/usr/bin/env python3
"""Project native review input from retained exports; never authenticate or run it.

Uses only public JSON contracts. The native verifier must independently read
the enrolled Switchyard and Foreman stores before AG accepts this candidate.
No internal component modules, provider calls or authority operations are used.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

MAX_BYTES = 16 * 1024 * 1024
MAX_SAFE_INTEGER = 2**53 - 1
RESULT_FIELDS = {'schema', 'binding_id', 'verdict', 'findings'}
FINDING_FIELDS = {'code', 'summary'}
MANIFEST_FIELDS = {'schema', 'binding_id', 'binding_bytes_base64', 'author_principal'}
TOKEN = re.compile(r'[A-Za-z0-9._:/-]{1,512}\Z')


def canonical(value):
    """JCS subset: ASCII object keys, strings, booleans, null and safe integers.

These closed record schemas need no floating point or arbitrary object keys.
Refuse other values instead of silently implementing a different identity law.
"""
    def check(item):
        if isinstance(item, dict):
            if any(not isinstance(key, str) or not key.isascii() for key in item):
                raise ValueError('only ASCII record field names are supported')
            for child in item.values(): check(child)
        elif isinstance(item, list):
            for child in item: check(child)
        elif item is None or isinstance(item, (str, bool)):
            pass
        elif type(item) is int and abs(item) <= MAX_SAFE_INTEGER:
            pass
        else:
            raise ValueError('unsupported canonical record value')
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digest(raw):
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result: raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_BYTES:
            raise ValueError('input must be a nonempty bounded regular file')
        raw = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
    stable = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if len(raw) > MAX_BYTES or stable(before) != stable(after): raise ValueError('input changed during read')
    return json.loads(raw, object_pairs_hook=pairs), raw


def compose_review_acceptance_tests(binding, binding_raw, config, technical_material, instruction):
    """Place the verifier manifest before reviewer-facing material.

    The installed verifier resolves its configured pointer against the canonical
    work item.  This helper owns that small composition convention; it does not
    seal a Foreman packet, contact a provider, or change verifier behavior.
    """
    if (not isinstance(binding, dict) or binding.get('schema') != 'maude.governed-plan-binding/v1' or
            not isinstance(binding.get('binding_id'), str)):
        raise ValueError('exact reviewed local-copy binding required')
    if canonical(binding) != binding_raw:
        raise ValueError('binding bytes must be exact canonical JSON')
    if (not isinstance(config, dict) or config.get('schema') != 'switchyard.shared-review-verifier-config/v1' or
            config.get('brief_manifest_pointer') != ['acceptance_tests', '0'] or
            config.get('brief_contract') != 'switchyard.shared-review-manifest/v1' or
            not isinstance(config.get('author_principal'), str) or not config['author_principal']):
        raise ValueError('review verifier manifest enrollment differs')
    if not isinstance(technical_material, dict):
        raise ValueError('technical review material must be a JSON object')
    if not isinstance(instruction, str) or not instruction:
        raise ValueError('review instruction must be nonempty text')
    manifest = {'schema': config['brief_contract'], 'binding_id': binding['binding_id'],
        'binding_bytes_base64': base64.b64encode(binding_raw).decode('ascii'),
        'author_principal': config['author_principal']}
    return [canonical(manifest).decode('utf-8'), canonical(technical_material).decode('utf-8'), instruction]


def verify_review_brief_manifest(brief, config, binding, binding_raw):
    """Fail closed on a brief that the enrolled native manifest extractor rejects.

    Native Switchyard remains the custody verifier after provider completion.
    This matching pre-provider check covers only the frozen brief composition and
    exact enrolled binding bytes, so a misplaced manifest cannot spend a request.
    """
    try:
        basis = json.loads(brief, object_pairs_hook=pairs)
        if canonical(basis) != brief:
            raise ValueError('worker brief is not canonical JSON')
        work_item = json.loads(basis['work_item']['canonical_json'].encode('utf-8'), object_pairs_hook=pairs)
        if canonical(work_item).decode('utf-8') != basis['work_item']['canonical_json']:
            raise ValueError('work item is not canonical JSON')
    except (KeyError, TypeError, AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('worker brief lacks a canonical work item') from exc
    value = work_item
    pointer = config.get('brief_manifest_pointer')
    if not isinstance(pointer, list) or not pointer:
        raise ValueError('review manifest pointer missing')
    for component in pointer:
        if isinstance(value, dict) and component in value:
            value = value[component]
        elif (isinstance(value, list) and isinstance(component, str) and
                re.fullmatch(r'0|[1-9][0-9]*', component) and int(component) < len(value)):
            value = value[int(component)]
        else:
            raise ValueError('review manifest pointer missing')
    if not isinstance(value, str):
        raise ValueError('review manifest must be a canonical JSON string')
    try:
        manifest = json.loads(value.encode('utf-8'), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid review manifest JSON') from exc
    if canonical(manifest).decode('utf-8') != value or not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise ValueError('review manifest is not the closed canonical contract')
    if (manifest['schema'] != config.get('brief_contract') or
            manifest['author_principal'] != config.get('author_principal') or
            manifest['binding_id'] != binding.get('binding_id')):
        raise ValueError('review manifest enrollment or binding differs')
    try:
        decoded = base64.b64decode(manifest['binding_bytes_base64'], validate=True)
    except (TypeError, ValueError) as exc:
        raise ValueError('review manifest binding encoding differs') from exc
    if (base64.b64encode(decoded).decode('ascii') != manifest['binding_bytes_base64'] or
            decoded != binding_raw or canonical(binding) != binding_raw):
        raise ValueError('review manifest does not carry the exact enrolled binding bytes')
    return manifest


def verify_review_packet_manifest(packet, work_item_id, config, binding, binding_raw):
    """Check the exact frozen packet work item using the brief extraction path."""
    if not isinstance(packet, dict) or packet.get('schema') != 'nightshift.orientation-packet/v1':
        raise ValueError('review packet schema differs')
    items = packet.get('work_items')
    if not isinstance(items, list):
        raise ValueError('review packet work items missing')
    matches = [item for item in items if isinstance(item, dict) and item.get('id') == work_item_id]
    if len(matches) != 1:
        raise ValueError('exact review work item is not unique')
    brief = canonical({'work_item': {'canonical_json': canonical(matches[0]).decode('utf-8')}})
    return verify_review_brief_manifest(brief, config, binding, binding_raw)


def validate_review_result(result, binding_id):
    """Apply the native review-verifier result contract before projection.

The native verifier remains the custody authority.  This is only a matching
fail-closed shape check so an impossible candidate is not projected.
"""
    if not isinstance(result, dict) or set(result) != RESULT_FIELDS:
        raise ValueError('review result fields do not match the native verifier contract')
    if (result['schema'] != 'switchyard.shared-source-review/v1' or
            result['binding_id'] != binding_id or result['verdict'] not in {'accepted', 'rejected'}):
        raise ValueError('review result does not match the native verifier contract')
    findings = result['findings']
    if not isinstance(findings, list) or len(findings) > 64:
        raise ValueError('review findings do not match the native verifier contract')
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != FINDING_FIELDS:
            raise ValueError('review finding fields do not match the native verifier contract')
        if not isinstance(finding['code'], str) or TOKEN.fullmatch(finding['code']) is None:
            raise ValueError('review finding code does not match the native verifier contract')
        if not isinstance(finding['summary'], str) or not 1 <= len(finding['summary'].encode('utf-8')) <= 4096:
            raise ValueError('review finding summary does not match the native verifier contract')


def project(binding, requirement, config, provider, disposition, now_ms):
    """A supplied-export candidate is not a native custody verification result."""
    if (binding.get('schema') != 'maude.governed-plan-binding/v1' or
            requirement.get('schema') != 'ag.governed-loop.review-requirement/v1' or
            config.get('schema') != 'switchyard.shared-review-verifier-config/v1'):
        raise ValueError('unsupported public input schema')
    if (requirement['route_enrollment_digest'] != digest(canonical(config)) or
            requirement['reviewer_id'] != config['reviewer_id'] or
            requirement['compiler_contract'] != binding['compiler_contract']):
        raise ValueError('review requirement differs from the enrolled route or binding')
    if (provider.get('state') != 'PROVIDER_COMPLETED' or provider.get('turn_status') != 'completed' or
            provider.get('semantic_retry') is not False or provider.get('approval_response_sent') is not False):
        raise ValueError('provider completion is not established; retain original occurrence')
    raw = provider.get('worker_output')
    if not isinstance(raw, str) or not raw: raise ValueError('exact reviewer output unavailable')
    result_raw = raw.encode('utf-8')
    if len(result_raw) > 32768: raise ValueError('reviewer output exceeds this example bound')
    result = json.loads(result_raw, object_pairs_hook=pairs)
    if canonical(result) != result_raw:
        raise ValueError('review is not an exact canonical accepted result for this binding')
    validate_review_result(result, binding['binding_id'])
    if result['verdict'] != 'accepted':
        raise ValueError('review is not an exact canonical accepted result for this binding')
    ended, age = provider.get('ended_at_unix_ms'), requirement.get('max_age_ms')
    if type(ended) is not int or type(age) is not int or not 0 < age <= 300000:
        raise ValueError('unsupported review lifetime')
    expires = ended + age
    if not 0 <= ended <= now_ms < expires <= MAX_SAFE_INTEGER:
        raise ValueError('original review time is future, expired or outside exact integer range')
    dispatch = provider['dispatch_record']
    if (dispatch['run_id'] != config['nightshift_run_id'] or
            disposition.get('schema') != 'nightshift.provider-admission-disposition/v1' or
            disposition.get('disposition') != 'EXECUTION_ADMITTED' or
            disposition.get('acquisition_complete') is not True or disposition.get('response_created') is not True or
            disposition.get('will_retry') is not False or disposition.get('approval_response_sent') is not False or
            disposition.get('protected_effect_absent') is not True):
        raise ValueError('retained disposition does not establish completed acquisition')
    for key in ('dispatch_digest', 'run_id', 'work_attempt_id', 'dispatch_occurrence_id'):
        if disposition.get(key) != dispatch.get(key): raise ValueError('disposition/dispatch mismatch: ' + key)
    for key in ('thread_id', 'turn_id'):
        if disposition.get(key) != provider.get(key): raise ValueError('disposition/result mismatch: ' + key)
    if provider['work_attempt_id'] != dispatch['work_attempt_id'] or provider['dispatch_occurrence_id'] != dispatch['dispatch_occurrence_id']:
        raise ValueError('provider/dispatch occurrence differs')
    custody = {'schema': 'switchyard.shared-source-review-custody/v1', 'binding_id': binding['binding_id'],
        'dispatch_id': dispatch['dispatch_digest'], 'dispatch_occurrence_id': provider['dispatch_occurrence_id'],
        'nightshift_run_id': config['nightshift_run_id'], 'work_attempt_id': provider['work_attempt_id'],
        'thread_id': provider['thread_id'], 'turn_id': provider['turn_id'], 'reviewer_id': config['reviewer_id'],
        'author_principal': config['author_principal'], 'worker_brief_digest': dispatch['worker_brief_digest'],
        'worker_output_digest': digest(result_raw), 'provider_disposition_digest': disposition['disposition_digest']}
    custody_raw = canonical(custody)
    requirement_digest = digest(canonical(requirement))
    review = {'schema': 'maude.governed-plan-review/v1', 'binding_id': binding['binding_id'],
        'requirement_digest': requirement_digest, 'dispatch_id': dispatch['dispatch_digest'],
        'reviewer_id': config['reviewer_id'], 'verdict': 'accepted', 'reviewed_at_unix_ms': ended,
        'expires_at_unix_ms': expires, 'result_digest': digest(result_raw),
        'custody_receipt_digest': digest(custody_raw)}
    artifacts = {'result_bytes_base64': base64.b64encode(result_raw).decode('ascii'),
        'custody_receipt_bytes_base64': base64.b64encode(custody_raw).decode('ascii')}
    return {'record-review-input.json': {'schema': 'ag.governed-loop.review-record-input/v1',
        'campaign': binding['campaign'], 'occurrence': binding['occurrence'], 'binding_id': binding['binding_id'],
        'requirement_digest': requirement_digest, 'review': review, 'artifacts': artifacts},
        'verification-request.json': {'schema': 'ag.governed-loop.review-verification-request/v1',
            'requirement': requirement, 'review': review, 'artifacts': artifacts},
        'permission-preflight-input.json': {'schema': 'ag.governed-loop.permission-preflight-input/v1',
            'binding_id': binding['binding_id']},
        'candidate-status.json': {'status': 'CANDIDATE_ONLY_NOT_AUTHENTICATED',
            'native_store_custody_verified': False, 'reviewed_at_unix_ms': ended,
            'expires_at_unix_ms': expires, 'provider_contact': False, 'authority': False}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binding', 'requirement', 'config', 'provider-run', 'disposition', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    values = [read(path)[0] for path in (args.binding, args.requirement, args.config, args.provider_run, args.disposition)]
    outputs = project(*values, time.time_ns() // 1000000)
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, value in outputs.items():
        with (args.output / name).open('xb') as stream:
            stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
    print('Candidate retained; native verifier and AG admission are still required.')


if __name__ == '__main__': main()
