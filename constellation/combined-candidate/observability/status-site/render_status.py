#!/usr/bin/env python3
"""Render the public status site for status.example.invalid (site glue, Python 3.10 stdlib).

Reads the current-stack projections read-only, writes index.html, status.json
and projection.sqlite atomically. This is a projection, not an authority: a
missing or stale input renders as "unavailable" with the reason, and never
changes what the underlying components say.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

SCHEMA = "constellation.status_site.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Rule id -> (runbook document key, anchor); mirrors the evaluator registry.
RUNBOOKS = {
    "host-posture-unknown": ("cartography", "host-posture-unknown"),
    "host-disk": ("cartography", "host-disk"),
    "nq-no-fresh-acquisition": ("cartography", "nq-no-fresh-acquisition"),
    "service-down": ("cartography", "service-down"),
    "memory-pressure": ("monitor", "memory-pressure"),
    "nightshift-recurrence-missing": ("cartography", "nightshift-recurrence-missing"),
    "sqlite-health": ("monitor", "sqlite-health"),
    "evaluator-input-unavailable": ("monitor", "evaluator-input-unavailable"),
    "docket-unsettled": ("cartography", "docket-unsettled"),
    "ag-executor-unavailable": ("cartography", "ag-executor-unavailable"),
}
RUNBOOK_DOCS = {
    "cartography": "cartography:architecture/beta-observability/docs/RUNBOOKS.md",
    "monitor": "constellation-monitor:docs/ATTENTION.md",
}


# ---------------------------------------------------------------- helpers

def parse_ts(text):
    """RFC3339 -> unix seconds (float) or None."""
    if not isinstance(text, str):
        return None
    m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?(Z|[+-]\d\d:\d\d)$", text)
    if not m:
        return None
    frac = (m.group(2) or "")[:7]
    tz = "+00:00" if m.group(3) == "Z" else m.group(3)
    try:
        return dt.datetime.fromisoformat(m.group(1) + frac + tz).timestamp()
    except ValueError:
        return None


def iso(unix):
    if unix is None:
        return None
    return dt.datetime.fromtimestamp(unix, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def age(now, then):
    return None if then is None else max(0, int(now - then))


def human(sec):
    if sec is None:
        return "unknown"
    if sec < 120:
        return f"{sec} s"
    if sec < 7200:
        return f"{sec // 60} min"
    if sec < 172800:
        return f"{sec // 3600} h"
    return f"{sec // 86400} d"


def unavailable(reason):
    return {"available": False, "reason": str(reason)[:300]}


def read_json(path, limit=8 * 1024 * 1024):
    with open(path, "rb") as f:
        raw = f.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("file larger than %d bytes" % limit)
    return json.loads(raw.decode("utf-8"))


def run(argv, timeout=15):
    """Run a command without a shell; return (rc, stdout, stderr) or raise."""
    p = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                       timeout=timeout, text=True)
    return p.returncode, p.stdout, p.stderr


def guarded(fn, *a):
    try:
        return fn(*a)
    except Exception as e:  # an input must never crash the render
        return unavailable("%s: %s" % (type(e).__name__, e))


# ---------------------------------------------------------------- inputs

def load_posture(a, now):
    root = a.posture_root
    pointer = read_json(os.path.join(root, "CURRENT"), 65536)
    if pointer.get("schema") != "constellation.status_current_pointer.v1":
        return unavailable("CURRENT has unexpected schema %r" % pointer.get("schema"))
    aid = pointer.get("artifact_id", "")
    hexid = aid.split(":", 1)[1] if aid.startswith("sha256:") else ""
    if not HEX64.match(hexid):
        return unavailable("CURRENT artifact_id is not sha256:<64 hex>")
    obj = read_json(os.path.join(root, "objects", hexid + ".json"), 1024 * 1024)
    if obj.get("schema") != "constellation.status_artifact.v1":
        return unavailable("artifact has unexpected schema %r" % obj.get("schema"))
    gen = obj.get("generated_at_unix_ms")
    fresh = obj.get("fresh_until_unix_ms")
    if not isinstance(gen, int) or not isinstance(fresh, int):
        return unavailable("artifact lacks generated_at/fresh_until")
    comps = []
    for c in obj.get("components") or []:
        comps.append({
            "id": c.get("id"), "state": c.get("state"), "mode": c.get("mode"),
            "reason": c.get("reason"), "display_name": c.get("display_name"),
            "detail": c.get("detail") if isinstance(c.get("detail"), (str, type(None))) else json.dumps(c["detail"])[:200],
        })
    is_fresh = now * 1000 <= fresh
    return {
        "available": True, "artifact_id": aid,
        "aggregate_state": obj.get("aggregate_state"),
        "generated_at": iso(gen / 1000), "fresh_until": iso(fresh / 1000),
        "age_seconds": age(now, gen / 1000), "fresh": is_fresh,
        "projection_id": obj.get("projection_id"),
        "projection_generation": obj.get("projection_generation"),
        "policy_digest": obj.get("policy_digest"),
        "components": comps,
        "stale_reason": None if is_fresh else "status artifact is past fresh_until (%s)" % iso(fresh / 1000),
    }


def load_attention(a, now):
    d = a.attention_dir
    report = read_json(os.path.join(d, "report.json"))
    if report.get("schema") != "constellation.attention_report.v1":
        return unavailable("report.json has unexpected schema %r" % report.get("schema"))
    ev = parse_ts(report.get("evaluated_at"))
    state = None
    state_err = None
    try:
        state = read_json(os.path.join(d, "state.json"))
    except Exception as e:
        state_err = "%s: %s" % (type(e).__name__, e)
    scond = (state or {}).get("conditions") or {}
    rules = {r.get("id"): r for r in report.get("rules") or []}
    active, pending = [], []
    for c in report.get("conditions") or []:
        rule = rules.get(c.get("rule")) or {}
        st = scond.get(c.get("id")) or {}
        rb = RUNBOOKS.get(c.get("rule"))
        item = {
            "id": c.get("id"), "rule": c.get("rule"),
            "severity": rule.get("class") or "unknown",
            "observation": c.get("observation"), "note": c.get("note"),
            "since": c.get("first_seen"),
            "last_seen": iso(st["last_seen"]) if isinstance(st.get("last_seen"), int) else None,
            "persisted_seconds": c.get("persisted_seconds"),
            "persistence_bound_seconds": c.get("persistence_bound_seconds"),
            "runbook": None if rb is None else {
                "document": RUNBOOK_DOCS[rb[0]], "anchor": rb[1],
                "url": _runbook_url(a, rb)},
        }
        if c.get("active"):
            active.append(item)
        elif c.get("first_seen"):
            pending.append(item)
    inputs = [{
        "label": i.get("label"), "kind": i.get("kind"), "status": i.get("status"),
        "error": i.get("error"),
        "identity": i.get("identity") if isinstance(i.get("identity"), dict) else {},
    } for i in report.get("inputs") or []]
    a_age = age(now, ev)
    stale = a_age is None or a_age > a.report_max_age
    return {
        "available": True, "site": report.get("site"),
        "evaluated_at": report.get("evaluated_at"), "age_seconds": a_age,
        "current": not stale,
        "stale_reason": ("evaluator report is %s old (limit %s)" % (human(a_age), human(a.report_max_age))) if stale else None,
        "policy_digest": report.get("attention_policy_digest"),
        "registry": report.get("registry"), "dry_run": bool(report.get("dry_run")),
        "active": active, "pending": pending, "inputs": inputs,
        "unresolved_deliveries": len(report.get("unresolved_deliveries") or []),
        "state_updated_at": iso((state or {}).get("updated_at")) if isinstance((state or {}).get("updated_at"), int) else None,
        "state_error": state_err,
    }


def _runbook_url(a, rb):
    base = a.runbook_url_cartography if rb[0] == "cartography" else a.runbook_url_monitor
    return (base + "#" + rb[1]) if base else None


TIMINGS = {}


def load_nq_status(a, now):
    nq = shutil.which("nq")
    if not nq:
        return unavailable("nq binary not found on PATH")
    t0 = time.monotonic()
    rc, out, err = run([nq, "--config", a.nq_config, "--json", "status", "export"], 60)
    TIMINGS["status_export_wall_seconds"] = round(time.monotonic() - t0, 3)
    TIMINGS["status_export_rc"] = rc
    if rc != 0:
        return unavailable("nq status export exited %d: %s" % (rc, err.strip()[:200]))
    doc = json.loads(out)
    if doc.get("schema") != "nq.status_snapshot.v3":
        return unavailable("status export schema is %r" % doc.get("schema"))
    watchers, store = [], {}
    for c in doc.get("components") or []:
        kind = c.get("kind")
        if kind == "database":
            val = ((c.get("detail") or {}).get("value")) or {}
            store = {"id": c.get("id"), "state": c.get("state"), "code": c.get("code"),
                     "schema_version": val.get("schema_version"),
                     "genesis": val.get("genesis") or val.get("store_genesis")}
        if kind != "instance":
            continue
        res = (((c.get("detail") or {}).get("result")) or {}).get("result") or {}
        evs = []
        for e in res.get("evaluations") or []:
            r = e.get("result") or {}
            st = r.get("state")
            observed = None
            ev0 = r.get("evidence") or []
            if ev0:
                observed = ev0[0].get("observed_at")
            observed = observed or e.get("evaluated_at")
            ts = parse_ts(observed)
            evs.append({
                "evaluation_id": e.get("evaluation_id"),
                "condition": r.get("condition"),
                "state": st if st in ("present", "explicitly_absent") else (st or "unknown"),
                "summary": r.get("summary"),
                "observed_at": observed, "observed_age_seconds": age(now, ts),
                "stale": ts is None or (now - ts) > a.watcher_max_age,
                "detector_digest": (e.get("detector") or {}).get("digest"),
                "profile_digest": ((e.get("profile") or {}).get("profile_digest")),
                "report_digest": (ev0[0].get("report_digest") if ev0 else None),
            })
        watchers.append({"instance": c.get("id"), "state": c.get("state"),
                         "code": c.get("code"), "observed_at": c.get("observed_at"),
                         "outcome": res.get("outcome"), "report_status": res.get("report_status"),
                         "semantic_digest": res.get("semantic_digest"),
                         "evaluations": evs})
    return {"available": True, "generated_at": doc.get("generated_at"),
            "age_seconds": age(now, parse_ts(doc.get("generated_at"))),
            "evaluation_through_sequence": doc.get("evaluation_through_sequence"),
            "store": store, "watchers": watchers}


def load_saved_checks(a, now):
    doc = read_json(a.saved_checks)
    if doc.get("schema") != "nq-ops.saved-check-run.v1":
        return unavailable("latest.json has unexpected schema %r" % doc.get("schema"))
    gen = parse_ts(doc.get("generated_at"))
    g_age = age(now, gen)
    nq = shutil.which("nq")
    results = []
    for r in doc.get("results") or []:
        digest, dnote = None, None
        if nq and r.get("evaluation_id"):
            try:
                rc, out, err = run([nq, "--config", a.nq_config, "--json", "saved-check",
                                    "result", "--evaluation-id", r["evaluation_id"]], 20)
                if rc == 0:
                    digest = (((json.loads(out).get("detail") or {}).get("binding")) or {}).get("definition_digest")
                else:
                    dnote = "nq saved-check result exited %d" % rc
            except Exception as e:
                dnote = "%s: %s" % (type(e).__name__, e)
        elif not nq:
            dnote = "nq not on PATH"
        results.append({
            "evaluation_id": r.get("evaluation_id"), "reference": r.get("reference"),
            "target": r.get("target"), "source_observed_at": r.get("source_observed_at"),
            "outcome": r.get("outcome"), "refusal_reason": r.get("refusal_reason"),
            "rc": r.get("rc"), "definition_digest": digest, "digest_note": dnote})
    stale = g_age is None or g_age > a.saved_max_age
    return {"available": True, "run_id": doc.get("run_id"), "generated_at": doc.get("generated_at"),
            "age_seconds": g_age, "current": not stale,
            "stale_reason": ("saved-check run is %s old (limit %s)" % (human(g_age), human(a.saved_max_age))) if stale else None,
            "results": results}


def load_nightshift(a, now):
    path = a.nightshift_db
    if not os.path.exists(path):
        return unavailable("store not found")
    con = sqlite3.connect("file:%s?mode=ro" % path, uri=True, timeout=5)
    try:
        con.execute("PRAGMA query_only=1")
        closed = con.execute(
            "SELECT cycle_id, updated_at, snapshot_json FROM canonical_observation_cycles "
            "WHERE status='closed' ORDER BY updated_at DESC LIMIT 1").fetchone()
        newest = con.execute(
            "SELECT cycle_id, status, updated_at, snapshot_json FROM canonical_observation_cycles "
            "ORDER BY updated_at DESC LIMIT 1").fetchone()
    finally:
        con.close()

    def attn(js):
        try:
            at = (json.loads(js) or {}).get("attention") or {}
            return {"class": at.get("class"), "reason_code": at.get("reason_code")}
        except Exception:
            return {"class": None, "reason_code": None}

    out = {"available": True, "last_closed": None, "newest": None}
    if closed:
        ts = parse_ts(closed[1])
        out["last_closed"] = {"cycle_id": closed[0], "updated_at": closed[1],
                              "age_seconds": age(now, ts), "attention": attn(closed[2]),
                              "current": ts is not None and (now - ts) <= a.nightshift_max_age}
    if newest:
        out["newest"] = {"cycle_id": newest[0], "status": newest[1], "updated_at": newest[2],
                         "age_seconds": age(now, parse_ts(newest[2])), "attention": attn(newest[3])}
    out["max_age_seconds"] = a.nightshift_max_age
    return out


def load_builds(a, now):
    items = {}

    def ver(name, argv):
        exe = shutil.which(argv[0])
        if not exe:
            items[name] = unavailable("%s not found on PATH" % argv[0])
            return
        try:
            rc, out, err = run([exe] + argv[1:], 10)
            text = (out or err).strip()
            items[name] = {"available": rc == 0, "text": text[:600],
                           **({} if rc == 0 else {"reason": "exit %d" % rc})}
        except Exception as e:
            items[name] = unavailable("%s: %s" % (type(e).__name__, e))

    ver("nq", ["nq", "--version"])
    ver("constellation-host-posture", ["constellation-host-posture", "--build-info"])
    ver("nightshift", ["nightshift", "--version"])
    pkgs = {}
    dpkg = shutil.which("dpkg-query")
    if dpkg:
        for p in ("nq-ng", "constellation-host-posture", "constellation-nightshift"):
            try:
                rc, out, err = run([dpkg, "-W", "-f=${Version}", p], 10)
                pkgs[p] = {"available": True, "version": out.strip()} if rc == 0 and out.strip() \
                    else unavailable("not installed")
            except Exception as e:
                pkgs[p] = unavailable("%s: %s" % (type(e).__name__, e))
    else:
        for p in ("nq-ng", "constellation-host-posture", "constellation-nightshift"):
            pkgs[p] = unavailable("dpkg-query not found")
    return {"available": True, "binaries": items, "packages": pkgs}


def load_tls(a, now):
    if a.no_tls:
        return unavailable("TLS probe disabled")
    ossl = shutil.which("openssl")
    if not ossl:
        return unavailable("openssl not found")
    p = subprocess.run([ossl, "s_client", "-connect", a.tls_connect, "-servername", a.tls_host],
                       input="", capture_output=True, text=True, timeout=15)
    m = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", p.stdout, re.S)
    if not m:
        return unavailable("no certificate returned by %s" % a.tls_connect)
    q = subprocess.run([ossl, "x509", "-noout", "-enddate", "-subject", "-issuer"],
                       input=m.group(0), capture_output=True, text=True, timeout=10)
    fields = dict(l.split("=", 1) for l in q.stdout.splitlines() if "=" in l)
    end = fields.get("notAfter")
    try:
        exp = dt.datetime.strptime(end, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=dt.timezone.utc).timestamp()
    except Exception:
        return unavailable("could not parse certificate notAfter %r" % end)
    return {"available": True, "host": a.tls_host, "not_after": iso(exp),
            "days_remaining": int((exp - now) // 86400),
            "issuer": fields.get("issuer", "").strip()[:200]}


# ---------------------------------------------------------------- assembly

def build_status(a, now):
    posture = guarded(load_posture, a, now)
    attention = guarded(load_attention, a, now)
    nqs = guarded(load_nq_status, a, now)
    saved = guarded(load_saved_checks, a, now)
    ns = guarded(load_nightshift, a, now)
    builds = guarded(load_builds, a, now)
    tls = guarded(load_tls, a, now)

    if not attention.get("available"):
        state, why = "unknown", "evaluator report unavailable: " + attention["reason"]
    elif not attention["current"]:
        state, why = "unknown", attention["stale_reason"]
    elif attention["active"]:
        state, why = "attention", "%d active condition(s)" % len(attention["active"])
    else:
        state, why = "all_clear", "no active attention conditions"

    prov = {
        "status_artifact_id": posture.get("artifact_id") if posture.get("available") else None,
        "posture_generated_at": posture.get("generated_at") if posture.get("available") else None,
        "nq_snapshot_generated_at": nqs.get("generated_at") if nqs.get("available") else None,
        "nq_evaluation_through_sequence": nqs.get("evaluation_through_sequence") if nqs.get("available") else None,
        "nq_store": nqs.get("store") if nqs.get("available") else None,
        "nightshift_cycle_id": ((ns.get("last_closed") or {}).get("cycle_id")) if ns.get("available") else None,
        "attention_policy_digest": attention.get("policy_digest") if attention.get("available") else None,
        "saved_check_run_id": saved.get("run_id") if saved.get("available") else None,
        "saved_check_evaluations": [
            {"reference": r["reference"], "evaluation_id": r["evaluation_id"],
             "definition_digest": r["definition_digest"]}
            for r in (saved.get("results") or [])] if saved.get("available") else [],
        "unavailable": {k: v["reason"] for k, v in (
            ("host_posture", posture), ("attention_report", attention), ("nq_status", nqs),
            ("saved_checks", saved), ("nightshift", ns)) if not v.get("available")},
    }
    return {
        "schema": SCHEMA, "rendered_at": iso(now), "rendered_at_unix": int(now),
        "refresh_seconds": 300,
        "notice": "Projection, not authority: a stale or missing page is an interface failure, not a change in product truth.",
        "attention_state": {"state": state, "reason": why},
        "attention": {"report": attention, "host_posture": posture},
        "support": {"watchers": nqs, "saved_checks": saved, "nightshift": ns},
        "provenance": prov,
        "substrate": {"builds": builds, "tls": tls},
    }


REQUIRED = {
    "schema": str, "rendered_at": str, "rendered_at_unix": int, "attention_state": dict,
    "attention": dict, "support": dict, "provenance": dict, "substrate": dict,
}


def validate_status(doc):
    """Return a list of problems (empty when the document is well-formed)."""
    errs = []
    if not isinstance(doc, dict):
        return ["not an object"]
    for k, t in REQUIRED.items():
        if not isinstance(doc.get(k), t):
            errs.append("%s missing or not %s" % (k, t.__name__))
    if doc.get("schema") != SCHEMA:
        errs.append("schema is not " + SCHEMA)
    st = (doc.get("attention_state") or {}).get("state")
    if st not in ("all_clear", "attention", "unknown"):
        errs.append("attention_state.state invalid: %r" % st)
    for path in (("attention", "report"), ("attention", "host_posture"),
                 ("support", "watchers"), ("support", "saved_checks"),
                 ("support", "nightshift"), ("substrate", "builds"), ("substrate", "tls")):
        node = (doc.get(path[0]) or {}).get(path[1])
        if not isinstance(node, dict) or not isinstance(node.get("available"), bool):
            errs.append("%s.%s lacks boolean 'available'" % path)
        elif not node["available"] and not node.get("reason"):
            errs.append("%s.%s unavailable without reason" % path)
    return errs


# ---------------------------------------------------------------- HTML

E = html.escape


def _na(node):
    return '<p class="na">unavailable: %s</p>' % E(node.get("reason", "unknown"))


def render_html(s):
    out = []
    w = out.append
    st = s["attention_state"]
    att = s["attention"]["report"]
    hp = s["attention"]["host_posture"]
    sup = s["support"]
    prov = s["provenance"]
    sub = s["substrate"]

    w("<!doctype html><html lang=en><head><meta charset=utf-8>"
      "<meta http-equiv=refresh content=300>"
      "<meta name=viewport content='width=device-width,initial-scale=1'>"
      "<title>Constellation status</title><style>"
      ":root{color-scheme:light dark;--bg:#fff;--fg:#1b1f23;--mut:#5b6670;--line:#d6dbe0;--ok:#116329;--warn:#9a6700;--bad:#b42318}"
      "@media(prefers-color-scheme:dark){:root{--bg:#14171a;--fg:#e4e7ea;--mut:#9aa5b0;--line:#2d343b;--ok:#56d364;--warn:#e3b341;--bad:#ff7b72}}"
      "body{margin:0 auto;max-width:60rem;padding:1rem 16px 3rem;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}"
      "h1{font-size:1.4rem;margin:.2rem 0}h2{font-size:1.1rem;margin:2rem 0 .4rem;border-bottom:1px solid var(--line)}"
      "h3{font-size:.95rem;margin:1rem 0 .3rem}table{border-collapse:collapse;width:100%;font-size:.88rem}"
      "td,th{text-align:left;padding:.25rem .5rem;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}"
      "code{font:.85em ui-monospace,monospace}.mut,.na{color:var(--mut)}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}"
      ".banner{font-size:1.1rem;padding:.6rem .8rem;border:1px solid var(--line);border-left-width:5px}"
      ".tw{overflow-x:auto}"
      "</style></head><body>")
    w("<h1>Constellation status</h1>")
    w('<p class=mut>Rendered %s. Auto-refreshes every 5 min. This page is a projection of the '
      'underlying components, not an authority; if it is stale or a section is unavailable, that is an '
      'interface failure, not a change in product truth.</p>' % E(s["rendered_at"]))

    # Layer 1
    w("<h2 id=attention>1. Current attention</h2>")
    cls, text = {
        "all_clear": ("ok", "All clear: no active attention conditions."),
        "attention": ("bad", "Attention: %s." % st["reason"]),
        "unknown": ("warn", "Attention state unknown: %s. This is an interface problem, not an all-clear." % st["reason"]),
    }[st["state"]]
    w('<p class="banner %s">%s</p>' % (cls, E(text)))
    if att.get("available"):
        w('<p class=mut>Evaluator report evaluated %s (%s ago)%s; %d condition(s) pending below their persistence bound.</p>' % (
            E(att["evaluated_at"] or "?"), E(human(att["age_seconds"])),
            ", dry run" if att["dry_run"] else "", len(att["pending"])))
        if att["active"]:
            w('<div class=tw><table><tr><th>Severity<th>Condition<th>Since<th>Runbook</tr>')
            for c in att["active"]:
                rb = c["runbook"]
                if rb and rb["url"]:
                    link = '<a href="%s">%s#%s</a>' % (E(rb["url"], True), E(rb["document"]), E(rb["anchor"]))
                elif rb:
                    link = "<code>%s#%s</code>" % (E(rb["document"]), E(rb["anchor"]))
                else:
                    link = '<span class=mut>none registered</span>'
                w("<tr><td class=bad>%s<td><code>%s</code><br><span class=mut>%s</span><td>%s<td>%s</tr>" % (
                    E(c["severity"]), E(c["id"] or ""), E(c["note"] or ""), E(c["since"] or "?"), link))
            w("</table></div>")
    else:
        w(_na(att))
    w("<h3>Host posture</h3>")
    if hp.get("available"):
        c2 = {"healthy": "ok", "degraded": "bad", "unknown": "warn"}.get(hp["aggregate_state"], "warn")
        w('<p>Aggregate: <strong class="%s">%s</strong>, generated %s (%s ago)%s.</p>' % (
            c2, E(str(hp["aggregate_state"])), E(hp["generated_at"]), E(human(hp["age_seconds"])),
            "" if hp["fresh"] else ' <span class=warn>(past fresh_until %s: stale)</span>' % E(hp["fresh_until"])))
        if hp["components"]:
            w("<div class=tw><table><tr><th>Component<th>State<th>Mode<th>Note</tr>")
            for c in hp["components"]:
                note = c.get("reason") or c.get("display_name") or ""
                w("<tr><td><code>%s</code><td>%s<td>%s<td>%s</tr>" % (
                    E(str(c["id"])), E(str(c["state"])), E(str(c["mode"] or "")), E(str(note))))
            w("</table></div>")
    else:
        w(_na(hp))

    # Layer 2
    w("<h2 id=support>2. Support and disposition</h2><h3>Watchers (NQ instances)</h3>")
    wt = sup["watchers"]
    if wt.get("available"):
        w("<p class=mut>NQ snapshot generated %s (%s ago).</p>" % (E(wt["generated_at"] or "?"), E(human(wt["age_seconds"]))))
        w("<div class=tw><table><tr><th>Instance<th>Condition<th>Disposition<th>Observed<th>Summary</tr>")
        for i in wt["watchers"]:
            if not i["evaluations"]:
                w("<tr><td><code>%s</code><td colspan=4 class=mut>no evaluations (%s)</tr>" % (E(str(i["instance"])), E(str(i["code"]))))
            for e in i["evaluations"]:
                c3 = "bad" if e["state"] == "present" else ("warn" if e["stale"] or e["state"] != "explicitly_absent" else "ok")
                w("<tr><td><code>%s</code><td>%s<td class=%s>%s<td>%s (%s ago)%s<td>%s</tr>" % (
                    E(str(i["instance"])), E(str(e["condition"])), c3, E(str(e["state"]).replace("_", " ")),
                    E(str(e["observed_at"])), E(human(e["observed_age_seconds"])),
                    " <span class=warn>stale</span>" if e["stale"] else "", E(str(e["summary"] or ""))))
        w("</table></div>")
    else:
        w(_na(wt))
    w("<h3>Saved checks</h3>")
    sc = sup["saved_checks"]
    if sc.get("available"):
        w("<p class=mut>Run %s generated %s (%s ago)%s.</p>" % (
            E(str(sc["run_id"])), E(sc["generated_at"] or "?"), E(human(sc["age_seconds"])),
            "" if sc["current"] else "; <span class=warn>%s</span>" % E(sc["stale_reason"])))
        w("<div class=tw><table><tr><th>Check<th>Outcome<th>Source observed</tr>")
        for r in sc["results"]:
            c4 = {"passed": "ok", "failed": "bad"}.get(r["outcome"], "warn")
            extra = " (%s)" % r["refusal_reason"] if r["refusal_reason"] else ""
            w("<tr><td><code>%s</code><td class=%s>%s%s<td>%s</tr>" % (
                E(str(r["reference"])), c4, E(str(r["outcome"] or "no result")), E(extra), E(str(r["source_observed_at"]))))
        w("</table></div>")
    else:
        w(_na(sc))
    w("<h3>Nightshift observation cycles</h3>")
    ns = sup["nightshift"]
    if ns.get("available"):
        lc = ns["last_closed"]
        if lc:
            w("<p>Last closed cycle: %s ago (%s)%s; attention class <code>%s</code> / <code>%s</code>.</p>" % (
                E(human(lc["age_seconds"])), E(lc["updated_at"]),
                "" if lc["current"] else ' <span class=warn>older than %s</span>' % E(human(ns["max_age_seconds"])),
                E(str(lc["attention"]["class"])), E(str(lc["attention"]["reason_code"]))))
        else:
            w("<p class=warn>No closed cycle recorded.</p>")
        nw = ns["newest"]
        if nw:
            w("<p class=mut>Newest cycle: status %s, %s ago.</p>" % (E(nw["status"]), E(human(nw["age_seconds"]))))
    else:
        w(_na(ns))
    if att.get("available"):
        w("<h3>Evaluator inputs</h3><div class=tw><table><tr><th>Input<th>Kind<th>Currentness<th>Note</tr>")
        for i in att["inputs"]:
            c5 = "ok" if i["status"] == "ok" else "warn"
            w("<tr><td><code>%s</code><td>%s<td class=%s>%s<td>%s</tr>" % (
                E(str(i["label"])), E(str(i["kind"])), c5, E(str(i["status"]).replace("_", " ")), E(str(i["error"] or ""))))
        w("</table></div>")
        if att["unresolved_deliveries"]:
            w("<p class=warn>%d notification delivery(ies) unresolved.</p>" % att["unresolved_deliveries"])

    # Layer 3
    w("<h2 id=provenance>3. Evidence and provenance</h2><div class=tw><table>")

    def row(k, v):
        w("<tr><th>%s<td><code>%s</code></tr>" % (E(k), E(str(v)) if v is not None else "<span class=mut>unavailable</span>"))
    row("Status artifact id", prov["status_artifact_id"])
    row("Host posture generated_at", prov["posture_generated_at"])
    row("NQ snapshot generated_at", prov["nq_snapshot_generated_at"])
    row("NQ evaluation through sequence", prov["nq_evaluation_through_sequence"])
    store = prov["nq_store"]
    row("NQ store", None if store is None else "database %s: schema_version %s" % (store.get("state"), store.get("schema_version")))
    row("NQ store genesis", None if store is None else (store.get("genesis") or "not exposed by status export"))
    row("Nightshift last closed cycle id", prov["nightshift_cycle_id"])
    row("Attention policy digest", prov["attention_policy_digest"])
    row("Saved-check run id", prov["saved_check_run_id"])
    for r in prov["saved_check_evaluations"]:
        row("Saved check %s" % r["reference"], "%s | definition %s" % (r["evaluation_id"], r["definition_digest"] or "unavailable"))
    w("</table></div>")
    if prov["unavailable"]:
        w("<p class=warn>Unavailable inputs: %s.</p>" % E("; ".join("%s (%s)" % kv for kv in prov["unavailable"].items())))

    # Layer 4
    w("<h2 id=substrate>4. Raw substrate</h2><div class=tw><table>")
    b = sub["builds"]
    if b.get("available"):
        for name, v in b["binaries"].items():
            w("<tr><th>%s<td>%s</tr>" % (E(name), "<code>%s</code>" % E(v["text"]) if v.get("available") else '<span class=na>unavailable: %s</span>' % E(v.get("reason", ""))))
        for name, v in b["packages"].items():
            w("<tr><th>package %s<td>%s</tr>" % (E(name), "<code>%s</code>" % E(v["version"]) if v.get("available") else '<span class=na>unavailable: %s</span>' % E(v.get("reason", ""))))
    else:
        w("<tr><td>%s</tr>" % _na(b))
    t = sub["tls"]
    if t.get("available"):
        w("<tr><th>TLS %s<td>expires %s (%d days)</tr>" % (E(t["host"]), E(t["not_after"]), t["days_remaining"]))
    else:
        w("<tr><th>TLS<td>%s</tr>" % _na(t))
    w("<tr><th>Rendered at<td><code>%s</code></tr></table></div>" % E(s["rendered_at"]))
    w("<p class=mut>Machine-readable: <a href=status.json>status.json</a> (schema <code>%s</code>).</p>" % SCHEMA)
    w("</body></html>\n")
    return "".join(out)


# ---------------------------------------------------------------- projection

def build_projection(path, s, now):
    if os.path.exists(path):
        os.unlink(path)
    con = sqlite3.connect(path)
    try:
        con.executescript("""
        CREATE TABLE current_attention(condition_id TEXT, rule TEXT, severity TEXT, active INTEGER, since TEXT, last_seen TEXT, runbook TEXT, note TEXT, projected_at TEXT NOT NULL);
        CREATE TABLE watchers(instance TEXT, condition_name TEXT, state TEXT, observed_at TEXT, observed_age_seconds INTEGER, stale INTEGER, evaluation_id TEXT, summary TEXT, projected_at TEXT NOT NULL);
        CREATE TABLE saved_checks(reference TEXT, evaluation_id TEXT, outcome TEXT, refusal_reason TEXT, source_observed_at TEXT, definition_digest TEXT, run_generated_at TEXT, projected_at TEXT NOT NULL);
        CREATE TABLE nightshift_cycles(which TEXT, cycle_id TEXT, status TEXT, updated_at TEXT, age_seconds INTEGER, attention_class TEXT, attention_reason TEXT, projected_at TEXT NOT NULL);
        CREATE TABLE host_posture(artifact_id TEXT, aggregate_state TEXT, generated_at TEXT, fresh_until TEXT, fresh INTEGER, component_id TEXT, component_state TEXT, component_mode TEXT, projected_at TEXT NOT NULL);
        CREATE TABLE installed_builds(name TEXT, kind TEXT, version_text TEXT, available INTEGER, reason TEXT, projected_at TEXT NOT NULL);
        """)
        p = iso(now)
        att = s["attention"]["report"]
        if att.get("available"):
            for c in att["active"] + att["pending"]:
                rb = c["runbook"]
                con.execute("INSERT INTO current_attention VALUES(?,?,?,?,?,?,?,?,?)", (
                    c["id"], c["rule"], c["severity"], 1 if c in att["active"] else 0, c["since"],
                    c["last_seen"], rb and "%s#%s" % (rb["document"], rb["anchor"]), c["note"], p))
        wt = s["support"]["watchers"]
        if wt.get("available"):
            for i in wt["watchers"]:
                for e in i["evaluations"]:
                    con.execute("INSERT INTO watchers VALUES(?,?,?,?,?,?,?,?,?)", (
                        i["instance"], e["condition"], e["state"], e["observed_at"],
                        e["observed_age_seconds"], int(e["stale"]), e["evaluation_id"], e["summary"], p))
        sc = s["support"]["saved_checks"]
        if sc.get("available"):
            for r in sc["results"]:
                con.execute("INSERT INTO saved_checks VALUES(?,?,?,?,?,?,?,?)", (
                    r["reference"], r["evaluation_id"], r["outcome"], r["refusal_reason"],
                    r["source_observed_at"], r["definition_digest"], sc["generated_at"], p))
        ns = s["support"]["nightshift"]
        if ns.get("available"):
            lc = ns["last_closed"]
            if lc:
                con.execute("INSERT INTO nightshift_cycles VALUES(?,?,?,?,?,?,?,?)", (
                    "last_closed", lc["cycle_id"], "closed", lc["updated_at"], lc["age_seconds"],
                    lc["attention"]["class"], lc["attention"]["reason_code"], p))
            nw = ns["newest"]
            if nw:
                con.execute("INSERT INTO nightshift_cycles VALUES(?,?,?,?,?,?,?,?)", (
                    "newest", nw["cycle_id"], nw["status"], nw["updated_at"], nw["age_seconds"],
                    nw["attention"]["class"], nw["attention"]["reason_code"], p))
        hp = s["attention"]["host_posture"]
        if hp.get("available"):
            for c in hp["components"] or [{"id": None, "state": None, "mode": None}]:
                con.execute("INSERT INTO host_posture VALUES(?,?,?,?,?,?,?,?,?)", (
                    hp["artifact_id"], hp["aggregate_state"], hp["generated_at"], hp["fresh_until"],
                    int(hp["fresh"]), c["id"], c["state"], c["mode"], p))
        b = s["substrate"]["builds"]
        if b.get("available"):
            for n, v in b["binaries"].items():
                con.execute("INSERT INTO installed_builds VALUES(?,?,?,?,?,?)", (
                    n, "binary", v.get("text"), int(bool(v.get("available"))), v.get("reason"), p))
            for n, v in b["packages"].items():
                con.execute("INSERT INTO installed_builds VALUES(?,?,?,?,?,?)", (
                    n, "package", v.get("version"), int(bool(v.get("available"))), v.get("reason"), p))
        con.commit()
    finally:
        con.close()
    os.chmod(path, 0o644)


def write_atomic(dirpath, name, data, mode=0o644):
    fd, tmp = tempfile.mkstemp(prefix="." + name + ".", dir=dirpath)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, os.path.join(dirpath, name))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="/var/www/constellation-status")
    ap.add_argument("--posture-root", default="/var/lib/constellation-host-posture/status")
    ap.add_argument("--nq-config", default="/etc/nq/nqd-ops.toml")
    ap.add_argument("--saved-checks", default="/var/lib/nq-ops-results/latest.json")
    ap.add_argument("--attention-dir", default="/var/lib/constellation-attention",
                    help="directory holding report.json and state.json (the evaluator's state_path directory)")
    ap.add_argument("--nightshift-db", default="/var/lib/constellation-nightshift-observation/nightshift.sqlite")
    ap.add_argument("--tls-host", default="status.example.invalid")
    ap.add_argument("--tls-connect", default="127.0.0.1:443")
    ap.add_argument("--no-tls", action="store_true")
    ap.add_argument("--runbook-url-cartography", default="")
    ap.add_argument("--runbook-url-monitor", default="")
    ap.add_argument("--report-max-age", type=int, default=900)
    ap.add_argument("--saved-max-age", type=int, default=1800)
    ap.add_argument("--watcher-max-age", type=int, default=600)
    ap.add_argument("--nightshift-max-age", type=int, default=3600)
    ap.add_argument("--now", default=None, help="RFC3339 override (tests)")
    a = ap.parse_args(argv)
    now = parse_ts(a.now) if a.now else dt.datetime.now(dt.timezone.utc).timestamp()
    if now is None:
        ap.error("--now is not RFC3339")

    status = build_status(a, now)
    os.makedirs(a.out, exist_ok=True)
    TIMINGS["render_started_at"] = iso(time.time())
    tmpdb = os.path.join(a.out, ".projection.sqlite.%d" % os.getpid())
    try:
        build_projection(tmpdb, status, now)
        os.replace(tmpdb, os.path.join(a.out, "projection.sqlite"))
    except Exception as e:  # projection failure must not block the page
        if os.path.exists(tmpdb):
            os.unlink(tmpdb)
        status["projection_error"] = "%s: %s" % (type(e).__name__, e)
    write_atomic(a.out, "status.json", (json.dumps(status, indent=1, sort_keys=True) + "\n").encode())
    TIMINGS["rendered_at"] = iso(time.time()); TIMINGS["schema"] = "constellation.status_site_render_timings.v1"
    write_atomic(a.out, "render-timings.json", (json.dumps(TIMINGS, sort_keys=True) + "\n").encode())
    write_atomic(a.out, "index.html", render_html(status).encode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
