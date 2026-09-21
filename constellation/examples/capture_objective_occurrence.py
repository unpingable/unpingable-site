#!/usr/bin/env python3
"""Capture one owner-minted Phosphor objective response and check its exact link.

This is deliberately a read-only qualification helper.  The selected Phosphor
process remains responsible for assembling Maude, Nightshift, AG and Docket
owner records; this helper fetches one bounded response, retains it once, and
passes the caller-supplied expected identity tuple to AG's public occurrence
checker.  It never infers an objective verdict, health, a causal relationship,
or authority for another action.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


MAX_BYTES = 2_097_152
MAX_CHECKER_BYTES = 2_097_152
OBJECTIVE_PATH = re.compile(r"/api/v1/objectives/[0-9a-f]{64}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


class RedirectRefused(HTTPRedirectHandler):
    """Keep the one capture on the selected loopback Phosphor process."""

    def redirect_request(self, request, fp, code, message, headers, newurl):  # type: ignore[no-untyped-def]
        raise HTTPError(request.full_url, code, "redirect refused", headers, fp)


def checked_url(value: str) -> str:
    """Accept only one literal loopback objective-detail endpoint."""
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("--url must have a valid loopback port") from error
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "::1"}
        or port is None
        or not OBJECTIVE_PATH.fullmatch(parsed.path)
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("--url must be one exact loopback Phosphor objective endpoint")
    return value


def fetch(url: str) -> bytes:
    """Fetch one bounded response without proxy or redirect traversal."""
    opener = build_opener(ProxyHandler({}), RedirectRefused())
    try:
        with opener.open(Request(url, method="GET"), timeout=12) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}")
            raw = response.read(MAX_BYTES + 1)
    except HTTPError as error:
        raise RuntimeError(f"HTTP {error.code}: {error.reason}") from error
    except URLError as error:
        raise RuntimeError(f"transport failure: {error.reason}") from error
    if not raw:
        raise RuntimeError("Phosphor objective response is empty")
    if len(raw) > MAX_BYTES:
        raise RuntimeError(f"Phosphor response exceeds {MAX_BYTES}-byte bound")
    return raw


def write_new_regular(path: Path, raw: bytes) -> None:
    """Retain the response once; refuse a pre-existing or indirect target."""
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("--output must be an absolute final-non-symlink path")
    parent = path.parent
    parent_status = parent.stat()
    if not stat.S_ISDIR(parent_status.st_mode) or parent.is_symlink():
        raise ValueError("--output parent must be an existing non-symlink directory")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError as error:
        raise ValueError("--output already exists; inspect the existing capture") from error
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        # A partial capture is not a valid retained input. This only owns the
        # just-created campaign output and does not touch any other path.
        path.unlink(missing_ok=True)
        raise


def _read_descriptor(descriptor: int, limit: int) -> bytes:
    parts = []
    remaining = limit + 1
    while remaining:
        part = os.read(descriptor, min(65_536, remaining))
        if not part:
            break
        parts.append(part)
        remaining -= len(part)
    value = b"".join(parts)
    if len(value) > limit:
        raise ValueError("checker exceeds bounded size")
    return value


def sealed_checker(path: Path, expected_digest: str) -> int:
    """Return an executable descriptor containing exactly the checked bytes.

    The public checker is selected by content digest, not by a pathname that a
    concurrent writer could replace after validation.  The returned descriptor
    is passed directly to the child via ``/proc/self/fd``.
    """
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("--checker must be an absolute final-non-symlink path")
    if not DIGEST.fullmatch(expected_digest):
        raise ValueError("--checker-sha256 must be sha256: followed by 64 lowercase hex digits")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode) or not (status.st_mode & stat.S_IXUSR):
            raise ValueError("--checker must be an executable regular file")
        raw = _read_descriptor(descriptor, MAX_CHECKER_BYTES)
    finally:
        os.close(descriptor)
    actual_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual_digest != expected_digest:
        raise ValueError("--checker-sha256 does not match checker bytes")
    sealed = os.memfd_create(
        "constellation-objective-occurrence-check",
        os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
    )
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(sealed, raw[offset:])
        os.fchmod(sealed, 0o700)
        fcntl.fcntl(
            sealed,
            fcntl.F_ADD_SEALS,
            fcntl.F_SEAL_WRITE
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_SEAL,
        )
        os.lseek(sealed, 0, os.SEEK_SET)
        return sealed
    except BaseException:
        os.close(sealed)
        raise


def run_sealed_checker(descriptor: int, input_path: Path, args: argparse.Namespace) -> subprocess.CompletedProcess[str]:
    command = [f"/proc/self/fd/{descriptor}", "--input", str(input_path)]
    for name in ("plan_digest", "campaign_id", "occurrence_id", "proposal_id", "exact_work_id", "issuance_id"):
        command.extend(("--" + name.replace("_", "-"), getattr(args, name)))
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=20, pass_fds=(descriptor,))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--checker-sha256", required=True)
    for name in ("plan-digest", "campaign-id", "occurrence-id", "proposal-id", "exact-work-id", "issuance-id"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    descriptor = None
    try:
        descriptor = sealed_checker(args.checker, args.checker_sha256)
        raw = fetch(checked_url(args.url))
        write_new_regular(args.output, raw)
        completed = run_sealed_checker(descriptor, args.output, args)
        if completed.returncode != 0:
            raise RuntimeError("occurrence checker refused the retained response: " + completed.stderr.strip())
        sys.stdout.write(completed.stdout)
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(
            f"objective occurrence not accepted: {error}. Preserve any retained response and inspect its owner records before another capture."
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


if __name__ == "__main__":
    raise SystemExit(main())
