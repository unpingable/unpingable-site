#!/usr/bin/env python3
"""Attach one exact native Maude handoff to an observed posture-only request.

Does not acquire evidence, change its timestamp, invoke Nightshift, or confer
authority. Native Nightshift and AG remain the semantic admission validators.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import re

from prepare_review_candidate import canonical, digest, read
from reviewed_action import require


def seal(binding, binding_raw, request, *, use_plan_observation_identity=False):
    require(binding.get('schema') == 'maude.governed-plan-binding/v1' and
        canonical(binding) == binding_raw, 'exact canonical Maude binding required')
    require(request.get('schema') == 'nightshift.canonical_cycle_request.v1' and
        request.get('proposal') is None and request.get('reviewed_plan_binding') is None,
        'unadmitted posture-only request required')
    request_preimage = dict(request); request_preimage.pop('request_id')
    require(request['request_id'] == digest(canonical(request_preimage)), 'posture request identity differs')
    artifact = binding['artifacts']['compiled_handoff']
    raw = base64.b64decode(artifact['bytes_base64'], validate=True)
    require(digest(raw) == artifact['sha256'] and len(raw) == artifact['byte_length'], 'compiled handoff artifact differs')
    proposal = json.loads(raw)
    require(canonical(proposal) == raw and proposal.get('schema') == 'nightshift.precompiled_workflow_proposal.v2',
        'exact native precompiled handoff required')
    require(proposal['campaign_id'] == binding['campaign'] and proposal['occurrence_id'] == binding['occurrence'] and
        proposal['subject_digest'] == binding['subject'] and proposal['proposal_input']['proposal']['work'] == binding['work'],
        'native proposal and binding coordinates differ')
    allocated = proposal['proposal_input']['observation']
    require(re.fullmatch(r'sha256:[0-9a-f]{64}', allocated) is not None, 'invalid owner observation identity')
    require(use_plan_observation_identity or allocated == request['observation_id'],
        'plan was compiled for a different observation; explicit owner identity allocation required')
    result = dict(request)
    if use_plan_observation_identity:
        # Native observation IDs are owner-allocated coordinates, not evidence
        # digests. The actual diagnostic/posture and original times stay exact.
        result['observation_id'] = allocated
    result['proposal'] = proposal
    result['reviewed_plan_binding'] = {'schema': 'nightshift.reviewed-plan-binding-transport/v1',
        'binding_sha256': digest(binding_raw), 'binding_base64': base64.b64encode(binding_raw).decode('ascii')}
    preimage = dict(result); preimage.pop('request_id')
    result['request_id'] = digest(canonical(preimage))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binding', 'posture-request', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--use-plan-observation-identity', action='store_true',
        help='assign the preallocated plan observation coordinate to this actual posture; never change evidence/times')
    args = parser.parse_args(argv)
    binding, raw = read(args.binding)
    result = seal(binding, raw, read(args.posture_request)[0], use_plan_observation_identity=args.use_plan_observation_identity)
    with args.output.open('xb') as stream:
        stream.write(canonical(result)); stream.flush(); os.fsync(stream.fileno())


if __name__ == '__main__': main()

