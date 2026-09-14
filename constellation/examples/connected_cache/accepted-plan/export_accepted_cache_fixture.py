#!/usr/bin/env python3
"""Validate and copy one portable accepted-cache input pair without mutation."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from maude.plan.store import CheckApplicability, DraftStore

MAX_BUNDLE = 1024 * 1024
MAX_STORE = 64 * 1024 * 1024
BUNDLE_SCHEMA = "maude.accepted-cache-plan-bundle/v1"
MANIFEST_SCHEMA = "maude.public-accepted-cache-fixture/v1"
REVIEWED_BUNDLE_SHA256 = "1fa0f621556484c916da8127083bf42e2a54646954de096a872d39d7d7abb441"
REVIEWED_STORE_SHA256 = "a9ceed5a625dcbc8708301b4aaac58c2ef0a4b394127b7cae953316e0503f4de"


def read_regular(path: Path, limit: int) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError(f"input is not a bounded regular file: {path}")
        data = b""
        while chunk := os.read(fd, min(1024 * 1024, limit + 1 - len(data))):
            data += chunk
            if len(data) > limit:
                raise ValueError(f"input exceeds its bound: {path}")
        after = os.fstat(fd)
        identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
        if identity(before) != identity(after) or len(data) != before.st_size:
            raise ValueError(f"input changed while read: {path}")
        return data
    finally:
        os.close(fd)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_hash(name: str, value: str) -> None:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")


def write_new(path: Path, data: bytes, mode: int = 0o644) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def export(args: argparse.Namespace) -> dict:
    for name in ("bundle_sha256", "store_sha256"):
        require_hash(name, getattr(args, name))
    if not all(p.is_absolute() for p in (args.bundle, args.store, args.output)):
        raise ValueError("bundle, store and output paths must be absolute")
    if args.bundle_sha256 != REVIEWED_BUNDLE_SHA256 or args.store_sha256 != REVIEWED_STORE_SHA256:
        raise ValueError("this exporter supports only the exact independently reviewed fixture hashes")
    if Path(str(args.store) + "-wal").exists() or Path(str(args.store) + "-shm").exists():
        raise ValueError("accepted store must be quiescent without WAL/SHM sidecars")

    bundle_bytes = read_regular(args.bundle, MAX_BUNDLE)
    store_bytes = read_regular(args.store, MAX_STORE)
    if sha256(bundle_bytes) != args.bundle_sha256:
        raise ValueError("accepted bundle differs from its expected SHA-256")
    if sha256(store_bytes) != args.store_sha256:
        raise ValueError("accepted store differs from its expected SHA-256")
    bundle = json.loads(bundle_bytes)
    if set(bundle) != {"schema", "draft_id", "plan_digest", "lock_id", "acceptance_ref"} \
            or bundle["schema"] != BUNDLE_SCHEMA:
        raise ValueError("accepted bundle is not the closed v1 schema")
    if bundle["draft_id"] != args.draft_id or bundle["plan_digest"] != args.plan_digest \
            or bundle["lock_id"] != args.lock_id or bundle["acceptance_ref"] != args.acceptance_ref:
        raise ValueError("accepted bundle differs from the selected public fixture identity")

    # Validate an immutable private snapshot of the measured bytes. Opening the
    # caller pathname here would create a pathname-replacement interval between
    # measurement and Plan Core validation.
    with tempfile.TemporaryDirectory(prefix="accepted-cache-fixture-") as temporary:
        snapshot = Path(temporary) / "accepted-plan.sqlite"
        write_new(snapshot, store_bytes, 0o600)
        store = DraftStore.open_readonly(snapshot)
        projection = store.projection(args.draft_id)
    if projection.current.plan_digest != args.plan_digest:
        raise ValueError("current Plan Core revision differs from accepted plan digest")
    if projection.check_summary != CheckApplicability.CURRENT_PASS:
        raise ValueError("accepted Plan Core revision lacks a current passing check")
    locks = [item.receipt for item in projection.locks if item.receipt.lock_id == args.lock_id]
    if len(locks) != 1 or locks[0].plan_digest != args.plan_digest \
            or locks[0].revision_id != projection.current.revision_id:
        raise ValueError("accepted lock does not bind the current Plan Core revision")

    # Sidecar absence is a required caller assertion of operator-established
    # quiescence, not proof that no concurrent writer exists. Re-read the exact
    # pathname after semantic validation and refuse any observed mutation or
    # replacement before publishing bytes.
    if Path(str(args.store) + "-wal").exists() or Path(str(args.store) + "-shm").exists():
        raise ValueError("accepted store acquired WAL/SHM sidecars during validation")
    if read_regular(args.bundle, MAX_BUNDLE) != bundle_bytes \
            or read_regular(args.store, MAX_STORE) != store_bytes:
        raise ValueError("accepted fixture source changed during validation")

    args.output.mkdir(mode=0o755)
    output_store = args.output / "accepted-plan.sqlite"
    output_bundle = args.output / "accepted-bundle.json"
    write_new(output_store, store_bytes)
    write_new(output_bundle, bundle_bytes)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "accepted_bundle": {"file": output_bundle.name, "sha256": sha256(bundle_bytes)},
        "accepted_store": {"file": output_store.name, "sha256": sha256(store_bytes)},
        "draft_id": args.draft_id,
        "revision_id": projection.current.revision_id,
        "plan_digest": args.plan_digest,
        "lock_id": args.lock_id,
        "applicable_check_receipts": list(locks[0].applicable_check_receipts),
        "acceptance_ref": args.acceptance_ref,
        "acceptance_proof": "opaque_caller_reference_not_authenticated_by_draft_store",
        "authority": "none",
        "effects": False,
        "privacy": "independently reviewed exact fixture hashes: generic synthetic-cache plan/check/lock records only; no credentials, provider bytes, conversation, private paths or runtime-owner records",
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    write_new(args.output / "manifest.json", manifest_bytes)
    return {**manifest, "manifest_sha256": sha256(manifest_bytes)}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "store", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    for name in ("bundle-sha256", "store-sha256", "draft-id", "plan-digest", "lock-id", "acceptance-ref"):
        p.add_argument("--" + name, required=True)
    return p


if __name__ == "__main__":
    print(json.dumps(export(parser().parse_args()), sort_keys=True))
