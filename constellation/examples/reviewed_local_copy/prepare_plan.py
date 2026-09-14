#!/usr/bin/env python3
"""Compile caller-selected native Maude documents into a fresh checked store.

Requires the pinned public Maude package in the selected Python environment.
This writes only plan preparation records. It does not invoke an executor,
provider, NQ acquisition, AG, Docket, or any authority operation.
"""
import argparse
import base64
import json
import os
from pathlib import Path

from prepare_review_candidate import canonical, read
from reviewed_action import require


def prepare(document_path, inputs_path, output, draft_id):
    # Import only after CLI parsing. These are Maude's supported Plan Core and
    # reviewed-local-copy constructors, not copied compiler implementations.
    from maude.plan.document import PlanDocumentV1
    from maude.plan.reviewed_local_copy import (
        ReviewedLocalCopyInputsV1, ReviewedLocalCopyValidatorConfigV1,
        compile_and_bind_reviewed_local_copy, validate_reviewed_local_copy_binding,
    )
    from maude.plan.store import DraftStore

    require(output.is_absolute(), 'absolute fresh preparation root required')
    document = PlanDocumentV1.from_data(read(document_path)[0])
    inputs = ReviewedLocalCopyInputsV1.from_bytes(read(inputs_path)[1])
    scratch = Path(inputs.scratch_root)
    require(scratch.is_dir() and not scratch.is_symlink() and not any(scratch.iterdir()), 'exclusive empty scratch required')
    output.mkdir(mode=0o700, exist_ok=False)
    def write(name, value):
        raw = value if isinstance(value, bytes) else canonical(value)
        with (output / name).open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    write('preparation-started.json', {'schema': 'constellation.reviewed-local-copy-preparation/v1',
        'draft_id': draft_id, 'compiler_contract': 'maude.reviewed-local-copy/v1',
        'executor_invoked': False, 'provider_contact': False, 'authority': False})
    store_path = output / 'plans.sqlite'
    store = DraftStore(store_path)
    revision = store.create(document, draft_id=draft_id)
    checked = store.check(revision.draft_id)
    require(checked.result == 'passed', 'native Plan Core check refused')
    store.lock(revision.draft_id)
    raw = compile_and_bind_reviewed_local_copy(store, revision.draft_id, inputs)
    binding = json.loads(raw)
    validator = ReviewedLocalCopyValidatorConfigV1(str(store_path))
    validated = validate_reviewed_local_copy_binding(raw, validator)
    require(validated['result'] == 'passed' and validated['binding_id'] == binding['binding_id'], 'native read-only plan validation refused')
    write('binding.json', raw)
    write('validator-config.json', validator.canonical_bytes)
    write('compiled-handoff.json', base64.b64decode(binding['artifacts']['compiled_handoff']['bytes_base64'], validate=True))
    state = output / 'executor-state'
    state.mkdir(mode=0o700)
    write('executor-config.json', {'schema': 'maude.reviewed-local-copy.executor-config/v1',
        'executor_plan_base64': binding['artifacts']['executor_plan']['bytes_base64'], 'state_root': str(state)})
    write('plan-validation.json', validated)
    write('preparation-finished.json', {'binding_id': binding['binding_id'], 'authority': False,
        'provider_contact': False, 'executor_invoked': False})
    return binding


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('document', 'compiler-inputs', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--draft-id', required=True)
    args = parser.parse_args(argv)
    prepare(args.document, args.compiler_inputs, args.output, args.draft_id)


if __name__ == '__main__': main()

