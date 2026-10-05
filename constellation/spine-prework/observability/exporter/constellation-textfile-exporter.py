#!/usr/bin/env python3
"""Constellation textfile exporter (Beta Observability MVP).

Reads the products' existing read-only surfaces and writes one Prometheus
text-format file atomically.  Operational telemetry only: counts, durations,
sizes, timestamps, closed enums and bounded build identities.  Never an
evidence id, artifact digest, subject, path or unbounded instance name as a
label value.  Ages are computed in PromQL, never exported.

Every input is guarded.  A missing or unreadable input omits its metric
families and sets constellation_exporter_input_ok{input="..."} 0.  The
program never raises; a failed final write is the only non-zero exit.
Python 3.10, standard library only.
"""
import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

LABEL_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
RULE_SAFE = re.compile(r"^[a-z][a-z0-9-]{0,47}$")
ENUM_SAFE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
MAX_INSTANCES = 32

POSTURE_STATES = ("healthy", "degraded", "partial_outage", "major_outage", "unknown")
OBSERVATIONS = ("present", "clear", "unknown")
CYCLE_STATUSES = ("observing", "posture_recorded", "awaiting_ag", "awaiting_ag_reconciliation",
                  "observation_required", "halted", "closed", "missed", "recovery_required")
CYCLE_TIMINGS = ("on_time", "late", "catch_up", "missed", "none")
UNIT_RESULTS = ("success", "exit-code", "signal", "core-dump", "timeout", "watchdog",
                "resources", "start-limit-hit", "protocol", "oom-kill", "other")
INPUT_STATUSES = ("ok", "not_current", "unavailable", "other")
SAVED_OUTCOMES = ("passed", "failed", "refused", "other")


# ---------------------------------------------------------------- output

class Registry:
    def __init__(self):
        self.families = {}   # name -> [type, help, [(labels, value)]]
        self.input_ok = {}
        self.dropped = 0

    def family(self, name, mtype, help_):
        fam = self.families.get(name)
        if fam is None:
            fam = self.families[name] = [mtype, help_, []]
        return fam[2]

    def gauge(self, name, help_, value, labels=None):
        self.family(name, "gauge", help_).append((labels or {}, value))

    def header_only(self, name, help_):
        self.family(name, "gauge", help_)

    def ok(self, name, flag):
        self.input_ok[name] = 1 if flag else 0

    def render(self):
        self.family("constellation_exporter_input_ok", "gauge",
                    "1 when the named input was read and parsed this run, else 0.")
        out = []
        fams = dict(self.families)
        fams["constellation_exporter_dropped_label_values"] = [
            "gauge", "Label values rejected this run as not operator-configured names (dropped, never exported).",
            [({}, self.dropped)]]
        fams["constellation_exporter_input_ok"] = [
            "gauge", "1 when the named input was read and parsed this run, else 0.",
            [({"input": k}, v) for k, v in sorted(self.input_ok.items())]]
        for name in sorted(fams):
            mtype, help_, samples = fams[name]
            out.append("# HELP %s %s" % (name, help_.replace("\\", "\\\\").replace("\n", " ")))
            out.append("# TYPE %s %s" % (name, mtype))
            for labels, value in samples:
                out.append("%s%s %s" % (name, fmt_labels(labels), fmt_value(value)))
        return "\n".join(out) + "\n"


def esc(v):
    return str(v).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def fmt_labels(labels):
    if not labels:
        return ""
    return "{" + ",".join('%s="%s"' % (k, esc(labels[k])) for k in sorted(labels)) + "}"


