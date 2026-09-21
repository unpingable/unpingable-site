#!/usr/bin/env python3
"""Accept one exact retained review candidate and continue without redispatch.

This is an operator transition, not a human-attestation generator. The caller
must name the exact candidate digest and run this under a durable manager. It
re-verifies native review custody, records that exact review in AG, obtains the
bounded local Docket grant, and advances the existing occurrence. It never
contacts a model provider or creates a replacement review occurrence.
"""
from __future__ import annotations

import argparse
import base64
import fcntl
import json
import os
from pathlib import Path

from prepare_review_candidate import canonical, digest, read
from prepare_finite_run import prepare
from reviewed_action import Caller, configuration, now, pinned, require


def retained_candidate(config, root, expected_digest):
    require(root.is_absolute() and root.is_dir() and not root.is_symlink(),
            "absolute retained review directory required")
    terminal, terminal_raw = read(root / "terminal.json")
    result = terminal.get("result", {})
    require(terminal.get("exit_code") == 0 and
            result.get("schema") == "constellation.review-only-result/v1" and
            result.get("provider_calls") == 1 and
            all(result.get(key) == 0 for key in
                ("grants", "spends", "docket_attempts", "executor_calls", "effects")),
            "retained review-only terminal differs")
    review_input, review_raw = read(root / "record-review-input.json")
    require(digest(review_raw) == expected_digest,
            "operator acceptance does not name the exact review candidate")
    verification_request, verification_raw = read(root / "verification-request.json")
    permission_input, permission_raw = read(root / "permission-preflight-input.json")
    provider, provider_raw = read(root / "provider-run.json")
    disposition, disposition_raw = read(root / "disposition.json")
    require(provider.get("state") == "PROVIDER_COMPLETED" and
            provider.get("turn_status") == "completed" and
            disposition.get("disposition") == "EXECUTION_ADMITTED" and
            disposition.get("will_retry") is False,
            "retained provider custody is not one completed no-retry occurrence")
    require(review_input.get("review") == verification_request.get("review"),
            "candidate review records disagree")
    binding_id = review_input.get("binding_id")
    require(result.get("binding_id") == binding_id and
            result.get("verification", {}).get("accepted") is True and
            result["verification"].get("binding_id") == binding_id and
            review_input.get("review", {}).get("binding_id") == binding_id and
            review_input["review"].get("verdict") == "accepted" and
            permission_input.get("schema") == "ag.governed-loop.permission-preflight-input/v1" and
            permission_input.get("binding_id") == binding_id and
            disposition.get("dispatch_digest") == review_input["review"].get("dispatch_id") and
            digest(provider["worker_output"].encode("utf-8")) == review_input["review"].get("result_digest"),
            "retained review candidate cross-record binding differs")
    return {
        "review_input": review_input,
        "verification_request": verification_request,
        "permission_input": permission_input,
        "pins": {
            "terminal": digest(terminal_raw),
            "record_review_input": digest(review_raw),
            "verification_request": digest(verification_raw),
            "permission_preflight_input": digest(permission_raw),
            "provider_run": digest(provider_raw),
            "disposition": digest(disposition_raw),
        },
        "raw": {
            "record_review_input": review_raw,
            "verification_request": verification_raw,
            "permission_preflight_input": permission_raw,
        },
    }


def materialize_candidate(caller, candidate):
    owned = {}
    for key, raw in candidate["raw"].items():
        name = "accepted-" + key.replace("_", "-") + ".json"
        caller.write(name, raw)
        path = caller.output / name
        require(digest(path.read_bytes()) == candidate["pins"][key],
                "continuation-owned candidate bytes differ")
        owned[key] = path
    return owned


def require_successful_settlement(inspected):
    state = inspected.get("current", {}).get("state", {})
    require(set(state) == {"settled_observation_required"} and
            state["settled_observation_required"].get("settlement", {}).get("outcome") == "success",
            "native settlement is not successful")


