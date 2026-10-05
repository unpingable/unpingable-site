# Operate and inspect the prepared spine

Historical accepted spine recipe, supplied for reference configuration details. Run commands from the **combined candidate root**, not this reference subdirectory. Install packages using the main INSTALLATION.md and current PACKAGES.json; the historical nine-package table/explicit install command and 0.2.3→0.2.4 qualification examples below are not the combined install/upgrade path. Main DAY-TWO-RUNBOOK.md defines the exact supplied 0.2.4 predecessor ↔ 0.2.5 combined boundary. No historical qualification record is rewritten or required reading.
This guide covers the source-defined component workflow. Workbench is the intended primary operator surface after its separate integration; use these documented CLI paths when that surface is unavailable or explicitly directs you here. This prepared cohort has no completed combined Workbench or human qualification claim.

## Find identity and current state

Use the package/executable manifest and installation identity commands in [INSTALLATION.md](INSTALLATION.md). Record source/build identity separately from observation time. `systemctl is-active` proves only service-manager state; a successful process or HTTP read does not make its evidence current.

```sh
sudo -u nq nq --config /etc/nq/nq.toml --json status export
sudo -u nq constellation-host-posture preflight /etc/constellation-host-posture/host-posture.toml
sudo -u nq constellation-attention state --config /etc/constellation-attention/attention.toml
sudo -u nq constellation-attention check-config --config /etc/constellation-attention/attention.toml
journalctl --unit constellation-host-posture.service --since '<SCENARIO_START>' --output cat --no-pager
journalctl --unit nightshift-observation-cycle.service --since '<SCENARIO_START>' --output cat --no-pager
journalctl --unit constellation-attention.service --since '<SCENARIO_START>' --output cat --no-pager
```

The status export may be expensive on a growing store. Attention's operated-store profile uses bounded evaluation-history pages rather than rerunning a full status export for each pass. Inspect the existing report at `/var/lib/constellation-attention/report.json`; its `evaluated_at`, input statuses, condition lifecycle and retained intents matter. State/configuration commands inspect; `evaluate`, even `--dry-run`, writes report/artifact output and is not a passive inspection command.

NQ `status` and other native reads may update validation caches or SQLite sidecars. Host-posture preflight checks current enrollment/qualification; it does not create them. Nightshift filesystem support remains unknown, not healthy merely because the cycle closed. A host-posture `fresh_until` is a presentation boundary; it is not proof of Pulse CURRENT support for an unrelated consumer.

## Inspect bounded remediation without requesting work

After a canary episode has created an existing AG campaign, inspect it:

```sh
sudo ag-loopctl inspect --database /var/lib/constellation-remediation/ag/campaign.sqlite
sudo ag-loopctl status --database /var/lib/constellation-remediation/ag/campaign.sqlite
sudo ag-loopctl replay --database /var/lib/constellation-remediation/ag/campaign.sqlite
sudo ag-loopctl history --database /var/lib/constellation-remediation/ag/campaign.sqlite
sudo ag-loopctl refusals --database /var/lib/constellation-remediation/ag/campaign.sqlite
sudo ag-loopctl verify-runtime-profile --runtime-profile /etc/constellation-remediation/runtime-profile.json
```

AG inspect returns the current occurrence, replay and profile binding and verifies digest agreement. These commands advance no engine transition, but open SQLite read/write and may configure sidecars. Use the exact enrolled existing database and documented root access. Before the first episode there may be no campaign; that is not permission to initialize one just for inspection. Finished campaigns can be archived by the consumer; select the exact corresponding retained campaign if examining an earlier episode.

Obtain the exact issuance identity from that episode's retained AG/consumer record, then:

```sh
sudo docket governed-loop inspect --state /var/lib/constellation-remediation/docket --issuance 'sha256:<EXACT_ISSUANCE_HEX>'
journalctl --unit constellation-remediation-consumer.service --since '<SCENARIO_START>' --output cat --no-pager
```

