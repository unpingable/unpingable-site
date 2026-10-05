# Operational spine release draft

**Draft prework only. No BC1 tag, label or publication claim.** This cohort prepares the source-free operational spine that Workbench will integrate. Exact spine package, lifecycle, canary and projection scope is recorded in QUALIFICATION-SUMMARY.json. These results do not establish the combined Workbench product or human operability.

## Exact source basis

| Component | Selected source |
|---|---|
| NQ | `9c1a1604f3e833dd5e671c198caf42b7ddb6e4b5` |
| Nightshift | `3333c791d32cae33dbb8c8302fc69ca2ba0ec217` |
| AG tools/Systemd executor | `2ac8675274c9eb3d209d7446ec13520d688fc449` |
| Docket | `75f08ebad207f09659801eccdcb272d3c30a7613` |
| Linear Accountant | `239803f83f9a54d0f181edcc3850df8b0c83e782` |
| Monitor/Pulse | `b0240b2646e46e00c8c8fb2949862b5144ba830e`; current public basis `5a44225ce9db0f58192df2f0d4c88501ba77f09c` plus selected accepted attention/remediation source |
| Workbench | `<WORKBENCH_ACCEPTED_SOURCE_AND_BUILD>` — separate owner, integration pending |
| Combined documentation/adapter | Extracted-bundle `SOURCE.json` documentation commit; `SHA256SUMS` binds every included file |

NQ package version is 0.2.4; the remaining selected package version is 0.1.0+spine.20261004.1. Protocol/schema and crate versions remain their own identities. Exact feature selection, source epochs, builder image/toolchain and ELF/systemd requirements are recorded in SOURCE-IDENTITIES.json, PACKAGES.json and EXECUTABLES.json.

## Frozen spine identities and remaining combined inputs

| Field | Required value |
|---|---|
| Frozen bundle location/identity | `bc1-spine-candidate-prework-20261004`; maintainer-visible neutral GitHub draft on unpingable/unpingable-site |
| Manifest and bundle SHA-256 | Exact external ARTIFACTS.json / SHA256SUMS on the neutral draft; no self-referential hash field |
| `SHA256SUMS`, package/executable inventory | PACKAGES.json, EXECUTABLES.json, installed-SHA256SUMS and extracted-bundle SHA256SUMS |
| Verification trust/procedure | INSTALLATION.md; verify draft/repository identity independently, then checksums and installed ELF hashes |
| Host-posture cohort issuance/qualification input | Owner chooses unique local issuance. Host-posture build/source/gate inputs are exact package bytes in PACKAGES.json; ten-step qualification issuance constellation-spine-20261004-5c88d76e |
| Ordinary build/check results | QUALIFICATION-SUMMARY.json build/check/independent package audit record hashes |
| Source-free install/day-two results | QUALIFICATION-SUMMARY.json: 5c88d76e-bec8-4c0d-b1eb-c0428afd62a9, ten passed lifecycle steps |
| Bounded deterministic canary activation/outcome | QUALIFICATION-SUMMARY.json: 964ff50a-2524-4259-8fec-940aa6cf3b3b, completed/settled, one start/use, fresh active postcondition, zero page intents |
| Ordinary sustained dogfood snapshot | DOGFOOD-SNAPSHOT.json; unchanged referencev1, current service/input evidence, existing application attention and storage-pressure followup explicit |
| Workbench artifact/access/operator workflow | `<WORKBENCH_ARTIFACT_ID_ACCESS_DOCUMENT_AND_ACCEPTANCE>` |
| Combined human 12-task qualification | **NOT EXECUTED**; `<FUTURE_HUMAN_RUN_AND_REVIEW>` |
| Independent combined acceptance | `<INDEPENDENT_ACCEPTANCE_RECORD>` |

Unfilled fields are unknown, not positive results. Any failed build/check remains a failed occurrence until its exact successor is independently reviewed; do not substitute a successful older package or erase the original failure.

## Capability disposition

| Class | Capability |
|---|---|
| Qualified and reference-default after explicit enrollment | NQ observation/currentness, filesystem-capacity posture, Nightshift recurrence, attention/status/metrics, deterministic v1 for one separately enrolled canary; installation itself remains inert |
| Qualified but optional | Model-backed v2 with LA accounting; default disabled, no credential or budget enrolled. Slack/Discord/PagerDuty require explicit routes; qualification here uses local notification custody. Central Grafana/metrics deployment is optional and separately installed. |
| Planned / later beta | Observer-only enrollment, orchestrated-application/k3s qualification, Silverblue, federation, CI/CD, hardware-backed authority, generalized diagnostic planning and broader remediation |

## Intended behavior and limits

The owner enrolls observations and optional notifications before any separately bounded effect authority. The default remediation consumer is deterministic v1 for one enrolled canary start. An actual optional v2 decider remains behind the same pinned AG/Docket boundary and LA accounting, but this installation enables no model mode, installs no provider key and authorizes no inference call.

Useful current observation, evaluator conditions, notification custody, AG admission/refusal, exact Docket effect custody, fresh postcondition and accounting are distinct records. Workbench must expose their owner semantics and identity/currentness rather than synthesizing one universal healthy/current verdict. Monitoring is operational telemetry, not action evidence or a paging authority.

Fresh installation and the conservative day-two generation/rollback procedure are documented in [INSTALLATION.md](INSTALLATION.md), [OPERATIONS.md](OPERATIONS.md) and [DAY-TWO-RUNBOOK.md](DAY-TWO-RUNBOOK.md). This bounded prework does not establish arbitrary cross-build store continuity, fleet discovery, NAS control, broad root execution, a native universal HTTP/SQL API or durable application recovery from a start receipt.

## Remaining combined-release gates

1. Spine prework identities and finite checks are frozen in the included manifests; neutral draft artifacts remain maintainer-visible until the combined release gate.
2. Separate canary enrollment/one-use activation, custody, fresh postcondition and local routing passed in the admitted disposable guest; this result does not activate production model mode.
3. The Workbench owner integrates the reviewed [contract](WORKBENCH-INTEGRATION-CONTRACT.md), packages its own accepted artifact and supplies the primary operator workflow plus documented CLI escape.
4. Execute the prepared [human operability protocol](HUMAN-OPERABILITY.md) on the exact combined candidate, preserving all 12 scores including documentation searches/hints/blocks.
5. Independent review records the exact combined disposition; only then may the separately authorized final release publication proceed.

Qualification never reaches production PagerDuty. A separately authorized dedicated TEST route and its receipt are required before network qualification. Passing qualification does not activate model mode or enlarge the one-canary envelope. This draft itself performs no installation, deployment, notification, Workbench mutation or publication.
