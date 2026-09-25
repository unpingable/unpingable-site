"""Draft and seal the five Foreman provider inputs for one cohort review.

Promoted from the B004 campaign draft constructor with no constants for
component identities: the Switchyard pins come from the installed runner's
`--build-info` (`foreman_requirement_pins`), the Foreman program is the
installed `nightshift-foreman`, and times are the real current wall clock.

    python3.11 -I -S -c 'import sys; sys.path[:0]=[SETUP, KIT]; import prepare_review_inputs; \
        prepare_review_inputs.main(sys.argv[1:])' --binding ... --reviewer-config ... \
        --switchyard-build-info ... --foreman ... --run-id ... --work-item ... \
        --workspace ... --custody-root ... --operator ... --label ... --output DIR

It writes `draft.json`, calls `nightshift-foreman provider-seal-inputs` (which
derives every digest), and writes each sealed body canonically to its own file
for `provider-admit`. It admits nothing, launches nothing, contacts no provider
and grants no authority. The admission window is bounded (at most 120 s), so run
it inside the review transition, never ahead of time.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

from prepare_review_candidate import canonical, compose_review_acceptance_tests, read, verify_review_packet_manifest

ADAPTER_ID = 'switchyard.codex-app-server'
ADAPTER_PROTOCOL = 'switchyard.codex-app-server/v2'
ADAPTER_VERSION = '2.0.0'
MODEL_CLASS = 'large'
POLICY_ID = 'one-dispatch-no-retry'
PLACEHOLDER = 'sha256:' + '0' * 64
PIN_FIELDS = ('codex_owner_head', 'deterministic_fixture_sha256', 'switchyard_owner_head', 'switchyard_schema_sha256')
MAX_WINDOW_SECONDS = 120


def digest(raw: bytes) -> str:
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def stamp(moment: dt.datetime) -> str:
    return moment.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def decoded_artifacts(binding: dict) -> dict:
    """The exact bound plan material, decoded for the reviewer (public-safe)."""
    result = {}
    for name in ('plan_document', 'compiler_inputs', 'executor_plan'):
        raw = base64.b64decode(binding['artifacts'][name]['bytes_base64'], validate=True)
        result[name] = {'sha256': binding['artifacts'][name]['sha256'], 'value': json.loads(raw)}
    return result


def technical_material(binding: dict, pins: dict, route: dict, label: str) -> dict:
    return {
        'schema': 'constellation.cohort-review-material/v1',
        'cohort': label,
        'binding_id': binding['binding_id'],
        'compiler_contract': binding['compiler_contract'],
        'reviewed_work': decoded_artifacts(binding),
        'bounded_review_route': {'route': route, 'switchyard_pins': pins},
        'provider_calls': 1, 'grants': 0, 'executor_calls': 0,
        'stop': 'Review testimony only; acceptance is a separate operator transition.',
    }


def instruction(binding_id: str) -> str:
    skeleton = canonical({'binding_id': binding_id, 'findings': [{'code': 'FINDING_CODE', 'summary': 'FINDING_SUMMARY'}],
                          'schema': 'switchyard.shared-source-review/v1', 'verdict': 'accepted'}).decode()
    return ('Review only the exact technical material in acceptance_tests[1] for the plan bound in acceptance_tests[0]. '
            'Assess whether the bounded local copy writes exactly the selected UTF-8 bytes once to an exclusive '
            'result.txt and nothing else. Do not infer execution, authority, effects, or current deployment state. '
            'Return exactly one newline-free compact canonical JSON object with the JCS-ordered keys binding_id, '
            'findings, schema, verdict. findings is an array of at most 64 objects with exactly the keys code then '
            'summary; use [] when there are no findings. Copy this skeleton, replacing placeholders and changing '
            'accepted to rejected only for a substantive blocker: ' + skeleton)


def draft(args, binding, binding_raw, reviewer, build_info, now) -> dict:
    pins = build_info.get('foreman_requirement_pins')
    if not isinstance(pins, dict) or any(not isinstance(pins.get(key), str) for key in PIN_FIELDS + ('adapter_executable_identity',)):
        raise SystemExit('Switchyard build info lacks foreman_requirement_pins')
    route = reviewer['route']
    if (route['adapter_id'], route['adapter_protocol'], route['adapter_version']) != (ADAPTER_ID, ADAPTER_PROTOCOL, ADAPTER_VERSION):
        raise SystemExit('reviewer route adapter differs from the Switchyard adapter')
    if pins['codex_owner_head'] != route['codex_source_head']:
        raise SystemExit('Switchyard codex pin differs from the enrolled reviewer route')
    if reviewer['nightshift_run_id'] != args.run_id:
        raise SystemExit('reviewer run id differs')
    created, until = stamp(now), stamp(now + dt.timedelta(seconds=args.window_seconds))
    handoff = json.loads(base64.b64decode(binding['artifacts']['compiled_handoff']['bytes_base64'], validate=True))
    proposal_ref = digest(canonical(handoff['proposal_input']['proposal']))
    executor = binding['artifacts']['executor_plan']
    custody = [{'branch': '', 'commit': args.maude_commit, 'discrepancy':
                'Installed release archive identity only; no checkout state is asserted. Exact review material is carried in the sealed brief.',
                'path': 'lib/executor.pyz', 'remote': None, 'remote_commit': None, 'repository': 'maude', 'worktree_clean': False}]
    evidence = [{'branch': '', 'commit': args.maude_commit, 'file_digest': args.executor_sha256, 'path': 'lib/executor.pyz',
                 'predecessor_classification': 'RELEASED_REVIEWED_LOCAL_COPY_EXECUTOR', 'repository': 'maude'}]
    work_item = {
        'acceptance_tests': compose_review_acceptance_tests(
            binding, binding_raw, reviewer, technical_material(binding, pins, route, args.label), instruction(binding['binding_id'])),
        'allowed_mutation_surfaces': ['NONE: independent read-only review only'],
        'campaign': {'canonical_slug': 'constellation-cohort-review', 'codename': 'COHORT-REVIEW'},
        'closeout_requirements': ['Retain only the sealed custody result; do not infer execution or authority'],
        'dependencies': [],
        'entry_predicates': ['Exact Maude binding and exact review instruction are present in this sealed brief'],
        'exact_work_refs': [{'branch': '', 'commit': args.maude_commit, 'contract_kind': 'exact_work_proposal_v1',
                             'contract_schema': 'ag.governed-loop.exact-work-proposal/v1', 'path': 'lib/executor.pyz',
                             'proposal_ref': proposal_ref, 'repository': 'maude'}],
        'expected_receipts': ['One compact switchyard.shared-source-review/v1 reviewer result for the exact binding ID'],
        'forbidden_actions': ['All file mutation', 'Network use', 'Provider/model substitution', 'Retry or fallback',
                              'New agents', 'Authority effects'],
        'id': args.work_item,
        'model_routing': {'class': MODEL_CLASS, 'maximum_mutating_workers': 0, 'reason': 'Pinned reviewer route'},
        'predecessor_lineage': [],
        'stop_conditions': ['Any binding, decoded artifact, instruction, or route identity mismatch',
                            'Any request to exceed the sealed review boundary'],
        'track': 'shared-interface-review',
    }
    packet = {
        'authoring': {'agent': reviewer['author_principal'], 'authority_basis': 'Technical review only; no grant or effect.',
                      'session': args.run_id},
        'canonicalization': {'algorithm': 'RFC8785-JCS', 'digest_algorithm': 'SHA-256', 'digest_preimage':
                             'domain prefix nightshift.orientation-packet.digest/v1 NUL, then packet object with '
                             'packet_digest and switchyard.plan_ref omitted as RFC8785-JCS'},
        'created_at': created, 'current_until': until,
        'global_constraints': {'allowed_actions': ['Read the sealed brief and return bounded reviewer testimony only'],
                               'forbidden_actions': ['File mutation', 'Network tools', 'Provider fallback', 'Retry',
                                                     'Delegated workers', 'Apps or plugins', 'Authority or target effects'],
                               'invariants': ['The binding and decoded plan artifacts are closed in the worker brief',
                                              'Worker output is testimony, not qualification or authorization']},
        'human_question_criteria': ['Missing final owner admission or route enrollment identity'],
        'packet_digest': PLACEHOLDER, 'packet_id': args.run_id,
        'repository_custody': custody, 'schema': 'nightshift.orientation-packet/v1', 'source_evidence': evidence,
        'switchyard': {'alias': args.work_item, 'plan_ref': 'nightshift-packet://' + '0' * 64,
                       'transport_fields': ['alias', 'plan_ref', 'nonce']},
        'work_items': [work_item],
        'worker_budget': {'maximum_concurrent_mutating_workers': 1, 'recursive_worker_swarms_forbidden': True,
                          'reserve_posture': 'One bounded read-only review; no retry or fallback'},
    }
    admission = {'admission_digest': PLACEHOLDER, 'admitted_at': created, 'allowed_adapter_ids': [ADAPTER_ID],
                 'allowed_provider_model_classes': [MODEL_CLASS], 'authority_effect': 'LOCAL_AGENT_COMPUTE_SCHEDULING_ONLY',
                 'expires_at': until, 'local_runtime_identity': args.label, 'maximum_concurrent_workers': 1,
                 'maximum_new_attempts_per_work_item': 1,
                 'operator_basis_digest': digest(canonical({'operator': args.operator, 'run_id': args.run_id,
                                                            'binding_id': binding['binding_id']})),
                 'packet_digest': PLACEHOLDER, 'run_id': args.run_id, 'schema': 'nightshift.foreman-admission/v1',
                 'target_effects_authorized': False}
    profile = {'adapter_timeout_seconds': 120,
               'adapters': {ADAPTER_ID: {'adapter_id': ADAPTER_ID, 'adapter_version': ADAPTER_VERSION, 'bounded_arguments': [],
                                         'executable_identity': pins['adapter_executable_identity'], 'protocol': ADAPTER_PROTOCOL}},
               'admission_digest': PLACEHOLDER, 'budget_policy_ref': POLICY_ID,
               'closeout_policy': 'ALL_EXPLICIT_TERMINAL_OR_NOT_STARTED',
               'log_custody_root': str(args.custody_root / 'logs'), 'maximum_event_bytes': 16777216,
               'maximum_receipt_bytes': 32768, 'maximum_worker_output_bytes': 32768, 'packet_digest': PLACEHOLDER,
               'profile_digest': PLACEHOLDER, 'receipt_custody_root': str(args.custody_root / 'receipts'),
               'schema': 'nightshift.foreman-execution-profile/v3',
               'work_items': {args.work_item: {'adapter_id': ADAPTER_ID, 'provider_model_class': MODEL_CLASS,
                                               'resource_lock_keys': [f'{args.work_item}:{args.run_id}'],
                                               'workspace_identity': str(args.workspace)}}}
    policy = {'allow_ordered_model_fallback': False, 'approval_response_authorized': False,
              'authority_effect': 'LOCAL_AGENT_COMPUTE_SCHEDULING_ONLY', 'automatic_semantic_retry': False,
              'backoff_seconds': [5], 'maximum_dispatch_occurrences_per_attempt': 1, 'maximum_total_deferral_seconds': 600,
              'parked_resource_lock_policy': 'RELEASE_AND_REACQUIRE', 'policy_digest': PLACEHOLDER, 'policy_id': POLICY_ID,
              'provider_capacity_released_while_parked': True, 'reconcile_indeterminate': True,
              'schema': 'nightshift.provider-execution-availability-policy/v1'}
    requirement = {'adapter_executable_identity': pins['adapter_executable_identity'], 'adapter_id': ADAPTER_ID,
                   'adapter_protocol': ADAPTER_PROTOCOL, 'adapter_version': ADAPTER_VERSION, 'admission_digest': PLACEHOLDER,
                   'admitted_at': created, 'authority_effect': 'LOCAL_AGENT_COMPUTE_SCHEDULING_ONLY',
                   'owner_pins': {key: pins[key] for key in PIN_FIELDS}, 'packet_digest': PLACEHOLDER,
                   'policy_digest': PLACEHOLDER, 'policy_id': POLICY_ID, 'profile_digest': PLACEHOLDER,
                   'requirement_digest': PLACEHOLDER, 'run_id': args.run_id,
                   'schema': 'nightshift.foreman-execution-availability-requirement/v1',
                   'work_item_model_selections': {args.work_item: [{'model_class': MODEL_CLASS, 'model_id': route['model'],
                                                                    'provider_id': route['provider']}]}}
    return {'packet': packet, 'admission': admission, 'profile': profile, 'policy': policy, 'requirement': requirement}


def write_new(path: Path, raw: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binding', 'reviewer-config', 'switchyard-build-info', 'foreman', 'workspace', 'custody-root', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('run-id', 'work-item', 'operator', 'label', 'maude-commit', 'executor-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--window-seconds', type=int, default=MAX_WINDOW_SECONDS)
    args = parser.parse_args(argv)
    if not 30 <= args.window_seconds <= MAX_WINDOW_SECONDS:
        raise SystemExit(f'admission window must be 30..{MAX_WINDOW_SECONDS} s')
    for path in (args.foreman, args.workspace, args.custody_root, args.output):
        if not path.is_absolute():
            raise SystemExit('absolute locators required')
    binding, binding_raw = read(args.binding)
    reviewer = read(args.reviewer_config)[0]
    build_info = read(args.switchyard_build_info)[0]
    now = dt.datetime.now(dt.timezone.utc)
    value = draft(args, binding, binding_raw.removesuffix(b'\n'), reviewer, build_info, now)
    args.output.mkdir(mode=0o700, exist_ok=False)
    write_new(args.output / 'draft.json', canonical(value))
    sealed = subprocess.run([str(args.foreman), 'provider-seal-inputs', '--draft', str(args.output / 'draft.json')],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
                            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    write_new(args.output / 'seal.stdout', sealed.stdout)
    write_new(args.output / 'seal.stderr', sealed.stderr)
    if sealed.returncode != 0:
        raise SystemExit(f'nightshift-foreman provider-seal-inputs refused (exit {sealed.returncode}): '
                         + sealed.stderr.decode(errors='replace')[-2000:])
    bodies = json.loads(sealed.stdout)
    if set(bodies) != {'packet', 'admission', 'profile', 'policy', 'requirement'}:
        raise SystemExit('sealed Foreman inputs differ from the five-body contract')
    for name, body in bodies.items():
        write_new(args.output / f'{name}.json', canonical(body))
    verify_review_packet_manifest(bodies['packet'], args.work_item, reviewer, binding, binding_raw.removesuffix(b'\n'))
    print(json.dumps({'schema': 'constellation.cohort-review-inputs/v1', 'run_id': args.run_id,
                      'admitted_at': bodies['requirement']['admitted_at'], 'expires_at': bodies['admission']['expires_at'],
                      'files': {name: digest(canonical(body)) for name, body in bodies.items()},
                      'provider_contact': False, 'authority': False}, sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    main()