def execute(config_path, retained_root, output, accepted_digest):
    config, config_digest = configuration(config_path)
    candidate = retained_candidate(config, retained_root, accepted_digest)
    require(bool(os.environ.get("INVOCATION_ID")),
            "continuation requires an operator-admitted durable manager")
    require(output.is_absolute() and not output.exists(), "fresh absolute output required")
    lock_path = Path(config["paths"]["ag_database"]).parent / "reviewed-action-caller.lock"
    owner_lock = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    fcntl.flock(owner_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    caller = Caller(config, output)
    caller.write("checkpoint.json", {
        "schema": "constellation.reviewed-action-continuation/v1",
        "config": str(config_path),
        "config_sha256": config_digest,
        "retained_review": str(retained_root),
        "accepted_candidate_sha256": accepted_digest,
        "provider_calls": 0,
        "next_action": "Inspect original native state; never redispatch or replace an uncertain transition.",
    })
    caller.write("operator-acceptance.json", {
        "schema": "constellation.exact-review-operator-acceptance/v1",
        "operator": config["operator"],
        "candidate_sha256": accepted_digest,
        "candidate_pins": candidate["pins"],
        "human_attestation": False,
        "meaning": "The durable operator admits this exact retained candidate; review testimony remains bounded to its content.",
    })
    owned = materialize_candidate(caller, candidate)
    try:
        programs = {key: value["path"] for key, value in config["programs"].items()}
        inputs = {key: Path(value["path"]) for key, value in config["inputs"].items()}
        paths = config["paths"]
        binding, _ = read(inputs["binding"])
        executor = read(inputs["executor_config"])[0]
        plan = json.loads(base64.b64decode(executor["executor_plan_base64"], validate=True))
        for directory in (Path(plan["scratch_root"]), Path(executor["state_root"]), Path(paths["docket_state"])):
            require(directory.is_dir() and not directory.is_symlink() and not any(directory.iterdir()),
                    "exclusive empty effect/custody directory required")
        require(not Path(paths["ag_mandates"]).exists(),
                "existing standing mandate; reconcile the original owner")
        verified = caller.call("profile-verify", [programs["ag"], "verify-runtime-profile-v2",
                               "--runtime-profile", inputs["runtime_profile"]])
        current = caller.ag("before-acceptance-inspect", "inspect")
        require(set(current["current"]["state"]) == {"proposal_recorded"},
                "existing AG occurrence is not awaiting this review")
        meta = current["current"]["state"]["proposal_recorded"]["meta"]
        require(meta["key"] == {"campaign": binding["campaign"], "occurrence": binding["occurrence"]} and
                meta["expected_work"] == binding["work"], "existing AG occurrence differs")
        review = candidate["review_input"]["review"]
        require(now() + 30000 < review["expires_at_unix_ms"],
                "retained review no longer has execution reserve; no retiming")
        reverification = caller.call(
            "native-review-reverification",
            [programs["review_verifier"], "--config", inputs["review_verifier_config"]],
            owned["verification_request"].read_bytes(), timeout=60,
        )
        require(reverification.get("accepted") is True and
                reverification.get("binding_id") == binding["binding_id"],
                "native review re-verification refused")
        require(now() + 30000 < review["expires_at_unix_ms"],
                "review reserve elapsed during re-verification; no recording or retiming")
        review_id = caller.ag("record-review", "record-review", "--input",
                              owned["record_review_input"])
        caller.ag("require-standing", "require-standing")
        issued = now()
        expires = min(issued + 60000, review["expires_at_unix_ms"])
        require(expires - issued >= 30000, "remaining review window insufficient; no retiming")
        caller.freshness("before-permission", expires - issued)
        mandate = {
            "schema": "ag.governed-loop.standing-mandate-store/v1",
            "mandates": [{"generation": 1, "scope": binding["scope"], "status": "active",
                          "subject": binding["subject"], "valid_until_unix_ms": expires}],
        }
        caller.write("mandate-create.started.json", {
            "path": paths["ag_mandates"], "expires_at_unix_ms": expires
        })
        with Path(paths["ag_mandates"]).open("xb") as stream:
            stream.write(canonical(mandate)); stream.flush(); os.fsync(stream.fileno())
        caller.write("mandate-create.finished.json", {"exit_code": 0})
        permission = caller.ag("permission-preflight", "permission-preflight", "--input",
                               owned["permission_preflight_input"])
        require(permission.get("decision") == "allowed" and
                permission.get("grants_authority") is False and
                permission.get("review_id") == review_id and
                permission.get("binding_id") == binding["binding_id"] and
                permission.get("profile_digest") == verified["profile_digest"] and
                permission.get("key") == meta["key"],
                "native preflight does not bind exact accepted review/occurrence")
        require(now() + 30000 < min(expires, permission["expires_at_unix_ms"]),
                "permission reserve exhausted")
        command = [programs["docket"], "governed-loop", "standing-grant", "--state",
                   paths["docket_state"], "--operator", config["operator"]]
        for key in ("campaign", "occurrence", "subject", "scope"):
            command += ["--" + key, binding[key]]
        command += ["--program", meta["program"], "--work-schema", binding["work_schema"],
                    "--work", binding["work"], "--issued-at-unix-ms", str(issued),
                    "--expires-at-unix-ms", str(expires)]
        caller.call("operator-grant", command, parsed=False)
        run = prepare(inputs["binding"], inputs["cycle_request"],
                      owned["record_review_input"], inputs["executor_config"],
                      verified["profile_digest"], min(expires, permission["expires_at_unix_ms"]))
        caller.write("run-input-v2.json", run)
        caller.write("run-input-identity.json", {
            "sha256": digest(canonical(run)), "config": digest(canonical(config))
        })
        for entry in config["programs"].values(): pinned(entry, 1024 * 1024**2)
        for entry in config["inputs"].values(): pinned(entry, 16 * 1024**2)
        require(now() + 30000 < run["deadline_unix_ms"], "finite run reserve exhausted")
        result = caller.ag("finite-run", "run", "--run-input", output / "run-input-v2.json")
        require(result.get("status") == "terminal" and
                result.get("reason") == "finite_continuation_bound_complete" and
                result.get("program_counter") == "settled_observation_required",
                "finite run did not reconcile the same owner")
        inspected = caller.inspect("settled")
        require(all(inspected["replay"][key] == 1 for key in
                    ("ag_spends", "docket_attempts", "settlements")),
                "unexpected native consequence cardinality")
        require_successful_settlement(inspected)
        caller.write("terminal.json", {
            "exit_code": 0, "result": result,
            "operator_acceptance": "exact_candidate_digest",
            "human_attestation": False, "provider_calls_in_continuation": 0,
        })
    except Exception as error:
        caller.write("terminal.json", {
            "exit_code": 1, "phase": caller.phase, "reason": str(error),
            "next_action": "Inspect the original transition and native owners; never redispatch or replace it.",
            "provider_calls_in_continuation": 0,
        })
        raise
    finally:
        os.close(owner_lock)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--retained-review", type=Path, required=True)
    parser.add_argument("--accept-candidate-sha256", required=True)
    parser.add_argument("--output", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--accept-and-execute", action="store_true")
    args = parser.parse_args(argv)
    config, _ = configuration(args.config)
    candidate = retained_candidate(config, args.retained_review,
                                   args.accept_candidate_sha256)
    if args.preflight_only:
        print(json.dumps({"candidate_sha256": args.accept_candidate_sha256,
                          "pins": candidate["pins"], "provider_calls": 0,
                          "authority": False}, sort_keys=True, separators=(",", ":")))
        return
    require(args.output is not None, "--output is required for execution")
    execute(args.config, args.retained_review, args.output,
            args.accept_candidate_sha256)


if __name__ == "__main__":
    main()
