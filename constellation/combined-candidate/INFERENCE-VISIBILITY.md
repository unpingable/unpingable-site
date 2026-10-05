# Inference expenditure in Workbench

An admitted model-backed workflow can use Linear Accountant (LA) to reserve a
finite inference envelope before a call. Workbench can show its owner-exported
accounting record, including the maximum calls, retry ceiling, runtime ceiling
and reserved micro-USD before invocation, then the native settlements afterward.
Workflows without an admitted model consumer do not require LA or a model.

The optional display reads a fixed, owner-selected disclosure file. It does not
open LA's store, run its privileged CLI, invoke a provider, edit a budget or
grant an effect. The LA store owner exports selected native reserve decisions,
inspection and reconciliation results into `constellation.la_selected_records/v1`.
The finite disclosure shape is described below; select only the intended
reservation and operation. Native results stay authoritative.
Protect full store exports separately: Workbench only needs the selected view,
with no provider credential, condition text or private store pathname.

```sh
constellation-inference-view --record /etc/constellation-workbench/inference.json
```

The disclosure carries the exact AG campaign/occurrence and reservation identity,
the native reserve request/decision, selected invocation history, native inspect
envelope and optional milestone reconciliation. It is a recorded assertion,
not a live-store transport. `recorded_at_unix_ms` names the last selected native
event; optional `snapshot_read_at_unix_ms` names the actual inspection time.
An unavailable timestamp stays unknown. A custodian must verify the records;
a file hash identifies bytes and does not authenticate their origin.

To add it to the installed Workbench, the operator installs this file readable
by `constellation-workbench`, mode 0640, in its existing configuration directory
and explicitly adds `--accounting-record /etc/constellation-workbench/inference.json`
to the service's existing ExecStart via a normal systemd override. Retain all
existing manifest, trusted-source, build and loopback-port arguments. Restart
Workbench after `systemctl daemon-reload`. `/api/accounting` and the operator
page expose only the fixed selection; HTTP clients cannot select a file.
No accounting configuration is installed or enabled by default.

The UI separates the **admitted** envelope from a refused **requested** envelope,
native provider-reported actual cost from conservative accounted/consumed call
ceilings, and remaining token capacity from enrollment stock. LA rounds actual
USD upward to integer micro-USD. Workbench does not estimate provider prices or
refund unused allocation. A revoked/closed token's retained capacity is
unavailable for further calls. Unknown actual cost remains null. Exhaustion
stops reasoning and requires escalation; this read-only view offers no
"continue anyway" action.

Accounting remains explicitly recorded even when its exact operation matches
the current typed AG assertion. An unmatched record is prominently a separate
recorded operation. Reconciliation is labeled with its milestone scope and
must not be mistaken for this one operation or for recovery.

LA bounds inference expenditure. AG independently admits effects. Docket keeps
exact attempt/settlement custody. Current observation establishes recovery.
Displaying these records together does not combine their authority.

The Workbench reveal did **not** exercise LA. This later integration uses the
separately accepted remediation-v2 accounting path. V2 remains qualified and
optional; deterministic v1 remains the reference/default remediation behavior.

Formalization consideration: this finite projection preserves native integer
quantities, exact operation joins and accounting-vs-effect distinctions. Tests
cover native recorded ceilings/settlement, retired capacity, missing reads,
foreign operation/settlement joins and exhaustion without action. Exact hashes
and independent review cover the selected-record correspondence. Authentic
owner export and source-store custody remain premises; no proof of arbitrary
record authenticity, live freshness or accounting semantics is asserted.
Decision owner: Constellation integration owner.

## Owner disclosure shape

The existing LA store/consumer custodian supplies the record; Workbench does
not generate it or gain access to the store. Use LA's documented `inspect` and
`reconcile` protocol and the native reserve decision already retained by that
consumer. Export only the chosen operation, not a database or a credential.
This version has no automatic live accounting publisher.

The JSON object has `schema: constellation.la_selected_records/v1`,
`presentation: recorded`, `recorded_at_unix_ms` (last selected native event),
optional `snapshot_read_at_unix_ms`, and `association` with `ag_campaign`,
`ag_occurrence`, `episode_id`, `reservation_id` (null on reserve refusal).
`records` contains one selected native reserve row (`seq`, `at_unix_ms`, `cmd`,
`request`, `result`); additional selected begin/settle/close rows may be retained
for owner custody. `inspect` is the native `v:1/cmd:inspect/result` envelope for
the exact reservation and enrollment. `reconcile` is the native milestone
result or null. A refused reservation has `inspect: null` and `reconcile: null`.
Native field names/units are documented in the public
[LA protocol](https://github.com/unpingable/constellation-linear-accountant/blob/dev/operator-beta/docs/INFERENCE_ACCOUNTING.md).

The projection uses native reserve bounds/provider/model, exact enrollment
join, reservation/invocation/settlement identity, token state and the matching
milestone scope. It omits condition/eligibility text, private custody locators
and unrelated records. A custodian should still minimize the selected input
and verify provenance before placing it in the unprivileged read location.
