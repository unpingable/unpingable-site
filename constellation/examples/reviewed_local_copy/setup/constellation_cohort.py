#!/usr/bin/python3.11 -IS
"""Set up one fresh reviewed-local-copy/v1 cohort on one Debian 12 host.

This is the cohort setup driver: the smallest mechanism that turns verified
release artifacts into one working cohort. It is not an orchestrator, a
cluster manager, a configuration language or a control plane. It runs the
public caller glue in this kit and the components' own commands, in a fixed
order, with fixed paths, and stops at the first refusal.

Newcomer steps:

  1. verify-manifest  check the cohort manifest and artifacts; writes nothing
  2. install          (root) verify again, install artifacts, check build info
  3. init             (root) account, synthetic identities and keys, codex
                      home, plan, ports, NQ store and watcher admission; no
                      observation, provider or effect
  4. review           (root) one durable unit: fresh NQ observation, Pulse
                      support, AG genesis, admission and one bounded review;
                      stops before acceptance
  5. status           read-only native inspection; prints the candidate digest
  6. accept           (root) the operator names the exact candidate digest;
                      one durable unit records the review and executes once
  7. evidence         read-only bundle of records, store backups and joins

Every run writes create-once started/finished records. A refusal has a stable
code and never leaves a half-written file presented as complete. Nothing is
retried, and nothing is overwritten: a second run of a step against the same
cohort refuses. Use a new cohort id or a new disposable host.

Run it as `python3.11 -I -S constellation_cohort.py ...` (Debian 12). Python
3.11 standard library only. No network.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import secrets
import shutil
import socket
import sqlite3
import stat
import subprocess
import sys
import tarfile
import time
import uuid

DRIVER_VERSION = '0.2.0'
MANIFEST_SCHEMA = 'constellation.cohort-manifest/v1'
PROFILE = 'reviewed-local-copy/v1'
RECORD_SCHEMA = 'constellation.cohort-driver-record/v1'

INSTALL_ROOT = Path('/opt/constellation/cohorts')
STATE_ROOT = Path('/var/lib/constellation/cohorts')
COHORT_ACCOUNT = 'constellation'
NQ_ACCOUNT = 'nq'
PYTHON = Path('/usr/bin/python3.11')
OPENSSL = Path('/usr/bin/openssl')
NQ = Path('/usr/bin/nq')
NQ_CONFIG_DIR = Path('/etc/nq')
NQ_STATE_DIR = Path('/var/lib/nq')
NQ_RUN_DIR = Path('/run/nq')
SYSTEM_PATH = '/usr/sbin:/usr/bin:/sbin:/bin'
WORK_ITEM = 'shared-source-review'
MODEL = 'gpt-5.6-terra'
PROVIDER = 'openai'

COMMIT = re.compile(r'[0-9a-f]{40}\Z')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}\Z')
VERSION = re.compile(r'[0-9A-Za-z][0-9A-Za-z.+~_-]{0,63}\Z')
COHORT_ID = re.compile(r'[a-z0-9][a-z0-9-]{2,39}\Z')
SELF = 'SELF'

# Components the profile requires, what each artifact must be, and the
# executables whose identity must report the manifest's version and commit.
# Member paths are relative to the extracted artifact root. Runners: `elf`
# and `script` are run with --build-info; `pyz` under python3.11 -I -S;
# `receipt` is bound by the artifact's build-info.json (the codex fork cannot
# report its commit); `kit` is this driver's own release (see check_kit).
COMPONENTS = {
    'nq': {'kind': 'deb', 'executables': {
        '/usr/bin/nq': 'elf', '/usr/lib/nq/helpers/nq-host-helper': 'elf'}},
    'maude': {'kind': 'tar', 'executables': {
        'lib/validator.pyz': 'pyz', 'lib/executor.pyz': 'pyz', 'lib/maude-plan.pyz': 'pyz'}},
    'pulse': {'kind': 'tar', 'executables': {'bin/pulse-nq-load-support': 'elf'}},
    'nightshift': {'kind': 'tar', 'executables': {
        'bin/nightshift': 'elf', 'bin/nightshift-foreman': 'elf', 'bin/nightshift-observation-resolver': 'elf'}},
    'ag': {'kind': 'tar', 'executables': {
        'bin/ag-loopctl': 'elf', 'bin/ag-standing-resolver': 'elf', 'bin/ag-operator-ui': 'elf'}},
    'docket': {'kind': 'tar', 'executables': {
        'bin/docket': 'elf', 'bin/docket-local-standing-resolver': 'elf'}},
    'switchyard': {'kind': 'tar', 'executables': {
        'bin/switchyard-provider-runner': 'script', 'bin/switchyard-review-verifier': 'script'}},
    'app-server': {'kind': 'tar', 'executables': {'bin/codex-app-server': 'receipt'}},
    'cohort-kit': {'kind': 'tar', 'executables': {'setup/constellation_cohort.py': 'kit'}},
}

# The only cohorts this driver release will set up. Each entry binds every
# required component to the exact package version, source commit and artifact
# digest that were qualified together. Compatibility is equality with one
# entry: no ranges, no "newer is fine", no partial match, no other artifact.
# The cohort kit cannot name its own commit (the commit contains this table),
# so its entry is SELF: the manifest's kit commit must equal the kit's
# BUILD-INFO.json and the kit's driver bytes must equal this running driver.
QUALIFIED_COHORTS = {
    PROFILE: {
        'alpha-exit-rc': {
            'nq': {'package_version': '0.2.0', 'source_commit': 'dbe29d81ba84061b08fec285f1218ec2145c65bc',
                   'artifact_sha256': 'sha256:9e953e88d1f79cffd03e97b530199459b5e45ead55ea4ba7d5066e0851008d7b'},
            'maude': {'package_version': '0.1.0', 'source_commit': '75d4dc1df1934cfc797c48c528d314804938eaae',
                      'artifact_sha256': 'sha256:f88b5823f6a7bc6ff1c9645daff6312eec5234559bb735d25db589e1904f7357'},
            'pulse': {'package_version': '0.1.0', 'source_commit': '30c89fe17723a7b9d77b19fd650aadb0a784748d',
                      'artifact_sha256': 'sha256:51e85b97f44504240044f3b666d6fb3602270939102676e65798f4cecd405c61'},
            'nightshift': {'package_version': '0.1.0', 'source_commit': '30c89fe17723a7b9d77b19fd650aadb0a784748d',
                           'artifact_sha256': 'sha256:cffbea38c4718c480fd9c0b5c41c28331d52132205a3e16f2fda2e572467a254'},
            'ag': {'package_version': '0.1.0', 'source_commit': 'e20c23a35f836d9f3913b62fbd3cb2621a866321',
                   'artifact_sha256': 'sha256:b03b8f06363ca73464c14b2131be8ac7b7bf8c38c9521fd594882d1cd15fac19'},
            'docket': {'package_version': '0.1.0', 'source_commit': '3093def030a5151d2e7b956eafb73d0c16f8c735',
                       'artifact_sha256': 'sha256:6596315fcdb92fd881d6c0f2159eb912ee9c96b99a58fdc5ddea5e11a192c81b'},
            'switchyard': {'package_version': '0.2.0', 'source_commit': '1c82e719cf358728d0262ae11138fb13fefe0cae',
                           'artifact_sha256': 'sha256:be418f76e9f5f8239d457137b19ff771d562d89a85ccda5b4ccfdc0049f665c1'},
            'app-server': {'package_version': '0.0.0', 'source_commit': '97b0acd5ce2ccb3c87a763606696c35a450947f6',
                           'artifact_sha256': 'sha256:9999bd8e75607071e1e43d9829fea253593f95323dff3a6e690b9d52433e2cd9'},
            'cohort-kit': {'package_version': DRIVER_VERSION, 'source_commit': SELF, 'artifact_sha256': SELF},
        },
    },
}

# Values the installed artifacts must report beyond version and commit.
SWITCHYARD_OWNER_HEAD = '299609cda100ccf8701d5619ac78499f8bddd303'

REVIEW_ROUTES = {
    # Real provider: operator-supplied credential placed by the operator.
    'real': {'reviewer_id_suffix': 'independent-reviewer', 'codex_home': 'codex-home-real'},
    # Labelled fixture: qualifies install, wiring, custody, authority and
    # effect; never review independence.
    'fixture-review': {'reviewer_id': 'fixture-deterministic-reviewer-not-independent',
                       'codex_home': 'codex-home-fixture-review'},
}

# NQ's documented capability-bearing unit for commands that execute a
# watcher (NQ docs/OPERATIONS.md, nq_helper_command), kept verbatim.
NQ_HELPER_UNIT = (
    'User=nq', 'Group=nq', 'UMask=0077', 'NoNewPrivileges=yes', 'PrivateTmp=yes',
    'TemporaryFileSystem=/tmp:rw,nosuid,nodev,noexec,mode=1777,size=64M /var/tmp:rw,nosuid,nodev,noexec,mode=1777,size=64M',
    'ProtectSystem=strict', 'ProtectHome=yes', 'ProtectClock=yes', 'ProtectControlGroups=yes', 'ProtectKernelLogs=yes',
    'ProtectKernelModules=yes', 'ProtectKernelTunables=yes', 'ProtectHostname=yes', 'RestrictNamespaces=yes',
    'RestrictRealtime=yes', 'RestrictSUIDSGID=yes', 'LockPersonality=yes', 'RemoveIPC=yes', 'KeyringMode=private',
    'SystemCallArchitectures=native', 'RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6', 'ReadOnlyPaths=/etc/nq',
    'ReadWritePaths=/var/lib/nq /run/nq', 'CapabilityBoundingSet=CAP_SETUID CAP_SETGID CAP_CHOWN CAP_KILL',
    'AmbientCapabilities=CAP_SETUID CAP_SETGID CAP_CHOWN CAP_KILL', 'LimitNOFILE=4096', 'LimitFSIZE=1G', 'LimitCORE=0',
    'TasksMax=256', 'MemoryMax=2G', 'MemorySwapMax=0', 'CPUQuota=200%')

# The durable unit for the review and accept transitions (one invocation,
# 600 s, no restart, bounded tasks and memory, explicit environment).
TRANSITION_UNIT = ('RuntimeMaxSec=600', 'Restart=no', 'TasksMax=1024', 'MemoryMax=6G', 'UMask=0077',
                   'PrivateTmp=yes', 'KillMode=control-group')


class Refusal(Exception):
    """A fail-closed stop with a stable code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f'{code}: {detail}')
        self.code = code
        self.detail = detail


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest_bytes(raw: bytes) -> str:
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def parse_rfc3339_ms(value: str) -> int:
    return int(dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp() * 1000)


def sha256_file(path: Path) -> str:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Refusal('artifact.not_regular', str(path))
        return 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()


def read_bytes(path: Path, limit: int = 16 * 1024 * 1024) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Refusal('artifact.not_regular', str(path))
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise Refusal('artifact.size', str(path))
    return raw


def read_json(path: Path):
    return json.loads(read_bytes(path))


