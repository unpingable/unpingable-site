"""Public-only candidate controls. All provider frames here are local fixtures."""
import copy
import base64
import importlib.util
from pathlib import Path
import sys
import tempfile
import time
import unittest
import io
import os
import subprocess
from unittest.mock import patch

EXAMPLE = Path(__file__).resolve().parents[1] / 'constellation/examples/reviewed_local_copy'
sys.path.insert(0, str(EXAMPLE))
import prepare_review_candidate as candidate
import prepare_finite_run as finite
import reviewed_action as action
import drop_success_response as drop_response
import prepare_plan
import prepare_owner
import seal_admission
import prepare_public_python_closure as python_closure


def fixture():
    identity = 'sha256:' + '1' * 64
    binding = {'schema': 'maude.governed-plan-binding/v1', 'binding_id': identity,
        'campaign': 'local-fixture-campaign', 'occurrence': 'local-fixture-occurrence',
        'compiler_contract': 'maude.reviewed-local-copy/v1'}
    config = {'schema': 'switchyard.shared-review-verifier-config/v1', 'reviewer_id': 'fixture-reviewer',
        'author_principal': 'fixture-author', 'nightshift_run_id': 'fixture-review-run'}
    requirement = {'schema': 'ag.governed-loop.review-requirement/v1', 'reviewer_id': config['reviewer_id'],
        'route_enrollment_digest': candidate.digest(candidate.canonical(config)),
        'compiler_contract': binding['compiler_contract'], 'max_age_ms': 300000}
    result = {'schema': 'switchyard.shared-source-review/v1', 'binding_id': identity,
        'verdict': 'accepted', 'findings': [{'code': 'FIXTURE', 'summary': 'Local substitution, not a real review.'}]}
    dispatch = {'dispatch_digest': 'sha256:' + '2' * 64, 'run_id': config['nightshift_run_id'],
        'work_attempt_id': 'fixture-attempt', 'dispatch_occurrence_id': 'fixture-dispatch',
        'worker_brief_digest': 'sha256:' + '3' * 64}
    provider = {'state': 'PROVIDER_COMPLETED', 'turn_status': 'completed', 'semantic_retry': False,
        'approval_response_sent': False, 'worker_output': candidate.canonical(result).decode(),
        'ended_at_unix_ms': 1000, 'dispatch_record': dispatch,
        'work_attempt_id': dispatch['work_attempt_id'], 'dispatch_occurrence_id': dispatch['dispatch_occurrence_id'],
        'thread_id': 'fixture-thread', 'turn_id': 'fixture-turn'}
    disposition = {'schema': 'nightshift.provider-admission-disposition/v1', 'disposition': 'EXECUTION_ADMITTED',
        'acquisition_complete': True, 'response_created': True, 'will_retry': False,
        'approval_response_sent': False, 'protected_effect_absent': True, **dispatch,
        'thread_id': provider['thread_id'], 'turn_id': provider['turn_id'],
        'disposition_digest': 'sha256:' + '4' * 64}
    return [binding, requirement, config, provider, disposition]


