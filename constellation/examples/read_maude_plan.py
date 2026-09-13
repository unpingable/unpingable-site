#!/usr/bin/env python3
"""Read a caller-selected Maude Plan Core draft through its supported CLI."""
from __future__ import annotations

import argparse
import json
import os
import selectors
import subprocess
import time
from pathlib import Path

MAX_OUTPUT = 1024 * 1024
TIMEOUT_SECONDS = 10
REVISION_SCHEMA = "maude.plan-revision/v1"
PROJECTION_SCHEMA = "maude.plan-lifecycle-projection/v1"
CHECK_SUMMARIES = {
    "never_checked", "current_pass", "current_findings", "historical_digest",
    "retired_checker_or_rules",
}


class InspectionError(ValueError):
    pass


def invoke(program: str, store: Path, *command: str) -> object:
    try:
        process = subprocess.Popen(
            [program, "--store", str(store), *command], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise InspectionError("program_unavailable") from error
    assert process.stdout is not None and process.stderr is not None
    buffers = {process.stdout: bytearray(), process.stderr: bytearray()}
    open_streams = set(buffers)
    selector = selectors.DefaultSelector()
    for stream in buffers:
        selector.register(stream, selectors.EVENT_READ)
    deadline = time.monotonic() + TIMEOUT_SECONDS
    try:
        while open_streams:
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                raise InspectionError("timeout")
            for key, _ in selector.select(timeout):
                stream = key.fileobj
                chunk = os.read(stream.fileno(), 65536)
                if not chunk:
                    selector.unregister(stream)
                    open_streams.remove(stream)
                    continue
                buffers[stream].extend(chunk)
                if len(buffers[stream]) > MAX_OUTPUT:
                    raise InspectionError("output_too_large")
    except InspectionError:
        process.kill()
        process.wait()
        raise
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        process.kill()
        process.wait()
        raise InspectionError("timeout")
    try:
        status = process.wait(timeout=remaining)
    except subprocess.TimeoutExpired as error:
        process.kill()
        process.wait()
        raise InspectionError("timeout") from error
    output = bytes(buffers[process.stdout])
    if status:
        raise InspectionError("command_refused")
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise InspectionError("invalid_json") from error


def revision(value: object, draft_id: str) -> dict[str, object]:
    if not isinstance(value, dict) or value.get("schema") != REVISION_SCHEMA:
        raise InspectionError("invalid_schema")
    if value.get("draft_id") != draft_id:
        raise InspectionError("draft_id_mismatch")
    if not all(isinstance(value.get(field), str) and value[field]
               for field in ("revision_id", "plan_digest")):
        raise InspectionError("invalid_schema")
    return value


def inspect(program: str, store: Path, draft_id: str) -> dict[str, object]:
    projection = invoke(program, store, "--read-only", "inspect", draft_id)
    if not isinstance(projection, dict) or projection.get("schema") != PROJECTION_SCHEMA:
        raise InspectionError("invalid_schema")
    current = revision(projection.get("current_revision"), draft_id)
    if projection.get("check_summary") not in CHECK_SUMMARIES:
        raise InspectionError("invalid_schema")
    lock_id = projection.get("last_lock_receipt_id")
    if lock_id is not None and (not isinstance(lock_id, str) or not lock_id):
        raise InspectionError("invalid_schema")
    return {"availability": "available", "draft_id": draft_id,
            "revision_id": current["revision_id"], "plan_digest": current["plan_digest"],
            "check_summary": projection["check_summary"], "last_lock_receipt_id": lock_id}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--maude-plan", required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--draft-id", required=True)
    args = parser.parse_args()
    try:
        value = inspect(args.maude_plan, args.store, args.draft_id)
    except InspectionError as error:
        value = {"availability": "unavailable", "reason": str(error),
                 "draft_id": args.draft_id}
    print(json.dumps({"schema": "constellation.maude-plan-inspection/v1", **value},
                     sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
