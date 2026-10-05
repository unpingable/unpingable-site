#!/usr/bin/env python3
"""Posture-only cycle request + Pulse load-support config generator (stdlib only, py3.10+).

usage: build_request.py ARTIFACT_JSON NOW EPOCH CADENCE_SECONDS ADMISSIBLE_SECONDS NQ_SOURCE_ID OUTDIR
                        [--scheduler-clock-id ID] [--max-age-seconds N] [--producer-public-key-hex HEX] ...

  ARTIFACT_JSON  exact bytes of `nq --config C diagnostics export <artifact_id>` (nq.diagnostic_execution.v2)
  NOW            RFC3339 UTC whole seconds, e.g. 2026-10-01T12:03:07Z  (becomes evaluated_at)
  EPOCH          RFC3339 UTC whole seconds; the schedule's first_due_at. Choose once, never change.
  CADENCE_SECONDS, ADMISSIBLE_SECONDS   slot grid step and (latest_admissible - nominal_due) window
  NQ_SOURCE_ID   must equal artifact producer.node_id (nightshift refuses otherwise)
  OUTDIR         receives current.json (JCS bytes) and pulse-load-support.json, each written atomically

Id rule (all verified against the Rust validators): every *_id is "sha256:" + hex(sha256(JCS(object
with that one id field removed))). observation_id is only checked as sha256:<64 lowercase hex>
(CanonicalCycleRequestV1::validate, canonical_runtime.rs:297); it is deterministically derived here.
Prints: request_id, slot_id and a summary line.
"""
import argparse, datetime as dt, hashlib, json, os, pathlib, re, sys, tempfile

TS = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


def die(msg):
    sys.stderr.write("build_request: %s\n" % msg)
    sys.exit(2)