def write_new(path: Path, raw: bytes, mode: int = 0o600, owner: str | None = None) -> Path:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    with os.fdopen(fd, 'wb') as out:
        out.write(raw)
        out.flush()
        os.fchmod(out.fileno(), mode)
        if owner is not None:
            account = pwd.getpwnam(owner)
            os.fchown(out.fileno(), account.pw_uid, account.pw_gid)
        os.fsync(out.fileno())
    return path


def make_dir(path: Path, mode: int, owner: str | None = None) -> Path:
    path.mkdir(mode=mode, exist_ok=False)
    os.chmod(path, mode)
    if owner is not None:
        account = pwd.getpwnam(owner)
        os.chown(path, account.pw_uid, account.pw_gid)
    return path


# ------------------------------------------------------------------ manifest

def load_manifest(raw: bytes) -> dict:
    """Parse and validate a cohort manifest. Refuses anything not exactly v1."""
    try:
        manifest = json.loads(raw, object_pairs_hook=_no_duplicates)
    except (ValueError, UnicodeDecodeError) as error:
        raise Refusal('manifest.not_json', str(error)) from None
    if not isinstance(manifest, dict) or set(manifest) != {'schema', 'profile', 'components'}:
        raise Refusal('manifest.shape', 'exactly schema, profile and components are required')
    if manifest['schema'] != MANIFEST_SCHEMA:
        raise Refusal('manifest.schema', repr(manifest['schema']))
    if manifest['profile'] != PROFILE:
        raise Refusal('manifest.profile', f'this driver sets up only {PROFILE}, not {manifest["profile"]!r}')
    entries = manifest['components']
    if not isinstance(entries, list):
        raise Refusal('manifest.shape', 'components must be a list')
    seen = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
                'component', 'package_version', 'source_commit', 'artifact_sha256'}:
            raise Refusal('manifest.component_shape',
                          'each component has exactly component, package_version, source_commit, artifact_sha256')
        name = entry['component']
        if name not in COMPONENTS:
            raise Refusal('manifest.unknown_component', repr(name))
        if name in seen:
            raise Refusal('manifest.duplicate_component', name)
        if not isinstance(entry['package_version'], str) or not VERSION.fullmatch(entry['package_version']):
            raise Refusal('manifest.version', f'{name}: {entry["package_version"]!r}')
        if not isinstance(entry['source_commit'], str) or not COMMIT.fullmatch(entry['source_commit']):
            raise Refusal('manifest.commit', f'{name}: full 40-hex lowercase commit required')
        if not isinstance(entry['artifact_sha256'], str) or not DIGEST.fullmatch(entry['artifact_sha256']):
            raise Refusal('manifest.digest', f'{name}: sha256:<64 hex> required')
        seen[name] = entry
    missing = sorted(set(COMPONENTS) - set(seen))
    if missing:
        raise Refusal('manifest.missing_component', ', '.join(missing))
    digests = [entry['artifact_sha256'] for entry in entries]
    if len(set(digests)) != len(digests):
        raise Refusal('manifest.shared_artifact', 'each component names its own artifact')
    return {'schema': MANIFEST_SCHEMA, 'profile': PROFILE, 'components': seen,
            'manifest_sha256': digest_bytes(raw)}


def _no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError('duplicate JSON key')
    return dict(pairs)


PIN_FIELDS = ('package_version', 'source_commit', 'artifact_sha256')


def check_cohort_pins(manifest: dict, qualified: dict | None = None) -> str:
    """Return the name of the qualified cohort the manifest matches, or refuse.

    Compatibility is exact equality with one qualified cohort, component by
    component, in version, commit and artifact digest. A SELF pin (the kit)
    is checked against the kit artifact itself by check_kit().
    """
    table = (QUALIFIED_COHORTS if qualified is None else qualified).get(manifest['profile'], {})
    mismatches = {}
    for name, pins in sorted(table.items()):
        if set(pins) != set(manifest['components']):
            mismatches[name] = 'component set differs'
            continue
        differ = []
        for component, pin in sorted(pins.items()):
            entry = manifest['components'][component]
            for field in PIN_FIELDS:
                expected = pin.get(field)
                if expected is None or (expected != SELF and entry[field] != expected):
                    differ.append(f'{component}.{field}')
        if not differ:
            return name
        mismatches[name] = 'differs in ' + ', '.join(differ)
    raise Refusal('pin.incompatible', json.dumps(mismatches, sort_keys=True) if mismatches else 'no qualified cohort for profile')


def locate_artifacts(manifest: dict, directory: Path) -> dict:
    """Map each component to the single regular file in `directory` with its digest."""
    if not directory.is_dir():
        raise Refusal('artifact.directory', str(directory))
    by_digest = {}
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file():
            continue
        by_digest.setdefault(sha256_file(path), []).append(path)
    located = {}
    for name, entry in sorted(manifest['components'].items()):
        paths = by_digest.get(entry['artifact_sha256'], [])
        if not paths:
            raise Refusal('artifact.missing', f'{name}: no file with {entry["artifact_sha256"]}')
        if len(paths) > 1:
            raise Refusal('artifact.ambiguous', f'{name}: {", ".join(p.name for p in paths)}')
        kind = COMPONENTS[name]['kind']
        suffix_ok = paths[0].name.endswith('.deb') if kind == 'deb' else paths[0].name.endswith(('.tar.gz', '.tgz'))
        if not suffix_ok:
            raise Refusal('artifact.kind', f'{name}: expected a {kind} artifact, got {paths[0].name}')
        located[name] = paths[0]
    return located


def tar_members(archive: Path) -> list:
    """Check every member: regular files and directories only, no escapes."""
    members = []
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar.getmembers():
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or not name.parts:
                raise Refusal('artifact.unsafe_member', f'{archive.name}: {member.name}')
            if not (member.isfile() or member.isdir()):
                raise Refusal('artifact.unsafe_member', f'{archive.name}: {member.name} is not a file or directory')
            if member.mode & (stat.S_ISUID | stat.S_ISGID | stat.S_IWOTH | stat.S_IWGRP):
                raise Refusal('artifact.unsafe_mode', f'{archive.name}: {member.name} {oct(member.mode)}')
            members.append(member)
    return members


def safe_extract(archive: Path, destination: Path) -> list[str]:
    """Extract a release tarball. Python 3.11.2 has no tarfile data filter."""
    members = tar_members(archive)
    try:
        make_dir(destination, 0o755)
    except FileExistsError:
        raise Refusal('artifact.destination_exists', str(destination)) from None
    with tarfile.open(archive, 'r:gz') as tar:
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(mode=0o755, parents=True, exist_ok=True)
                os.chmod(target, 0o755)
                continue
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            source = tar.extractfile(member)
            mode = 0o755 if member.mode & 0o111 else 0o644
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
            with os.fdopen(fd, 'wb') as out:
                shutil.copyfileobj(source, out)
                out.flush()
                os.fchmod(out.fileno(), mode)
                os.fsync(out.fileno())
    return sorted(member.name for member in members if member.isfile())


