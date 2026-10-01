"""Strict, bounded JSON loading with duplicate-key and stable-file refusal."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Any

MAX_CONTRACT_BYTES = 1_048_576


class ContractParseError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractParseError("PARSE_DUPLICATE_KEY", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ContractParseError("PARSE_NONFINITE_NUMBER", f"non-finite JSON number is not permitted: {token}")


def loads_contract(raw: bytes | str) -> Any:
    if isinstance(raw, str):
        encoded = raw.encode("utf-8")
        text = raw
    else:
        encoded = raw
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ContractParseError("PARSE_UTF8", "contract is not UTF-8") from error
    if len(encoded) > MAX_CONTRACT_BYTES:
        raise ContractParseError("PARSE_SIZE_LIMIT", "contract exceeds 1 MiB")
    try:
        return json.loads(text, object_pairs_hook=_object_pairs, parse_constant=_reject_nonfinite)
    except ContractParseError:
        raise
    except json.JSONDecodeError as error:
        raise ContractParseError("PARSE_JSON", f"invalid JSON at line {error.lineno}, column {error.colno}") from error


def load_contract(path: str | Path) -> Any:
    """Read one exact regular file without following a final symlink."""
    candidate = Path(path)
    try:
        before = candidate.lstat()
    except OSError as error:
        raise ContractParseError("READ_UNAVAILABLE", f"contract is unavailable: {candidate}") from error
    if not stat.S_ISREG(before.st_mode):
        raise ContractParseError("READ_NOT_REGULAR", "contract must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as error:
        raise ContractParseError("READ_OPEN", "contract could not be opened without following links") from error
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ContractParseError("READ_PATH_REPLACED", "contract pathname changed before open")
        if opened.st_size > MAX_CONTRACT_BYTES:
            raise ContractParseError("PARSE_SIZE_LIMIT", "contract exceeds 1 MiB")
        chunks: list[bytes] = []
        remaining = MAX_CONTRACT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
        if len(b"".join(chunks)) > MAX_CONTRACT_BYTES:
            raise ContractParseError("PARSE_SIZE_LIMIT", "contract exceeds 1 MiB")
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
        if any(getattr(opened, field) != getattr(after, field) for field in stable_fields):
            raise ContractParseError("READ_CONTENT_CHANGED", "contract changed during read")
    finally:
        os.close(descriptor)
    return loads_contract(b"".join(chunks))
