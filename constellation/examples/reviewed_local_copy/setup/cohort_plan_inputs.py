"""Write the fixed cohort PlanDocument and ReviewedLocalCopyInputsV1 bytes.

Run by the cohort setup driver as the cohort account, under
`python3.11 -I -S` with Maude's `maude-plan.pyz` first on `sys.path`:

    python3.11 -I -S -c 'import sys; sys.path[:0]=[PYZ, SETUP]; import cohort_plan_inputs; \
        cohort_plan_inputs.main(sys.argv[1:])' --values VALUES.json --output DIR

It uses Maude's own constructors and serialization (never hand-written plan
JSON) and refuses unless `maude` and `yaml` load from the plan archive. It
creates no plan store, invokes nothing and confers nothing: `prepare_plan.py`
compiles these bytes afterwards.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

GOAL = 'Copy exactly the selected public text to exclusive result.txt'
CRITERION = 'Exact selected UTF-8 bytes; exclusive create; no repeated copy.'
VALUE_FIELDS = {'campaign', 'occurrence', 'program', 'subject', 'scope', 'scratch_root',
                'observation', 'reviewed_text_base64', 'author'}


def require_archive(archive: str) -> dict:
    import maude
    import yaml
    origins = {'maude': maude.__file__, 'yaml': yaml.__file__}
    for name, origin in origins.items():
        if not origin or not origin.startswith(archive + os.sep):
            raise SystemExit(f'{name} must load from {archive}, not {origin}')
    return origins


def build(values: dict):
    from maude.plan.document import (DocumentConstraintsV1, PlanDocumentV1, PlanNodeV1,
                                     StructuredWorkV1, SubmitterV1)
    from maude.plan.reviewed_local_copy import ReviewedLocalCopyInputsV1
    document = PlanDocumentV1(
        goal=GOAL, workspace='exclusive-scratch',
        submitter=SubmitterV1('synthetic_agent', 'imported_from_review', values['author']),
        nodes=(PlanNodeV1('pn_copy', 'Copy selected text once', work=StructuredWorkV1(('result.txt',))),),
        constraints=DocumentConstraintsV1(declared_write_paths=('result.txt',)),
        acceptance_criteria=(CRITERION,))
    inputs = ReviewedLocalCopyInputsV1(
        values['campaign'], values['occurrence'], values['program'], values['subject'], values['scope'],
        values['scratch_root'], values['observation'], base64.b64decode(values['reviewed_text_base64'], validate=True))
    return document.canonical_bytes, inputs.canonical_bytes


def write_new(path: Path, raw: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--values', type=Path, required=True)
    parser.add_argument('--archive', required=True, help='absolute maude-plan.pyz path that must supply maude and yaml')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    origins = require_archive(args.archive)
    values = json.loads(args.values.read_bytes())
    if set(values) != VALUE_FIELDS:
        raise SystemExit('plan values must name exactly ' + ', '.join(sorted(VALUE_FIELDS)))
    if not args.output.is_absolute():
        raise SystemExit('absolute fresh output required')
    document, inputs = build(values)
    args.output.mkdir(mode=0o700, exist_ok=False)
    write_new(args.output / 'document.json', document)
    write_new(args.output / 'compiler-inputs.json', inputs)
    print(json.dumps({'schema': 'constellation.cohort-plan-inputs/v1', 'document': str(args.output / 'document.json'),
                      'compiler_inputs': str(args.output / 'compiler-inputs.json'), 'module_origins': origins,
                      'authority': False}, sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    main()