def artifact_root(extracted: Path) -> Path:
    """A release tarball holds exactly one top-level directory."""
    entries = list(extracted.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        raise Refusal('artifact.layout', f'{extracted}: exactly one top-level directory required')
    return entries[0]


def parse_build_info(stdout: bytes) -> dict:
    """Build info is one newline-terminated JSON object (NQ nq.build_info.v2 style)."""
    if not stdout.endswith(b'\n') or b'\n' in stdout[:-1]:
        raise Refusal('build_info.format', 'one newline-terminated JSON line required')
    try:
        value = json.loads(stdout)
    except ValueError as error:
        raise Refusal('build_info.format', str(error)) from None
    if not isinstance(value, dict):
        raise Refusal('build_info.format', 'JSON object required')
    return value


def check_build_info(component: str, program: str, info: dict, pin: dict) -> dict:
    """Refuse unless the executable reports the manifest's version and commit."""
    observed = {key: info.get(key) for key in ('component', 'version', 'source_commit')}
    if not isinstance(observed['component'], str) or not observed['component']:
        raise Refusal('build_info.component', f'{component} {program}: component absent')
    if observed['version'] != pin['package_version']:
        raise Refusal('build_info.version', f'{component} {program}: {observed["version"]!r} != {pin["package_version"]!r}')
    if observed['source_commit'] != pin['source_commit']:
        raise Refusal('build_info.commit', f'{component} {program}: {observed["source_commit"]!r} != {pin["source_commit"]!r}')
    if info.get('debug_assertions') is True or info.get('profile') in ('debug', 'dev') \
            or info.get('cargo_profile') in ('debug', 'dev'):
        raise Refusal('build_info.debug_build', f'{component} {program}: release builds only')
    return observed


def check_receipt_identity(component: str, root: Path, relative: str, pin: dict) -> dict:
    """Identity for an executable that cannot report build info itself.

    `<root>/build-info.json` is one JSON object with component, version,
    source_commit, a release profile and `executable_sha256` of the ELF.
    """
    try:
        info = json.loads(read_bytes(root / 'build-info.json', 1024 * 1024))
    except ValueError as error:
        raise Refusal('build_info.format', f'{component}: {error}') from None
    if not isinstance(info, dict):
        raise Refusal('build_info.format', f'{component}: JSON object required')
    observed = check_build_info(component, relative, info, pin)
    if info.get('executable_sha256') != sha256_file(root / relative):
        raise Refusal('build_info.executable_digest', f'{component} {relative}: digest not bound by build-info.json')
    return observed


def check_kit(root: Path, pin: dict) -> dict:
    """The cohort kit is this driver's own release (SELF pin)."""
    info = read_json(root / 'BUILD-INFO.json')
    observed = check_build_info('cohort-kit', 'BUILD-INFO.json', info, pin)
    files = info.get('files')
    if not isinstance(files, dict) or not files:
        raise Refusal('build_info.format', 'cohort-kit BUILD-INFO.json lacks files')
    for relative, expected in sorted(files.items()):
        if sha256_file(root / relative) != expected:
            raise Refusal('build_info.executable_digest', f'cohort-kit {relative}')
    running = sha256_file(Path(__file__).resolve())
    if files.get('setup/constellation_cohort.py') != running:
        raise Refusal('build_info.executable_digest', 'the installed kit driver differs from the running driver')
    return observed


# ------------------------------------------------------------------- records

class Records:
    """Create-once JSON records for one driver invocation."""

    def __init__(self, root: Path, command: str) -> None:
        self.root = root
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.run = root / f'{stamp}-{command}'
        self.run.mkdir(mode=0o700, exist_ok=False)
        self.sequence = 0
        self.timings = []

    def write(self, name: str, value) -> Path:
        raw = value if isinstance(value, bytes) else canonical(value) + b'\n'
        return write_new(self.run / name, raw)

    def mark(self, label: str) -> None:
        self.timings.append({'label': label, 'at': utc_now(), 'at_unix_ms': now_ms(),
                             'monotonic_ns': time.monotonic_ns()})

    def call(self, label: str, argv: list, *, env: dict | None = None, timeout: int = 120,
             stdin: bytes | None = None, check: bool = True, user: str | None = None) -> subprocess.CompletedProcess:
        """Run one child with an explicit environment; retain argv, output and exit."""
        self.sequence += 1
        name = f'{self.sequence:03d}-{label}'
        argv = [str(item) for item in argv]
        if user is not None:
            argv = as_user(user, argv)
        environment = {'PATH': SYSTEM_PATH, 'LANG': 'C.UTF-8'} if env is None else env
        started = time.monotonic_ns()
        self.write(name + '.started.json', {'schema': RECORD_SCHEMA, 'argv': argv, 'env_keys': sorted(environment),
                                            'at': utc_now(), 'timeout_seconds': timeout, 'retries': 0})
        try:
            done = subprocess.run(argv, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env=environment, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as error:
            self.write(name + '.finished.json', {'exit': None, 'timeout': True, 'at': utc_now()})
            raise Refusal('child.timeout', f'{label} after {timeout}s') from error
        except OSError as error:
            self.write(name + '.finished.json', {'exit': None, 'os_error': str(error), 'at': utc_now()})
            raise Refusal('child.exec', f'{label}: {error}') from error
        self.write(name + '.stdout', done.stdout)
        self.write(name + '.stderr', done.stderr)
        self.write(name + '.finished.json', {'exit': done.returncode, 'at': utc_now(),
                                             'elapsed_ms': (time.monotonic_ns() - started) // 1_000_000,
                                             'stdout_sha256': digest_bytes(done.stdout)})
        if check and done.returncode != 0:
            tail = done.stderr.decode(errors='replace').strip().splitlines()[-1:] or ['']
            raise Refusal('child.failed', f'{label} exited {done.returncode}: {tail[0][:400]}; '
                                          f'see {self.run / (name + ".stderr")}')
        return done

    def json_call(self, label: str, argv: list, **kwargs):
        done = self.call(label, argv, **kwargs)
        try:
            return json.loads(done.stdout)
        except ValueError:
            raise Refusal('child.output', f'{label} did not print one JSON document') from None


def as_user(user: str, argv: list[str]) -> list[str]:
    """Drop from root to a service account for one child (no new privileges)."""
    return ['/usr/bin/setpriv', f'--reuid={user}', f'--regid={user}', '--init-groups', '--no-new-privs',
            '--inh-caps=-all', '--', *argv]


def nq_unit(argv: list[str]) -> list[str]:
    """NQ's documented capability-bearing transient unit (nq_helper_command)."""
    command = ['/usr/bin/systemd-run', '--quiet', '--wait', '--pipe', '--collect']
    command += [f'--property={item}' for item in NQ_HELPER_UNIT]
    return command + ['--', str(NQ), *argv]


def kit_module(paths: list[Path], module: str, args: list) -> list[str]:
    """Run one kit module's main() under python3.11 -I -S with an explicit path.

    -I implies -P on 3.11, so a script's own directory is not importable; the
    kit's helpers import each other, so their directories go first explicitly.
    """
    code = (f'import sys; sys.path[:0]={[str(p) for p in paths]!r}; import {module}; '
            f'{module}.main(sys.argv[1:])')
    return [str(PYTHON), '-I', '-S', '-c', code, *[str(a) for a in args]]


def host_facts() -> dict:
    facts = {'hostname': socket.gethostname(), 'python': sys.version.split()[0],
             'python_executable': sys.executable, 'euid': os.geteuid()}
    try:
        release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
        facts['os'] = f'{release.get("ID", "").strip(chr(34))}:{release.get("VERSION_ID", "").strip(chr(34))}'
    except OSError:
        facts['os'] = None
    for label, path in (('python311', PYTHON), ('openssl', OPENSSL)):
        facts[label + '_sha256'] = sha256_file(path) if path.exists() and not path.is_symlink() else None
    return facts


def require_host(facts: dict) -> None:
    if facts['os'] != 'debian:12':
        raise Refusal('host.unsupported', f'Debian 12 required, found {facts["os"]}')
    if facts['python311_sha256'] is None or facts['openssl_sha256'] is None:
        raise Refusal('host.missing_tool', 'python3.11 and openssl are required')
    if facts['euid'] != 0:
        raise Refusal('host.not_root', 'install, init, review and accept run as root')
    for tool in ('systemd-run', 'setpriv', 'dpkg', 'useradd'):
        if shutil.which(tool, path=SYSTEM_PATH) is None:
            raise Refusal('host.missing_tool', tool)


def require_free(path: Path, minimum_bytes: int) -> None:
    fs = os.statvfs(path)
    if fs.f_bavail * fs.f_frsize < minimum_bytes or fs.f_favail < 10000:
        raise Refusal('host.storage', f'{path} has less than {minimum_bytes // 1024**2} MiB or 10000 inodes free')


# ------------------------------------------------------------------ paths

def cohort_paths(cohort: str) -> dict:
    if not COHORT_ID.fullmatch(cohort):
        raise Refusal('cohort.id', 'lowercase letters, digits and hyphens, 3-40 characters')
    install = INSTALL_ROOT / cohort
    state = STATE_ROOT / cohort
    return {
        'install': install, 'state': state, 'records': state / 'driver',
        'inputs': state / 'inputs', 'plan_input': state / 'plan-input', 'plan': state / 'plan',
        'scratch': state / 'scratch', 'ports': state / 'ports', 'owner': state / 'owner',
        'deployment': state / 'deployment', 'observation': state / 'observation',
        'review': state / 'review', 'workspace': state / 'review' / 'workspace',
        'review_output': state / 'review' / 'review-001', 'runs': state / 'runs',
        'continuation': state / 'runs' / 'continuation-001',
        'nq_config': NQ_CONFIG_DIR / f'cohort-{cohort}.toml', 'nq_state': NQ_STATE_DIR / f'cohort-{cohort}',
    }


def installed(cohort: str) -> dict:
    """Installed program locations, from the create-once install record."""
    paths = cohort_paths(cohort)
    record = paths['install'] / 'installed.json'
    if not record.is_file():
        raise Refusal('cohort.not_installed', cohort)
    return read_json(record)


def read_manifest(path: Path) -> dict:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise Refusal('manifest.size', 'manifest exceeds 1 MiB')
    return load_manifest(raw)


# ------------------------------------------------------------------ install

def cmd_verify_manifest(args) -> dict:
    manifest = read_manifest(args.manifest)
    cohort = check_cohort_pins(manifest)
    located = locate_artifacts(manifest, args.artifacts)
    for name, path in located.items():
        if COMPONENTS[name]['kind'] == 'tar':
            tar_members(path)
    return {'result': 'verified', 'qualified_cohort': cohort, 'manifest_sha256': manifest['manifest_sha256'],
            'artifacts': {name: path.name for name, path in located.items()}, 'writes': 0}


def install_nq(records: Records, artifact: Path) -> None:
    """Install the NQ package, or accept the identical already-installed one."""
    status = subprocess.run(['dpkg-query', '-W', '-f=${Status} ${Version}', 'nq-ng'], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, env={'PATH': SYSTEM_PATH}, check=False)
    if status.returncode == 0 and status.stdout.startswith(b'install ok installed'):
        records.write('nq-package-already-installed.json', {'dpkg_status': status.stdout.decode()})
        records.call('dpkg-verify-nq', ['dpkg', '--verify', 'nq-ng'], timeout=120)
        return
    records.call('dpkg-install-nq', ['dpkg', '--install', artifact], timeout=300)


def cmd_install(args) -> dict:
    facts = host_facts()
    require_host(facts)
    manifest = read_manifest(args.manifest)
    qualified = check_cohort_pins(manifest)
    located = locate_artifacts(manifest, args.artifacts)
    for name, path in located.items():
        if COMPONENTS[name]['kind'] == 'tar':
            tar_members(path)
    paths = cohort_paths(args.cohort)
    if paths['install'].exists() or paths['state'].exists() or paths['nq_config'].exists():
        raise Refusal('cohort.exists', f'{args.cohort} already has install or state; use a fresh cohort id')
    require_free(Path('/opt'), 2 * 1024**3)
    INSTALL_ROOT.mkdir(mode=0o755, parents=True, exist_ok=True)
    for directory in (Path('/opt/constellation'), INSTALL_ROOT):
        os.chmod(directory, 0o755)
    make_dir(paths['install'], 0o755)
    records = Records(paths['install'] / 'install-records', 'install')
    records.write('host.json', facts)
    records.write('manifest.json', manifest)
    identities, roots = {}, {}
    for name, artifact in sorted(located.items()):
        pin = manifest['components'][name]
        if COMPONENTS[name]['kind'] == 'deb':
            install_nq(records, artifact)
            root = Path('/')
        else:
            members = safe_extract(artifact, paths['install'] / name)
            records.write(f'members-{name}.json', members)
            root = artifact_root(paths['install'] / name)
        roots[name] = str(root)
        for relative, runner in sorted(COMPONENTS[name]['executables'].items()):
            program = root / relative.lstrip('/')
            if runner == 'receipt':
                observed = check_receipt_identity(name, root, relative, pin)
            elif runner == 'kit':
                observed = check_kit(root, pin)
            else:
                argv = {'elf': [program], 'script': [program], 'pyz': [PYTHON, '-I', '-S', program]}[runner]
                done = records.call(f'build-info-{name}-{program.name}', argv + ['--build-info'], timeout=30)
                info = parse_build_info(done.stdout)
                observed = check_build_info(name, str(program), info, pin)
                if name == 'switchyard':
                    if info.get('installed_closure_matches_provenance') is not True:
                        raise Refusal('build_info.executable_digest', f'{program}: installed closure differs from provenance')
                    if info.get('canonical_switchyard_revision') != SWITCHYARD_OWNER_HEAD:
                        raise Refusal('build_info.commit', f'{program}: canonical Switchyard revision differs')
            identities[str(program)] = {'component': name, 'sha256': sha256_file(program), **observed}
    records.write('installed-identities.json', identities)
    record = {'schema': 'constellation.cohort-install/v1', 'cohort': args.cohort, 'qualified_cohort': qualified,
              'manifest_sha256': manifest['manifest_sha256'], 'roots': roots, 'identities': identities,
              'records': str(records.run)}
    write_new(paths['install'] / 'installed.json', canonical(record) + b'\n', 0o644)
    return {'result': 'installed', 'cohort': args.cohort, 'qualified_cohort': qualified,
            'install_root': str(paths['install']), 'executables': len(identities), 'records': str(records.run)}


class Programs:
    """Absolute program and file locations of one installed cohort."""

    def __init__(self, cohort: str) -> None:
        record = installed(cohort)
        roots = {name: Path(path) for name, path in record['roots'].items()}
        self.identities = record['identities']
        self.maude = roots['maude']
        self.kit = roots['cohort-kit']
        self.setup = self.kit / 'setup'
        self.validator = self.maude / 'lib/validator.pyz'
        self.executor = self.maude / 'lib/executor.pyz'
        self.plan_library = self.maude / 'lib/maude-plan.pyz'
        self.cache_helper = self.maude / 'share/helpers/cache-host-bootstrap.py'
        self.pulse_prepare = self.maude / 'share/helpers/prepare_pulse_support.py'
        self.pulse = roots['pulse'] / 'bin/pulse-nq-load-support'
        self.pulse_sealer = roots['pulse'] / 'share/pulse-nq-load-support/seal-pulse-support-resolver-launcher.py'
        self.nightshift = roots['nightshift'] / 'bin/nightshift'
        self.foreman = roots['nightshift'] / 'bin/nightshift-foreman'
        self.observation = roots['nightshift'] / 'bin/nightshift-observation-resolver'
        self.ag = roots['ag'] / 'bin/ag-loopctl'
        self.ag_standing = roots['ag'] / 'bin/ag-standing-resolver'
        self.ag_sealer = roots['ag'] / 'share/seal-standing-resolver-launcher.py'
        self.docket = roots['docket'] / 'bin/docket'
        self.docket_resolver = roots['docket'] / 'bin/docket-local-standing-resolver'
        self.runner = roots['switchyard'] / 'bin/switchyard-provider-runner'
        self.verifier = roots['switchyard'] / 'bin/switchyard-review-verifier'
        self.provenance = roots['switchyard'] / 'share/switchyard/SOURCE-PROVENANCE.json'
        self.app_server = roots['app-server'] / 'bin/codex-app-server'
        self.app_server_info = roots['app-server'] / 'build-info.json'
        self.maude_commit = record['identities'][str(self.validator)]['source_commit']

    def sha(self, path: Path) -> str:
        entry = self.identities.get(str(path))
        actual = sha256_file(path)
        if entry is not None and entry['sha256'] != actual:
            raise Refusal('artifact.changed', f'{path} differs from its install record')
        return actual

    def kit_call(self, module: str, args: list, extra: list[Path] = ()) -> list[str]:
        return kit_module([*extra, self.setup, self.kit], module, args)


# ------------------------------------------------------------------ init

def synthetic_identities(cohort: str, route: str) -> dict:
    """Free-form identity strings, consistent across Docket, AG and the caller."""
    spec = REVIEW_ROUTES[route]
    run_id = f'cohort-{cohort}-review-001'
    return {
        'schema': 'constellation.cohort-identities/v1',
        'cohort': cohort,
        'operator': f'cohort-{cohort}-operator',
        'issuer_principal': f'cohort-{cohort}-ag-issuer',
        'issuer_key_id': f'cohort-{cohort}-ag-issuer-k1',
        'standing_resolver_id': f'cohort-{cohort}-ag-standing/v1',
        'author_principal': f'cohort-{cohort}-author',
        'reviewer_id': spec.get('reviewer_id') or f'cohort-{cohort}-{spec["reviewer_id_suffix"]}',
        'pulse_authority_id': f'cohort-{cohort}-pulse',
        'pulse_producer_id': f'cohort-{cohort}-pulse-producer',
        'occurrence': str(uuid.uuid4()),
        'campaign': digest_bytes(f'constellation-cohort:{cohort}:campaign'.encode()),
        'program': digest_bytes(f'constellation-cohort:{cohort}:program'.encode()),
        'subject': digest_bytes(f'constellation-cohort:{cohort}:subject'.encode()),
        'observation': digest_bytes(f'constellation-cohort:{cohort}:allocated-observation'.encode()),
        'nq_instance': f'cohort-{cohort}-host',
        'nq_subject': f'host:cohort-{cohort}-host',
        'run_id': run_id,
        'work_item': WORK_ITEM,
        'dispatch_id': f'{run_id}-dispatch-1',
        'adapter_process': 'adapter-' + secrets.token_hex(16),
        'draft_id': 'draft_' + secrets.token_hex(16),
        'review_route': route,
        'reviewed_text_base64': base64.b64encode(f'Constellation cohort {cohort} reviewed copy.\n'.encode()).decode(),
    }


def codex_home_files(route: str, fixture_port: int | None) -> dict:
    """Cohort-owned codex home contents. Never a copied or shared home.

    The real route gets config only: the operator places auth.json themselves
    (documented step); this driver never reads, writes or copies a credential.
    The fixture route gets a loopback base URL and a generated dummy key in
    the API-key form (lane E's zero-cost spike).
    """
    common = ('cli_auth_credentials_store = "file"\ncheck_for_update_on_startup = false\n'
              '[analytics]\nenabled = false\n')
    if route == 'real':
        return {'config.toml': ('# cohort-owned codex home, real provider route\n' + common).encode()}
    if fixture_port is None or not 1024 <= fixture_port <= 65535:
        raise Refusal('fixture.port', 'fixture-review needs --fixture-port on 127.0.0.1')
    dummy = 'fixture-not-a-credential-' + secrets.token_hex(16)
    return {'config.toml': (f'# cohort-owned codex home, review_route = loopback-fixture\n'
                            f'openai_base_url = "http://127.0.0.1:{fixture_port}/v1"\n' + common).encode(),
            'auth.json': canonical({'OPENAI_API_KEY': dummy}) + b'\n'}


def nq_config_text(cohort: str, ids: dict) -> bytes:
    """One nq.host watcher for the cohort subject under NQ's own directories."""
    host = ids['nq_instance']
    return f'''# Constellation cohort {cohort}: one nq.host watcher (NQ release account model).
schema = "nq.config.v1"
database_path = "{NQ_STATE_DIR}/cohort-{cohort}/nq.db"
socket_path = "{NQ_RUN_DIR}/cohort-{cohort}/nqd.sock"
admissions_dir = "{NQ_STATE_DIR}/cohort-{cohort}/admissions"
helper_runtime_dir = "{NQ_RUN_DIR}/cohort-{cohort}/helpers"

[[watchers]]
instance_id = "{host}"
carrier = "stdio"
subject = "{ids['nq_subject']}"
capability_ceiling = ["read_procfs", "read_system_info"]
checkpoint_policy = "disabled"

[watchers.command]
executable = "/usr/lib/nq/helpers/nq-host-helper"
args = []
env = {{}}
execution_account = "nq-helper"
working_directory = "/usr/lib/nq/helpers"

[watchers.profile]
id = "nq.host"
version = 1

[watchers.scope]
kind = "host"
value = {{ id = "{host}" }}

[watchers.vantage]
kind = "local"
value = {{}}

[watchers.schedule]
interval_seconds = 300
jitter_seconds = 15
deadline_ms = 30000
retry_backoff_seconds = 10
max_retry_backoff_seconds = 300

[watchers.resources]
max_response_bytes = 1048576
max_stderr_bytes = 65536
max_observations = 1
max_address_space_bytes = 536870912
max_cpu_seconds = 60
max_processes = 32
max_open_files = 128
max_file_bytes = 67108864
'''.encode()


def reviewer_config(ids: dict, paths: dict, programs: Programs, app_server_sha: str) -> dict:
    return {
        'schema': 'switchyard.shared-review-verifier-config/v1', 'reviewer_id': ids['reviewer_id'],
        'author_principal': ids['author_principal'], 'excluded_thread_ids': [],
        'switchyard_state_path': str(paths['deployment'] / 'switchyard.sqlite'),
        'nightshift_state_path': str(paths['deployment'] / 'foreman.sqlite'),
        'nightshift_foreman_program': str(programs.foreman), 'nightshift_foreman_sha256': programs.sha(programs.foreman),
        'nightshift_run_id': ids['run_id'], 'brief_manifest_pointer': ['acceptance_tests', '0'],
        'brief_contract': 'switchyard.shared-review-manifest/v1',
        'route': {'codex_source_head': QUALIFIED_COHORTS[PROFILE]['alpha-exit-rc']['app-server']['source_commit'],
                  'app_server_executable_sha256': app_server_sha, 'provider': PROVIDER, 'model': MODEL,
                  'adapter_id': 'switchyard.codex-app-server', 'adapter_version': '2.0.0',
                  'adapter_protocol': 'switchyard.codex-app-server/v2'},
        'limits': {'max_result_bytes': 32768, 'max_custody_bytes': 32768, 'max_events_bytes': 16777216,
                   'foreman_timeout_seconds': 60},
    }


def ensure_account(records: Records) -> None:
    try:
        pwd.getpwnam(COHORT_ACCOUNT)
    except KeyError:
        records.call('account', ['useradd', '--system', '--home-dir', '/var/lib/constellation',
                                 '--no-create-home', '--shell', '/usr/sbin/nologin', '--user-group', COHORT_ACCOUNT])


def cmd_init(args) -> dict:
    facts = host_facts()
    require_host(facts)
    paths = cohort_paths(args.cohort)
    programs = Programs(args.cohort)
    if paths['state'].exists() or paths['nq_config'].exists() or paths['nq_state'].exists():
        raise Refusal('cohort.exists', f'{paths["state"]} exists; init runs once per cohort')
    if args.review_route == 'real' and args.fixture_port is not None:
        raise Refusal('fixture.port', 'the real route takes no fixture port')
    home_files = codex_home_files(args.review_route, args.fixture_port)
    for directory in (Path('/var/lib/constellation'), STATE_ROOT):
        directory.mkdir(mode=0o755, exist_ok=True)
        os.chmod(directory, 0o755)  # the runner opens every ancestor O_RDONLY
    records = Records(paths['install'] / 'init-records', 'init')
    records.write('host.json', facts)
    ensure_account(records)
    make_dir(paths['state'], 0o700, COHORT_ACCOUNT)
    make_dir(paths['records'], 0o700)
    ids = synthetic_identities(args.cohort, args.review_route)
    ids['codex_home'] = str(paths['state'] / REVIEW_ROUTES[args.review_route]['codex_home'])
    ids['app_server_session_identity'] = digest_bytes(ids['codex_home'].encode())
    ids['fixture_port'] = args.fixture_port
    write_new(paths['records'] / 'identities.json', canonical(ids) + b'\n', 0o644)
    records.write('identities.json', ids)
    # Cohort-owned directories.
    for key in ('inputs', 'scratch', 'deployment', 'observation', 'review', 'runs'):
        make_dir(paths[key], 0o700, COHORT_ACCOUNT)
    make_dir(paths['workspace'], 0o700, COHORT_ACCOUNT)
    home = make_dir(Path(ids['codex_home']), 0o700, COHORT_ACCOUNT)
    for name, raw in home_files.items():
        write_new(home / name, raw, 0o600, COHORT_ACCOUNT)
    records.write('codex-home.json', {'path': str(home), 'route': args.review_route,
                                      'files': sorted(os.listdir(home)), 'credential_read': False})
    records.mark('accounts-and-directories')
    # 2. Plan: Maude constructors, then the kit's prepare_plan with Maude's
    # exact qualified invocation, then the installed validator and executor.
    profiles = records.json_call('nq-profiles', [NQ, '--json', 'profiles', 'list'], user=COHORT_ACCOUNT)
    host_profile = [row for row in profiles if row.get('id') == 'nq.host' and row.get('version') == 1]
    if len(host_profile) != 1:
        raise Refusal('child.output', 'NQ profile catalog lacks exactly one nq.host v1')
    scope = digest_bytes(canonical({'schema': 'nq.diagnostic_scope.v1', 'subject': ids['nq_subject'],
                                    'scope': {'kind': 'host', 'value': {'id': ids['nq_instance']}},
                                    'profile': {'id': 'nq.host', 'version': '1', 'digest': host_profile[0]['digest']}}))
    values = {'campaign': ids['campaign'], 'occurrence': ids['occurrence'], 'program': ids['program'],
              'subject': ids['subject'], 'scope': scope, 'scratch_root': str(paths['scratch']),
              'observation': ids['observation'], 'reviewed_text_base64': ids['reviewed_text_base64'],
              'author': ids['author_principal']}
    write_new(paths['inputs'] / 'plan-values.json', canonical(values), 0o600, COHORT_ACCOUNT)
    records.call('plan-inputs', programs.kit_call('cohort_plan_inputs', [
        '--values', paths['inputs'] / 'plan-values.json', '--archive', programs.plan_library,
        '--output', paths['plan_input']], extra=[programs.plan_library]), user=COHORT_ACCOUNT)
    records.call('prepare-plan', kit_module([programs.plan_library, programs.kit], 'prepare_plan', [
        '--document', paths['plan_input'] / 'document.json', '--compiler-inputs', paths['plan_input'] / 'compiler-inputs.json',
        '--output', paths['plan'], '--draft-id', ids['draft_id']]), user=COHORT_ACCOUNT, timeout=120)
    records.json_call('plan-validator', [programs.validator, 'validate', '--config', paths['plan'] / 'validator-config.json',
                                         '--binding', paths['plan'] / 'binding.json'], user=COHORT_ACCOUNT)
    records.call('plan-id', [programs.executor, 'plan-id', paths['plan'] / 'executor-config.json'], user=COHORT_ACCOUNT)
    records.mark('plan')
    # 3. Ports: fresh issuer key, Docket trust and standing launcher, AG
    # standing launcher (sealer under -I -S), observation launcher.
    records.call('local-ports', programs.kit_call('prepare_local_ports', [
        '--output', paths['ports'], '--ag-standing', programs.ag_standing, '--ag-standing-sealer', programs.ag_sealer,
        '--docket', programs.docket, '--docket-resolver', programs.docket_resolver,
        '--nightshift-observation', programs.observation, '--python', PYTHON, '--openssl', OPENSSL,
        '--executor', programs.executor, '--operator', ids['operator'], '--issuer', ids['issuer_principal'],
        '--issuer-key-id', ids['issuer_key_id'], '--standing-resolver-id', ids['standing_resolver_id']]),
        user=COHORT_ACCOUNT, timeout=120)
    records.mark('ports')
    # Reviewer enrollment (route and custody stores are fixed now; the AG
    # genesis that pins it needs the observation and is sealed in review).
    app_server_info = read_json(programs.app_server_info)
    if app_server_info.get('executable_sha256') != programs.sha(programs.app_server):
        raise Refusal('build_info.executable_digest', 'app server differs from its build info')
    reviewer = reviewer_config(ids, paths, programs, app_server_info['executable_sha256'])
    write_new(paths['inputs'] / 'review-verifier-config.json', canonical(reviewer), 0o600, COHORT_ACCOUNT)
    # 4. NQ: a cohort config under NQ's own directories, a fresh store and
    # the one watcher admission in NQ's capability-bearing unit.
    write_new(paths['nq_config'], nq_config_text(args.cohort, ids), 0o640)
    os.chown(paths['nq_config'], 0, pwd.getpwnam(NQ_ACCOUNT).pw_gid)
    records.json_call('nq-init', [NQ, '--config', paths['nq_config'], '--json', 'init'], user=NQ_ACCOUNT)
    records.json_call('nq-watcher-admit', nq_unit(['--config', str(paths['nq_config']), '--json', 'watcher', 'admit',
                                                   ids['nq_instance']]), timeout=120)
    records.mark('nq')
    records.write('timings.json', records.timings)
    finished = {'schema': 'constellation.cohort-init/v1', 'cohort': args.cohort, 'review_route': args.review_route,
                'binding_id': read_json(paths['plan'] / 'binding.json')['binding_id'], 'occurrence': ids['occurrence'],
                'records': str(records.run), 'observation': 'none', 'provider_calls': 0, 'grants': 0, 'effects': 0}
    write_new(paths['records'] / 'init.finished.json', canonical(finished) + b'\n', 0o644)
    return {'result': 'initialized', **finished}


# ------------------------------------------------------------------ transitions

def claim(paths: dict, name: str, value: dict) -> None:
    """Create-once claim of a transition. A second claim refuses."""
    try:
        write_new(paths['records'] / f'{name}.claimed.json', canonical(value) + b'\n', 0o644)
    except FileExistsError:
        raise Refusal(f'{name}.exists', f'{name} was already started for this cohort; inspect '
                                         f'{paths["records"]} and use a fresh cohort for another occurrence') from None


def run_unit(records: Records, cohort: str, step: str, argv: list[str]) -> dict:
    """Run one transition in a transient system unit and read its result."""
    unit = f'constellation-{cohort}-{step}-{secrets.token_hex(4)}'
    command = ['/usr/bin/systemd-run', f'--unit={unit}', '--wait', '--collect', '--quiet', '--service-type=exec',
               f'--setenv=PATH={SYSTEM_PATH}', '--setenv=LANG=C.UTF-8', '--setenv=TMPDIR=/tmp']
    command += [f'--property={item}' for item in TRANSITION_UNIT]
    records.write('unit.json', {'unit': unit + '.service', 'argv': command + argv, 'properties': list(TRANSITION_UNIT),
                                'at': utc_now()})
    done = records.call('unit-' + step, command + argv, timeout=660, check=False)
    result_path = records.run / 'unit-result.json'
    if not result_path.exists():
        raise Refusal('child.failed', f'{unit} exited {done.returncode} without a result; see {records.run}')
    result = read_json(result_path)
    if result.get('result') == 'refused':
        raise Refusal(result.get('code', 'child.failed'), result.get('detail', ''))
    return result


def unit_entry(function, args) -> int:
    """Body of a transition unit: always leave one result record."""
    records_dir = Path(args.records)
    try:
        result = function(args, records_dir)
    except Refusal as refusal:
        write_new(records_dir / 'unit-result.json', canonical({'result': 'refused', 'code': refusal.code,
                                                               'detail': refusal.detail, 'at': utc_now()}) + b'\n')
        return 2
    except Exception as error:  # noqa: BLE001 - retained, never hidden
        write_new(records_dir / 'unit-result.json', canonical({'result': 'refused', 'code': 'child.failed',
                                                               'detail': f'{type(error).__name__}: {error}',
                                                               'at': utc_now()}) + b'\n')
        raise
    write_new(records_dir / 'unit-result.json', canonical(result) + b'\n')
    return 0


def cmd_review(args) -> dict:
    facts = host_facts()
    require_host(facts)
    paths = cohort_paths(args.cohort)
    Programs(args.cohort)
    if not (paths['records'] / 'init.finished.json').is_file():
        raise Refusal('cohort.not_initialized', args.cohort)
    ids = read_json(paths['records'] / 'identities.json')
    if ids['review_route'] == 'real' and not args.paid_request_allowed:
        raise Refusal('review.paid_request', 'the real route sends one billable provider request; '
                                             'pass --paid-request-allowed after placing the credential')
    if ids['review_route'] == 'fixture-review':
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(2)
            if probe.connect_ex(('127.0.0.1', ids['fixture_port'])) != 0:
                raise Refusal('fixture.unreachable', f'nothing listens on 127.0.0.1:{ids["fixture_port"]}; '
                                                     'start the loopback fixture first')
    require_free(Path('/var/lib'), 2 * 1024**3)
    claim(paths, 'review', {'at': utc_now(), 'route': ids['review_route']})
    records = Records(paths['records'], 'review')
    records.write('host.json', facts)
    driver = Path(__file__).resolve()
    result = run_unit(records, args.cohort, 'review', [str(PYTHON), '-I', '-S', str(driver), '_review-unit',
                                                       '--cohort', args.cohort, '--records', str(records.run)])
    return {**result, 'records': str(records.run)}


def _review_unit(args, records_dir: Path) -> dict:
    paths = cohort_paths(args.cohort)
    programs = Programs(args.cohort)
    ids = read_json(paths['records'] / 'identities.json')
    invocation = os.environ.get('INVOCATION_ID')
    if not invocation:
        raise Refusal('host.unit', 'the review transition runs only inside its durable unit')
    records = Records(records_dir, 'unit')
    records.mark('unit-start')
    config = str(paths['nq_config'])
    # 6. NQ: one bounded diagnostic in NQ's capability-bearing unit, then the
    # exact export and qualification as the nq account.
    executed = records.call('nq-diagnostics-execute', nq_unit(['--config', config, 'diagnostics', 'execute',
                                                               ids['nq_instance']]), timeout=120)
    records.mark('nq-executed')
    artifact_raw = executed.stdout
    artifact = json.loads(artifact_raw)
    if (artifact.get('schema') != 'nq.diagnostic_execution.v2' or artifact.get('profile', {}).get('id') != 'nq.host'
            or artifact.get('question', {}).get('id') != 'nq.host.load_pressure'):
        raise Refusal('observation.shape', 'NQ artifact is not the nq.host load-pressure diagnostic v2')
    if artifact.get('outcome', {}).get('condition') != 'explicitly_absent':
        raise Refusal('observation.condition', f'host load condition is {artifact.get("outcome")}, not explicitly_absent')
    try:
        return _review_after_observation(args, records, paths, programs, ids, invocation, artifact_raw, artifact)
    finally:
        records.mark('unit-end')
        records.write('timings.json', records.timings)
        records.write('review-timings.json', review_timings(artifact, paths['review_output'], records.timings))


def _review_after_observation(args, records, paths, programs, ids, invocation, artifact_raw, artifact) -> dict:
    obs, deployment, owner, ports = paths['observation'], paths['deployment'], paths['owner'], paths['ports']
    config = str(paths['nq_config'])
    artifact_id = artifact['artifact_id']
    exported = records.call('nq-diagnostics-export', [NQ, '--config', config, 'diagnostics', 'export', artifact_id],
                            user=NQ_ACCOUNT)
    if exported.stdout != artifact_raw:
        raise Refusal('observation.export', 'NQ export bytes differ from the execute output')
    provenance = records.call('nq-diagnostics-qualify', [NQ, '--config', config, '--json', 'diagnostics', 'qualify',
                                                         artifact_id], user=NQ_ACCOUNT).stdout
    write_new(obs / 'artifact.json', artifact_raw, 0o600, COHORT_ACCOUNT)
    write_new(obs / 'nq-provenance.json', provenance, 0o600, COHORT_ACCOUNT)
    source_id = json.loads(provenance)['source']['source_id']
    # The cohort account cannot read NQ's private store, so Nightshift's
    # read-only qualification runs against a verified NQ backup restored by
    # NQ itself into the cohort's observation directory.
    backup = paths['nq_state'] / f'backup-{ids["run_id"]}'
    records.json_call('nq-backup', [NQ, '--config', config, '--json', 'backup', backup], user=NQ_ACCOUNT)
    replica = make_dir(obs / 'nq-replica', 0o700, COHORT_ACCOUNT)
    shutil.copyfile(backup, replica / 'backup.db')
    os.chown(replica / 'backup.db', pwd.getpwnam(COHORT_ACCOUNT).pw_uid, pwd.getpwnam(COHORT_ACCOUNT).pw_gid)
    replica_config = nq_config_text(args.cohort, ids).decode().replace(
        f'{NQ_STATE_DIR}/cohort-{args.cohort}', str(replica)).replace(f'{NQ_RUN_DIR}/cohort-{args.cohort}', str(replica / 'run'))
    write_new(replica / 'nq.toml', replica_config.encode(), 0o600, COHORT_ACCOUNT)
    records.json_call('nq-replica-restore', [NQ, '--config', replica / 'nq.toml', '--json', 'restore',
                                             replica / 'backup.db', replica / 'nq.db'], user=COHORT_ACCOUNT)
    replica_provenance = records.call('nq-replica-qualify', [NQ, '--config', replica / 'nq.toml', '--json', 'diagnostics',
                                                             'qualify', artifact_id], user=COHORT_ACCOUNT).stdout
    if replica_provenance != provenance:
        raise Refusal('observation.replica', 'replica qualification differs from the NQ store')
    records.mark('nq-exported-qualified-replicated')
    # Posture-only request from the actual artifact (Maude helper, -I -S).
    role = {'purpose': 'one reviewed-copy host prerequisite', 'condition': 'explicitly_absent', 'delivery': 'not_required'}
    write_new(obs / 'role.json', canonical(role), 0o600, COHORT_ACCOUNT)
    label = f'cohort-{args.cohort}'
    records.call('posture-construct', [PYTHON, '-I', '-S', programs.cache_helper, 'construct', '--artifact',
                                       obs / 'artifact.json', '--role-id', 'reviewed-copy-host', '--role-version', '1',
                                       '--role-digest', digest_bytes(canonical(role)), '--generation', label,
                                       '--schedule-id', label, '--attempt-id', label, '--configuration-version', label,
                                       '--scheduler-clock-id', f'{label}-wall-clock', '--cycle-request-out',
                                       obs / 'posture.json'], user=COHORT_ACCOUNT)
    # 7. Pulse: fresh producer key, config and sealed resolver launcher.
    records.json_call('pulse-prepare', [PYTHON, '-I', '-S', programs.pulse_prepare, '--artifact', obs / 'artifact.json',
                                        '--posture-request', obs / 'posture.json', '--output', obs / 'pulse',
                                        '--pulse', programs.pulse, '--pulse-sha256', programs.sha(programs.pulse),
                                        '--python', PYTHON, '--python-sha256', sha256_file(PYTHON),
                                        '--openssl', OPENSSL, '--openssl-sha256', sha256_file(OPENSSL),
                                        '--sealer', programs.pulse_sealer, '--sealer-sha256', programs.sha(programs.pulse_sealer),
                                        '--authority-id', ids['pulse_authority_id'], '--producer-id', ids['pulse_producer_id']],
                      user=COHORT_ACCOUNT)
    records.mark('pulse-prepared')
    # 4. Owner and AG genesis: the Nightshift config pins the Pulse resolver,
    # the NQ source and the original observation time, so it is sealed here.
    def identity(path: Path) -> dict:
        return {'path': str(path), 'sha256': sha256_file(path)}
    nightshift_config = {
        'schema': 'nightshift.ag_cycle_config.v1', 'store': str(ports / 'nightshift.sqlite'),
        'present_evidence_resolver': identity(obs / 'pulse' / 'pulse-support-resolver'),
        'nq_program': identity(NQ), 'nq_config': identity(replica / 'nq.toml'), 'nq_source_id': source_id,
        'ag_loopctl': identity(programs.ag), 'ag_database': str(deployment / 'ag.sqlite'),
        'ag_observation_resolver': identity(ports / 'observation-launcher'),
        'ag_observation_resolver_id': 'nightshift-observation-resolver/v1',
        'ag_runtime_profile': str(deployment / 'runtime-profile.json'), 'recover_observed_at': artifact['completed_at']}
    write_new(paths['inputs'] / 'nightshift-ag-cycle-config.json', canonical(nightshift_config), 0o600, COHORT_ACCOUNT)
    records.call('owner-assemble', programs.kit_call('prepare_owner', [
        '--binding', paths['plan'] / 'binding.json', '--reviewer-config', paths['inputs'] / 'review-verifier-config.json',
        '--nightshift-config', paths['inputs'] / 'nightshift-ag-cycle-config.json',
        '--docket-enrollment', ports / 'docket-root-enrollment.json', '--output', owner,
        '--runtime-profile', deployment / 'runtime-profile.json', '--observation-resolver', ports / 'observation-launcher',
        '--standing-resolver', ports / 'ag-standing-launcher', '--plan-validator', programs.validator,
        '--validator-config', paths['plan'] / 'validator-config.json', '--review-verifier', programs.verifier,
        '--nightshift-program', programs.nightshift, '--profile-label', label,
        '--standing-resolver-id', ids['standing_resolver_id']]), user=COHORT_ACCOUNT)
    sealed = records.json_call('ag-seal-runtime-profile', [programs.ag, 'seal-runtime-profile-v2', '--enrollment',
                                                           owner / 'runtime-profile-enrollment-v2.json', '--output',
                                                           deployment / 'runtime-profile.json'], user=COHORT_ACCOUNT)
    verified = records.json_call('ag-verify-runtime-profile', [programs.ag, 'verify-runtime-profile-v2',
                                                               '--runtime-profile', deployment / 'runtime-profile.json'],
                                 user=COHORT_ACCOUNT)
    if sealed != verified:
        raise Refusal('child.output', 'AG profile verification receipt differs from the seal receipt')
    records.json_call('ag-init', [programs.ag, 'init-v2', '--database', deployment / 'ag.sqlite', '--genesis',
                                  owner / 'genesis-v1.json', '--runtime-profile', deployment / 'runtime-profile.json'],
                      user=COHORT_ACCOUNT)
    records.mark('ag-genesis')
    # 7 (cont.). Pulse produce and ingest: actual signed support and receipt.
    acquisition = f'{ids["run_id"]}-acquisition-001'
    pulse_config = obs / 'pulse' / 'config.json'
    for step in ('produce', 'ingest'):
        records.call('pulse-' + step, [programs.pulse, step, '--config', pulse_config, '--acquisition-id', acquisition],
                     user=COHORT_ACCOUNT)
    records.mark('pulse-support')
    # 8. Seal the observed admission request with the plan's preallocated
    # observation coordinate; retained Pulse receipt and query.
    records.call('seal-admission', programs.kit_call('seal_admission', [
        '--binding', paths['plan'] / 'binding.json', '--posture-request', obs / 'posture.json',
        '--output', deployment / 'cycle-request.json', '--use-plan-observation-identity']), user=COHORT_ACCOUNT)
    config_value = read_json(pulse_config)
    receipt = read_json(obs / 'pulse' / 'receipts' / ('sha256-' + hashlib.sha256(acquisition.encode()).hexdigest() + '.json'))
    retention = {'evidence_id': receipt['evidence']['evidence']['evidence_id'], 'received_at': receipt['received_at'],
                 'expiry_tick_ms': receipt['expiry_tick_ms']}
    write_new(deployment / 'pulse-retention.json', canonical(retention), 0o600, COHORT_ACCOUNT)
    query = {'schema': 'nightshift.present_evidence_query.v1', 'observation_cycle_id': label, 'request_nonce': invocation,
             'observation_id': ids['observation'],
             'diagnostic_inputs_id': config_value['expected_diagnostic']['diagnostic_inputs_id'],
             'subject_id': config_value['subject_id'], 'scope_id': config_value['scope_id'],
             'artifact_ids': config_value['expected_diagnostic']['artifact_ids']}
    query['query_id'] = digest_bytes(canonical(query))
    write_new(deployment / 'pulse-query.json', canonical(query), 0o600, COHORT_ACCOUNT)
    # Foreman inputs (admission window at most 120 s, so only now).
    build_info = records.call('switchyard-build-info', [programs.runner, '--build-info'], user=COHORT_ACCOUNT).stdout
    write_new(deployment / 'switchyard-build-info.json', build_info, 0o600, COHORT_ACCOUNT)
    records.json_call('foreman-inputs', programs.kit_call('prepare_review_inputs', [
        '--binding', paths['plan'] / 'binding.json', '--reviewer-config', owner / 'review-verifier-config.json',
        '--switchyard-build-info', deployment / 'switchyard-build-info.json', '--foreman', programs.foreman,
        '--workspace', paths['workspace'], '--custody-root', deployment / 'foreman-custody',
        '--output', deployment / 'foreman-inputs', '--run-id', ids['run_id'], '--work-item', ids['work_item'],
        '--operator', ids['operator'], '--label', label, '--maude-commit', programs.maude_commit,
        '--executor-sha256', programs.sha(programs.executor)]), user=COHORT_ACCOUNT)
    records.mark('foreman-inputs')
    backend = {'schema': 'switchyard.provider-backend/v1', 'executable': str(programs.app_server),
               'executable_sha256': programs.sha(programs.app_server), 'executable_shape': 'standalone-app-server',
               'codex_source_head': QUALIFIED_COHORTS[PROFILE]['alpha-exit-rc']['app-server']['source_commit'],
               'codex_home': ids['codex_home'], 'provider': PROVIDER, 'model': MODEL}
    write_new(deployment / 'backend.json', canonical(backend), 0o600, COHORT_ACCOUNT)
    inputs = deployment / 'foreman-inputs'
    layout = {
        'schema': 'constellation.reviewed-local-copy-caller/v1',
        'programs': {'ag': str(programs.ag), 'nightshift': str(programs.nightshift), 'foreman': str(programs.foreman),
                     'provider': str(programs.runner), 'review_verifier': str(programs.verifier),
                     'docket': str(programs.docket), 'pulse': str(obs / 'pulse' / 'pulse-support-resolver'),
                     'app_server': str(programs.app_server)},
        'inputs': {'binding': str(paths['plan'] / 'binding.json'), 'cycle_request': str(deployment / 'cycle-request.json'),
                   'nightshift_config': str(owner / 'nightshift-ag-cycle-config.json'),
                   'runtime_profile': str(deployment / 'runtime-profile.json'),
                   'review_requirement': str(owner / 'review-requirement.json'),
                   'review_verifier_config': str(owner / 'review-verifier-config.json'),
                   'executor_config': str(paths['plan'] / 'executor-config.json'), 'backend': str(deployment / 'backend.json'),
                   'packet': str(inputs / 'packet.json'), 'admission': str(inputs / 'admission.json'),
                   'profile': str(inputs / 'profile.json'), 'policy': str(inputs / 'policy.json'),
                   'provider_requirement': str(inputs / 'requirement.json'), 'source_provenance': str(programs.provenance),
                   'pulse_query': str(deployment / 'pulse-query.json'),
                   'pulse_retention': str(deployment / 'pulse-retention.json'),
                   'docket_standing_config': str(ports / 'docket-standing-config.json')},
        'paths': {'ag_database': str(deployment / 'ag.sqlite'), 'foreman_database': str(deployment / 'foreman.sqlite'),
                  'switchyard_database': str(deployment / 'switchyard.sqlite'), 'docket_state': str(ports / 'docket-state'),
                  'ag_mandates': str(ports / 'ag-mandates.json')},
        'review': {'run_id': ids['run_id'], 'work_item': ids['work_item'], 'dispatch_id': ids['dispatch_id'],
                   'adapter_process': ids['adapter_process'],
                   'app_server_session_identity': ids['app_server_session_identity']},
        'operator': ids['operator'],
    }
    write_new(deployment / 'layout.json', canonical(layout), 0o600, COHORT_ACCOUNT)
    records.call('enroll-caller', programs.kit_call('enroll_caller', ['--layout', deployment / 'layout.json',
                                                                      '--output', deployment / 'caller.json']),
                 user=COHORT_ACCOUNT)
    records.call('caller-preflight', programs.kit_call('reviewed_action', [
        '--config', deployment / 'caller.json', '--output', deployment / 'unused-preflight-output', '--preflight-only']),
        user=COHORT_ACCOUNT)
    records.mark('caller-enrolled')
    # 9. One bounded review, then stop before acceptance.
    caller_env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'INVOCATION_ID': invocation}
    done = records.call('reviewed-action-review-only', programs.kit_call('reviewed_action', [
        '--config', deployment / 'caller.json', '--output', paths['review_output'], '--review-only']),
        user=COHORT_ACCOUNT, env=caller_env, timeout=420, check=False)
    records.mark('review-finished')
    terminal = read_json(paths['review_output'] / 'terminal.json') if (paths['review_output'] / 'terminal.json').is_file() else None
    timing = review_timings(artifact, paths['review_output'], records.timings)
    if done.returncode != 0 or not terminal or terminal.get('exit_code') != 0:
        reason = (terminal or {}).get('reason', f'caller exited {done.returncode}')
        raise Refusal('review.refused', f'{(terminal or {}).get("phase", "caller")}: {reason}')
    candidate = sha256_file(paths['review_output'] / 'record-review-input.json')
    return {'result': 'reviewed', 'cohort': args.cohort, 'binding_id': terminal['result']['binding_id'],
            'verdict_accepted': terminal['result']['verification'].get('accepted'),
            'candidate_sha256': candidate, 'candidate': str(paths['review_output'] / 'record-review-input.json'),
            'provider_calls': terminal['result']['provider_calls'], 'grants': 0, 'effects': 0,
            'timings': timing, 'next': 'Inspect the candidate, then accept it by its exact digest.'}


def review_timings(artifact: dict, review_output: Path, marks: list) -> dict:
    """Elapsed time per phase, against the 300 000 ms observation TTL."""
    observed = parse_rfc3339_ms(artifact['completed_at'])
    result = {'observation_completed_at': artifact['completed_at'],
              'phases_ms_after_observation': {mark['label']: mark['at_unix_ms'] - observed for mark in marks}}
    for name in ('before-review', 'immediately-before-review'):
        path = review_output / f'{name}-reserve.json'
        if path.is_file():
            reserve = read_json(path)
            result[name] = {'observation_remaining_ms': reserve['original_observation_remaining_ms'],
                            'elapsed_since_observation_ms': 300000 - reserve['original_observation_remaining_ms'],
                            'pulse_remaining_ms': reserve['pulse_remaining_ms'], 'minimum_ms': reserve['minimum_ms']}
    started = review_output / 'provider-run.started.json'
    if started.is_file():
        result['provider_run_started_ms_after_observation'] = read_json(started)['at_unix_ms'] - observed
    return result


def retained_candidate(paths: dict) -> tuple[str, dict]:
    terminal_path = paths['review_output'] / 'terminal.json'
    if not terminal_path.is_file():
        raise Refusal('review.not_ready', 'no retained review; run review first')
    terminal = read_json(terminal_path)
    if terminal.get('exit_code') != 0 or not (paths['review_output'] / 'record-review-input.json').is_file():
        raise Refusal('review.not_ready', f'the retained review refused: {terminal.get("reason")}')
    return sha256_file(paths['review_output'] / 'record-review-input.json'), terminal


def cmd_accept(args) -> dict:
    if not DIGEST.fullmatch(args.candidate_sha256 or ''):
        raise Refusal('accept.candidate', 'name the exact record-review-input digest as sha256:<64 hex>')
    facts = host_facts()
    require_host(facts)
    paths = cohort_paths(args.cohort)
    Programs(args.cohort)
    if (paths['records'] / 'accept.claimed.json').exists():
        raise Refusal('accept.exists', 'this cohort already has an acceptance transition; its effect is create-once')
    candidate, _ = retained_candidate(paths)
    if args.candidate_sha256 != candidate:
        raise Refusal('accept.candidate_mismatch', 'the named digest is not the retained candidate; nothing was recorded')
    claim(paths, 'accept', {'at': utc_now(), 'candidate_sha256': args.candidate_sha256})
    records = Records(paths['records'], 'accept')
    records.write('host.json', facts)
    driver = Path(__file__).resolve()
    result = run_unit(records, args.cohort, 'accept', [str(PYTHON), '-I', '-S', str(driver), '_accept-unit',
                                                       '--cohort', args.cohort, '--records', str(records.run),
                                                       '--candidate-sha256', args.candidate_sha256])
    return {**result, 'records': str(records.run)}


def _accept_unit(args, records_dir: Path) -> dict:
    paths = cohort_paths(args.cohort)
    programs = Programs(args.cohort)
    invocation = os.environ.get('INVOCATION_ID')
    if not invocation:
        raise Refusal('host.unit', 'the accept transition runs only inside its durable unit')
    records = Records(records_dir, 'unit')
    records.mark('unit-start')
    caller_env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'INVOCATION_ID': invocation}
    done = records.call('continue-accept-and-execute', programs.kit_call('continue_reviewed_action', [
        '--config', paths['deployment'] / 'caller.json', '--retained-review', paths['review_output'],
        '--accept-candidate-sha256', args.candidate_sha256, '--output', paths['continuation'], '--accept-and-execute']),
        user=COHORT_ACCOUNT, env=caller_env, timeout=420, check=False)
    records.mark('continuation-finished')
    records.write('timings.json', records.timings)
    terminal_path = paths['continuation'] / 'terminal.json'
    terminal = read_json(terminal_path) if terminal_path.is_file() else None
    if done.returncode != 0 or not terminal or terminal.get('exit_code') != 0:
        reason = (terminal or {}).get('reason', f'continuation exited {done.returncode}')
        raise Refusal('accept.refused', f'{(terminal or {}).get("phase", "continuation")}: {reason}')
    return {'result': 'accepted_and_executed', 'cohort': args.cohort, 'candidate_sha256': args.candidate_sha256,
            'native': terminal['result'], 'operator_acceptance': terminal['operator_acceptance'],
            'human_attestation': terminal['human_attestation'],
            'provider_calls_in_continuation': terminal['provider_calls_in_continuation']}


