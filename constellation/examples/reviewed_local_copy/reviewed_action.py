#!/usr/bin/env python3
"""One explicit native reviewed-action caller, not a scheduler or authority owner.

Requires a deployment-provisioned V2 AG genesis and exact current native inputs.
The operator admits the entire finite action before --execute. No retries,
fallback routes, automatic grants after refusal, or arbitrary command fields.
"""
from __future__ import annotations
import argparse
import base64
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import selectors
import socket
import stat
import subprocess
import time

from prepare_review_candidate import (canonical, digest, project, read,
    verify_review_brief_manifest, verify_review_packet_manifest)
from prepare_finite_run import prepare

PROGRAMS = {'ag', 'nightshift', 'foreman', 'provider', 'review_verifier', 'docket', 'pulse', 'app_server'}
INPUTS = {'binding', 'cycle_request', 'nightshift_config', 'runtime_profile', 'review_requirement',
    'review_verifier_config', 'executor_config', 'backend', 'packet', 'admission', 'profile',
    'policy', 'provider_requirement', 'source_provenance', 'pulse_query', 'pulse_retention',
    'docket_standing_config'}
PATHS = {'ag_database', 'foreman_database', 'switchyard_database', 'docket_state', 'ag_mandates'}


def require(value, reason):
    if not value: raise ValueError(reason)


def now(): return time.time_ns() // 1000000


