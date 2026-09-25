"""QUALIFICATION-ONLY guest helper for the A -> B upgrade-continuity harness.

Runs as root under /usr/bin/python3.11 -I -S. It imports the successor's
driver (the B kit) only to reuse its pure functions (signed-envelope
re-assembly, restored view); it never calls a driver command itself except
`upgrade` in the interrupt case, which it runs as a separate process.

    interrupt --driver KIT_DRIVER --journal DIR --step NAME -- ARGS...
        start `upgrade`, SIGKILL its process group the moment the journal
        step NAME.json appears, and report what the attempt left behind.
    present-issuance --kit-setup DIR --retained DIR -- DOCKET_ACCEPT_ARGV...
        re-assemble the retired cohort's retained signed issuance and feed it
        to `docket governed-loop accept` (argv given) as the cohort account.
    ag-view --kit-setup DIR --state DIR --cohort ID --ag BIN --database DB [--without FILE]
        run `ag-loopctl inspect` in a restored view of a copy of STATE,
        optionally with one file removed from the copy.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def load(kit_setup):
    sys.path.insert(0, kit_setup)
    import constellation_cohort as cc  # noqa: PLC0415
    return cc


def interrupt(args):
    command = ['/usr/bin/python3.11', '-I', '-S', args.driver, *args.rest]
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    journal = Path(args.journal)
    killed_at = None
    while process.poll() is None and time.monotonic() - started < 600:
        hits = sorted(journal.glob(f'attempt-*/{args.step}.json')) if journal.is_dir() else []
        if hits and args.glob:
            # Kill only once the step has visibly written part of its output.
            hits = [f'{hits[-1]} + {match}' for match in sorted(Path('/').glob(args.glob.lstrip('/')))][:1]
        if hits:
            os.killpg(process.pid, signal.SIGKILL)
            killed_at = str(hits[-1])
            break
        time.sleep(0.001)
    stdout, stderr = process.communicate()
    steps = {path.name: sorted(p.name for p in path.iterdir()) for path in sorted(journal.glob('attempt-*'))}
    print(json.dumps({'killed_after': killed_at, 'returncode': process.returncode, 'stdout': stdout.decode()[-2000:],
                      'stderr': stderr.decode()[-2000:], 'attempt_files': steps,
                      'elapsed_s': round(time.monotonic() - started, 3)}, sort_keys=True))


def present_issuance(args):
    cc = load(args.kit_setup)
    record = json.loads(Path(args.retained, 'native', 'docket-inspect.json').read_bytes())['record']
    envelope = cc.signed_issuance_envelope(record)
    argv = cc.as_user(cc.COHORT_ACCOUNT, args.rest)
    started = time.time_ns() // 1_000_000
    done = subprocess.run(argv, input=envelope, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env={'PATH': cc.SYSTEM_PATH, 'LANG': 'C.UTF-8'}, timeout=120, check=False)
    print(json.dumps({'issuance': record['issuance']['issuance'], 'not_after_unix_ms': record['issuance']['not_after_unix_ms'],
                      'presented_at_unix_ms': started, 'signer_key_id': record['authentication']['signer_key_id'],
                      'envelope_sha256': cc.digest_bytes(envelope), 'exit': done.returncode,
                      'stdout': done.stdout.decode()[-3000:], 'stderr': done.stderr.decode()[-3000:]}, sort_keys=True))


def ag_view(args):
    cc = load(args.kit_setup)
    with tempfile.TemporaryDirectory(dir='/var/lib/constellation', prefix='g3-view-') as tmp:
        root = Path(tmp)
        copy = root / 'state'
        subprocess.run(['/bin/cp', '-a', '--', args.state, str(copy)], check=True)  # keeps owners and modes
        removed = None
        if args.without:
            target = copy / args.without
            removed = target.is_file()
            target.unlink()
        account = cc.pwd.getpwnam(cc.COHORT_ACCOUNT)
        os.chown(root, account.pw_uid, account.pw_gid)
        database = root / 'db' / 'ag.sqlite'
        database.parent.mkdir()
        shutil.copyfile(args.database, database)
        for path in (database.parent, database):
            os.chown(path, account.pw_uid, account.pw_gid)
        stage = root / 'stage'
        stage.mkdir(mode=0o700)
        argv = cc.restored_view(copy, args.cohort, stage, cc.as_user(cc.COHORT_ACCOUNT, [args.ag, 'inspect', '--database',
                                                                                          str(database)]))
        done = subprocess.run([str(a) for a in argv], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env={'PATH': cc.SYSTEM_PATH, 'LANG': 'C.UTF-8'}, timeout=120, check=False)
        try:
            value = json.loads(done.stdout) if done.returncode == 0 else None
        except ValueError:
            value = None
        print(json.dumps({'without': args.without, 'removed': removed, 'exit': done.returncode,
                          'state_digest': (value or {}).get('current', {}).get('state_digest'),
                          'program_counter': next(iter((value or {}).get('current', {}).get('state', {'none': 0}))),
                          'stderr': done.stderr.decode()[-1500:]}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('interrupt')
    p.add_argument('--driver', required=True)
    p.add_argument('--journal', required=True)
    p.add_argument('--step', required=True)
    p.add_argument('--glob', help='also wait until this absolute glob matches')
    p.add_argument('rest', nargs=argparse.REMAINDER)
    p = sub.add_parser('present-issuance')
    p.add_argument('--kit-setup', required=True)
    p.add_argument('--retained', required=True)
    p.add_argument('rest', nargs=argparse.REMAINDER)
    p = sub.add_parser('ag-view')
    for name in ('--kit-setup', '--state', '--cohort', '--ag', '--database'):
        p.add_argument(name, required=True)
    p.add_argument('--without')
    args = parser.parse_args()
    if getattr(args, 'rest', None) and args.rest[0] == '--':
        args.rest = args.rest[1:]
    {'interrupt': interrupt, 'present-issuance': present_issuance, 'ag-view': ag_view}[args.command](args)


if __name__ == '__main__':
    main()