def fmt_value(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    return repr(float(v))


# ---------------------------------------------------------------- helpers

def parse_ts(text):
    """RFC3339 (any fractional precision, Z or offset) -> unix seconds, or None."""
    if not isinstance(text, str):
        return None
    m = re.match(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$", text.strip())
    if not m:
        return None
    base = dt.datetime.strptime(m.group(1) + " " + m.group(2), "%Y-%m-%d %H:%M:%S")
    secs = base.replace(tzinfo=dt.timezone.utc).timestamp()
    if m.group(3):
        secs += float("0" + m.group(3))
    tz = m.group(4)
    if tz and tz != "Z":
        sign = 1 if tz[0] == "+" else -1
        digits = tz[1:].replace(":", "")
        secs -= sign * (int(digits[:2]) * 3600 + int(digits[2:]) * 60)
    return secs


def num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return v


def read_json(path, limit=32 * 1024 * 1024):
    with open(path, "rb") as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError("file exceeds %d bytes" % limit)
    return json.loads(data)


def run(argv, timeout=10, env=None):
    p = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=timeout, env=env)
    return p.returncode, p.stdout, p.stderr


IDENTITY_LIKE = re.compile(
    r"(sha256|[0-9a-fA-F]{32,}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})")


def safe_label(v, rx=LABEL_SAFE, other="other"):
    """Operator-configured names only: short, slash-free, never digest/uuid shaped."""
    if isinstance(v, str) and rx.match(v) and not IDENTITY_LIKE.search(v):
        return v
    return other


def one_hot(reg, name, help_, key, current, values, extra=None):
    current = current if current in values else "other" if "other" in values else None
    for v in values:
        labels = dict(extra or {})
        labels[key] = v
        reg.gauge(name, help_, 1 if v == current else 0, labels)


def guard(reg, name, fn, *a):
    """Run a collector; any failure marks the input and omits its families."""
    snapshot = {k: list(v[2]) for k, v in reg.families.items()}
    try:
        fn(reg, *a)
    except BaseException as e:  # noqa: BLE001 - the exporter never raises
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        for k in list(reg.families):
            if k not in snapshot:
                del reg.families[k]
            else:
                reg.families[k][2][:] = snapshot[k]
        reg.ok(name, False)
        sys.stderr.write("input %s: %s: %s\n" % (name, type(e).__name__, str(e)[:200]))


def load_optional(reg, input_name, path, limit=32 * 1024 * 1024):
    try:
        doc = read_json(path, limit)
        if not isinstance(doc, dict):
            raise ValueError("not an object")
        reg.ok(input_name, True)
        return doc
    except Exception as e:  # noqa: BLE001
        reg.ok(input_name, False)
        sys.stderr.write("input %s: %s: %s\n" % (input_name, type(e).__name__, str(e)[:200]))
        return None


# ---------------------------------------------------------------- collectors

def c_status(reg, status, now):
    """Families derived from status.json; each section guarded on its own."""
    ts = num(status.get("rendered_at_unix"))
    if ts is not None:
        reg.gauge("constellation_status_site_rendered_timestamp_seconds",
                  "Unix time the status-site renderer produced status.json.", ts)
    sections = (("host_posture", s_posture), ("nq_watchers", s_watchers),
                ("saved_checks", s_saved), ("tls", s_tls))
    for name, fn in sections:
        guard(reg, name, lambda r, f=fn, n=name: r.ok(n, f(r, status, now) is not False))


def s_posture(reg, status, now):
    hp = ((status.get("attention") or {}).get("host_posture"))
    if not isinstance(hp, dict):
        raise ValueError("no host_posture section")
    gen = parse_ts(hp.get("generated_at"))
    fresh_until = parse_ts(hp.get("fresh_until"))
    avail = hp.get("available") is True
    state = hp.get("aggregate_state")
    if not avail or gen is None or fresh_until is None or now > fresh_until or state not in POSTURE_STATES:
        effective = "unknown"
    else:
        effective = state
    for s in POSTURE_STATES:
        reg.gauge("constellation_host_posture_projection_state",
                  "Host-posture projection state, one-hot; unknown when absent or past fresh_until.",
                  1 if s == effective else 0, {"state": s})
    if not avail:
        return False   # one-hot unknown stays; timestamps omitted; input_ok 0
    reg.gauge("constellation_host_posture_generated_timestamp_seconds",
              "Unix time the current host-posture status artifact was generated.", gen)
    reg.gauge("constellation_host_posture_fresh_until_timestamp_seconds",
              "Unix time until which the current host-posture status artifact is fresh.", fresh_until)


def s_watchers(reg, status, now):
    ws = (((status.get("support") or {}).get("watchers")) or {})
    if ws.get("available") is not True:
        raise ValueError("watchers unavailable")
    name = "constellation_nq_watcher_observed_timestamp_seconds"
    help_ = "Unix time of the newest observation per operator-configured NQ watcher instance."
    reg.header_only(name, help_)
    n, seen = 0, set()
    for w in ws.get("watchers") or []:
        t = parse_ts(w.get("observed_at"))
        inst = safe_label(w.get("instance"), other=None)
        if inst is None:
            reg.dropped += 1
            continue
        if t is None or inst in seen or n >= MAX_INSTANCES:
            continue
        seen.add(inst)
        reg.gauge(name, help_, t, {"store": "ops", "instance": inst})
        n += 1
    seq = num(ws.get("evaluation_through_sequence"))
    if seq is not None:
        reg.gauge("constellation_nq_evaluation_through_sequence",
                  "Evaluation sequence covered by the NQ status snapshot.", seq, {"store": "ops"})
    gen = parse_ts(ws.get("generated_at"))
    if gen is not None:
        reg.gauge("constellation_nq_status_snapshot_timestamp_seconds",
                  "Unix time the NQ status snapshot was generated.", gen, {"store": "ops"})


def s_saved(reg, status, now):
    sc = (((status.get("support") or {}).get("saved_checks")) or {})
    if sc.get("available") is not True:
        raise ValueError("saved checks unavailable")
    name = "constellation_nq_saved_check_outcome"
    help_ = "Latest outcome per saved-check reference, one-hot."
    reg.header_only(name, help_)
    seen, refs = 0, set()
    for r in sc.get("results") or []:
        ref = r.get("reference")
        if safe_label(ref, other=None) is None:
            reg.dropped += 1
            continue
        if ref in refs or seen >= 16:
            continue
        refs.add(ref)
        seen += 1
        one_hot(reg, name, help_, "outcome", r.get("outcome"), SAVED_OUTCOMES, {"reference": ref})
    gen = parse_ts(sc.get("generated_at"))
    if gen is not None:
        reg.gauge("constellation_nq_saved_check_generated_timestamp_seconds",
                  "Unix time of the latest saved-check run.", gen)


def s_tls(reg, status, now):
    tls = (((status.get("substrate") or {}).get("tls")) or {})
    if tls.get("available") is not True:
        raise ValueError("tls unavailable")
    d = num(tls.get("days_remaining"))
    if d is None:
        raise ValueError("no days_remaining")
    reg.gauge("constellation_tls_days_remaining",
              "Whole days until the public certificate expires.", d)


def c_attention(reg, report, now):
    ev = parse_ts(report.get("evaluated_at"))
    if ev is None:
        raise ValueError("report has no evaluated_at")
    reg.gauge("constellation_attention_report_evaluated_timestamp_seconds",
              "Unix time of the evaluator's latest pass.", ev)
    rules = []
    for r in report.get("rules") or []:
        rid = r.get("id") if isinstance(r, dict) else None
        if isinstance(rid, str) and RULE_SAFE.match(rid) and rid not in rules:
            rules.append(rid)
    conds = [c for c in report.get("conditions") or [] if isinstance(c, dict)]
    for c in conds:
        rid = c.get("rule")
        if isinstance(rid, str) and RULE_SAFE.match(rid) and rid not in rules:
            rules.append(rid)
    rules = rules[:MAX_INSTANCES]
    counts = {(r, o): 0 for r in rules for o in OBSERVATIONS}
    active = {r: 0 for r in rules}
    for c in conds:
        rid = c.get("rule")
        if rid not in active:
            continue
        o = c.get("observation") if c.get("observation") in OBSERVATIONS else "unknown"
        counts[(rid, o)] += 1
        if c.get("active") is True:
            active[rid] += 1
    for (r, o), n in sorted(counts.items()):
        reg.gauge("constellation_attention_conditions",
                  "Conditions per registry rule and observation in the last evaluator pass.",
                  n, {"rule": r, "observation": o})
    for r, n in sorted(active.items()):
        reg.gauge("constellation_attention_active_conditions",
                  "Active (past persistence bound) conditions per registry rule.", n, {"rule": r})
    # input statuses: kind is a closed enum, label an operator-configured name
    name = "constellation_attention_input_status"
    help_ = "Evaluator input status per configured input, one-hot."
    reg.header_only(name, help_)
    seen_inputs = set()
    for i in (report.get("inputs") or [])[:MAX_INSTANCES]:
        if not isinstance(i, dict):
            continue
        st = i.get("status") if i.get("status") in INPUT_STATUSES else "other"
        kind, label = safe_label(i.get("kind"), ENUM_SAFE, None), safe_label(i.get("label"), other=None)
        if kind is None or label is None:
            reg.dropped += 1
            continue
        if (kind, label) in seen_inputs:
            continue
        seen_inputs.add((kind, label))
        base = {"kind": kind, "input": label}
        one_hot(reg, name, help_, "status", st, INPUT_STATUSES, base)
    # intents of the last pass, a gauge of that pass
    name = "constellation_attention_intents_total"
    help_ = "Notification intents recorded by the last evaluator pass (gauge of that pass, not a counter)."
    reg.header_only(name, help_)
    tally = {}
    for it in report.get("intents") or []:
        if not isinstance(it, dict):
            continue
        key = (safe_label(it.get("action"), ENUM_SAFE), safe_label(it.get("route_role"), ENUM_SAFE),
               safe_label(it.get("outcome"), ENUM_SAFE))
        tally[key] = tally.get(key, 0) + 1
    for (a, rr, oc), n in sorted(tally.items())[:64]:
        reg.gauge(name, help_, n, {"action": a, "route_role": rr, "outcome": oc})
    ud = report.get("unresolved_deliveries")
    n = len(ud) if isinstance(ud, (list, dict)) else num(ud)
    if n is not None:
        reg.gauge("constellation_attention_unresolved_deliveries",
                  "Notification deliveries without a definite outcome after the last pass.", n)
    reg.ok("attention_report", True)


def c_attention_state(reg, state, now):
    u = num(state.get("updated_at"))
    if u is None:
        raise ValueError("no updated_at")
    reg.gauge("constellation_attention_state_updated_timestamp_seconds",
              "Unix time the evaluator last persisted its state.", u)
    reg.ok("attention_state", True)


def c_timings(reg, doc, now):
    v = num(doc.get("status_export_wall_seconds"))
    if v is None:
        raise ValueError("no status_export_wall_seconds")
    reg.gauge("constellation_nq_status_export_duration_seconds",
              "Wall time of the last `nq status export` made by the status-site renderer.",
              v, {"store": "ops"})
    reg.ok("render_timings", True)


def c_nq_store(reg, store, directory, db_name):
    db = os.path.join(directory, db_name)
    size = os.stat(db).st_size
    try:
        wal = os.stat(db + "-wal").st_size
    except FileNotFoundError:
        wal = 0
    reg.gauge("constellation_nq_store_bytes", "NQ store file size in bytes.", size,
              {"store": store, "file": "db"})
    reg.gauge("constellation_nq_store_bytes", "NQ store file size in bytes.", wal,
              {"store": store, "file": "wal"})
    reg.ok("nq_store_" + store, True)


def c_watermark(reg, store, directory, db_name):
    path = os.path.join(directory, db_name + ".validation-watermark.json")
    wm = read_json(path)
    if not isinstance(wm, dict) or not str(wm.get("schema", "")).startswith("nq.validation_watermark."):
        raise ValueError("unexpected watermark schema")
    frontier = wm.get("frontier") or {}
    seq = num(frontier.get("evaluation_sequence"))
    if seq is None:
        raise ValueError("no frontier.evaluation_sequence")
    reg.gauge("constellation_nq_validation_watermark_certified",
              "1 when the validation watermark also certifies the complete semantic history.",
              1 if wm.get("semantic") is not None else 0, {"store": store})
    reg.gauge("constellation_nq_validation_watermark_evaluation_sequence",
              "Evaluation append sequence covered by the validation watermark.", seq, {"store": store})
    v = parse_ts(wm.get("validated_at"))
    if v is not None:
        reg.gauge("constellation_nq_validation_watermark_validated_timestamp_seconds",
                  "Unix time the covered validation completed.", v, {"store": store})
    reg.ok("nq_watermark_" + store, True)


def systemd_show(unit, systemctl):
    props = ("LoadState", "Result", "ExecMainStartTimestamp", "ExecMainExitTimestamp")
    argv = [systemctl, "show", "--timestamp=utc", unit] + ["-p" + p for p in props]
    rc, out, err = run(argv, 10)
    if rc != 0:
        rc, out, err = run([systemctl, "show", unit] + ["-p" + p for p in props], 10)
    if rc != 0:
        raise ValueError("systemctl show exited %d" % rc)
    d = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
    if d.get("LoadState") != "loaded":
        raise ValueError("unit not loaded (%s)" % d.get("LoadState"))
    return d


def parse_systemd_ts(text):
    text = (text or "").strip()
    if not text or text == "n/a":
        return None
    if text.startswith("@"):
        try:
            return float(text[1:])
        except ValueError:
            return None
    m = re.search(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})(\.\d+)?", text)
    if not m:
        return None
    return parse_ts(m.group(1) + "T" + m.group(2) + (m.group(3) or "") + "Z")


