#!/usr/bin/python3
"""Set up one fresh reviewed-local-copy/v1 cohort on one Debian 12 host.

This is the cohort setup driver: the smallest mechanism that turns verified
release artifacts into one working cohort. It is not an orchestrator, a
cluster manager, a configuration language or a control plane. It runs the
public caller glue in this kit and the components' own commands, in a fixed
order, with fixed paths, and stops at the first refusal.

Newcomer steps (see F-SETUP-DRIVER-DESIGN.md for detail):

  1. verify-manifest  check the cohort manifest and artifacts; writes nothing
  2. install          (root) verify again, install artifacts, check build info
  3. init             (root) accounts, synthetic identities and keys, config,
                      plan, ports, AG genesis; no observation, provider or effect
  4. review           (root) one durable unit: fresh observation, admission,
                      one bounded review; stops before acceptance
  5. accept           (root) the operator names the exact candidate digest;
                      one durable unit records the review and executes once
  6. status           read-only native inspection and driver records
  7. evidence         read-only bundle of records and store snapshots

Every run writes started/finished/terminal records under the cohort's driver
directory. A refusal has a stable code and never leaves a half-written file
presented as complete. Nothing is retried, and nothing is overwritten: a
second run of a step against the same cohort refuses. Use a new cohort id or
a new disposable host.

Status: SKELETON (alpha-exit closure lane F, phase 1). Manifest validation,
cohort pin checks, artifact verification, safe extraction and the record
format are implemented and unit tested. Steps that need component artifacts
still pending from lanes A-E refuse with code `pending.<lane>`; they never
pretend to succeed.

Python 3.11 standard library only (Debian 12 /usr/bin/python3). No network.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import uuid

DRIVER_VERSION = '0.1.0-skeleton'
MANIFEST_SCHEMA = 'constellation.cohort-manifest/v1'
PROFILE = 'reviewed-local-copy/v1'
RECORD_SCHEMA = 'constellation.cohort-driver-record/v1'

INSTALL_ROOT = Path('/opt/constellation/cohorts')
STATE_ROOT = Path('/var/lib/constellation/cohorts')
COHORT_ACCOUNT = 'constellation'
PYTHON = Path('/usr/bin/python3.11')
OPENSSL = Path('/usr/bin/openssl')

COMMIT = re.compile(r'[0-9a-f]{40}\Z')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}\Z')
VERSION = re.compile(r'[0-9A-Za-z][0-9A-Za-z.+~_-]{0,63}\Z')
COHORT_ID = re.compile(r'[a-z0-9][a-z0-9-]{2,39}\Z')
PENDING = 'PENDING'

# Components the profile requires, what each artifact must be, and the
# executables whose --build-info must report the manifest's version and
# commit. Member paths are relative to the extracted artifact root.
# PROVISIONAL: the names follow G1A-CLOSURE-INVENTORY.md section 6; each lane's
# PKG-<component>.md report fixes the final member list.
COMPONENTS = {
    'nq': {'lane': 'NQ-P', 'kind': 'deb', 'executables': {
        '/usr/bin/nq': 'elf', '/usr/lib/nq/helpers/nq-host-helper': 'elf'}},
    'maude': {'lane': 'C', 'kind': 'tar', 'executables': {
        'lib/validator.pyz': 'pyz', 'lib/executor.pyz': 'pyz', 'lib/maude-plan.pyz': 'pyz'}},
    'pulse': {'lane': 'D', 'kind': 'tar', 'executables': {
        'bin/pulse-nq-load-support': 'elf'}},
    'nightshift': {'lane': 'D', 'kind': 'tar', 'executables': {
        'bin/nightshift': 'elf', 'bin/nightshift-foreman': 'elf',
        'bin/nightshift-observation-resolver': 'elf'}},
    'ag': {'lane': 'A', 'kind': 'tar', 'executables': {
        'bin/ag-loopctl': 'elf', 'bin/ag-standing-resolver': 'elf'}},
    'docket': {'lane': 'B', 'kind': 'tar', 'executables': {
        'bin/docket': 'elf', 'bin/docket-local-standing-resolver': 'elf'}},
    'switchyard': {'lane': 'E', 'kind': 'tar', 'executables': {
        'bin/switchyard-provider-runner': 'script', 'bin/switchyard-review-verifier': 'script'}},
    # The codex fork cannot grow --build-info without moving the commit that
    # Switchyard pins (FINAL_CODEX_SOURCE_HEAD), so its identity comes from
    # the artifact's build-info.json, which binds the executable's digest.
    'app-server': {'lane': 'E', 'kind': 'tar', 'executables': {
        'bin/codex-app-server': 'receipt'}},
    'cohort-kit': {'lane': 'F', 'kind': 'tar', 'executables': {}},
}

# The only cohorts this driver release will set up. Each entry binds every
# required component to the exact (package version, source commit) that was
# qualified together. A manifest that differs in any component refuses. The
# artifact digest is bound by the manifest and checked against the bytes.
# All values are PENDING until the lanes publish artifacts and the cohort
# checkpoint qualifies them together; with PENDING entries every real
# manifest refuses (fail closed).
QUALIFIED_COHORTS = {
    PROFILE: {
        'alpha-exit-rc': {name: {'package_version': PENDING, 'source_commit': PENDING}
                          for name in COMPONENTS},
    },
}

REVIEW_ROUTES = {
    # Real provider: operator-supplied credential placed by the operator.
    'real': {'reviewer_id_suffix': 'independent-reviewer', 'codex_home': 'codex-home-real'},
    # Labelled fixture: qualifies install, wiring, custody, authority and
    # effect; never review independence.
    'fixture-review': {'reviewer_id': 'fixture-deterministic-reviewer-not-independent',
                       'codex_home': 'codex-home-fixture-review'},
}


class Refusal(Exception):
    """A fail-closed stop with a stable code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f'{code}: {detail}')
        self.code = code
        self.detail = detail


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def sha256_file(path: Path) -> str:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Refusal('artifact.not_regular', str(path))
        return 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()


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
            'manifest_sha256': 'sha256:' + hashlib.sha256(raw).hexdigest()}


