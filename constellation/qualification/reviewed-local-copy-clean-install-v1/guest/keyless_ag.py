"""QUALIFICATION-ONLY guest helper: keyless AG reads over a settled cohort.

Runs as root under /usr/bin/python3.11 -I -S. It imports the extracted kit's
driver only for pure functions (the restored view, the service-account drop
and the AG read-only exit classification); it never calls a driver command.

    keyless_ag.py --kit-setup DIR --cohort ID --ag BIN

For each variant it copies the cohort's live state (`cp -a`, owners and modes
kept) into a private scratch directory, changes only the copy, and runs
`ag-loopctl inspect`, `replay`, `history` and `status` as the cohort account
over a private writable copy of the AG store. The altered state copy is
mounted read-only at the cohort's original state path in a private mount
namespace, so AG sees its enrolled locators and the live state is never
touched:

    with-key                  the copy unchanged (control)
    without-key               ports/issuer.pk8 removed
    garbage-key               ports/issuer.pk8 replaced by random bytes
    without-validator-config  plan/validator-config.json removed (enrolled
                              shared_admission.plan_validator_config)
    read-only-database        with-key, but the AG store copy is 0400 in a
                              0500 directory, both the cohort account's (the
                              owner limitation: AG opens its store
                              read-write even to read; observed, not gated)

Prints one JSON object with each variant's per-command exit, classified
outcome, named unavailable files, stdout digest and state digest.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile

COMMANDS = ('inspect', 'replay', 'history', 'status')
VARIANTS = ('with-key', 'without-key', 'garbage-key', 'without-validator-config', 'read-only-database')


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ('--kit-setup', '--cohort', '--ag'):
        parser.add_argument(name, required=True)
    args = parser.parse_args()
    sys.path.insert(0, args.kit_setup)
    import constellation_cohort as cc  # noqa: PLC0415
    live = cc.STATE_ROOT / args.cohort
    account = cc.pwd.getpwnam(cc.COHORT_ACCOUNT)
    report = {'cohort': args.cohort, 'ag': args.ag, 'ag_sha256': cc.sha256_file(Path(args.ag)),
              'live_key_present': (live / 'ports' / 'issuer.pk8').is_file(), 'variants': {}}
    for variant in VARIANTS:
        with tempfile.TemporaryDirectory(dir='/var/lib/constellation', prefix='keyless-') as tmp:
            root = Path(tmp)
            os.chown(root, account.pw_uid, account.pw_gid)
            copy = root / 'state'
            subprocess.run(['/bin/cp', '-a', '--', str(live), str(copy)], check=True)
            key = copy / 'ports' / 'issuer.pk8'
            if variant == 'without-key':
                key.unlink()
            elif variant == 'garbage-key':
                key.write_bytes(secrets.token_bytes(48))
            elif variant == 'without-validator-config':
                (copy / 'plan' / 'validator-config.json').unlink()
            database = root / 'db' / 'ag.sqlite'
            database.parent.mkdir()
            shutil.copyfile(live / 'deployment' / 'ag.sqlite', database)
            for path in (database.parent, database):
                os.chown(path, account.pw_uid, account.pw_gid)
            if variant == 'read-only-database':
                os.chmod(database, 0o400)
                os.chmod(database.parent, 0o500)
            stage = root / 'stage'
            stage.mkdir(mode=0o700)
            results = {}
            for command in COMMANDS:
                argv = cc.restored_view(copy, args.cohort, stage,
                                        cc.as_user(cc.COHORT_ACCOUNT, [args.ag, command, '--database', str(database)]))
                done = subprocess.run([str(a) for a in argv], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      env={'PATH': cc.SYSTEM_PATH, 'LANG': 'C.UTF-8'}, timeout=120, check=False)
                outcome = cc.ag_read_only_outcome(done.returncode, done.stdout, done.stderr)
                value = outcome['json'] if isinstance(outcome['json'], dict) else {}
                results[command] = {
                    'exit': done.returncode, 'outcome': outcome['status'], 'unavailable': outcome['unavailable'],
                    'stdout_sha256': 'sha256:' + hashlib.sha256(done.stdout).hexdigest(),
                    'state_digest': (value.get('current') or {}).get('state_digest') if command == 'inspect' else None,
                    'program_counter': next(iter((value.get('current') or {}).get('state') or {'none': 0}))
                    if command == 'inspect' else None,
                    'stderr_tail': done.stderr.decode(errors='replace')[-700:]}
            report['variants'][variant] = {'key_present_in_view': key.is_file(), 'commands': results}
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