def c_unit(reg, key, unit, systemctl, prefix, result_name, ts_name, dur_name, what):
    d = systemd_show(unit, systemctl)
    res = d.get("Result", "")
    one_hot(reg, result_name, "Result of the last %s run (systemd Result), one-hot." % what,
            "result", res if res else "other", UNIT_RESULTS)
    start = parse_systemd_ts(d.get("ExecMainStartTimestamp"))
    exit_ = parse_systemd_ts(d.get("ExecMainExitTimestamp"))
    if exit_ is not None:
        reg.gauge(ts_name, "Unix time the last %s run exited." % what, exit_)
        if start is not None and exit_ >= start:
            reg.gauge(dur_name, "Wall duration of the last %s run (exit minus start)." % what,
                      exit_ - start)
    reg.ok(key, True)


def c_nightshift(reg, path):
    if not os.path.exists(path):
        raise FileNotFoundError("store not found")
    con = sqlite3.connect("file:%s?mode=ro" % path, uri=True, timeout=5)
    try:
        con.execute("PRAGMA query_only=1")
        row = con.execute("SELECT MAX(updated_at) FROM canonical_observation_cycles "
                          "WHERE status='closed'").fetchone()
        last = parse_ts(row[0]) if row and row[0] else None
        try:
            rows = con.execute(
                "SELECT status, COALESCE(json_extract(snapshot_json,'$.timing'),'none'), COUNT(*) "
                "FROM canonical_observation_cycles GROUP BY 1,2").fetchall()
            with_timing = True
        except sqlite3.Error:
            rows = [(s, None, n) for s, n in con.execute(
                "SELECT status, COUNT(*) FROM canonical_observation_cycles GROUP BY 1").fetchall()]
            with_timing = False
    finally:
        con.close()
    if last is not None:
        reg.gauge("constellation_nightshift_last_closed_cycle_timestamp_seconds",
                  "Unix time (store updated_at) of the newest closed Nightshift cycle.", last)
    name = "constellation_nightshift_cycles_total"
    help_ = ("Rows in the Nightshift cycle store by status and slot timing "
             "(a store row count; rows change status in place, so this is a gauge).")
    agg = {}
    for status, timing, n in rows:
        s = status if status in CYCLE_STATUSES else "other"
        labels = {"status": s}
        if with_timing:
            labels["timing"] = timing if timing in CYCLE_TIMINGS else "other"
        k = tuple(sorted(labels.items()))
        agg[k] = agg.get(k, 0) + n
    reg.header_only(name, help_)
    for k, n in sorted(agg.items()):
        reg.gauge(name, help_, n, dict(k))
    reg.ok("nightshift_store", True)