def _no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError('duplicate JSON key')
    return dict(pairs)


def check_cohort_pins(manifest: dict, qualified: dict | None = None) -> str:
    """Return the name of the qualified cohort the manifest matches, or refuse.

    Compatibility is exact equality with one qualified cohort, component by
    component. There are no ranges, no "newer is fine" and no partial match.
    """
    table = (QUALIFIED_COHORTS if qualified is None else qualified).get(manifest['profile'], {})
    mismatches = {}
    for name, pins in sorted(table.items()):
        if any(PENDING in (pin['package_version'], pin['source_commit']) for pin in pins.values()):
            mismatches[name] = 'qualified cohort pins are still PENDING'
            continue
        if set(pins) != set(manifest['components']):
            mismatches[name] = 'component set differs'
            continue
        differ = [component for component, pin in sorted(pins.items())
                  if (manifest['components'][component]['package_version'], manifest['components'][component]['source_commit'])
                  != (pin['package_version'], pin['source_commit'])]
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


def safe_extract(archive: Path, destination: Path) -> list[str]:
    """Extract a release tarball: regular files and directories only, no escapes."""
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
        try:
            destination.mkdir(mode=0o755, parents=False, exist_ok=False)
        except FileExistsError:
            raise Refusal('artifact.destination_exists', str(destination)) from None
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(mode=0o755, parents=True, exist_ok=True)
                continue
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            source = tar.extractfile(member)
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o755 if member.mode & 0o111 else 0o644)
            with os.fdopen(fd, 'wb') as out:
                shutil.copyfileobj(source, out)
                out.flush()
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
    if info.get('debug_assertions') is True or info.get('profile') in ('debug', 'dev'):
        raise Refusal('build_info.debug_build', f'{component} {program}: release builds only')
    return observed


