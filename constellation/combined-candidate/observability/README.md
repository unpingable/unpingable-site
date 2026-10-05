# Beta Observability MVP

Operational telemetry for the beta: a textfile exporter on the reference host, and
VictoriaMetrics + vmalert + Grafana on central-monitor. It answers "is the machinery
behaving" (is observation current, is Nightshift recurring, is the evaluator
running, how big and how slow is NQ). It is not evidence, not support, and not
a product verdict; the attention evaluator owns product conditions, and
nothing here pages. This directory carries the bounded accepted MVP implementation and carries no deployment authority of its own. Nothing in it touches
a host until the operator deploys it.

```
Linode (nq account)                               central-monitor
constellation-telemetry-exporter.timer (60 s)
  -> /var/lib/constellation-telemetry/constellation.prom
  -> symlink in node_exporter textfile dir
  -> node_exporter :9100 (firewalled)  <== ssh -L ==  127.0.0.1:19100
                                                      VictoriaMetrics :8428 (90 d)
                                                      vmalert :8880 -> ALERTS back into VM
                                                      Grafana 127.0.0.1:3100
```

## Boundary rules

- Metrics are counts, durations, sizes, timestamps, closed enums and bounded
  build identities. Ages are never exported; compute them in PromQL
  (`time() - metric`).
- Never a label value that is an evidence id, artifact digest, subject, path,
  condition id, cycle/slot id, free-text reason, or an unbounded instance
  name. The exporter drops (and counts in
  `constellation_exporter_dropped_label_values`) any operator-configured name
  that is long, slash-bearing, or sha256/uuid shaped.
- Allowed non-enum labels: NQ watcher `instance` and evaluator input `input`
  (operator-configured, at most 32), attention `rule` (closed registry), saved
  check `reference` (at most 16), and `constellation_build_info`
  `version`/`source_commit` (12-char commit).
- Every input is guarded. A missing or unreadable input omits its metric
  families and sets `constellation_exporter_input_ok{input="..."} 0`.
- The exporter reads existing surfaces only. It opens the Nightshift store
  `mode=ro` with `query_only`, never takes the NQ instance lock, never runs
  `nq doctor` or any validation.
- Product metric names in the pack registry are reused where it defines them.
  Names it does not define (the `constellation_attention_*`,
  `constellation_exporter_*`, `constellation_status_site_*`, `*_last_*`
  families, `constellation_tls_days_remaining`, `constellation_build_info`) are
  MVP proposals and need owner acceptance before they become stable.

## Linode deployment (operator)

Run as root. The exporter needs Python 3.10+ and `systemd` only.

```sh
install -d /usr/local/lib/constellation-telemetry
install -m 0755 exporter/constellation-textfile-exporter.py /usr/local/lib/constellation-telemetry/
install -m 0644 exporter/constellation-telemetry-exporter.service \
                exporter/constellation-telemetry-exporter.timer /etc/systemd/system/
systemctl daemon-reload
systemctl start constellation-telemetry-exporter.service   # first run creates the state dir
journalctl -u constellation-telemetry-exporter -n 20       # input errors are logged here
head -40 /var/lib/constellation-telemetry/constellation.prom

# node_exporter's textfile dir is the Debian default; confirm with
# `systemctl cat prometheus-node-exporter` (no --collector.textfile.directory flag expected).
ln -s /var/lib/constellation-telemetry/constellation.prom \
      /var/lib/prometheus/node-exporter/constellation.prom
curl -s 127.0.0.1:9100/metrics | grep -c '^constellation_'

systemctl enable --now constellation-telemetry-exporter.timer
```

Notes: the symlink target must stay traversable by the `prometheus` user
(`/var/lib/constellation-telemetry` is created 0755). node_exporter stats the
symlink itself for `node_textfile_mtime_seconds`, so use
`constellation_exporter_last_run_timestamp_seconds` for freshness. If your
node_exporter refuses to follow the symlink, copy the file instead (for
example an `ExecStartPost=` install into the textfile dir) or add a second
textfile directory flag; do not move the exporter to root. To remove:
`rm` the symlink, disable the timer.

## Optional central dashboards

