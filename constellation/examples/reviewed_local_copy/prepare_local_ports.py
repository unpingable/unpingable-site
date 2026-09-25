#!/usr/bin/env python3
"""Prepare fresh native local standing/issuer ports, with no standing grant.

Generates new deployment-owned local issuer material; never reads or copies
provider credentials or another deployment's keys. Only native launcher writers
and OpenSSL are invoked. No AG proposal, Docket accept or executor is invoked.
"""
import argparse
import base64
import hashlib
import os
from pathlib import Path
import stat

from prepare_review_candidate import canonical
from reviewed_action import Caller, pinned, require


def identity(path):
    require(path.is_absolute(), 'absolute native program required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        meta = os.fstat(stream.fileno())
        require(stat.S_ISREG(meta.st_mode) and 0 < meta.st_size <= 256 * 1024**2, 'native program type/size refused')
        result = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'sha256': result}


def observation_launcher(program, expected, python, store):
    # Fixed purpose and argv. The captured program, not its mutable pathname,
    # is executed. Interpreter/stdlib are deployment-enrolled inputs; -IS keeps
    # the host's site-packages and .pth hooks out of the launcher.
    return f'''#!{python} -IS
import fcntl, hashlib, os, stat, sys
if len(sys.argv) != 1: raise SystemExit("observation launcher accepts no arguments")
fd = os.open({str(program)!r}, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
meta = os.fstat(fd)
if not stat.S_ISREG(meta.st_mode) or not 0 < meta.st_size <= 256*1024*1024: raise SystemExit("observation program type/size refused")
image = os.memfd_create("nightshift-observation", os.MFD_ALLOW_SEALING)
h = hashlib.sha256(); total = 0
while True:
    block = os.read(fd, 65536)
    if not block: break
    total += len(block)
    if total > 256*1024*1024: raise SystemExit("observation program exceeds bound")
    h.update(block); view = memoryview(block)
    while view:
        count = os.write(image, view)
        if count <= 0: raise SystemExit("incomplete observation capture")
        view = view[count:]
if "sha256:" + h.hexdigest() != {expected!r}: raise SystemExit("observation program identity differs")
os.close(fd); os.fchmod(image, 0o500)
fcntl.fcntl(image, fcntl.F_ADD_SEALS, fcntl.F_SEAL_WRITE|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SEAL)
os.set_inheritable(image, True)
executable = "/proc/self/fd/" + str(image)
os.execve(executable, [executable, "--store", {str(store)!r}, "--resolver-id", "nightshift-observation-resolver/v1", "--default-ttl-ms", "300000"], {{}})
'''.encode()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'ag-standing', 'ag-standing-sealer', 'docket', 'docket-resolver',
            'nightshift-observation', 'python', 'openssl', 'executor'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('operator', 'issuer', 'issuer-key-id', 'standing-resolver-id'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    selected = {name: getattr(args, name) for name in ('ag_standing', 'ag_standing_sealer', 'docket',
        'docket_resolver', 'nightshift_observation', 'python', 'openssl', 'executor')}
    pins = {name: identity(path) for name, path in selected.items()}
    for name, pin in pins.items():
        pinned(pin, 256 * 1024**2)
        require(Path(pin['path']).is_absolute(), 'absolute native program required')
    require(args.output.is_absolute(), 'absolute fresh output root required')
    args.output.mkdir(mode=0o700, exist_ok=False)
    root = args.output
    record = Caller({'programs': {}, 'inputs': {}, 'paths': {}}, root)
    record.write('ports-preparation-started.json', {'pins': pins, 'provider_contact': False,
        'standing_grants': 0, 'issuer': args.issuer, 'issuer_key_id': args.issuer_key_id})
    (root / 'docket-state').mkdir(mode=0o700)
    record.write('docket-standing-config.json', {'schema': 'docket.governed-loop.local-standing-resolver-config/v1',
        'state_database': str(root / 'docket-state/state.sqlite'), 'operator': args.operator})
    record.call('docket-standing-launcher', [args.docket, 'governed-loop', 'standing-write-launcher',
        '--resolver', args.docket_resolver, '--config', root / 'docket-standing-config.json',
        '--python-interpreter', args.python, '--output', root / 'docket-standing-launcher'], parsed=False)
    record.write('ag-standing-enrollment.json', {'schema': 'ag.governed-loop.standing-launcher-enrollment/v1',
        'resolver_program': str(args.ag_standing), 'resolver_sha256': pins['ag_standing']['sha256'],
        'mandate_store': str(root / 'ag-mandates.json'), 'resolver_id': args.standing_resolver_id,
        'answer_ttl_ms': 300000, 'python_interpreter': str(args.python), 'python_sha256': pins['python']['sha256']})
    # The sealer is qualified only under an isolated interpreter without site.
    record.call('ag-standing-launcher', [args.python, '-I', '-S', args.ag_standing_sealer, '--enrollment', root / 'ag-standing-enrollment.json',
        '--launcher', root / 'ag-standing-launcher', '--manifest', root / 'ag-standing-manifest.json'], parsed=False)
    record.write('observation-launcher', observation_launcher(args.nightshift_observation,
        pins['nightshift_observation']['sha256'], args.python, root / 'nightshift.sqlite'))
    (root / 'observation-launcher').chmod(0o500)
    # Fresh local issuer generation. No private bytes enter stdout/phase logs.
    record.call('issuer-generate', [args.openssl, 'genpkey', '-algorithm', 'Ed25519',
        '-outform', 'DER', '-out', root / 'issuer-seed.pk8'], parsed=False)
    (root / 'issuer-seed.pk8').chmod(0o600)
    public = record.call('issuer-public', [args.openssl, 'pkey', '-inform', 'DER', '-in', root / 'issuer-seed.pk8',
        '-pubout', '-outform', 'DER'], parsed=False)
    seed = (root / 'issuer-seed.pk8').read_bytes()
    private_prefix = bytes.fromhex('302e020100300506032b657004220420')
    public_prefix = bytes.fromhex('302a300506032b6570032100')
    require(len(seed) == 48 and seed.startswith(private_prefix) and len(public) == 44 and public.startswith(public_prefix),
        'native Ed25519 representation differs')
    public_key = public[12:]
    record.write('issuer.pk8', bytes.fromhex('3051020101300506032b657004220420') + seed[16:] + bytes.fromhex('812100') + public_key)
    (root / 'issuer.pk8').chmod(0o600)
    record.write('docket-trust.json', {'issuers': [{'issuer_principal': args.issuer, 'key_id': args.issuer_key_id,
        'public_key': base64.urlsafe_b64encode(public_key).rstrip(b'=').decode('ascii')}]})
    record.write('docket-root-enrollment.json', {'schema': 'ag.governed-loop.docket-root-enrollment/v1',
        'docket_program': str(args.docket), 'state_directory': str(root / 'docket-state'),
        'trust_config': str(root / 'docket-trust.json'), 'standing_resolver': str(root / 'docket-standing-launcher'),
        'executor_adapter': str(args.executor), 'issuer_principal': args.issuer,
        'issuer_key_id': args.issuer_key_id, 'issuer_key': str(root / 'issuer.pk8')})
    record.write('ports-preparation-finished.json', {'authority': False, 'standing_grants': 0,
        'ag_mandate_store_created': False, 'provider_contact': False, 'executor_invoked': False})


if __name__ == '__main__': main()