# ------------------------------------------------------------------ status

def native_read(programs: Programs, paths: dict) -> dict:
    """Read-only native inspection as the cohort account."""
    def run(argv):
        done = subprocess.run(as_user(COHORT_ACCOUNT, [str(a) for a in argv]), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env={'PATH': SYSTEM_PATH, 'LANG': 'C.UTF-8'}, timeout=60, check=False)
        if done.returncode != 0:
            raise Refusal('child.failed', f'{argv[1]}: {done.stderr.decode(errors="replace")[-400:]}')
        return json.loads(done.stdout)
    result = {}
    database = paths['deployment'] / 'ag.sqlite'
    if not database.exists():
        return {'ag': 'absent'}
    inspected = run([programs.ag, 'inspect', '--database', database])
    result['ag_inspect'] = inspected
    state = inspected['current']['state']
    variant = next(iter(state))  # one tagged variant; never a fixed path
    result['program_counter'] = variant
    value = state[variant]
    custody = value.get('dispatch', {}).get('custody') if isinstance(value, dict) else None
    if custody:
        result['docket_inspect'] = run([programs.docket, 'governed-loop', 'inspect', '--state', paths['ports'] / 'docket-state',
                                        '--issuance', custody['issuance']])
        result['standing_snapshot'] = run([programs.docket, 'governed-loop', 'standing-snapshot', '--state',
                                           paths['ports'] / 'docket-state', '--issuance', custody['issuance']])
    return result


