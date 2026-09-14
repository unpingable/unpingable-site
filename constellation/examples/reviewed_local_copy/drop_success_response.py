#!/usr/bin/env python3
"""Qualification-only Docket transport: lose response AFTER executor completion.

Enroll a fixed launcher supplying --executor, --sha256 and --records followed
by Docket's operation/config arguments. This changes the executor program pin
and requires a fresh enrollment. It does not manufacture a receipt, authority,
or a pre-success-record interruption. Never use it as the normal executor.
"""
import argparse
import os
from pathlib import Path
import sys

from reviewed_action import Caller, pinned, require


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executor', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('operation', choices=('plan-id', 'execute', 'reconcile'))
    parser.add_argument('config', type=Path)
    args = parser.parse_args(argv)
    executor = pinned({'path': args.executor, 'sha256': args.sha256}, 256 * 1024**2)
    require(args.records.is_absolute() and args.config.is_absolute(), 'absolute qualification paths required')
    require(args.records.is_dir() and not args.records.is_symlink(), 'existing exclusive qualification records directory required')
    command = [executor, args.operation, str(args.config)]
    if args.operation != 'execute':
        # Same qualified executor/plan/attempt; no new execute operation.
        os.execve(executor, command, {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
    dispatch = sys.stdin.buffer.read(16 * 1024**2 + 1)
    require(len(dispatch) <= 16 * 1024**2, 'dispatch exceeds qualification bound')
    # Exclusive native-execute.started prevents repeating even a lost invocation.
    collector = Caller({'programs': {}, 'inputs': {}, 'paths': {}}, args.records)
    collector.call('native-execute', command, dispatch, parsed=False)
    collector.write('response-withheld.json', {'qualification': 'COMPLETED_EXECUTOR_RESPONSE_LOSS',
        'native_exit_code': 0, 'stdout_forwarded_bytes': 0, 'repeat_execute_allowed': False,
        'next_action': 'Same-attempt native reconciliation; inspect native custody and retained receipt.'})
    # The real stdout is retained privately by the qualification collector, but
    # Docket receives no outcome bytes and must use its native reconciliation.
    return 74


if __name__ == '__main__': raise SystemExit(main())