class CandidateControls(unittest.TestCase):
    def test_public_python_closure_requirement_set_covers_declared_format_extra(self):
        required = {entry.split('==', 1)[0] for entry in python_closure.WHEEL_REQUIREMENTS}
        self.assertEqual(len(required), len(python_closure.WHEEL_REQUIREMENTS))
        self.assertTrue({'jsonschema', 'attrs', 'pyrsistent', 'fqdn', 'idna', 'isoduration',
            'jsonpointer', 'rfc3339-validator', 'rfc3987', 'types-python-dateutil', 'uri-template', 'webcolors'} <= required)
        self.assertEqual(python_closure.SWITCHYARD_REVISION, '1c82e719cf358728d0262ae11138fb13fefe0cae')
        self.assertEqual(python_closure.MAUDE_REVISION, '0d5b6c91102b1088818d0493c687f9f23db7684e')
        self.assertEqual(python_closure.PUBLIC_LOCK.read_text().splitlines(), sorted(python_closure.PUBLIC_LOCK.read_text().splitlines()))
        self.assertEqual(len(python_closure.PUBLIC_LOCK.read_text().splitlines()), len(required))

    def test_public_python_closure_wrapper_has_no_campaign_local_defaults(self):
        wrapper = (EXAMPLE / 'run_public_python_closure_001.sh').read_text()
        self.assertIn('--switchyard ABSOLUTE_SOURCE', wrapper)
        self.assertIn('--maude ABSOLUTE_SOURCE', wrapper)
        self.assertNotIn('/data/git/', wrapper)
        self.assertNotIn('constellation-public-', wrapper)
        self.assertNotIn('/tmp/', wrapper)

    def test_static_owner_projection_keeps_review_gate_and_no_delivery_catalog(self):
        """Wire projection only; no native genesis or authority is created."""
        binding, _, reviewer, _, _ = fixture()
        binding.update(subject='sha256:'+'5'*64, scope='sha256:'+'6'*64,
            work='sha256:'+'7'*64, work_schema='maude.reviewed-local-copy/v1')
        plan = {'campaign': binding['campaign'], 'occurrence': binding['occurrence'],
            'subject_digest': binding['subject'], 'scope_digest': binding['scope'],
            'program_basis': 'sha256:'+'8'*64, 'destination': 'result.txt'}
        binding['artifacts'] = {'executor_plan': {'bytes_base64': base64.b64encode(candidate.canonical(plan)).decode()}}
        ns = {'schema': 'nightshift.ag_cycle_config.v1', 'ag_observation_resolver': {'path': '/fixture/observation'},
            'ag_runtime_profile': '/fixture/profile', 'ag_observation_resolver_id': 'fixture-observation/v1'}
        kwargs = {'output': Path('/fixture/owner'), 'runtime_profile': Path('/fixture/profile'),
            'profile_label': 'fixture-local-copy', 'observation_resolver': Path('/fixture/observation'),
            'standing_resolver': Path('/fixture/standing'), 'standing_resolver_id': 'fixture-standing/v1',
            'plan_validator': Path('/fixture/validator'), 'validator_config': Path('/fixture/validator.json'),
            'review_verifier': Path('/fixture/reviewer'), 'nightshift_program': Path('/fixture/nightshift')}
        docket = {'schema': 'ag.governed-loop.docket-root-enrollment/v1'}
        result = prepare_owner.assemble(binding, reviewer, ns, docket, **kwargs)
        self.assertEqual(result['genesis-v1.json']['expected_ag_work'], binding['work'])
        self.assertEqual(result['review-requirement.json']['max_age_ms'], 300000)
        self.assertIn('shared_admission', result['runtime-profile-enrollment-v2.json'])
        law = result['exact-work-catalog-v2.json']['entries'][binding['work_schema']]['observation_basis']['requirement']
        self.assertEqual(law['required'], ['condition.clean', 'delivery.not_required'])
        self.assertEqual(len(law['forbidden']), 4)
        self.assertFalse(result['preparation-status.json']['review_present'])
        ns['shared_admission_requirement_digest'] = 'sha256:'+'0'*64
        with self.assertRaisesRegex(ValueError, 'requirement differs'):
            prepare_owner.assemble(binding, reviewer, ns, docket, **kwargs)

    def test_native_maude_plan_preparation_when_public_package_is_installed(self):
        try:
            from maude.plan.document import PlanDocumentV1, SubmitterV1, PlanNodeV1, StructuredWorkV1, DocumentConstraintsV1
            from maude.plan.reviewed_local_copy import ReviewedLocalCopyInputsV1, ReviewedLocalCopyValidatorConfigV1, validate_reviewed_local_copy_binding
        except ModuleNotFoundError:
            self.skipTest('install the pinned public Maude package to run the actual native preparation control')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); scratch = root / 'scratch'; scratch.mkdir()
            document = PlanDocumentV1(goal='Local component fixture: prepare a sealed copy, never execute',
                workspace='exclusive-scratch', submitter=SubmitterV1('synthetic_agent', 'imported_from_review', 'local-qualification'),
                nodes=(PlanNodeV1('pn_copy', 'Copy exact selected bytes', work=StructuredWorkV1(('result.txt',))),),
                constraints=DocumentConstraintsV1(declared_write_paths=('result.txt',)),
                acceptance_criteria=('The exact selected bytes would be written only to result.txt.',))
            inputs = ReviewedLocalCopyInputsV1('sha256:' + 'a'*64, '11111111-1111-4111-8111-111111111111',
                'sha256:' + 'b'*64, 'sha256:' + 'c'*64, 'sha256:' + 'd'*64, str(scratch), 'sha256:' + 'e'*64,
                b'Local preparation fixture; not copied.\n')
            (root / 'document').write_bytes(document.canonical_bytes)
            (root / 'inputs').write_bytes(inputs.canonical_bytes)
            binding = prepare_plan.prepare(root / 'document', root / 'inputs', root / 'prepared', 'draft_' + 'a'*32)
            config = ReviewedLocalCopyValidatorConfigV1.from_bytes((root / 'prepared/validator-config.json').read_bytes())
            validated = validate_reviewed_local_copy_binding((root / 'prepared/binding.json').read_bytes(), config)
            self.assertEqual(validated['binding_id'], binding['binding_id'])
            self.assertEqual(list(scratch.iterdir()), [])
            request = {'schema': 'nightshift.canonical_cycle_request.v1', 'observation_id': inputs.observation,
                'evaluated_at': '2020-01-01T00:00:00Z', 'proposal': None, 'reviewed_plan_binding': None}
            request['request_id'] = candidate.digest(candidate.canonical(request))
            sealed = seal_admission.seal(binding, (root / 'prepared/binding.json').read_bytes(), request)
            self.assertEqual(sealed['evaluated_at'], request['evaluated_at'])
            self.assertEqual(sealed['observation_id'], inputs.observation)
            self.assertEqual(sealed['proposal']['campaign_id'], binding['campaign'])
            request['observation_id'] = 'sha256:' + 'f'*64
            request.pop('request_id'); request['request_id'] = candidate.digest(candidate.canonical(request))
            with self.assertRaisesRegex(ValueError, 'different observation'):
                seal_admission.seal(binding, (root / 'prepared/binding.json').read_bytes(), request)
            allocated = seal_admission.seal(binding, (root / 'prepared/binding.json').read_bytes(), request,
                use_plan_observation_identity=True)
            self.assertEqual(allocated['observation_id'], inputs.observation)
            self.assertEqual(allocated['evaluated_at'], request['evaluated_at'])
            with self.assertRaises(FileExistsError):
                prepare_plan.prepare(root / 'document', root / 'inputs', root / 'prepared', 'draft_' + 'a'*32)

    def test_candidate_never_claims_authentication_or_permission(self):
        outputs = candidate.project(*fixture(), 2000)
        self.assertEqual(outputs['candidate-status.json']['status'], 'CANDIDATE_ONLY_NOT_AUTHENTICATED')
        self.assertFalse(outputs['candidate-status.json']['native_store_custody_verified'])
        self.assertFalse(outputs['candidate-status.json']['authority'])
        self.assertEqual(outputs['record-review-input.json']['review']['reviewed_at_unix_ms'], 1000)
        self.assertEqual(outputs['record-review-input.json']['review']['expires_at_unix_ms'], 301000)

    def test_currentness_and_contract_refusals(self):
        for case in ('expired', 'future', 'binding', 'rejected', 'lost', 'retry', 'thread', 'enrollment', 'oversize'):
            with self.subTest(case=case):
                values, now = fixture(), 2000
                if case == 'expired': now = 301000
                if case == 'future': now = 999
                if case == 'binding': values[0]['binding_id'] = 'sha256:' + '9' * 64
                if case == 'rejected': values[3]['worker_output'] = values[3]['worker_output'].replace('accepted', 'rejected')
                if case == 'lost': values[3]['worker_output'] = None
                if case == 'retry': values[3]['semantic_retry'] = True
                if case == 'thread': values[4]['thread_id'] = 'other-thread'
                if case == 'enrollment': values[1]['route_enrollment_digest'] = 'sha256:' + '0' * 64
                if case == 'oversize': values[3]['worker_output'] = 'x' * 32769
                with self.assertRaises(ValueError): candidate.project(*values, now)

    def test_exact_json_and_regular_file_boundary(self):
        for value in ({'number': 1.5}, {'number': 2**53}, {'nonascii-\u2603': True}):
            with self.assertRaises(ValueError): candidate.canonical(value)
        with self.assertRaises(ValueError): candidate.pairs([('a', 1), ('a', 2)])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'input').write_bytes(b'{"a":1}')
            (root / 'link').symlink_to(root / 'input')
            self.assertEqual(candidate.read(root / 'input')[0], {'a': 1})
            with self.assertRaises(OSError): candidate.read(root / 'link')

    def test_finite_input_exact_binding_transport_and_original_deadline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            values = fixture()
            binding = values[0]
            binding.update(subject='sha256:' + '5' * 64, scope='sha256:' + '6' * 64)
            plan = {'campaign': binding['campaign'], 'occurrence': binding['occurrence'],
                'subject_digest': binding['subject'], 'scope_digest': binding['scope'], 'destination': 'result.txt'}
            encoded = base64.b64encode(candidate.canonical(plan)).decode()
            binding['artifacts'] = {'executor_plan': {'bytes_base64': encoded}}
            binding_raw = candidate.canonical(binding)
            request = {'schema': 'nightshift.canonical_cycle_request.v1',
                'proposal': {'campaign_id': binding['campaign'], 'occurrence_id': binding['occurrence']},
                'reviewed_plan_binding': {'binding_sha256': candidate.digest(binding_raw),
                    'binding_base64': base64.b64encode(binding_raw).decode()}}
            outputs = candidate.project(*values, 2000)
            for name, value in {'binding': binding, 'cycle': request, 'review': outputs['record-review-input.json'],
                    'executor': {'executor_plan_base64': encoded}}.items():
                (root / name).write_bytes(candidate.canonical(value))
            args = [root / name for name in ('binding', 'cycle', 'review', 'executor')]
            prepared = finite.prepare(*args, 'sha256:' + '7' * 64, 3000)
            self.assertEqual(prepared['continuations'], [])
            self.assertEqual(prepared['deadline_unix_ms'], 3000)
            self.assertEqual(prepared['initial']['plan_binding_sha256'], candidate.digest(binding_raw))
            with self.assertRaises(ValueError): finite.prepare(*args, 'sha256:' + '7' * 64, 301001)
            request['reviewed_plan_binding']['binding_sha256'] = 'sha256:' + '9' * 64
            (root / 'cycle').write_bytes(candidate.canonical(request))
            with self.assertRaisesRegex(ValueError, 'transport'): finite.prepare(*args, 'sha256:' + '7' * 64, 3000)

    def test_help_and_missing_cli_arguments_never_launch_a_child(self):
        for argv in (['--help'], [], ['--execute']):
            with self.subTest(argv=argv), patch.object(action.subprocess, 'Popen', side_effect=AssertionError('unexpected child')):
                with self.assertRaises(SystemExit): action.main(argv)

    def test_bounded_subprocess_collection_and_failure_retention(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            instance = action.Caller({'programs': {}, 'inputs': {}, 'paths': {}}, root)
            self.assertEqual(instance.call('local-json', [sys.executable, '-c', 'print("{}")']), {})
            with self.assertRaisesRegex(ValueError, 'refused'):
                instance.call('local-refusal', [sys.executable, '-c', 'raise SystemExit(7)'])
            self.assertTrue((root / 'local-refusal.started.json').is_file())
            self.assertTrue((root / 'local-refusal.finished.json').is_file())
            with self.assertRaises(FileExistsError): instance.call('local-json', [sys.executable, '-c', 'print("{}")'])

    def test_independent_original_observation_and_pulse_clock_reserves(self):
        for case in ('current', 'nq_reserve', 'pulse_reserve', 'retimed_nq', 'clock', 'receipt'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                query = {'schema': 'nightshift.qualified_support_query.v1', 'subject': 'fixture-subject'}
                retention = {'evidence_id': 'fixture-receipt', 'received_at': {'clock_id': 'fixture-boot'}, 'expiry_tick_ms': 300000}
                support = {'schema': 'nightshift.qualified_support.v1', 'standing': 'current',
                    'subject': query['subject'], 'evidence_refs': ['fixture-receipt'],
                    'evaluated_at': {'clock_id': 'fixture-boot', 'tick': 1000},
                    'expiry': {'clock_id': 'fixture-boot', 'tick': 300000}}
                observation = {'schema': 'ag.governed-loop.observation-resolution/v2', 'status': 'current',
                    'resolved_at_unix_ms': 1000, 'fresh_until_unix_ms': 300000}
                checked = 1000
                if case == 'nq_reserve': checked = 70001
                if case == 'pulse_reserve': support['evaluated_at']['tick'] = 70001
                if case == 'retimed_nq': observation['fresh_until_unix_ms'] += 1
                if case == 'clock': support['evaluated_at']['clock_id'] = 'different-boot'
                if case == 'receipt': support['evidence_refs'] = ['different-receipt']
                support['support_id'] = candidate.digest(candidate.canonical(support))
                for name, value in {'pulse_query': query, 'pulse_retention': retention,
                        'cycle_request': {'evaluated_at': '1970-01-01T00:00:00.000Z'}}.items():
                    (root / name).write_bytes(candidate.canonical(value))
                config = {'programs': {'pulse': {'path': 'fixture-pulse'}},
                    'inputs': {name: {'path': str(root / name)} for name in ('pulse_query', 'pulse_retention', 'cycle_request')}, 'paths': {}}
                instance = action.Caller(config, root)
                with patch.object(instance, 'call', return_value=support), patch.object(instance, 'ag',
                        return_value={'current': {'state': {'proposal_recorded': {'observation': observation}}}}), patch.object(action, 'now', return_value=checked):
                    if case == 'current': instance.freshness('check', 230000)
                    else:
                        with self.assertRaises(ValueError): instance.freshness('check', 230000)

    def test_same_run_recovery_never_invokes_execute_or_changes_original_deadline(self):
        for case in ('exact', 'mutated_run', 'changed_config', 'not_started'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); original = root / 'original'; original.mkdir()
                config = {'programs': {}, 'inputs': {}, 'paths': {'ag_database': str(root / 'ag.sqlite')}}
                run = {'schema': 'ag.governed-loop.run-input/v2', 'deadline_unix_ms': 1}
                raw = candidate.canonical(run)
                (original / 'run-input-v2.json').write_bytes(raw)
                identity = {'sha256': candidate.digest(raw), 'config': candidate.digest(candidate.canonical(config))}
                if case == 'mutated_run': (original / 'run-input-v2.json').write_bytes(raw + b' ')
                if case == 'changed_config': identity['config'] = 'sha256:' + '0' * 64
                (original / 'run-input-identity.json').write_bytes(candidate.canonical(identity))
                if case != 'not_started': (original / 'finite-run.started.json').write_bytes(b'{}')
                with patch.object(action, 'configuration', return_value=(config, 'fixture-config')), patch.dict(os.environ, INVOCATION_ID='fixture-manager'), \
                        patch.object(action.Caller, 'execute', side_effect=AssertionError('restarted execution')), \
                        patch.object(action.Caller, 'inspect', return_value={}), patch.object(action.Caller, 'ag', return_value={'status': 'waiting'}) as native:
                    argv = ['--config', str(root / 'config'), '--output', str(root / 'recovery'), '--recover-run', str(original)]
                    if case == 'exact':
                        action.main(argv)
                        self.assertEqual(native.call_args.args, ('same-run-recovery', 'run', '--run-input', original / 'run-input-v2.json'))
                        self.assertEqual(candidate.read(root / 'recovery/recovery-original.json')[0]['deadline_unix_ms'], 1)
                    else:
                        with self.assertRaises(ValueError): action.main(argv)
                        native.assert_not_called()

    def test_completed_response_loss_wrapper_with_harmless_local_program(self):
        """Actual subprocess collection, but no Maude operation or authority."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); records = root / 'records'; records.mkdir()
            program = root / 'local-json'
            program.write_text('#!/usr/bin/python3.12\nprint("{}")\n'); program.chmod(0o700)
            pin = candidate.digest(program.read_bytes())
            argv = ['--executor', str(program), '--sha256', pin, '--records', str(records), 'execute', str(root / 'unused-config')]
            with patch.object(drop_response.sys, 'stdin', type('Input', (), {'buffer': io.BytesIO(b'{}')})()):
                self.assertEqual(drop_response.main(argv), 74)
            self.assertEqual((records / 'native-execute.stdout').read_bytes(), b'{}\n')
            self.assertEqual(candidate.read(records / 'response-withheld.json')[0]['stdout_forwarded_bytes'], 0)
            with patch.object(drop_response.sys, 'stdin', type('Input', (), {'buffer': io.BytesIO(b'{}')})()), \
                    patch.object(action.subprocess, 'Popen', side_effect=AssertionError('repeated execute')):
                with self.assertRaises(FileExistsError): drop_response.main(argv)

    def test_whole_caller_transport_schedule_only_no_native_authority(self):
        """All stage returns below are labeled substitutions, not live owners."""
        for failure in (None, 'nightshift-admission', 'provider-run', 'native-review-verification',
                'permission-preflight', 'operator-grant', 'finite-run'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); output = root / 'output'; output.mkdir()
                scratch = root / 'scratch'; scratch.mkdir()
                executor_state = root / 'executor-state'; executor_state.mkdir()
                docket = root / 'docket'; docket.mkdir()
                values = fixture(); binding, requirement, review_config, provider, disposition = values
                binding.update(subject='sha256:' + '5' * 64, scope='sha256:' + '6' * 64,
                    work='sha256:' + '7' * 64, work_schema='maude.reviewed-local-copy/v1')
                provider['ended_at_unix_ms'] = action.now(); provider['provider_admission'] = {}
                plan = {'campaign': binding['campaign'], 'occurrence': binding['occurrence'],
                    'subject_digest': binding['subject'], 'scope_digest': binding['scope'], 'destination': 'result.txt',
                    'scratch_root': str(scratch), 'reviewed_text_byte_length': 38}
                encoded = base64.b64encode(candidate.canonical(plan)).decode()
                binding['artifacts'] = {'executor_plan': {'bytes_base64': encoded}}
                raw = candidate.canonical(binding)
                cycle = {'schema': 'nightshift.canonical_cycle_request.v1',
                    'proposal': {'campaign_id': binding['campaign'], 'occurrence_id': binding['occurrence']},
                    'reviewed_plan_binding': {'binding_sha256': candidate.digest(raw), 'binding_base64': base64.b64encode(raw).decode()}}
                documents = {'binding': binding, 'runtime_profile': {'schema': 'ag.governed-loop.runtime-profile/v2'},
                    'executor_config': {'executor_plan_base64': encoded, 'state_root': str(executor_state)},
                    'review_requirement': requirement, 'review_verifier_config': review_config, 'cycle_request': cycle}
                for key in action.INPUTS:
                    (root / (key + '.json')).write_bytes(candidate.canonical(documents.get(key, {})))
                config = {'programs': {key: {'path': 'fixture-' + key, 'sha256': 'fixture-only'} for key in action.PROGRAMS},
                    'inputs': {key: {'path': str(root / (key + '.json')), 'sha256': 'fixture-only'} for key in action.INPUTS},
                    'paths': {'ag_database': str(root / 'ag.sqlite'), 'foreman_database': str(root / 'foreman.sqlite'),
                        'switchyard_database': str(root / 'switchyard.sqlite'), 'docket_state': str(docket),
                        'ag_mandates': str(root / 'mandate.json')},
                    'operator': 'fixture-operator', 'review': {'run_id': 'fixture-review-run', 'work_item': 'fixture-item',
                        'dispatch_id': 'fixture-dispatch', 'adapter_process': 'fixture-process', 'app_server_session_identity': 'fixture-session'}}
                meta = {'key': {'campaign': binding['campaign'], 'occurrence': binding['occurrence']},
                    'program': 'fixture-program', 'expected_work': binding['work']}
                profile_digest = 'sha256:' + '8' * 64
                request = {'timeout_seconds': 120, 'maximum_output_bytes': 32768, 'semantic_retry': False,
                    'approval_response_authorized': False, 'internal_provider_retry_count': 0,
                    'recursive_worker_swarms_forbidden': True, 'selected_model_ordinal': 0,
                    'request_digest': 'fixture-request', 'work_attempt_id': 'fixture-attempt'}
                steps = []
                class FixtureCaller(action.Caller):
                    def call(self, name, argv, stdin=None, timeout=30, parsed=True):
                        self.phase = name; steps.append(name)
                        self.write(name + '.started.json', {'qualification': 'SUBSTITUTED_TRANSPORT_ONLY'})
                        if name == failure: raise ValueError('fixture response loss/refusal')
                        self.write(name + '.finished.json', {'exit_code': 0})
                        if name == 'profile-verify': return {'profile_digest': profile_digest}
                        if name == 'initial-inspect': return {'runtime_profile': {'digest': profile_digest},
                            'current': {'state': {'observation_required': {}}},
                            'replay': {'ag_spends': 0, 'docket_attempts': 0, 'settlements': 0}}
                        if name == 'admitted-inspect': return {'current': {'state': {'proposal_recorded': {'meta': meta}}}}
                        if name == 'review-prepare': return {'worker_start_request': request, 'dispatch': provider['dispatch_record']}
                        if name == 'review-brief': return b'{}'
                        if name == 'review-local-preflight': return {'provider_contact': False, 'request_digest': 'fixture-request'}
                        if name == 'provider-run': return provider
                        if name == 'derive-review-evidence': return {'graph_validation': 'VALIDATED', 'observation': {}, 'disposition': disposition}
                        if name == 'native-review-verification': return {'accepted': True, 'binding_id': binding['binding_id']}
                        if name == 'record-review': return 'fixture-native-review'
                        if name == 'permission-preflight': return {'decision': 'allowed', 'grants_authority': False,
                            'review_id': 'fixture-native-review', 'binding_id': binding['binding_id'],
                            'profile_digest': profile_digest, 'key': meta['key'], 'expires_at_unix_ms': action.now() + 60000}
                        if name == 'finite-run': return {'status': 'terminal', 'reason': 'finite_continuation_bound_complete', 'program_counter': 'settled_observation_required'}
                        return {}
                    def freshness(self, name, minimum): steps.append(name)
                    def inspect(self, prefix): return {'replay': {'ag_spends': 1, 'docket_attempts': 1, 'settlements': 1},
                        'current': {'state': {'settled_observation_required': {'settlement': {'outcome': 'success'}}}}}
                instance = FixtureCaller(config, output)
                with patch.object(action, 'pinned'), patch.object(action.subprocess, 'Popen', side_effect=AssertionError('fixture launched a child')):
                    if failure:
                        with self.assertRaises(ValueError): instance.execute()
                    else: instance.execute()
                self.assertLessEqual(steps.count('provider-run'), 1)
                if 'provider-run' in steps: self.assertLess(steps.index('nightshift-admission'), steps.index('provider-run'))
                if 'operator-grant' in steps: self.assertLess(steps.index('permission-preflight'), steps.index('operator-grant'))
                if failure in ('nightshift-admission', 'provider-run', 'native-review-verification', 'permission-preflight'):
                    self.assertNotIn('operator-grant', steps)
                if failure:
                    self.assertFalse((output / (failure + '.finished.json')).exists())


if __name__ == '__main__': unittest.main()