`central/` contains the existing MVP dashboard, rule and backend configuration,
with image versions matching the qualified reference deployment. Installing the
spine does not start this backend, create a listener or provide a remote credential.
Supply an independently authorized metrics connection at `127.0.0.1:19100`; no
SSH transport or key is included. Review `central/prometheus-scrape.yml` for your
metrics subject. Backend listeners bind only to loopback.

```sh
cd central
cp .env.example .env
chmod 600 .env
# Set GF_SECURITY_ADMIN_PASSWORD before activation.
$EDITOR .env
docker compose up -d
```

This optional backend needs Docker Compose and its declared images. It is not
a runtime dependency of the Jammy spine packages. Grafana listens at
`http://127.0.0.1:3100`; VictoriaMetrics at port8428 and vmalert at8880. The
notifier remains blackholed: operational telemetry alerts do not send pages.
Stop with `docker compose down`; removing volumes is a separate data-loss action.

## Alert subset

`central/rules/constellation-beta.rules.yml` has 15 rules, all
`severity="operational"`: LinodeNodeTargetDown, ExporterStale,
ExporterInputUnreadable, StatusSiteRenderStale, HostPostureUnknownPersisting,
NqWatcherObservationStale, NqStatusExportSlow, NqValidateFullNotSucceeding,
NightshiftRecurrenceMissing, NightshiftTickNotSucceeding,
AttentionEvaluatorStale, AttentionPassNotSucceeding,
AttentionUnresolvedDeliveries, PublicCertificateExpiryNear,
HostRootFilesystemNearFull. They say the machinery looks wrong; they do not
restate evaluator rules and are never PagerDuty-semantic pages. Pack rules whose
metrics do not exist (NQ acquisition and open cost, refusals, retention,
Docket, AG, build identity, `constellation-.*` service-down) are dropped; the
rules file header lists them.

## render-timings.json (status-site renderer)

The exporter reads `/var/www/constellation-status/render-timings.json`, an
optional file the renderer writes atomically next to `status.json` (same
`write_atomic` call, mode 0644) at the end of every render:

```json
{
  "schema": "constellation.status_site_render_timings.v1",
  "rendered_at": "2026-10-03T02:21:41Z",
  "status_export_wall_seconds": 1.25
}
```

`status_export_wall_seconds` is the wall time of the `nq ... status export`
subprocess (`time.monotonic()` around `run(...)` in `load_nq_status`, recorded
even when the command fails). It is the only key the exporter uses; extra keys
(`status_export_rc`, `render_started_at`) are ignored. The file is optional:
if absent the exporter omits `constellation_nq_status_export_duration_seconds`
and reports `constellation_exporter_input_ok{input="render_timings"} 0`, and
no alert depends on it being present. The included renderer
writes this shape.

## Metrics

`constellation_exporter_{last_run_timestamp_seconds,duration_seconds,dropped_label_values,input_ok}`;
`constellation_host_posture_{projection_state,generated_timestamp_seconds,fresh_until_timestamp_seconds}`
(`projection_state` is one-hot over healthy, degraded, partial_outage,
major_outage, unknown, and reads unknown when the artifact is absent or past
`fresh_until`); `constellation_nq_{store_bytes,validation_watermark_*,watcher_observed_timestamp_seconds,status_export_duration_seconds,validate_full_last_*,saved_check_*,evaluation_through_sequence,status_snapshot_timestamp_seconds}`;
`constellation_nightshift_{last_closed_cycle_timestamp_seconds,cycles_total,tick_duration_seconds,tick_last_result,tick_last_timestamp_seconds}`;
`constellation_attention_{report_evaluated_timestamp_seconds,state_updated_timestamp_seconds,pass_*,input_status,conditions,active_conditions,intents_total,unresolved_deliveries}`;
`constellation_status_site_rendered_timestamp_seconds`,
`constellation_tls_days_remaining`, `constellation_build_info`.
`constellation_nightshift_cycles_total` and `constellation_attention_intents_total`
are gauges (store row count; last-pass tally) despite the `_total` names the
pack uses.

## Retained qualification

The accepted MVP qualification exercised missing/corrupt/current/stale inputs and bounded label handling. Test fixtures are deliberately excluded from this runtime bundle.