BUILD_SOURCES = (
    ("nq", ["nq", "--build-info"], ["nq", "--version"]),
    ("host-posture", ["constellation-host-posture", "--build-info"], None),
    ("nightshift", ["nightshift", "--version"], None),
)


def parse_build(text):
    version, commit = None, None
    try:
        doc = json.loads(text)
        if isinstance(doc, dict):
            version = doc.get("version")
            commit = doc.get("source_commit")
    except ValueError:
        pass
    if not isinstance(version, str):
        m = re.search(r"\b(\d+\.\d+(?:\.\d+)?(?:[-+~][0-9A-Za-z.+~-]*)?)", text)
        version = m.group(1) if m else None
    if not isinstance(commit, str):
        m = re.search(r"(?:rev|commit|source_commit)[=: ]+([0-9a-f]{7,40})", text)
        commit = m.group(1) if m else None
    version = version if isinstance(version, str) and re.match(r"^[0-9A-Za-z.+~_-]{1,40}$", version) else "unknown"
    commit = commit[:12] if isinstance(commit, str) and re.match(r"^[0-9a-f]{7,64}$", commit) else "unknown"
    return version, commit


def c_build(reg, key, component, argv, fallback):
    text = None
    for cand in (argv, fallback):
        if not cand:
            continue
        try:
            rc, out, err = run(cand, 10)
        except FileNotFoundError:
            continue
        if rc == 0 and (out or err).strip():
            text = out if out.strip() else err
            break
    if text is None:
        raise ValueError("no build output")
    version, commit = parse_build(text)
    reg.gauge("constellation_build_info", "Installed component build identity (value is always 1).",
              1, {"component": component, "version": version, "source_commit": commit})
    reg.ok(key, True)


