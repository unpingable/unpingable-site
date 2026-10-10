# Glossary

Terms that appear in these documents, the Workbench pages and native command output, each defined from the component that owns it. The onboarding guides name the release approver, installing operator, study facilitator or component explicitly. Some native output retains broader historical terms.

## The product and its parts

- **Operational EDA**: an analogy and product direction ("EDA for operations"): model and instrument a system, establish what is currently known, diagnose within bounds, govern changes and independently verify the result.
- **Operational spine**: the installed components working together (NQ, Monitor, AG, Docket, Nightshift and, optionally, LA) underneath Workbench.
- **Workbench**: the read-only web pages on 127.0.0.1:18861 that project what the other components assert; it holds no authority of its own.
- **NQ**: the observation and evaluation component; here it watches the enrolled unit's systemd state through `nqd-ops.service`.
- **Monitor**: the present-confidence component, which judges whether current evidence supports a claim now; Workbench shows its judgment (current, stale, contradictory, and so on) under Currentness and Judgment.
- **AG**: the governor that owns each attempt's state machine and spends the one-use authorization; its CLI is `ag-loopctl`.
- **Docket**: the execution-custody component that receives the authorized action, runs it through the executor and records the receipt and settlement.
- **LA** (Linear Accountant): optional accounting for model inference spend in remediation v2; not used by the local exercise.
- **Nightshift**: the scheduled observation-cycle component of the reference spine; not used by the local exercise.
- **Native**: produced by the owning component itself (for example `ag-loopctl` or the NQ reader) rather than reinterpreted by Workbench.
- **Cohort**: the hosts and units one Workbench installation reads, fixed by `/etc/constellation-workbench/live-cohort.json`; here, one VM and one unit.

## Releases and identity

- **BC1 / Beta Candidate 1**: the planned first beta release; this archive is a prepared candidate; it is not approved, not published and not BC1.
- **Neutral candidate**: this archive, with machine-specific and private material removed for an explicit trial on a supported fresh private VM.
- **Owner**: a historical overloaded label. The guides use **release approver**, **operator**, **study facilitator** or the component name instead. Native “owner assertion” means the named component’s claim.
- **Owner assertion**: a claim shown in Workbench exactly as the component that owns it made it, labelled with that component's name.
- **`commit` vs `accepted_runtime_source`** (SOURCE-IDENTITIES.json): `commit` is the current source revision, which may differ only in docs or packaging; `accepted_runtime_source` is the revision the shipped executables were built from.
- **Documentary source**: the source revision Workbench was built from, shown as a label; it identifies bytes and grants no promotion or authority.
- **Promotion**: in the Workbench banner it only says that the label does not turn this build into the reference installation.
- **Reveal**: the earlier recorded Workbench demonstration campaign; "the reveal did not exercise LA" means that campaign never used LA.
- **Tier 5**: qualification substrate 5 of 6 in Workbench's scale, an orchestrated (k3s) application; "bounded Tier-5 standing" means Kubernetes observation and diagnosis were accepted there, with no executor.
- **Semantic generation**: a version of what the observation and evaluation rules mean, as opposed to a package version; the supplied .1 to .2 upgrade does not change it.
- **NQ admission / re-admission boundary**: NQ records the exact helper executables it trusts; replacing one changes its file identity and can require explicit re-admission before NQ accepts it again.
- **Historical recovery custody**: older NQ 0.2.4 packages kept privately for owner rollback and deliberately not shipped here.
- **`historical_custody_only`**: NQ's label on an exported observation record meaning it is a stored copy that grants no currentness and no effect authority.

## Observation and judgment

- **Current**: Monitor judges the claim (here "the unit is active in this boot") supported by evidence within its age bound and from the current boot.
- **Contradictory**: fresh, current-boot evidence contradicts the claim; under Currentness this means the unit is not active, not that the data is old.
- **Stale**: the evidence is past its age bound (`source_or_evaluation_expired`), for example when the collector is stopped.
- **`present` / `explicitly_absent` / `cannot_evaluate`**: NQ condition states meaning the problem condition is shown present, shown absent by sufficient current evidence, or cannot be judged.
- **Gaps / owner gaps**: in this release, a list of failed native reads or missing required observations; it does not list things that were never instrumented, such as HTTP.
- **Inspect dependency health**: no command of that name exists; for package dependencies use `sudo dpkg --audit` (empty output means consistent).

## Governed action

- **Occurrence**: AG's durable record of one attempt at one exact piece of work; authority belongs to exactly one occurrence.
- **Standing**: In AG and Docket it is the current permission to act (the enrolled mandate and grant, checked by `require-standing`); elsewhere it means the accepted status of a qualification claim.
- **Standing grant**: Docket's owner-issued grant to execute the enrolled action, here limited to one use and two hours; resolving it consumes a use, so never probe it.
- **Admissible governed Start**: AG's `decide` found the fixed Start of the enrolled unit allowed under current evidence and standing (`admissible_pending_authorization`); nothing has run yet.
- **Settlement**: Docket's final record of what the dispatched action did (for example `outcome: success` or `outcome: failure`), with its receipt. It is the result of the governed Start; Workbench prints it as the settlement sentence on the attempt line.
- **`completed`** (AG state): the enrolled unit was observed active after settlement. It does not by itself mean the governed Start succeeded: on the try and manual paths AG can reach `completed` after a failed settlement when something else made the unit active ([known issues](KNOWN-ISSUES.md)).
- **Custody / Docket custody**: Docket holding the authorized action and its receipt and settlement records so that they cannot be replaced or re-run.
- **Authority-empty successor**: the new occurrence opened by `continue` after settlement; it holds no grant and only waits for fresh evidence, so its own settlement and receipt fields are `null`.
- **Independent postcondition**: the fresh observation, taken after settlement, that the unit is active; `complete` succeeds only on it, not on the action's receipt.
- **Dwell requirement**: the local exercise configures no dwell value (the reference deterministic remediation in reference/OPERATIONS.md has its own postcondition dwell, default 15 seconds), and in the local exercise `complete` returns `CURRENT_POSTCONDITION_REQUIRED` (a native reader/action facade precheck before AG’s authoritative validation) while Monitor does not yet judge a fresh active observation of the unit `current`.
- **State custody / owner-managed rollback custody**: retained protected recovery records; in practice, keep a copy of `/etc/constellation-live-ecad` and `/var/lib/constellation-live-ecad` before changing packages and do not edit them.
- **Owner reconciliation**: operator review of unresolved records; no general repair procedure is supplied in this release, for an attempt left unresolved (for example authorization spent with no settlement); do not delete its records.

- **Native reader/action facade**: `constellation-live-reader.service`, separate from read-only Workbench pages. It serves unauthenticated GET reads and token-authenticated POST actions on port 8081, applies enrollment/request prechecks and invokes native AG transitions.
- **Apply claim**: the exclusive enrollment record created before installer effects. An incomplete claim refuses reapplication; deleting it is not a recovery procedure.
- **This candidate versus earlier archives**: this candidate carries NQ with bounded retention (issue #27 remains open) and its own package identities. The 8 October archive, retired as a release candidate, keeps its NQ package without retention; the 10 October supervised archive is superseded. Neither component qualification nor a checksum establishes release approval or human usability.
- **Capacity envelope**: the persisted filesystem, file-limit and byte budget admitted for a store. Ordinary restart does not silently resize it. Protected history and retained identity commitments can cause controlled refusal.
- **Retention target**: the configured history horizon (seven days by default), subject to protected dependencies and finite capacity; it is not a promised duration of successful ingestion, and on this trial the store's ceiling is reached before it.