Docket reads that exact existing custody record with a read-only database open, no resolver or executor. Native known, refused, absent and indeterminate custody outcomes stay distinct. The consumer's JSON pass/result/episode summary and exit zero can describe completion, abstention, refusal, escalation, pending or busy; inspect the actual result.

Never call `docket-standing-grant-resolver` to inspect a grant: it consumes a use. Do not replace inspection with AG advance/proposal, Docket dispatch/reconcile, effectd execute/reconcile or LA reserve/recover/settle. These are authority-changing or recovery operations even when they do not produce another external effect.

## Understand a result

The evaluator report is a trigger, not action evidence. The consumer establishes a fresh bound precondition, AG independently checks the pinned work/standing/budget, and Docket retains custody of the exact admitted attempt. A successful start receipt does not prove recovery.

`completed` means the governed start settled as success and a later NQ evaluation, taken at least the configured postcondition dwell after settlement, showed the enrolled unit loaded and active within the resolver freshness bound. The default dwell is 15 seconds. It does not promise durable service recovery: the evaluator requires 120 seconds continuously clear to resolve the condition; relapse can still lead to escalation. This profile starts an inactive or failed unit and does not restart an active-but-wedged application.

Stale, absent, contradictory, unsupported or refused evidence must remain visible. On an exhausted/revoked/expired grant, dispatch can leave AG at `authorization_consumed`; later episodes abstain `prior_campaign_unresolved`. Do not delete or casually archive this spent unresolved campaign. Stop the consumer timer, inspect exact AG/Docket custody and grant-use records, preserve them, and follow an owner-reviewed reconciliation procedure. There is no generic automatic repair for that state.

## Accounting inspection for an already enrolled optional v2

No accounting enrollment or provider credential is needed for v1. On an existing separately enrolled v2 book:

```sh
la_inference version
printf '%s\n' '{"v":1,"cmd":"inspect","reservation_id":null}' | sudo la_inference --store '<EXISTING_BOOK_PATH>' inspect
sudo la_inference --store '<EXISTING_BOOK_PATH>' reconcile --milestone '<ENROLLED_MILESTONE_ID>'
```

Inspect/reconcile make no inference debit, but take a writer lock and may create lock/WAL files or initialize an absent store. Use only the exact named existing production books, root access and every relevant enrolled milestone. Do not use `--dev` or copy/relocate the book; the ordinary CLI refuses changed canonical path/device/inode identity. Check the structured reconciliation verdict, not just exit zero. Provider execution and reporting remain distinct from local accounting recovery.

## Restart, upgrade and rollback

Use [DAY-TWO-RUNBOOK.md](DAY-TWO-RUNBOOK.md) for the prepared NQ 0.2.3 → 0.2.4 lifecycle. It archives with the old binary, retains old store/admissions together, initializes and re-admits a fresh successor, then re-enrolls/prepares the posture generation. An old-store compatibility probe does not establish active cross-build continuity.

After reboot, recheck current observations, host-posture preflight/health, Nightshift recurrence and attention input/outcome state. A timer active with stale data is not healthy. Qualification defaults and the profile's expected unknown support still apply.

Rollback preserves the failed successor and previous exact package/evidence. Reinstalling an older helper changes its inode: restored NQ admission may drift and require explicit re-admission, a fresh acquisition and a new posture policy generation/qualification. Restoring one file from the old generation is insufficient. Returning to an old binary never undoes an externally visible effect or revives spent authority. The deliberately omitted prepare-qualification negative control in the runbook must refuse; do not bypass preflight or widen tolerances.

## Notifications and monitoring

Local-only qualification uses `attention-test` with `local_file`, the owner-selected inbox and `network_enabled = false`. Inspect retained NQ custody and local delivery results; an intent is not proof of delivery or human acknowledgment. The reference canary helper's disabled page route does not permit a production page.

Operational metrics and status-site projections describe machinery liveness; they are neither evidence nor a product verdict, and the included exporter does not page. Missing metrics/input reads and stale renders must stay unknown. Monitoring deployment, listeners, credentials, retention and component permissions are separate explicit owner choices. Do not follow a historical observability recipe as authority to contact a host or enable notification routes.