def result_file(paths: dict) -> dict:
    """No-follow exact-bytes read of result.txt; a caller observation, not an NQ judgment."""
    executor = read_json(paths['plan'] / 'executor-config.json')
    plan = json.loads(base64.b64decode(executor['executor_plan_base64'], validate=True))
    target = Path(plan['scratch_root']) / 'result.txt'
    entry = {'path': str(target), 'expected_sha256': plan['reviewed_text_digest'],
             'expected_bytes': plan['reviewed_text_byte_length'],
             'interpretation': 'Exact regular file inspected; not an NQ current-postcondition judgment.'}
    try:
        raw = read_bytes(target, 65536)
    except FileNotFoundError:
        return {**entry, 'present': False}
    entry.update(present=True, sha256=digest_bytes(raw), bytes=len(raw),
                 matches_plan=digest_bytes(raw) == plan['reviewed_text_digest'] and len(raw) == plan['reviewed_text_byte_length'],
                 content_base64=base64.b64encode(raw).decode(), scratch_entries=sorted(os.listdir(plan['scratch_root'])))
    return entry


def cmd_status(args) -> dict:
    paths = cohort_paths(args.cohort)
    if not paths['install'].is_dir():
        raise Refusal('cohort.not_installed', args.cohort)
    status = {'result': 'status', 'cohort': args.cohort, 'installed': True,
              'initialized': (paths['records'] / 'init.finished.json').is_file() if paths['state'].exists() else False}
    if not status['initialized']:
        return status
    if os.geteuid() != 0:
        raise Refusal('host.not_root', 'status reads the cohort account\'s private state')
    programs = Programs(args.cohort)
    status['identities'] = read_json(paths['records'] / 'identities.json')
    review_terminal = paths['review_output'] / 'terminal.json'
    if review_terminal.is_file():
        terminal = read_json(review_terminal)
        review = {'exit_code': terminal.get('exit_code'), 'phase': terminal.get('phase'), 'reason': terminal.get('reason')}
        if terminal.get('exit_code') == 0:
            result = terminal['result']
            review.update(binding_id=result['binding_id'], verification=result['verification'],
                          provider_calls=result['provider_calls'], grants=result['grants'], spends=result['spends'],
                          docket_attempts=result['docket_attempts'], executor_calls=result['executor_calls'],
                          effects=result['effects'],
                          candidate=str(paths['review_output'] / 'record-review-input.json'),
                          candidate_sha256=sha256_file(paths['review_output'] / 'record-review-input.json'),
                          candidate_review=read_json(paths['review_output'] / 'record-review-input.json')['review'])
        status['review'] = review
    else:
        status['review'] = 'not_started' if not (paths['records'] / 'review.claimed.json').exists() else 'no_retained_terminal'
    continuation = paths['continuation'] / 'terminal.json'
    if continuation.is_file():
        terminal = read_json(continuation)
        status['accept'] = {key: terminal.get(key) for key in ('exit_code', 'phase', 'reason', 'result', 'operator_acceptance',
                                                               'human_attestation', 'provider_calls_in_continuation')}
    else:
        status['accept'] = 'not_started' if not (paths['records'] / 'accept.claimed.json').exists() else 'no_retained_terminal'
    native = native_read(programs, paths)
    status['native'] = {key: value for key, value in native.items() if key != 'ag_inspect'}
    if 'ag_inspect' in native:
        status['native']['replay'] = native['ag_inspect'].get('replay')
        state = native['ag_inspect']['current']['state']
        value = state[native['program_counter']]
        if isinstance(value, dict) and 'settlement' in value:
            status['native']['settlement_outcome'] = value['settlement'].get('outcome')
    status['result_file'] = result_file(paths)
    return status