def stamp(milliseconds):
    return dt.datetime.fromtimestamp(milliseconds / 1000, dt.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def pinned(entry, maximum):
    require(set(entry) == {'path', 'sha256'}, 'pin must name exact pathname and content')
    path = Path(entry['path'])
    require(path.is_absolute(), 'absolute input pathname required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= maximum, 'input type/size refused')
        actual = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    stable = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    require(stable(before) == stable(after) and actual == entry['sha256'], 'input content changed: ' + str(path))
    return str(path)


def require_docket_standing(value, operator, state_directory):
    require(value == {
        'schema': 'docket.governed-loop.local-standing-resolver-config/v1',
        'operator': operator,
        'state_database': str(Path(state_directory) / 'state.sqlite'),
    }, 'Docket local-standing operator/state differs from the caller')


def configuration(path):
    config, raw = read(path)
    require(set(config) == {'schema', 'programs', 'inputs', 'paths', 'review', 'operator'}, 'closed example config required')
    require(config['schema'] == 'constellation.reviewed-local-copy-caller/v1', 'unsupported caller configuration')
    require(set(config['programs']) == PROGRAMS and set(config['inputs']) == INPUTS and set(config['paths']) == PATHS,
        'configuration must name every native program, input and mutable owner path')
    require(set(config['review']) == {'run_id', 'work_item', 'dispatch_id', 'adapter_process', 'app_server_session_identity'},
        'review occurrence coordinates must be explicit')
    for key, entry in config['programs'].items(): pinned(entry, (1024 if key == 'app_server' else 256) * 1024**2)
    for entry in config['inputs'].values(): pinned(entry, 16 * 1024**2)
    for value in config['paths'].values(): require(Path(value).is_absolute(), 'absolute mutable owner path required')
    require(isinstance(config['operator'], str) and config['operator'], 'operator identity required')
    inputs = {key: value['path'] for key, value in config['inputs'].items()}
    values = {key: read(Path(inputs[key]))[0] for key in ('runtime_profile', 'nightshift_config',
        'review_verifier_config', 'backend', 'docket_standing_config')}
    profile, ns, review, backend, docket_standing = (values[key] for key in
        ('runtime_profile', 'nightshift_config', 'review_verifier_config', 'backend',
         'docket_standing_config'))
    require(profile.get('schema') == 'ag.governed-loop.runtime-profile/v2', 'protected V2 genesis required')
    for key in ('review_requirement', 'review_verifier_config'):
        require(profile['shared_admission'][key] == {'path': inputs[key], 'identity': config['inputs'][key]['sha256']}, 'genesis shared input differs: ' + key)
    for key, enrolled in (('review_verifier', profile['shared_admission']['review_verifier']),
            ('nightshift', profile['nightshift_cycle']['program']), ('docket', profile['docket']['docket_program'])):
        require(enrolled == {'path': config['programs'][key]['path'], 'identity': config['programs'][key]['sha256']}, 'genesis program differs: ' + key)
    require(profile['nightshift_cycle']['config']['path'] == inputs['nightshift_config'] and
        ns['ag_loopctl'] == config['programs']['ag'] and ns['present_evidence_resolver'] == config['programs']['pulse'] and
        ns['ag_database'] == config['paths']['ag_database'] and ns['ag_runtime_profile'] == inputs['runtime_profile'], 'native admission locators differ')
    require(review['switchyard_state_path'] == config['paths']['switchyard_database'] and
        review['nightshift_state_path'] == config['paths']['foreman_database'] and review['nightshift_run_id'] == config['review']['run_id'] and
        review['nightshift_foreman_program'] == config['programs']['foreman']['path'] and
        review['nightshift_foreman_sha256'] == config['programs']['foreman']['sha256'], 'review custody enrollment differs')
    require(config['programs']['app_server'] == {'path': backend['executable'], 'sha256': backend['executable_sha256']}, 'provider executable enrollment differs')
    require(all(review['route'][key] == backend[key] for key in ('codex_source_head', 'provider', 'model')) and
        review['route']['app_server_executable_sha256'] == backend['executable_sha256'], 'reviewer route differs from approved backend')
    require(profile['docket']['state_directory'] == config['paths']['docket_state'], 'Docket owner root differs')
    require_docket_standing(docket_standing, config['operator'], config['paths']['docket_state'])
    binding, binding_raw = read(Path(inputs['binding']))
    verify_review_packet_manifest(read(Path(inputs['packet']))[0], config['review']['work_item'],
        review, binding, binding_raw)
    return config, digest(raw)


class Caller:
    def __init__(self, config, output):
        self.config, self.output = config, output
        self.program = {key: value['path'] for key, value in config['programs'].items()}
        self.inputs = {key: Path(value['path']) for key, value in config['inputs'].items()}
        self.paths = config['paths']
        self.phase = 'initial'

    def write(self, name, value):
        raw = value if isinstance(value, bytes) else canonical(value)
        with (self.output / name).open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())

    def call(self, name, argv, stdin=None, timeout=30, parsed=True):
        self.phase = name
        argv = [str(value) for value in argv]
        self.write(name + '.started.json', {'argv': argv, 'at_unix_ms': now(), 'retries': 0,
            'timeout_seconds': timeout, 'output_limit_per_stream': 16 * 1024**2})
        if stdin is not None: self.write(name + '.stdin.json', stdin)
        source = (self.output / (name + '.stdin.json')).open('rb') if stdin is not None else open(os.devnull, 'rb')
        temporary = self.output / 'native-tmp'
        temporary.mkdir(mode=0o700, exist_ok=True)
        require(temporary.is_dir() and not temporary.is_symlink(), 'native temporary directory differs')
        with source, (self.output / (name + '.stdout')).open('xb') as out, (self.output / (name + '.stderr')).open('xb') as err:
            process = subprocess.Popen(argv, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
                    'TMPDIR': str(temporary), 'SQLITE_TMPDIR': str(temporary)})
            deadline = time.monotonic() + timeout
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ, [out, 0])
                selector.register(process.stderr, selectors.EVENT_READ, [err, 0])
                try:
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        require(remaining > 0, name + ' collection timed out; inspect original native owner')
                        for key, _ in selector.select(min(remaining, 0.2)):
                            block = os.read(key.fileobj.fileno(), 65536)
                            if not block: selector.unregister(key.fileobj); continue
                            key.data[1] += len(block)
                            require(key.data[1] <= 16 * 1024**2, name + ' output bound exceeded')
                            key.data[0].write(block)
                    code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try: process.wait(timeout=5)
                        except subprocess.TimeoutExpired: process.kill(); process.wait()
                    out.flush(); os.fsync(out.fileno()); err.flush(); os.fsync(err.fileno())
                    process.stdout.close(); process.stderr.close()
        self.write(name + '.finished.json', {'at_unix_ms': now(), 'exit_code': code})
        require(code == 0, name + ' refused; no automatic retry')
        raw = (self.output / (name + '.stdout')).read_bytes()
        return json.loads(raw) if parsed else raw

    def ag(self, name, command, *args):
        return self.call(name, [self.program['ag'], command, '--database', self.paths['ag_database'], *args])

    def freshness(self, name, minimum):
        query = read(self.inputs['pulse_query'])[0]
        retention = read(self.inputs['pulse_retention'])[0]
        support = self.call(name, [self.program['pulse']], canonical(query))
        require(support.get('schema') == 'nightshift.qualified_support.v1' and support.get('standing') == 'current', 'Pulse not current')
        require(all(support.get(key) == value for key, value in query.items() if key != 'schema'), 'Pulse query binding differs')
        require(support.get('evidence_refs') == [retention['evidence_id']], 'Pulse retained receipt differs')
        at, expiry = support['evaluated_at'], support['expiry']
        require(at['clock_id'] == expiry['clock_id'] == retention['received_at']['clock_id'], 'Pulse clock identity differs')
        require(expiry['tick'] == retention['expiry_tick_ms'] and expiry['tick'] - at['tick'] >= minimum, 'Pulse reserve insufficient')
        preimage = dict(support); preimage.pop('support_id')
        require(support['support_id'] == digest(canonical(preimage)), 'Pulse support identity differs')
        current = self.ag(name + '-ag-inspect', 'inspect')
        state = current['current']['state']
        value = next(iter(state.values()))
        observation = value['observation']
        request = read(self.inputs['cycle_request'])[0]
        evaluated = int(dt.datetime.fromisoformat(request['evaluated_at'].replace('Z', '+00:00')).timestamp() * 1000)
        checked = now()
        require(observation['schema'] == 'ag.governed-loop.observation-resolution/v2' and observation['status'] == 'current', 'native observation not current')
        require(evaluated <= observation['resolved_at_unix_ms'] <= checked and observation['fresh_until_unix_ms'] == evaluated + 300000,
            'original observation clock/TTL differs')
        require(observation['fresh_until_unix_ms'] - checked >= minimum, 'original observation reserve insufficient')
        self.write(name + '-reserve.json', {'original_observation_remaining_ms': observation['fresh_until_unix_ms'] - checked,
            'pulse_remaining_ms': expiry['tick'] - at['tick'], 'minimum_ms': minimum, 'timestamps_changed': False})

    def execute(self, *, review_only=False):
        p, i, paths, r = self.program, self.inputs, self.paths, self.config['review']
        binding, binding_raw = read(i['binding'])
        profile = read(i['runtime_profile'])[0]
        require(profile.get('schema') == 'ag.governed-loop.runtime-profile/v2', 'native shared-admission V2 profile required')
        require(binding['compiler_contract'] == 'maude.reviewed-local-copy/v1', 'only reviewed local-copy supported')
        executor = read(i['executor_config'])[0]
        plan = json.loads(base64.b64decode(executor['executor_plan_base64'], validate=True))
        require(plan['destination'] == 'result.txt' and 0 < plan['reviewed_text_byte_length'] <= 65536, 'bounded local-copy plan required')
        for directory in (Path(plan['scratch_root']), Path(executor['state_root']), Path(paths['docket_state'])):
            require(directory.is_dir() and not directory.is_symlink() and not any(directory.iterdir()), 'exclusive empty effect/custody directory required')
        require(not Path(paths['ag_mandates']).exists(), 'existing standing mandate; reconcile owner')
        for key in ('foreman_database', 'switchyard_database'):
            require(not Path(paths[key]).exists(), 'existing review store; reconcile original request')
        verified = self.call('profile-verify', [p['ag'], 'verify-runtime-profile-v2', '--runtime-profile', i['runtime_profile']])
        initial = self.ag('initial-inspect', 'inspect')
        require(initial['runtime_profile']['digest'] == verified['profile_digest'] and
            set(initial['current']['state']) == {'observation_required'}, 'fresh exact AG genesis required')
        require(all(initial['replay'][key] == 0 for key in ('ag_spends', 'docket_attempts', 'settlements')), 'nonempty authority history')
        self.call('nightshift-admission', [p['nightshift'], 'cycle', 'run-config', '--config', i['nightshift_config'], '--request', i['cycle_request']], timeout=60)
        admitted = self.ag('admitted-inspect', 'inspect')
        require(set(admitted['current']['state']) == {'proposal_recorded'}, 'native proposal admission missing')
        meta = admitted['current']['state']['proposal_recorded']['meta']
        require(meta['key'] == {'campaign': binding['campaign'], 'occurrence': binding['occurrence']} and meta['expected_work'] == binding['work'], 'native work/occurrence differs')
        self.freshness('before-review', 230000)
        provider_requirement = read(i['provider_requirement'])[0]
        require(provider_requirement.get('schema') == 'nightshift.foreman-execution-availability-requirement/v1' and
            provider_requirement.get('run_id') == r['run_id'] and isinstance(provider_requirement.get('admitted_at'), str),
            'execution availability requirement identity differs')
        # Foreman binds the admission transition to the owner's exact admitted_at
        # value. Wall-clock time here would describe a different run requirement.
        command = [p['foreman'], 'provider-admit', '--db', paths['foreman_database'],
            '--evaluated-at', provider_requirement['admitted_at']]
        for key in ('packet', 'admission', 'profile', 'policy', 'requirement'):
            command += ['--' + key, i['provider_requirement' if key == 'requirement' else key]]
        self.call('review-admit', command)
        prepared = self.call('review-prepare', [p['foreman'], 'provider-prepare', '--db', paths['foreman_database'],
            '--run-id', r['run_id'], '--work-item', r['work_item'], '--dispatch', r['dispatch_id'],
            '--adapter-process', r['adapter_process'], '--app-server-session', r['app_server_session_identity'],
            '--selected-model-ordinal', '0', '--recorded-at', stamp(now())])
        self.write('request.json', prepared['worker_start_request']); self.write('dispatch.json', prepared['dispatch'])
        brief = self.call('review-brief', [p['foreman'], 'brief', '--db', paths['foreman_database'], '--run-id', r['run_id'], '--work-item', r['work_item']], parsed=False)
        self.write('brief.json', brief)
        verify_review_brief_manifest(brief, read(i['review_verifier_config'])[0], binding, binding_raw)
        request = prepared['worker_start_request']
        require(request['timeout_seconds'] == 120 and request['maximum_output_bytes'] == 32768, 'request bounds differ')
        require(request.get('semantic_retry') is False and request.get('approval_response_authorized') is False and
            request.get('internal_provider_retry_count') == 0 and request.get('recursive_worker_swarms_forbidden') is True and
            request.get('selected_model_ordinal') == 0, 'request retry/authority constraints differ')
        preflight_args = ['--request', self.output / 'request.json', '--brief', self.output / 'brief.json', '--backend', i['backend']]
        checked = self.call('review-local-preflight', [p['provider'], 'preflight-request', *preflight_args])
        require(checked.get('provider_contact') is False and checked.get('request_digest') == request['request_digest'], 'provider local preflight mismatch')
        self.freshness('immediately-before-review', 230000)
        for key, entry in self.config['programs'].items(): pinned(entry, (1024 if key == 'app_server' else 256) * 1024**2)
        for entry in self.config['inputs'].values(): pinned(entry, 16 * 1024**2)
        provider = self.call('provider-run', [p['provider'], '--state', paths['switchyard_database'], 'run',
            '--source-provenance', i['source_provenance'], *preflight_args, '--dispatch-record', self.output / 'dispatch.json'], timeout=150)
        self.write('provider-run.json', provider)
        require(provider.get('provider_admission') is not None, 'provider custody unavailable; no retry')
        self.write('snapshot.json', provider['provider_admission'])
        received = now()
        evidence = self.call('derive-review-evidence', [p['foreman'], 'provider-derive-evidence', '--requirement', i['provider_requirement'],
            '--dispatch', self.output / 'dispatch.json', '--policy', i['policy'], '--snapshot', self.output / 'snapshot.json',
            '--received-at', stamp(received), '--expires-at', stamp(received + 30000)])
        require(evidence.get('graph_validation') == 'VALIDATED', 'provider custody graph refused')
        for name in ('observation', 'disposition'): self.write(name + '.json', evidence[name])
        self.call('record-review-custody', [p['foreman'], 'provider-record', '--db', paths['foreman_database'], '--run-id', r['run_id'],
            '--work-item', r['work_item'], '--attempt-id', request['work_attempt_id'], '--observation', self.output / 'observation.json',
            '--disposition', self.output / 'disposition.json'])
        candidates = project(binding, read(i['review_requirement'])[0], read(i['review_verifier_config'])[0], provider, evidence['disposition'], now())
        for name, value in candidates.items(): self.write(name, value)
        verification = self.call('native-review-verification', [p['review_verifier'], '--config', i['review_verifier_config']], canonical(candidates['verification-request.json']), timeout=60)
        require(verification.get('binding_id') == binding['binding_id'], 'native review verifier binding differs')
        if review_only:
            return {'schema': 'constellation.review-only-result/v1', 'binding_id': binding['binding_id'],
                'verification': verification, 'candidate_review': 'record-review-input.json',
                'provider_calls': 1, 'grants': 0, 'spends': 0, 'docket_attempts': 0,
                'executor_calls': 0, 'effects': 0,
                'next_action': 'Human/operator acceptance is a separate transition; this result grants no authority.'}
        require(verification.get('accepted') is True, 'native review verifier refused')
        review_id = self.ag('record-review', 'record-review', '--input', self.output / 'record-review-input.json')
        self.ag('require-standing', 'require-standing')
        issued = now(); expires = min(issued + 60000, candidates['record-review-input.json']['review']['expires_at_unix_ms'])
        require(expires - issued >= 30000, 'remaining review window insufficient; no retiming')
        self.freshness('before-permission', expires - issued)
        mandate = {'schema': 'ag.governed-loop.standing-mandate-store/v1', 'mandates': [{'generation': 1,
            'scope': binding['scope'], 'status': 'active', 'subject': binding['subject'], 'valid_until_unix_ms': expires}]}
        self.write('mandate-create.started.json', {'path': paths['ag_mandates'], 'expires_at_unix_ms': expires})
        with Path(paths['ag_mandates']).open('xb') as stream:
            stream.write(canonical(mandate)); stream.flush(); os.fsync(stream.fileno())
        self.write('mandate-create.finished.json', {'exit_code': 0})
        permission = self.ag('permission-preflight', 'permission-preflight', '--input', self.output / 'permission-preflight-input.json')
        require(permission.get('decision') == 'allowed' and permission.get('grants_authority') is False and
            permission.get('review_id') == review_id and permission.get('binding_id') == binding['binding_id'] and
            permission.get('profile_digest') == verified['profile_digest'] and
            permission.get('key') == meta['key'], 'native preflight does not bind exact accepted review/occurrence')
        require(now() + 30000 < min(expires, permission['expires_at_unix_ms']), 'permission reserve exhausted')
        command = [p['docket'], 'governed-loop', 'standing-grant', '--state', paths['docket_state'], '--operator', self.config['operator']]
        for key in ('campaign', 'occurrence', 'subject', 'scope'): command += ['--' + key, binding[key]]
        command += ['--program', meta['program'], '--work-schema', binding['work_schema'], '--work', binding['work'],
            '--issued-at-unix-ms', issued, '--expires-at-unix-ms', expires]
        self.call('operator-grant', command, parsed=False)
        run = prepare(i['binding'], i['cycle_request'], self.output / 'record-review-input.json', i['executor_config'],
            verified['profile_digest'], min(expires, permission['expires_at_unix_ms']))
        self.write('run-input-v2.json', run)
        self.write('run-input-identity.json', {'sha256': digest(canonical(run)), 'config': digest(canonical(self.config))})
        for key, entry in self.config['programs'].items(): pinned(entry, (1024 if key == 'app_server' else 256) * 1024**2)
        for entry in self.config['inputs'].values(): pinned(entry, 16 * 1024**2)
        require(now() + 30000 < run['deadline_unix_ms'], 'finite run reserve exhausted')
        result = self.ag('finite-run', 'run', '--run-input', self.output / 'run-input-v2.json')
        require(result.get('status') == 'terminal' and result.get('reason') == 'finite_continuation_bound_complete' and
            result.get('program_counter') == 'settled_observation_required', 'finite run requires same-owner reconciliation')
        inspected = self.inspect('settled')
        require(all(inspected['replay'][key] == 1 for key in ('ag_spends', 'docket_attempts', 'settlements')), 'unexpected native consequence cardinality')
        require(inspected['current']['state']['settled_observation_required']['settlement']['outcome'] == 'success', 'native outcome is not success')
        return result

    def inspect(self, prefix):
        inspected = self.ag(prefix + '-ag-inspect', 'inspect')
        state = inspected['current']['state']
        if 'settled_observation_required' in state:
            settled = state['settled_observation_required']
            custody = settled['dispatch']['custody']
            docket = self.call(prefix + '-docket-inspect', [self.program['docket'], 'governed-loop', 'inspect',
                '--state', self.paths['docket_state'], '--issuance', custody['issuance']])
            require(docket['record']['custody'] == custody and docket['record']['settlement'] == settled['settlement'], 'native custody projections disagree')
            snapshot = self.call(prefix + '-standing-snapshot', [self.program['docket'], 'governed-loop', 'standing-snapshot',
                '--state', self.paths['docket_state'], '--issuance', custody['issuance']])
            require(snapshot['execution_standing'] == custody['execution_standing'], 'Docket standing custody differs')
            if settled['settlement']['outcome'] == 'success':
                executor = read(self.inputs['executor_config'])[0]
                plan = json.loads(base64.b64decode(executor['executor_plan_base64'], validate=True))
                output = {'path': str(Path(plan['scratch_root']) / 'result.txt'), 'sha256': plan['reviewed_text_digest']}
                pinned(output, 65536)
                require(Path(output['path']).stat().st_size == plan['reviewed_text_byte_length'], 'result byte count differs')
                self.write(prefix + '-physical-result.json', {**output, 'bytes': plan['reviewed_text_byte_length'],
                    'interpretation': 'Exact regular file inspected; not an NQ current-postcondition judgment.'})
        return inspected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--execute', action='store_true')
    modes.add_argument('--review-only', action='store_true',
        help='perform and retain bounded independent review, then stop before acceptance, grants, Docket, or effects')
    modes.add_argument('--inspect', action='store_true')
    modes.add_argument('--preflight-only', action='store_true')
    modes.add_argument('--recover-run', type=Path, metavar='ORIGINAL_OUTPUT',
        help='explicitly resume only the same retained AG run; never review or grant')
    args = parser.parse_args(argv)
    config, config_digest = configuration(args.config)
    if args.preflight_only:
        print('Exact local caller pins checked; no native invocation, provider or authority.'); return
    require(args.output.is_absolute(), 'absolute fresh output required')
    if args.execute or args.review_only or args.recover_run:
        require(bool(os.environ.get('INVOCATION_ID')), 'execution/recovery requires an operator-admitted durable service manager')
    owner_lock = None
    if args.execute or args.review_only or args.recover_run:
        lock_path = Path(config['paths']['ag_database']).parent / 'reviewed-action-caller.lock'
        owner_lock = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        fcntl.flock(owner_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    caller = Caller(config, args.output)
    caller.write('checkpoint.json', {'config': str(args.config), 'config_sha256': config_digest,
        'host': socket.gethostname(), 'manager_invocation': os.environ.get('INVOCATION_ID'),
        'mode': 'execute' if args.execute else 'review-only' if args.review_only else 'recover-run' if args.recover_run else 'inspect',
        'provider_limit': 1 if args.execute or args.review_only else 0,
        'next_action': 'Inspect original started/finished records and native owners; never restart this caller to recover.'})
    try:
        if args.recover_run:
            original = args.recover_run
            require(original.is_absolute() and original != args.output, 'separate original recovery root required')
            identity = read(original / 'run-input-identity.json')[0]
            run, raw = read(original / 'run-input-v2.json')
            require(identity['sha256'] == digest(raw) and identity['config'] == digest(canonical(config)), 'original run/config identity changed')
            require((original / 'finite-run.started.json').is_file(), 'native run was never invoked; explicit new owner decision required')
            caller.write('recovery-original.json', {'output': str(original), 'run_sha256': identity['sha256'],
                'deadline_unix_ms': run['deadline_unix_ms'], 'retimed': False, 'provider_calls': 0, 'grants': 0})
            caller.inspect('before-recovery')
            result = caller.ag('same-run-recovery', 'run', '--run-input', original / 'run-input-v2.json')
            caller.inspect('after-recovery')
        else:
            result = caller.execute(review_only=args.review_only) if args.execute or args.review_only else caller.inspect('read-only')
        caller.write('terminal.json', {'exit_code': 0, 'result': result,
            'claim': 'Native result retained for independent inspection; no blanket success or recovery qualification.'})
    except Exception as error:
        caller.write('terminal.json', {'exit_code': 1, 'phase': caller.phase, 'reason': str(error),
            'next_action': 'Reconcile the original request/attempt. No automatic review, grant, effect or deadline replacement.'})
        raise
    finally:
        if owner_lock is not None: os.close(owner_lock)


if __name__ == '__main__': main()