def check_receipt_identity(component: str, root: Path, relative: str, pin: dict) -> dict:
    """Identity for an executable that cannot report build info itself.

    `<root>/build-info.json` is one JSON line with component, version,
    source_commit and `executables: {relative path: sha256:<hex>}`.
    """
    path = root / 'build-info.json'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        info = parse_build_info(stream.read(1024 * 1024))
    observed = check_build_info(component, relative, info, pin)
    listed = info.get('executables')
    if not isinstance(listed, dict) or listed.get(relative) != sha256_file(root / relative):
        raise Refusal('build_info.executable_digest', f'{component} {relative}: digest not bound by build-info.json')
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

    def write(self, name: str, value) -> Path:
        path = self.run / name
        raw = value if isinstance(value, bytes) else canonical(value) + b'\n'
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        with os.fdopen(fd, 'wb') as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        return path

    def call(self, label: str, argv: list, *, env: dict | None = None, timeout: int = 120,
             stdin: bytes | None = None, check: bool = True) -> subprocess.CompletedProcess:
        """Run one child with an explicit environment; retain argv, output and exit."""
        self.sequence += 1
        name = f'{self.sequence:03d}-{label}'
        argv = [str(item) for item in argv]
        environment = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'} if env is None else env
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
                                             'stdout_sha256': 'sha256:' + hashlib.sha256(done.stdout).hexdigest()})
        if check and done.returncode != 0:
            raise Refusal('child.failed', f'{label} exited {done.returncode}; see {self.run / (name + ".stderr")}')
        return done


def host_facts() -> dict:
    facts = {'hostname': socket.gethostname(), 'python': sys.version.split()[0],
             'python_executable': sys.executable, 'euid': os.geteuid()}
    try:
        release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
        facts['os'] = f'{release.get("ID", "").strip(chr(34))}:{release.get("VERSION_ID", "").strip(chr(34))}'
    except OSError:
        facts['os'] = None
    for label, path in (('python311', PYTHON), ('openssl', OPENSSL)):
        facts[label + '_sha256'] = sha256_file(path) if path.exists() else None
    return facts


def require_host(facts: dict) -> None:
    if facts['os'] != 'debian:12':
        raise Refusal('host.unsupported', f'Debian 12 required, found {facts["os"]}')
    if facts['python311_sha256'] is None or facts['openssl_sha256'] is None:
        raise Refusal('host.missing_tool', 'python3.11 and openssl are required')
    if facts['euid'] != 0:
        raise Refusal('host.not_root', 'install, init, review and accept run as root')
    for tool in ('systemd-run', 'setpriv', 'dpkg', 'useradd'):
        if shutil.which(tool, path='/usr/sbin:/usr/bin:/sbin:/bin') is None:
            raise Refusal('host.missing_tool', tool)


# ------------------------------------------------------------------ commands

def cohort_paths(cohort: str) -> dict:
    if not COHORT_ID.fullmatch(cohort):
        raise Refusal('cohort.id', 'lowercase letters, digits and hyphens, 3-40 characters')
    install = INSTALL_ROOT / cohort
    state = STATE_ROOT / cohort
    return {'install': install, 'state': state, 'records': state / 'driver',
            'keys': state / 'keys', 'plan': state / 'plan', 'scratch': state / 'scratch',
            'ports': state / 'ports', 'owner': state / 'owner', 'deployment': state / 'deployment',
            'observation': state / 'observation', 'review': state / 'review', 'runs': state / 'runs'}


def read_manifest(path: Path) -> dict:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise Refusal('manifest.size', 'manifest exceeds 1 MiB')
    return load_manifest(raw)


def cmd_verify_manifest(args) -> dict:
    manifest = read_manifest(args.manifest)
    cohort = check_cohort_pins(manifest)
    located = locate_artifacts(manifest, args.artifacts)
    return {'result': 'verified', 'qualified_cohort': cohort, 'manifest_sha256': manifest['manifest_sha256'],
            'artifacts': {name: path.name for name, path in located.items()}, 'writes': 0}