# ------------------------------------------------------------------ evidence

def sqlite_backup(source: Path, destination: Path) -> str:
    """Online consistent copy through SQLite's backup API, read-only source."""
    uri = f'file:{source}?mode=ro'
    with sqlite3.connect(uri, uri=True) as origin, sqlite3.connect(destination) as copy:
        origin.backup(copy)
    return sha256_file(destination)


def evidence_join(native: dict, paths: dict) -> dict:
    """Join binding, occurrence, candidate, issuance, attempt and settlement."""
    binding = read_json(paths['plan'] / 'binding.json')
    candidate_raw = read_bytes(paths['review_output'] / 'record-review-input.json')
    candidate = json.loads(candidate_raw)
    inspected = native['ag_inspect']
    variant = native['program_counter']
    value = inspected['current']['state'][variant]
    checks = {}
    dispatch = value.get('dispatch', {})
    authorized = dispatch.get('authorized', {})
    spend = authorized.get('spend', {})
    issuance = authorized.get('issuance', {})
    custody = dispatch.get('custody', {})
    settlement = value.get('settlement', {})
    record = native.get('docket_inspect', {}).get('record', {})
    snapshot = native.get('standing_snapshot', {})
    checks['settled'] = variant == 'settled_observation_required' and settlement.get('outcome') == 'success'
    checks['occurrence'] = (spend.get('key', {}).get('occurrence') == binding['occurrence'] == candidate['occurrence']
                            and spend.get('key', {}).get('campaign') == binding['campaign'] == candidate['campaign']
                            and issuance.get('key') == spend.get('key') and issuance.get('work') == binding['work'])
    checks['binding'] = candidate['binding_id'] == binding['binding_id'] == candidate['review']['binding_id']
    accepted = paths['continuation'] / 'operator-acceptance.json'
    accepted_copy = paths['continuation'] / 'accepted-record-review-input.json'
    checks['candidate_accepted'] = (accepted.is_file() and accepted_copy.is_file()
                                    and read_json(accepted)['candidate_sha256'] == digest_bytes(candidate_raw)
                                    and read_bytes(accepted_copy) == candidate_raw)
    checks['issuance_v2_not_after'] = (issuance.get('schema') == 'ag.governed-loop.issuance/v2'
                                       and type(issuance.get('not_after_unix_ms')) is int
                                       and issuance['not_after_unix_ms'] > spend.get('consumed_at_unix_ms', 2**63))
    checks['issuance_ag_docket'] = (custody.get('issuance') is not None and issuance.get('issuance') == custody['issuance']
                                    and record.get('issuance') == issuance and record.get('custody') == custody
                                    and native.get('docket_inspect', {}).get('requested_issuance') == custody['issuance'])
    checks['attempt_ag_docket'] = (custody.get('attempt') is not None
                                   and record.get('settlement', {}).get('attempt') == custody.get('attempt'))
    checks['settlement_ag_docket'] = record.get('settlement') == settlement and record.get('status') == 'settled'
    checks['standing_join'] = (snapshot.get('execution_standing') == custody.get('execution_standing')
                               and snapshot.get('currentness') == custody.get('standing_currentness'))
    checks['replay_once'] = all(inspected['replay'].get(key) == 1 for key in ('ag_spends', 'docket_attempts', 'settlements'))
    return {'schema': 'constellation.cohort-evidence-join/v1', 'complete': all(checks.values()), 'checks': checks,
            'binding_id': binding['binding_id'], 'occurrence': binding['occurrence'], 'campaign': binding['campaign'],
            'candidate_sha256': digest_bytes(candidate_raw), 'review_id_digest': candidate['review']['result_digest'],
            'issuance': custody.get('issuance'), 'attempt': custody.get('attempt'), 'spend': spend.get('spend'),
            'settlement': settlement.get('settlement'), 'not_after_unix_ms': issuance.get('not_after_unix_ms'),
            'state_digest': inspected['current'].get('state_digest')}


