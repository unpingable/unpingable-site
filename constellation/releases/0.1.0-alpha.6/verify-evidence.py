#!/usr/bin/env python3
"""Verify the frozen public Recipe B evidence without repeating its effect."""

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys


EXPECTED = {
    "objective.json": "03496495b2d673fb4a3c58e234cb32c44e9b7d9395cccfc5a21e0804b149f1fb",
    "objective-check.json": "63716876a4e8136b3698559a52c0bd2973c3e4969e9b083c5408e354331c4f51",
    "post-observation.json": "e475da3a037a028c4160787f67717deaab9c64ecc77df121207bd48fc59e9e10",
    "reviewed-action.json": "622ef60f1cdf364a0c793f4b1e20d837ba50d49eb6a2946a2b85db3fa7197cf2"
}


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = EXPECTED[path.name]
    if value != expected:
        raise SystemExit(f"{path.name}: digest mismatch: {value}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ag-checkout", required=True, type=pathlib.Path)
    parser.add_argument("--evidence", type=pathlib.Path,
                        default=pathlib.Path(__file__).with_name("evidence"))
    args = parser.parse_args()
    for name in EXPECTED:
        digest(args.evidence / name)

    checker = args.ag_checkout / "examples" / "phosphor-objective-occurrence-check"
    command = [
        sys.executable, str(checker),
        "--input", str(args.evidence / "objective.json"),
        "--campaign-id", "sha256:1725b2a0a10f5fc6c95150820ef94ba09421b60814688db879f14e1f7dd01142",
        "--occurrence-id", "b0040000-0000-4000-8000-000000000004",
        "--proposal-id", "sha256:0313f71d68535cbd465987009a87cafbd4835275bb4d66192f86ef214f3149e0",
        "--exact-work-id", "sha256:0ab2a9e8c3686102dbd9ab483ae843127424e4d99ffc57d754f2f4df53252036",
        "--plan-digest", "sha256:575551994f711bf58706ff6ef89a52878684d0e10d05336342873797fc810c03",
        "--issuance-id", "sha256:2f33d498a0753457402c2afe99ec05da25dd9c425a0f53adddc01fed640013d9",
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    observed = json.loads(completed.stdout)
    retained = json.loads((args.evidence / "objective-check.json").read_text())
    if observed != retained:
        raise SystemExit("public checker output differs from retained qualification")
    if observed["objective_completion"] != "not_determined":
        raise SystemExit("objective completion was incorrectly promoted")
    if observed["authority_for_another_action"] != "none":
        raise SystemExit("frozen evidence unexpectedly grants continuation authority")

    mismatch = list(command)
    mismatch[mismatch.index("--plan-digest") + 1] = "sha256:" + "0" * 64
    refused = subprocess.run(mismatch, capture_output=True, text=True)
    if refused.returncode == 0:
        raise SystemExit("mismatched plan digest did not refuse")
    print(json.dumps({
        "schema": "constellation.recipe-b-public-evidence-check/v1",
        "result": "passed",
        "objective_sha256": "sha256:" + EXPECTED["objective.json"],
        "projection_correspondence": observed["projection_correspondence"],
        "objective_completion": observed["objective_completion"],
        "authority_for_another_action": observed["authority_for_another_action"],
        "mismatched_plan_digest": "refused"
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
