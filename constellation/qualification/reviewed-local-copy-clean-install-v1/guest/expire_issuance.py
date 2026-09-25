"""QUALIFICATION-ONLY: show that an expired AG issuance is never presented.

Run as root in the guest: python3.11 -I -S expire_issuance.py --cohort C --candidate-sha256 D

1. As a labelled SYNTHETIC OPERATOR, run the kit continuation for the exact
   retained candidate in a durable unit as the cohort account, with its run
   document bounded to two AG steps (decide, then authorize) and its deadline
   set to the end of the review window (inside the window prepare_finite_run
   validates). AG mints the issuance (the spend) and stops before dispatch.
2. Wait until the issuance's signed not_after has passed (the run deadline
   has not).
3. Run AG's finite runner again with the same run document, which AG resumes
   at dispatch. AG must refuse to present the retained issuance because it is
   past its not_after; Docket must hold no record and the executor must not
   have run.

Prints one JSON report. Nothing here is a product path.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

STATE = Path('/var/lib/constellation/cohorts')
INSTALL = Path('/opt/constellation/cohorts')


def as_cohort(argv, *, env=None, timeout=120):
    return subprocess.run(['/usr/bin/setpriv', '--reuid=constellation', '--regid=constellation', '--init-groups',
                           '--no-new-privs', '--', *map(str, argv)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=env or {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, timeout=timeout, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', required=True)
    parser.add_argument('--candidate-sha256', required=True)
    args = parser.parse_args()
    state = STATE / args.cohort
    roots = json.loads((INSTALL / args.cohort / 'installed.json').read_text())['roots']
    kit, ag, docket = Path(roots['cohort-kit']), Path(roots['ag']) / 'bin/ag-loopctl', Path(roots['docket']) / 'bin/docket'
    report = {'schema': 'constellation.qualification.expired-issuance/v1', 'cohort': args.cohort,
              'operator': 'SYNTHETIC OPERATOR (harness)'}
    output = state / 'runs' / 'continuation-bounded-001'
    code = (f"import sys; sys.path[:0]=[{str(kit / 'setup')!r}, {str(kit)!r}]; import continue_reviewed_action as c; "
            "original = c.prepare\n"
            "import json\n"
            "def bounded(*a):\n    value = original(*a); value['max_steps'] = 2\n"
            "    review = json.loads(open(a[2], 'rb').read())['review']\n"
            "    value['deadline_unix_ms'] = review['expires_at_unix_ms'] - 1000; return value\n"
            "c.prepare = bounded; c.main(sys.argv[1:])")
    first = subprocess.run(['systemd-run', '--wait', '--pipe', '--collect', '--quiet', '--uid=constellation',
                            '--gid=constellation', '--setenv=PATH=/usr/bin:/bin', '--setenv=LANG=C.UTF-8', '--',
                            '/usr/bin/python3.11', '-I', '-S', '-c', code, '--config', state / 'deployment/caller.json',
                            '--retained-review', state / 'review/review-001', '--accept-candidate-sha256',
                            args.candidate_sha256, '--output', output, '--accept-and-execute'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, check=False)
    report['bounded_continuation_exit'] = first.returncode
    finite = output / 'finite-run.stdout'
    report['first_run'] = json.loads(finite.read_bytes()) if finite.is_file() else None
    inspected = json.loads(as_cohort([ag, 'inspect', '--database', state / 'deployment/ag.sqlite']).stdout)
    variant = next(iter(inspected['current']['state']))
    value = inspected['current']['state'][variant]
    issuance = value.get('authorized', value).get('issuance') if isinstance(value, dict) else None
    if issuance is None:
        issuance = value.get('dispatch', {}).get('authorized', {}).get('issuance')
    report['after_spend'] = {'program_counter': variant, 'replay': inspected['replay'],
                             'issuance': issuance.get('issuance') if issuance else None,
                             'not_after_unix_ms': issuance.get('not_after_unix_ms') if issuance else None}
    if not issuance:
        report['error'] = 'no retained issuance after the bounded run'
        print(json.dumps(report, sort_keys=True))
        return 1
    first_input = output / 'run-input-v2.json'
    deadline = json.loads(first_input.read_bytes())['deadline_unix_ms']
    report['run_deadline_unix_ms'] = deadline
    wait = issuance['not_after_unix_ms'] - time.time_ns() // 1_000_000 + 1500
    report['waited_ms'] = max(0, wait)
    time.sleep(max(0, wait) / 1000)
    now = time.time_ns() // 1_000_000
    report['resumed_at_unix_ms'] = now
    report['resumed_after_not_after_before_deadline'] = issuance['not_after_unix_ms'] <= now < deadline
    second = as_cohort([ag, 'run', '--database', state / 'deployment/ag.sqlite', '--run-input', first_input])
    report['second_run'] = {'exit': second.returncode, 'stdout': second.stdout.decode(errors='replace')[-1500:],
                            'stderr': second.stderr.decode(errors='replace')[-1500:]}
    try:
        second_value = json.loads(second.stdout)
    except ValueError:
        second_value = {}
    # AG must refuse to present because of the issuance not-after, not for any
    # other reason (run identity, deadline, step bound).
    report['second_run_refused'] = (report['resumed_after_not_after_before_deadline']
                                    and second_value.get('status') == 'waiting'
                                    and second_value.get('reason') == 'issuance_not_current')
    docket_view = as_cohort([docket, 'governed-loop', 'inspect', '--state', state / 'ports/docket-state',
                             '--issuance', issuance['issuance']])
    report['docket_inspect'] = docket_view.stdout.decode(errors='replace')[-800:]
    try:
        record = json.loads(docket_view.stdout).get('record')
    except ValueError:
        record = None
    report['docket_records'] = 0 if record in (None, {}) else 1
    after = json.loads(as_cohort([ag, 'inspect', '--database', state / 'deployment/ag.sqlite']).stdout)
    report['after_refusal'] = {'program_counter': next(iter(after['current']['state'])), 'replay': after['replay']}
    report['result_present'] = (state / 'scratch/result.txt').exists()
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