# ---------------------------------------------------------------- main

def collect(a, now):
    reg = Registry()
    t0 = time.monotonic()

    status = load_optional(reg, "status_json", a.status_json)
    if status is not None:
        guard(reg, "status_json", c_status, status, now)

    report = load_optional(reg, "attention_report", a.attention_report)
    if report is not None:
        guard(reg, "attention_report", c_attention, report, now)
    state = load_optional(reg, "attention_state", a.attention_state)
    if state is not None:
        guard(reg, "attention_state", c_attention_state, state, now)

    timings = load_optional(reg, "render_timings", a.render_timings, 1024 * 1024)
    if timings is not None:
        guard(reg, "render_timings", c_timings, timings, now)

    for store, directory in (("observation", a.nq_dir), ("ops", a.nq_ops_dir)):
        guard(reg, "nq_store_" + store, c_nq_store, store, directory, a.db_name)
        guard(reg, "nq_watermark_" + store, c_watermark, store, directory, a.db_name)

    guard(reg, "nightshift_store", c_nightshift, a.nightshift_db)

    guard(reg, "systemd_nq_validate_full", c_unit, "systemd_nq_validate_full",
          "nq-validate-full.service", a.systemctl, "nq",
          "constellation_nq_validate_full_last_result",
          "constellation_nq_validate_full_last_timestamp_seconds",
          "constellation_nq_validate_full_last_duration_seconds", "nq-validate-full")
    guard(reg, "systemd_nightshift", c_unit, "systemd_nightshift",
          "nightshift-observation-cycle.service", a.systemctl, "nightshift",
          "constellation_nightshift_tick_last_result",
          "constellation_nightshift_tick_last_timestamp_seconds",
          "constellation_nightshift_tick_duration_seconds", "Nightshift tick")
    guard(reg, "systemd_attention", c_unit, "systemd_attention",
          "constellation-attention.service", a.systemctl, "attention",
          "constellation_attention_pass_last_result",
          "constellation_attention_pass_last_timestamp_seconds",
          "constellation_attention_pass_duration_seconds", "evaluator pass")

    for component, argv, fallback in BUILD_SOURCES:
        key = "build_" + component.replace("-", "_")
        guard(reg, key, c_build, key, component, argv, fallback)

    reg.gauge("constellation_exporter_last_run_timestamp_seconds",
              "Unix time this exporter run started.", now)
    reg.gauge("constellation_exporter_duration_seconds",
              "Wall time spent collecting inputs in this run.", time.monotonic() - t0)
    return reg


