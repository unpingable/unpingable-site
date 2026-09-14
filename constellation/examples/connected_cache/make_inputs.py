#!/usr/bin/env python3
"""Make the two closed input documents consumed by Maude's public example."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import uuid

MAUDE_REVISION = "0d5b6c91102b1088818d0493c687f9f23db7684e"
SOURCE_REVISIONS = {
    "nq_cli": "d3089a9787a27c50faf1e3f393a88f8e64bd412d",
    "nq_helpers": "d3089a9787a27c50faf1e3f393a88f8e64bd412d",
    "nightshift": "2db475b0bb8be5e3afa7ac6c95e2ab1f73a9ceb4",
    "ag": "5c8b22b77193798f25298b02758ac3caa3a8fe24",
    "docket": "c49ad8d0f26fb2a13b9dbafdde84d7abfe1f867b",
    "pulse_integration": "d91b214cd22afd5585fcd259d22463d08d606b58",
}
PROGRAMS = {
    "nq": "nq", "nq_host_helper": "nq-host-helper",
    "nq_result_helper": "nq-synthetic-cache-result-helper",
    "nightshift": "nightshift",
    "nightshift_observation_resolver": "nightshift-observation-resolver",
    "ag": "ag-loopctl", "ag_standing_resolver": "ag-standing-resolver",
    "docket": "docket", "pulse": "pulse-nq-load-support",
    "docker": "docker", "openssl": "openssl",
}
MAX_FILE_BYTES = 128 * 1024 * 1024


def digest(path: Path) -> str:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError(f"not a regular, non-symlink file: {path}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            raise ValueError(f"file is not a bounded regular file: {path}")
        value = hashlib.sha256()
        total = 0
        while block := os.read(descriptor, min(1024 * 1024, MAX_FILE_BYTES + 1 - total)):
            total += len(block)
            if total > MAX_FILE_BYTES:
                raise ValueError(f"file exceeds the 128 MiB input limit: {path}")
            value.update(block)
        after = os.fstat(descriptor)
        stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                  before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size,
                                          after.st_mtime_ns, after.st_ctime_ns)
        if not stable or total != before.st_size:
            raise ValueError(f"file changed while it was measured: {path}")
        return value.hexdigest()
    finally:
        os.close(descriptor)


def write_new(path: Path, value: dict) -> None:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(data)


def source_revision(source: Path) -> str:
    environment = {"PATH": "/usr/bin:/bin", "GIT_OPTIONAL_LOCKS": "0"}
    def git(*arguments: str) -> str:
        try:
            result = subprocess.run(
                ["/usr/bin/git", "-C", str(source), *arguments], env=environment,
                capture_output=True, text=True, timeout=8, check=True,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError("public source checkout could not be verified") from error
        return result.stdout.strip()
    revision = git("rev-parse", "HEAD")
    if git("status", "--porcelain=v1"):
        raise ValueError("Maude checkout must be clean")
    return revision


def make(args: argparse.Namespace) -> tuple[dict, dict]:
    if source_revision(args.maude_source) != MAUDE_REVISION:
        raise ValueError("Maude checkout is not the tested public revision")
    sources = {
        "nq_cli": args.nq_source, "nq_helpers": args.nq_source,
        "nightshift": args.nightshift_source, "ag": args.ag_source,
        "docket": args.docket_source, "pulse_integration": args.pulse_source,
    }
    if any(source_revision(sources[name]) != revision
           for name, revision in SOURCE_REVISIONS.items()):
        raise ValueError("component checkout differs from the tested source cohort")
    if not args.label or len(args.label) > 64 or any(
            c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.label):
        raise ValueError("label must contain lowercase ASCII letters, digits, or hyphens")
    if not args.role_digest.startswith("sha256:") or len(args.role_digest) != 71 \
            or any(c not in "0123456789abcdef" for c in args.role_digest[7:]):
        raise ValueError("role digest must be sha256 plus 64 lowercase hexadecimal characters")
    pins = {name: {"filename": filename, "sha256": digest(args.program_dir / filename)}
            for name, filename in PROGRAMS.items()}
    install = {
        "schema": "maude.connected-cache-example-install/v1",
        "maude_source_revision": MAUDE_REVISION,
        "maude_build_plan_sha256": digest(args.maude_source / "qualification/synthetic_cache/build_plan.py"),
        "maude_executor_sha256": digest(args.maude_source / "qualification/synthetic_cache/local_compose_executor.py"),
        "programs": pins, "python_sha256": digest(args.python),
        "pulse_launcher_sealer_sha256": digest(args.pulse_launcher_sealer),
        "source_revisions": SOURCE_REVISIONS,
    }
    seed = uuid.uuid4()
    identity = lambda name: "sha256:" + hashlib.sha256(f"{seed}:{args.label}:{name}".encode()).hexdigest()
    q_occurrence, t_occurrence = str(uuid.uuid4()), str(uuid.uuid4())
    profile = {
        "schema": "maude.connected-cache-example-profile/v1",
        "identities": {
            "campaign_id": identity("campaign"), "program_id": identity("program"),
            "subject_digest": identity("subject"), "qualification_occurrence_id": q_occurrence,
            "successor_occurrence_id": t_occurrence, "watcher_instance_id": f"cache-host-{args.label}",
            "local_successor_acquisition_id": f"acquisition:cache-successor-{args.label}",
            "runtime_id": f"nightshift:cache-{args.label}", "generation": f"generation:cache-{args.label}",
            "configuration_version": f"configuration:cache-{args.label}",
            "role_id": "nightshift-role:cache-bootstrap-host", "role_version": 1,
            "role_digest": args.role_digest, "qualification_schedule_id": f"schedule:q-{args.label}",
            "successor_schedule_id": f"schedule:t-{args.label}",
            "qualification_attempt_id": f"attempt:q-{args.label}",
            "successor_attempt_id": f"attempt:t-{args.label}", "scheduler_clock_id": "clock:local-realtime",
            "qualification_pulse_acquisition_id": f"acquisition:pulse-q-{args.label}",
            "successor_pulse_acquisition_id": f"acquisition:pulse-t-{args.label}",
        },
        "nq": {"nq_subject": f"host:cache-{args.label}", "nq_scope_id": f"cache-{args.label}"},
        "runtime": {"image": "python:3.13-alpine@sha256:46ee549c88617e9bc8acb843a326f1a5c0fa5608d7f9703509efe6d53b55f318",
                    "docker_client_version": "29.1.3", "docker_server_version": "29.1.3",
                    "compose_version": "5.0.0", "project": "maude-cache-birthday", "front_port": 8080},
        "governance": {"profile_label": "synthetic-standing-cache-example",
                       "observation_resolver_id": "nightshift-observation-resolver/v1",
                       "standing_resolver_id": "ag-standing-resolver/integration-v1",
                       "issuer_principal": f"synthetic-cache-issuer:{args.label}",
                       "issuer_key_id": f"synthetic-cache-issuer-key:{args.label}",
                       "observation_ttl_ms": 120000, "standing_ttl_ms": 60000,
                       "docket_standing_ttl_ms": 60000},
    }
    return install, profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maude-source", type=Path, required=True)
    parser.add_argument("--nq-source", type=Path, required=True)
    parser.add_argument("--nightshift-source", type=Path, required=True)
    parser.add_argument("--ag-source", type=Path, required=True)
    parser.add_argument("--docket-source", type=Path, required=True)
    parser.add_argument("--pulse-source", type=Path, required=True)
    parser.add_argument("--program-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--pulse-launcher-sealer", type=Path, required=True)
    parser.add_argument("--role-digest", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if not all(path.is_absolute() for path in
               (args.output, args.maude_source, args.nq_source, args.nightshift_source,
                args.ag_source, args.docket_source, args.pulse_source, args.program_dir,
                args.python, args.pulse_launcher_sealer)):
        raise ValueError("all paths must be absolute")
    install, profile = make(args)
    args.output.mkdir(mode=0o700)
    write_new(args.output / "connected-cache-install.json", install)
    write_new(args.output / "connected-cache-profile.json", profile)


if __name__ == "__main__":
    main()