def cmd_install(args) -> dict:
    facts = host_facts()
    require_host(facts)
    manifest = read_manifest(args.manifest)
    qualified = check_cohort_pins(manifest)
    located = locate_artifacts(manifest, args.artifacts)
    paths = cohort_paths(args.cohort)
    if paths['install'].exists() or paths['state'].exists():
        raise Refusal('cohort.exists', f'{args.cohort} already has install or state; use a fresh cohort id')
    INSTALL_ROOT.mkdir(mode=0o755, parents=True, exist_ok=True)
    STATE_ROOT.mkdir(mode=0o711, parents=True, exist_ok=True)
    paths['install'].mkdir(mode=0o755)
    records = Records(paths['install'] / 'install-records', 'install')
    records.write('host.json', facts)
    records.write('manifest.json', manifest)
    identities = {}
    for name, artifact in sorted(located.items()):
        pin = manifest['components'][name]
        if COMPONENTS[name]['kind'] == 'deb':
            records.call(f'dpkg-install-{name}', ['dpkg', '--install', artifact], timeout=300)
            root = Path('/')
        else:
            members = safe_extract(artifact, paths['install'] / name)
            records.write(f'members-{name}.json', members)
            root = artifact_root(paths['install'] / name)
        for relative, runner in sorted(COMPONENTS[name]['executables'].items()):
            program = root / relative.lstrip('/')
            if runner == 'receipt':
                observed = check_receipt_identity(name, root, relative, pin)
            else:
                argv = {'elf': [program], 'script': [program], 'pyz': [PYTHON, '-I', program]}[runner]
                done = records.call(f'build-info-{name}-{program.name}', argv + ['--build-info'], timeout=30)
                observed = check_build_info(name, str(program), parse_build_info(done.stdout), pin)
            identities[str(program)] = {'component': name, 'sha256': sha256_file(program), **observed}
    records.write('installed-identities.json', identities)
    return {'result': 'installed', 'cohort': args.cohort, 'qualified_cohort': qualified,
            'install_root': str(paths['install']), 'executables': len(identities), 'records': str(records.run)}


def synthetic_identities(cohort: str, route: str) -> dict:
    """Free-form identity strings, consistent across Docket, AG and the caller."""
    spec = REVIEW_ROUTES[route]
    return {
        'operator': f'cohort-{cohort}-operator',
        'issuer_principal': f'cohort-{cohort}-ag-issuer',
        'issuer_key_id': f'cohort-{cohort}-ag-issuer-k1',
        'standing_resolver_id': f'cohort-{cohort}-ag-standing/v1',
        'author_principal': f'cohort-{cohort}-author',
        'reviewer_id': spec.get('reviewer_id') or f'cohort-{cohort}-{spec["reviewer_id_suffix"]}',
        'pulse_producer_id': f'cohort-{cohort}-pulse-producer',
        'occurrence': str(uuid.uuid4()),
        'review_route': route,
    }


def codex_home_files(route: str, fixture_port: int | None) -> dict:
    """Cohort-owned codex home contents. Never a copied or shared home.

    The real route gets config only: the operator places auth.json themselves
    (documented step); this driver never reads, writes or copies a credential.
    The fixture route gets a loopback base URL and a generated dummy key.
    UNVERIFIED until lane E's zero-cost spike (G1A section 4).
    """
    if route == 'real':
        return {'config.toml': b'# cohort-owned codex home, real provider route\n'}
    if fixture_port is None or not 1024 <= fixture_port <= 65535:
        raise Refusal('fixture.port', 'fixture-review needs --fixture-port on 127.0.0.1')
    dummy = 'fixture-not-a-credential-' + secrets.token_hex(16)
    return {'config.toml': f'openai_base_url = "http://127.0.0.1:{fixture_port}/v1"\n'.encode(),
            'auth.json': canonical({'OPENAI_API_KEY': dummy}) + b'\n'}


