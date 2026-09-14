#!/usr/bin/env python3
"""Create an exact one-occurrence native AG V2 run document, without running it."""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
import re

from prepare_review_candidate import canonical, digest, read


def prepare(binding_path, cycle_path, review_path, executor_path, profile_digest, deadline):
    paths = [binding_path, cycle_path, review_path, executor_path]
    if any(not path.is_absolute() for path in paths): raise ValueError('native material paths must be absolute')
    binding, binding_raw = read(binding_path)
    request, request_raw = read(cycle_path)
    review, _ = read(review_path)
    executor, _ = read(executor_path)
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', profile_digest): raise ValueError('invalid native profile digest')
    if (binding.get('schema') != 'maude.governed-plan-binding/v1' or
            review.get('schema') != 'ag.governed-loop.review-record-input/v1' or
            review.get('binding_id') != binding['binding_id'] or
            review.get('campaign') != binding['campaign'] or review.get('occurrence') != binding['occurrence']):
        raise ValueError('review candidate does not bind this exact occurrence')
    if canonical(binding) != binding_raw.removesuffix(b'\n'):
        raise ValueError('plan binding must retain canonical bytes')
    plan_raw = base64.b64decode(executor['executor_plan_base64'], validate=True)
    plan = json.loads(plan_raw)
    if (binding['compiler_contract'] != 'maude.reviewed-local-copy/v1' or
            plan['destination'] != 'result.txt' or
            base64.b64decode(binding['artifacts']['executor_plan']['bytes_base64'], validate=True) != plan_raw):
        raise ValueError('executor configuration differs from the exact reviewed plan')
    for name, plan_name in (('campaign', 'campaign'), ('occurrence', 'occurrence'),
            ('subject', 'subject_digest'), ('scope', 'scope_digest')):
        if plan[plan_name] != binding[name]: raise ValueError('executor occurrence differs: ' + name)
    if request.get('schema') != 'nightshift.canonical_cycle_request.v1':
        raise ValueError('unsupported native cycle request schema')
    proposal, transport = request.get('proposal', {}), request.get('reviewed_plan_binding', {})
    if (proposal.get('campaign_id') != binding['campaign'] or proposal.get('occurrence_id') != binding['occurrence'] or
            transport.get('binding_sha256') != digest(binding_raw) or
            base64.b64decode(transport.get('binding_base64', ''), validate=True) != binding_raw):
        raise ValueError('cycle request does not transport this exact binding')
    if (type(deadline) is not int or not review['review']['reviewed_at_unix_ms'] < deadline <=
            review['review']['expires_at_unix_ms']):
        raise ValueError('run deadline must fit the original review window')
    # This helper does not claim current evidence, accepted review or permission.
    # Native AG verifies exact request, profile, plan and review at live gates.
    return {'schema': 'ag.governed-loop.run-input/v2', 'campaign': binding['campaign'],
        'runtime_profile_digest': profile_digest,
        'initial': {'occurrence': binding['occurrence'], 'plan_binding': str(binding_path),
            'plan_binding_sha256': digest(binding_raw), 'review_input': str(review_path),
            'nightshift_cycle_request': str(cycle_path), 'nightshift_cycle_request_sha256': digest(request_raw),
            'executor_config': str(executor_path)},
        'continuations': [], 'max_steps': 32, 'max_polls': 2, 'deadline_unix_ms': deadline}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binding', 'cycle-request', 'review-input', 'executor-config', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--runtime-profile-digest', required=True)
    parser.add_argument('--deadline-unix-ms', type=int, required=True)
    args = parser.parse_args(argv)
    value = prepare(args.binding, args.cycle_request, args.review_input, args.executor_config,
        args.runtime_profile_digest, args.deadline_unix_ms)
    with args.output.open('xb') as stream:
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
    print('Exact native run document prepared; no native command or authority operation was invoked.')


if __name__ == '__main__': main()

