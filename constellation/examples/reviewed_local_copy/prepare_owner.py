#!/usr/bin/env python3
"""Assemble native V2 genesis/enrollment from explicit deployment-owned ports.

No native process, key read, provider, observation, grant or effect is performed.
The native seal/verify/init commands remain separate and must succeed before
admission. Inputs are native documents; this is not a new runtime profile API.
"""
import argparse
import base64
import json
import os
from pathlib import Path

from prepare_review_candidate import canonical, digest, read
from reviewed_action import require


def assemble(binding, reviewer, nightshift, docket, *, output, runtime_profile,
             profile_label, observation_resolver, standing_resolver, standing_resolver_id,
             plan_validator, validator_config, review_verifier, nightshift_program):
    require(binding.get('schema') == 'maude.governed-plan-binding/v1' and
        binding.get('compiler_contract') == 'maude.reviewed-local-copy/v1', 'exact local-copy binding required')
    plan = json.loads(base64.b64decode(binding['artifacts']['executor_plan']['bytes_base64'], validate=True))
    require(plan['campaign'] == binding['campaign'] and plan['occurrence'] == binding['occurrence'] and
        plan['subject_digest'] == binding['subject'] and plan['scope_digest'] == binding['scope'] and
        plan['destination'] == 'result.txt', 'sealed plan occurrence differs')
    require(reviewer.get('schema') == 'switchyard.shared-review-verifier-config/v1' and
        reviewer['reviewer_id'] != reviewer['author_principal'], 'independent native reviewer enrollment required')
    require(nightshift.get('schema') == 'nightshift.ag_cycle_config.v1', 'native Nightshift config required')
    require(docket.get('schema') == 'ag.governed-loop.docket-root-enrollment/v1', 'native Docket root enrollment required')
    for locator in (output, runtime_profile, observation_resolver, standing_resolver,
            plan_validator, validator_config, review_verifier, nightshift_program):
        require(Path(locator).is_absolute(), 'absolute native material locators required')
    require(nightshift['ag_observation_resolver']['path'] == str(observation_resolver) and
        nightshift['ag_runtime_profile'] == str(runtime_profile), 'preselected Nightshift/AG locators differ')
    paths = {name: str(output / filename) for name, filename in {
        'catalog': 'exact-work-catalog-v2.json', 'reviewer': 'review-verifier-config.json',
        'requirement': 'review-requirement.json', 'nightshift': 'nightshift-ag-cycle-config.json'}.items()}
    requirement = {'schema': 'ag.governed-loop.review-requirement/v1',
        'reviewer_id': reviewer['reviewer_id'], 'route_enrollment_digest': digest(canonical(reviewer)),
        'compiler_contract': binding['compiler_contract'], 'max_age_ms': 300000}
    # This is a fresh output config, not a rewrite of an enrolled owner's file.
    ns = dict(nightshift)
    existing = ns.get('shared_admission_requirement_digest')
    require(existing is None or existing == digest(canonical(requirement)), 'existing shared requirement differs')
    ns['shared_admission_requirement_digest'] = digest(canonical(requirement))
    catalog = {'schema': 'ag.governed-loop.exact-work-catalog/v2', 'entries': {
        binding['work_schema']: {'work_schema': binding['work_schema'], 'subject': binding['subject'],
            'scope': binding['scope'], 'observation_basis': {'kind': 'nightshift_atoms',
                'requirement': {'required': ['condition.clean', 'delivery.not_required'],
                    'forbidden': ['condition.condition_present', 'condition.unresolved', 'delivery.failed', 'delivery.partial_delivery']}}}}}
    enrollment = {'schema': 'ag.governed-loop.runtime-profile-enrollment/v2', 'profile_label': profile_label,
        'observation_resolver': str(observation_resolver),
        'observation_resolver_id': ns['ag_observation_resolver_id'],
        'standing_resolver': str(standing_resolver), 'standing_resolver_id': standing_resolver_id,
        'max_standing_ttl_ms': 300000, 'exact_work_catalog': paths['catalog'],
        'controlling_review': None, 'human_verifier': None, 'docket': docket,
        'nightshift_cycle': {'schema': 'ag.governed-loop.nightshift-cycle-port/v1',
            'program': str(nightshift_program), 'config': paths['nightshift']},
        'shared_admission': {'schema': 'ag.governed-loop.shared-admission/v1',
            'plan_binding_schema': binding['schema'], 'compiler_contract': binding['compiler_contract'],
            'plan_validator': str(plan_validator), 'plan_validator_config': str(validator_config),
            'review_verifier': str(review_verifier), 'review_verifier_config': paths['reviewer'],
            'review_requirement': paths['requirement']}}
    genesis = {'campaign': binding['campaign'], 'occurrence': binding['occurrence'],
        'program': plan['program_basis'], 'expected_ag_work': binding['work'], 'residuals': [],
        'budget': {'retry_limit': 0, 'retries_used': 0, 'probe_limit': 1, 'probes_used': 0,
            'escalation_limit': 0, 'escalations_used': 0}}
    return {'exact-work-catalog-v2.json': catalog, 'review-verifier-config.json': reviewer,
        'review-requirement.json': requirement, 'nightshift-ag-cycle-config.json': ns,
        'runtime-profile-enrollment-v2.json': enrollment, 'genesis-v1.json': genesis,
        'preparation-status.json': {'status': 'NATIVE_SEAL_VERIFY_INIT_REQUIRED', 'authority': False,
            'provider_contact': False, 'review_present': False, 'observation_ttl_ms': 300000,
            'observation_ttl_basis': 'Configure native resolver from original posture time; never from this preparation.',
            'catalog_basis': 'This operation has no notification or delivery requirement.'}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binding', 'reviewer-config', 'nightshift-config', 'docket-enrollment', 'output',
            'runtime-profile', 'observation-resolver', 'standing-resolver', 'plan-validator',
            'validator-config', 'review-verifier', 'nightshift-program'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--profile-label', required=True)
    parser.add_argument('--standing-resolver-id', required=True)
    args = parser.parse_args(argv)
    material = [read(path)[0] for path in (args.binding, args.reviewer_config, args.nightshift_config, args.docket_enrollment)]
    values = assemble(*material, output=args.output, runtime_profile=args.runtime_profile,
        profile_label=args.profile_label, observation_resolver=args.observation_resolver,
        standing_resolver=args.standing_resolver, standing_resolver_id=args.standing_resolver_id,
        plan_validator=args.plan_validator, validator_config=args.validator_config,
        review_verifier=args.review_verifier, nightshift_program=args.nightshift_program)
    # Native program/config references are measured later by the supported seal
    # command. In particular this helper never opens issuer_key contents.
    args.output.mkdir(mode=0o700, exist_ok=False)
    for name, value in values.items():
        with (args.output / name).open('xb') as stream:
            stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())


if __name__ == '__main__': main()