def cmd_evidence(args) -> dict:
    if os.geteuid() != 0:
        raise Refusal('host.not_root', 'evidence reads the cohort account\'s private state')
    paths = cohort_paths(args.cohort)
    programs = Programs(args.cohort)
    if not (paths['records'] / 'init.finished.json').is_file():
        raise Refusal('cohort.not_initialized', args.cohort)
    output = args.output
    if not output.is_absolute():
        raise Refusal('evidence.output', 'absolute fresh output directory required')
    try:
        make_dir(output, 0o700)
    except FileExistsError:
        raise Refusal('evidence.output', f'{output} exists; evidence is written once to a fresh directory') from None
    files = {}
    def keep(relative: str, raw: bytes) -> None:
        target = output / relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        write_new(target, raw, 0o600)
        files[relative] = digest_bytes(raw)
    def copy_tree(source: Path, prefix: str, skip=()) -> None:
        if not source.is_dir():
            return
        for path in sorted(source.rglob('*')):
            if path.is_symlink() or not path.is_file() or path.suffix in ('.sqlite', '.db', '.lock') or path.name in skip \
                    or path.name.endswith(('-wal', '-shm')) or 'native-tmp' in path.parts:
                continue
            keep(f'{prefix}/{path.relative_to(source)}', read_bytes(path, 64 * 1024 * 1024))
    copy_tree(paths['install'] / 'install-records', 'records/install')
    keep('records/installed.json', read_bytes(paths['install'] / 'installed.json'))
    copy_tree(paths['install'] / 'init-records', 'records/init')
    copy_tree(paths['records'], 'records/driver')
    copy_tree(paths['review_output'], 'caller/review-001')
    copy_tree(paths['continuation'], 'caller/continuation-001')
    for key, names in (('plan', ('binding.json', 'validator-config.json', 'executor-config.json', 'compiled-handoff.json',
                                 'plan-validation.json')),
                       ('owner', ('exact-work-catalog-v2.json', 'genesis-v1.json', 'nightshift-ag-cycle-config.json',
                                  'review-requirement.json', 'review-verifier-config.json', 'runtime-profile-enrollment-v2.json')),
                       ('deployment', ('runtime-profile.json', 'cycle-request.json', 'backend.json', 'layout.json',
                                       'caller.json', 'pulse-query.json', 'pulse-retention.json')),
                       ('observation', ('artifact.json', 'nq-provenance.json', 'posture.json', 'role.json')),
                       ('ports', ('docket-trust.json', 'docket-standing-config.json', 'docket-root-enrollment.json',
                                  'ag-standing-enrollment.json', 'ag-standing-manifest.json', 'ag-mandates.json'))):
        for name in names:
            if (paths[key] / name).is_file():
                keep(f'state/{key}/{name}', read_bytes(paths[key] / name))
    copy_tree(paths['deployment'] / 'foreman-inputs', 'state/deployment/foreman-inputs')
    backups = {}
    for label, source in (('ag', paths['deployment'] / 'ag.sqlite'), ('foreman', paths['deployment'] / 'foreman.sqlite'),
                          ('switchyard', paths['deployment'] / 'switchyard.sqlite'),
                          ('nightshift', paths['ports'] / 'nightshift.sqlite'),
                          ('docket', paths['ports'] / 'docket-state' / 'state.sqlite'),
                          ('plan', paths['plan'] / 'plans.sqlite')):
        if source.is_file():
            target = output / 'stores' / f'{label}.sqlite'
            target.parent.mkdir(mode=0o700, exist_ok=True)
            backups[label] = sqlite_backup(source, target)
            files[f'stores/{label}.sqlite'] = backups[label]
    native = native_read(programs, paths)
    for key in ('ag_inspect', 'docket_inspect', 'standing_snapshot'):
        if key in native:
            keep(f'native/{key.replace("_", "-")}.json', canonical(native[key]) + b'\n')
    result = result_file(paths)
    keep('native/result-file.json', canonical(result) + b'\n')
    join = evidence_join(native, paths) if native.get('program_counter') and (paths['review_output'] / 'record-review-input.json').is_file() else \
        {'schema': 'constellation.cohort-evidence-join/v1', 'complete': False, 'checks': {}, 'reason': 'no settled occurrence'}
    join['checks']['result_file_matches_plan'] = bool(result.get('matches_plan'))
    join['complete'] = bool(join['checks']) and all(join['checks'].values())
    keep('JOIN.json', canonical(join) + b'\n')
    sums = ''.join(f'{value.removeprefix("sha256:")}  {name}\n' for name, value in sorted(files.items()))
    write_new(output / 'SHA256SUMS', sums.encode(), 0o600)
    return {'result': 'evidence', 'cohort': args.cohort, 'output': str(output), 'files': len(files),
            'join_complete': join['complete'], 'join': join['checks']}