def cmd_init(args) -> dict:
    facts = host_facts()
    require_host(facts)
    paths = cohort_paths(args.cohort)
    if not (paths['install'] / 'install-records').is_dir():
        raise Refusal('cohort.not_installed', args.cohort)
    if paths['state'].exists():
        raise Refusal('cohort.exists', f'{paths["state"]} exists; init runs once per cohort')
    # 1. Account and directories. The state root is private to the cohort account.
    records = Records(paths['install'] / 'init-records', 'init')
    if subprocess.run(['getent', 'passwd', COHORT_ACCOUNT], stdout=subprocess.DEVNULL).returncode != 0:
        records.call('account', ['useradd', '--system', '--home-dir', '/var/lib/constellation',
                                 '--no-create-home', '--shell', '/usr/sbin/nologin', COHORT_ACCOUNT])
    paths['state'].mkdir(mode=0o700)
    identities = synthetic_identities(args.cohort, args.review_route)
    records.write('identities.json', identities)
    home = paths['state'] / REVIEW_ROUTES[args.review_route]['codex_home']
    home.mkdir(mode=0o700)
    for name, raw in codex_home_files(args.review_route, args.fixture_port).items():
        fd = os.open(home / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as out:
            out.write(raw)
    records.write('codex-home.json', {'path': str(home), 'route': args.review_route,
                                      'files': sorted(os.listdir(home)), 'credential_read': False})
    # 2-5. Plan, ports, owner, AG seal/verify/init and NQ config/admission.
    # Each step is the kit helper or the component's own command, called
    # with plain argv. See F-SETUP-DRIVER-DESIGN.md "Start order".
    raise Refusal('pending.component_artifacts',
                  'plan (lane C maude-plan.pyz), ports (lanes A, B, D), owner and AG seal/verify/init '
                  '(lane A), NQ config and watcher admission (NQ-P) are not wired yet; '
                  f'account, identities and codex home were written under {paths["state"]}')


def cmd_review(args) -> dict:
    cohort_paths(args.cohort)
    raise Refusal('pending.component_artifacts',
                  'review runs NQ acquisition, Pulse produce/ingest, seal_admission, Foreman input sealing, '
                  'enroll_caller and reviewed_action --review-only in one systemd-run unit; needs lanes C, D, E, NQ-P')


def cmd_accept(args) -> dict:
    cohort_paths(args.cohort)
    if not DIGEST.fullmatch(args.candidate_sha256 or ''):
        raise Refusal('accept.candidate', 'name the exact record-review-input digest as sha256:<64 hex>')
    raise Refusal('pending.component_artifacts',
                  'accept runs continue_reviewed_action --accept-and-execute in one systemd-run unit; needs lanes A, B, C')


def cmd_status(args) -> dict:
    paths = cohort_paths(args.cohort)
    runs = {}
    for group in ('install-records', 'init-records'):
        root = paths['install'] / group
        runs[group] = sorted(p.name for p in root.iterdir()) if root.is_dir() else []
    return {'result': 'status', 'cohort': args.cohort, 'installed': paths['install'].is_dir(),
            'state_present': paths['state'].exists(), 'driver_runs': runs,
            'native_inspection': 'PENDING: reviewed_action.py --inspect once the cohort is initialized'}


def cmd_evidence(args) -> dict:
    cohort_paths(args.cohort)
    raise Refusal('pending.component_artifacts',
                  'evidence bundles driver records, caller records and sqlite backups of the AG, Nightshift, '
                  'Foreman, Switchyard and Docket stores; the join check needs the lane A/B verifier')


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
    for name in ('review', 'status', 'evidence'):
        sub.add_parser(name).add_argument('--cohort', required=True)
    p = sub.add_parser('accept')
    p.add_argument('--cohort', required=True)
    p.add_argument('--candidate-sha256', required=True,
                   help='the exact record-review-input.json digest the operator inspected and accepts')
    return top


COMMANDS = {'verify-manifest': cmd_verify_manifest, 'install': cmd_install, 'init': cmd_init,
            'review': cmd_review, 'accept': cmd_accept, 'status': cmd_status, 'evidence': cmd_evidence}


def main(argv=None) -> int:
    args = parser().parse_args(argv)
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