def ts(value, name):
    if not TS.match(value):
        die("%s must be RFC3339 UTC whole seconds ending in Z (got %r)" % (name, value))
    return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def z(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _check(v):
    # JCS (RFC 8785) via json.dumps is exact only for: ASCII keys, no floats, ints within 2**53.
    if isinstance(v, float):
        die("artifact contains a float; refusing to guess JCS number formatting")
    if isinstance(v, int) and not isinstance(v, bool) and abs(v) > 2**53:
        die("artifact contains an integer beyond 2**53")
    if isinstance(v, dict):
        for k, x in v.items():
            if not k.isascii():
                die("non-ASCII object key; UTF-16 key ordering would differ")
            _check(x)
    elif isinstance(v, list):
        for x in v:
            _check(x)


def jcs(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha(b):
    return "sha256:" + hashlib.sha256(b).hexdigest()


def oid(v, field):
    p = dict(v)
    p.pop(field, None)
    return sha(jcs(p))


def atomic_write(path, data):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def default_clock():
    try:
        mid = pathlib.Path("/etc/machine-id").read_text().strip()
    except OSError:
        die("no /etc/machine-id; pass --scheduler-clock-id")
    return "nightshift-timer:" + mid


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("artifact_json")
    ap.add_argument("now")
    ap.add_argument("epoch")
    ap.add_argument("cadence_seconds", type=int)
    ap.add_argument("admissible_seconds", type=int)
    ap.add_argument("nq_source_id")
    ap.add_argument("outdir")
    ap.add_argument("--scheduler-clock-id", default=None)
    ap.add_argument("--max-age-seconds", type=int, default=600)
    ap.add_argument("--standing-window-seconds", type=int, default=600)
    ap.add_argument("--exec-budget-seconds", type=int, default=60)
    ap.add_argument("--configuration-version", default="config-v1")
    ap.add_argument("--policy-generation", default="generation:fs-data-capacity-1")
    ap.add_argument("--schedule-id", default="schedule:fs-data-capacity")
    ap.add_argument("--authority-id", default="pulse-authority:nightshift-host")
    ap.add_argument("--producer-id", default="pulse-producer:nightshift-host")
    ap.add_argument("--producer-key-id", default="pulse-key:unprovisioned")
    # Config validation only demands 64 lowercase hex; the key is used only to verify receipts, and
    # there are none. 01 00..00 is the (valid) Ed25519 identity point: it can never verify anything.
    ap.add_argument("--producer-public-key-hex", default="01" + "00" * 31)
    ap.add_argument("--producer-private-key-path", default="/var/lib/pulse-load-support/producer-key.hex")
    ap.add_argument("--outgoing-directory", default="/var/lib/pulse-load-support/outgoing")
    ap.add_argument("--receipt-directory", default="/var/lib/pulse-support-receiver/receipts")
    a = ap.parse_args()

    if a.cadence_seconds <= 0 or a.admissible_seconds < 0 or a.max_age_seconds <= 0:
        die("cadence/max-age must be positive, admissible non-negative")
    now, epoch = ts(a.now, "NOW"), ts(a.epoch, "EPOCH")
    if now < epoch:
        die("NOW precedes EPOCH")
    outdir = pathlib.Path(a.outdir)
    if not outdir.is_dir():
        die("OUTDIR is not a directory")
    clock = a.scheduler_clock_id or default_clock()
    if re.search(r"\s", clock):
        die("scheduler clock id must contain no whitespace")

    raw = pathlib.Path(a.artifact_json).read_bytes()
    try:
        art = json.loads(raw, parse_float=lambda s: die("float in artifact"))
    except ValueError as e:
        die("artifact is not JSON: %s" % e)
    if art.get("schema") != "nq.diagnostic_execution.v2":
        die("artifact schema is %r, need nq.diagnostic_execution.v2" % art.get("schema"))
    _check(art)
    if jcs(art) != raw.rstrip(b"\n"):
        sys.stderr.write("build_request: warning: artifact bytes are not JCS-canonical as read; "
                         "using re-canonicalised form (nightshift re-serialises the same way)\n")
    node = art["producer"]["node_id"]
    if node != a.nq_source_id:
        die("NQ_SOURCE_ID %r != artifact producer.node_id %r (nightshift would refuse admission)"
            % (a.nq_source_id, node))
    subj, claim = art["subject"], art["primary_claim_id"]
    key = {"question_id": art["question"]["id"], "subject_id": subj["id"],
           "profile_id": art["profile"]["id"], "vantage_id": art["vantage"]["id"]}
    binding = {"producer_node_id": node, "producer_build": art["producer"]["build"],
               "producer_cohort": art["producer"]["cohort"], "question": art["question"],
               "profile": art["profile"], "profile_semantic_id": art["profile_semantic_id"],
               "vantage": art["vantage"], "state_model": art["state_model"],
               "evaluator": art["evaluator"], "threshold_policy": art["threshold_policy"],
               "projection": art["projection"], "subject": subj, "claim_id": claim}

    role_id, role_ver = "nightshift-role:host-posture", "1"
    policy = {"schema": "nightshift.diagnostic_posture_policy.v2", "policy_id": "",
              "generation": a.policy_generation, "subject": subj,
              "role": {"id": role_id, "version": role_ver, "digest": sha(("%s/%s" % (role_id, role_ver)).encode())},
              "delivery_required": False,
              "inventory": [{"binding": binding, "requirement": "mandatory",
                             "required_state_bindings": [{"kind": "subject_identity", "value": subj["id"]}],
                             "max_age_seconds": a.max_age_seconds}]}
    policy["policy_id"] = oid(policy, "policy_id")

    inputs = {"schema": "nightshift.diagnostic_inputs.v2", "inputs_id": "",
              "inputs": [{"key": key, "status": "delivered", "artifact": art}]}
    inputs["inputs_id"] = oid(inputs, "inputs_id")

    recurrence = {"schema": "nightshift.recurrence_evidence.v2", "recurrence_id": "",
                  "delivery": "not_required", "records": [],
                  "obligations": [{"key": key, "policy": {
                      "schedule_id": a.schedule_id, "first_due_at": z(epoch),
                      "cadence_seconds": a.cadence_seconds, "jitter_bound_seconds": 0,
                      "max_execution_budget_seconds": a.exec_budget_seconds,
                      "standing_window_seconds": a.standing_window_seconds}}]}
    recurrence["recurrence_id"] = oid(recurrence, "recurrence_id")

    n = int((now - epoch).total_seconds() // a.cadence_seconds)   # == expected_occurrence_at()
    due = epoch + dt.timedelta(seconds=n * a.cadence_seconds)
    latest = due + dt.timedelta(seconds=a.admissible_seconds)
    slot = {"schema": "nightshift.recurrence_slot.v1", "slot_id": "", "policy_id": policy["policy_id"],
            "configuration_version": a.configuration_version, "subject_id": subj["id"],
            "scope_id": subj["scope"]["digest"], "scheduler_clock_id": clock,
            "nominal_due_at": z(due), "latest_admissible": {"scheduler_clock_id": clock, "at": z(latest)},
            "occurrence": n, "trigger": "scheduled"}
    slot["slot_id"] = oid(slot, "slot_id")

    req = {"schema": "nightshift.canonical_cycle_request.v1", "request_id": "", "slot": slot,
           "scheduler_clock_id": clock, "evaluated_at": z(now),
           "observation_id": sha(jcs({"schema": "site.posture_observation.v1", "slot_id": slot["slot_id"],
                                      "inputs_id": inputs["inputs_id"], "policy_id": policy["policy_id"]})),
           "policy": policy, "inputs": inputs, "recurrence": recurrence}
    req["request_id"] = oid(req, "request_id")

    cfg = {"schema": "pulse.nq_host_load_pressure_support_config.v1",
           "authority_id": a.authority_id, "support_family": "pulse.nq_host_load_pressure.v1",
           "producer_id": a.producer_id, "producer_key_id": a.producer_key_id,
           "producer_public_key_hex": a.producer_public_key_hex,
           "producer_private_key_path": a.producer_private_key_path,
           "subject_id": subj["id"], "scope_id": subj["scope"]["digest"], "vantage_id": art["vantage"]["id"],
           "question": {"id": "nq.host.load_pressure", "version": "1",
                        "digest": "sha256:7de797da3d9d3a6ae8e21e5d77b95095453336cd38f606ffb3eb29ff6a32e2cf"},
           "profile": {"id": "nq.host", "version": "1",
                       "digest": "sha256:c8c10fed1cc5598d953b4defbc98e8c106fc59e035c249d43681698a5c7b4ff9"},
           "profile_semantic_id": "sha256:382b8dac14ef9353a3603757d60fc8fbc727e1bcaf088c9aab4bdf895d3f6ab1",
           "threshold_policy": {"id": "nq.host.load_pressure.threshold_policy", "version": "1",
                                "digest": "sha256:52b815509d26878fad1f88c6352bcd17537452f704072e56664e18434fee855e"},
           "outgoing_directory": a.outgoing_directory, "receipt_directory": a.receipt_directory,
           "expected_diagnostic": {"diagnostic_inputs_id": inputs["inputs_id"],
                                   "artifact_ids": [art["artifact_id"]], "expected_state": "explicitly_absent"}}

    # config first: the resolver child reads it while `cycle run` is in flight.
    atomic_write(outdir / "pulse-load-support.json", (json.dumps(cfg, indent=2, sort_keys=True) + "\n").encode())
    atomic_write(outdir / "current.json", jcs(req))
    print("request_id=%s" % req["request_id"])
    print("slot_id=%s" % slot["slot_id"])
    print("occurrence=%d due=%s latest_admissible=%s evaluated_at=%s observation_id=%s"
          % (n, z(due), z(latest), z(now), req["observation_id"]), file=sys.stderr)
    if now > latest:
        sys.stderr.write("build_request: warning: NOW is past latest_admissible; cycle will be recorded Missed\n")


if __name__ == "__main__":
    main()
