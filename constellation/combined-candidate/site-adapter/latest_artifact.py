#!/usr/bin/env python3
"""Print the artifact_id of the newest LOCAL nq.diagnostic_execution.v2 artifact for one watcher instance.

usage: latest_artifact.py NQ_DB INSTANCE_ID        (stdlib only; read-only; no network)

The selected NQ 0.2.4 has NO CLI that lists artifact ids (diagnostics = purpose-support|execute|acquire-next-local|
replay-local-successor|inspect|qualify|export|import; crates/nq-app/src/cli.rs:290-330;
`query` accepts only public_finding_snapshot_v3 / public_status_snapshot_v1, nq-core engine.rs:10034-10066;
evaluation history carries run_id but no artifact_id). This reads the internal schema-v13 tables
(nq-store schema.sql:401 diagnostic_artifact_commitments, :424 local_diagnostic_artifact_origins, :118 watcher_runs).
It is an UNSUPPORTED surface: the frozen source pins NQ 0.2.4/schema13 and fail closed on any schema surprise.
Opened mode=ro (NOT immutable=1), same semantics as nq-store Store::open_read_only.
Export bytes afterwards with:  nq --config /etc/nq/nq.toml diagnostics export "$(latest_artifact.py ...)"
"""
import sqlite3, sys, urllib.parse

SQL = """SELECT c.artifact_id FROM diagnostic_artifact_commitments c
 JOIN local_diagnostic_artifact_origins o ON o.artifact_id = c.artifact_id
 JOIN watcher_runs r ON r.run_id = o.run_id
 WHERE r.instance_id = ? AND c.contract_schema = 'nq.diagnostic_execution.v2'
 ORDER BY c.artifact_sequence DESC LIMIT 1"""

def main():
    if len(sys.argv) != 3:
        sys.exit("usage: latest_artifact.py NQ_DB INSTANCE_ID")
    uri = "file:%s?mode=ro" % urllib.parse.quote(sys.argv[1])
    try:
        con = sqlite3.connect(uri, uri=True, timeout=5)
        ver = con.execute("SELECT schema_version FROM schema_metadata").fetchone()
        if ver != (13,):
            sys.exit('latest_artifact: unsupported internal schema version')
        row = con.execute(SQL, (sys.argv[2],)).fetchone()
    except sqlite3.Error as e:
        sys.exit("latest_artifact: %s" % e)
    if row is None:
        sys.exit("latest_artifact: no local v2 artifact for instance %r (schema_version=%s)" % (sys.argv[2], ver))
    print(row[0])

main()