# ------------------------------------------------------------------ cli

def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog='constellation-cohort', description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    top.add_argument('--version', action='version', version=f'constellation-cohort {DRIVER_VERSION}')
    sub = top.add_subparsers(dest='command', required=True)
    for name in ('verify-manifest', 'install'):
        p = sub.add_parser(name)
        p.add_argument('--manifest', type=Path, required=True)
        p.add_argument('--artifacts', type=Path, required=True)
        if name == 'install':
            p.add_argument('--cohort', required=True)
    p = sub.add_parser('init')
    p.add_argument('--cohort', required=True)
    p.add_argument('--review-route', choices=sorted(REVIEW_ROUTES), required=True)
    p.add_argument('--fixture-port', type=int)
    p = sub.add_parser('review')
    p.add_argument('--cohort', required=True)
    p.add_argument('--paid-request-allowed', action='store_true',
                   help='real route only: the operator allows its one billable provider request')
    sub.add_parser('status').add_argument('--cohort', required=True)
    p = sub.add_parser('accept')
    p.add_argument('--cohort', required=True)
    p.add_argument('--candidate-sha256', required=True,
                   help='the exact record-review-input.json digest the operator inspected and accepts')
    p = sub.add_parser('evidence')
    p.add_argument('--cohort', required=True)
    p.add_argument('--output', type=Path, required=True)
    for name in ('_review-unit', '_accept-unit'):
        p = sub.add_parser(name, help=argparse.SUPPRESS)
        p.add_argument('--cohort', required=True)
        p.add_argument('--records', required=True)
        if name == '_accept-unit':
            p.add_argument('--candidate-sha256', required=True)
    return top


COMMANDS = {'verify-manifest': cmd_verify_manifest, 'install': cmd_install, 'init': cmd_init,
            'review': cmd_review, 'accept': cmd_accept, 'status': cmd_status, 'evidence': cmd_evidence}
UNITS = {'_review-unit': _review_unit, '_accept-unit': _accept_unit}


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.command in UNITS:
        return unit_entry(UNITS[args.command], args)
    try:
        result = COMMANDS[args.command](args)
    except Refusal as refusal:
        sys.stdout.write(canonical({'result': 'refused', 'command': args.command, 'code': refusal.code,
                                    'detail': refusal.detail}).decode() + '\n')
        return 2
    sys.stdout.write(canonical(result).decode() + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