def write_atomic(path, text):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", dir=d)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="/var/lib/constellation-telemetry/constellation.prom")
    ap.add_argument("--status-json", default="/var/www/constellation-status/status.json")
    ap.add_argument("--render-timings", default="/var/www/constellation-status/render-timings.json")
    ap.add_argument("--attention-report", default="/var/lib/constellation-attention/report.json")
    ap.add_argument("--attention-state", default="/var/lib/constellation-attention/state.json")
    ap.add_argument("--nightshift-db",
                    default="/var/lib/constellation-nightshift-observation/nightshift.sqlite")
    ap.add_argument("--nq-dir", default="/var/lib/nq")
    ap.add_argument("--nq-ops-dir", default="/var/lib/nq-ops")
    ap.add_argument("--db-name", default="nq.db")
    ap.add_argument("--systemctl", default="systemctl")
    ap.add_argument("--now", type=float, default=None, help="unix seconds override (tests)")
    a = ap.parse_args(argv)
    now = a.now if a.now is not None else time.time()
    try:
        text = collect(a, now).render()
    except BaseException as e:  # noqa: BLE001
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        sys.stderr.write("collect failed: %s: %s\n" % (type(e).__name__, e))
        text = ("# TYPE constellation_exporter_last_run_timestamp_seconds gauge\n"
                "constellation_exporter_last_run_timestamp_seconds %s\n" % fmt_value(now))
    try:
        write_atomic(a.out, text)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("write failed: %s: %s\n" % (type(e).__name__, e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
