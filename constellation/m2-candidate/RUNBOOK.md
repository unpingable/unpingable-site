# Fresh M2 release-candidate preparation

**Disposition: BLOCKED — do not launch the governed-effect showing from this generation.**

This prepares the September operator-beta service-action scenario against the
October 1 Ubuntu 22.04 amendment. It does not resume C1 or transfer historical
showing acceptance to these sources. The publication and planning work selected
one forward line; ordinary source/build checks now expose two current product
seams that prevent a runnable composed candidate.

Owning release work: [installable closure](https://github.com/unpingable/unpingable-site/issues/12).

## Exact scenario and dependency closure

Use two fresh Ubuntu 22.04 amd64 VMs on a bounded private network: a
controller/observer and a target/authority VM. The deliberately inactive,
disabled `constellation-beta-http-fixture.service` is the sole effect target.
One exact proposed **start** passes AG authorization/one-use spend and Docket
attempt custody before the target-local AG Systemd D-Bus executor. Fresh NQ
`nq.systemd_unit/v1` target-local and `nq.http_endpoint/v1` controller-HTTP
observations then inspect that same subject, separately. The literal endpoint is
`http://<fresh-target-address>:18080/healthz`, method GET, redirects refused,
expected status 200 and the hash of the supplied `fixture/healthz` body. Expected
systemd tuple: loaded/active/running/disabled. Both profiles retain their own
scope, vantage, policy and 60-second reliance law; neither proves aggregate
health, recovery, causation or distributed exactly-once execution.

The subject is the current NQ contract's closed
`constellation.operator_beta.service_subject.v1` descriptor: campaign_id
`constellation-operator-beta-2026`, fresh fixture_run_id, target_machine_identity,
unit_name and exact installed unit_file_sha256. Canonical JCS bytes and AG's
`constellation/operator-beta/service-subject/v1` domain-separated digest bind
AG, Docket and both NQ observations. Fresh machine/address/occurrence values
are obtained at installation; they are not guessed here or copied from old VMs.

| Component | Required role | Current boundary |
|---|---|---|
| AG | Exact-work admission, signed issuance, one-use spend; Systemd mechanics; read-only Phosphor inspector | Genesis-bound runtime profile, `ag.governed-loop.signed-issuance/v1`; machine-bound Systemd plan/work v2 |
| Docket | Fresh independent execution-standing decision, durable custody, same-attempt reconciliation | `docket.governed-executor-dispatch/v2`, inner dispatch and outcome v1 |
| NQ 0.2.0 | Pre/post target-local systemd and controller-HTTP diagnostic custody | `nq.diagnostic_execution.v2`, current compiled descriptors and profile-owned immutable threshold policies |
| Nightshift | Current diagnostic evidence/temporal applicability and exact proposal binding in the intended release topology | Locally qualified NQ admission, canonical observations, `nightshift.precompiled_workflow_proposal.v2`, read-only AG observation resolver |

The historical deterministic M2 showing invoked no AI model. Foreman external
provider/model selection, enrollment and credential custody therefore are not
inputs to this fixed scenario. Do not claim that this closes its separately
required operator-beta provider lifecycle. Monitor/Pulse is an optional
present-support overlay; Switchyard is conditional on a model/provider route;
Maude/Standing service-investigation authoring is another optional path. None
is added to this runtime closure by historical campaign ancestry. The ECAD
Integration Contract has no live import in these Rust process-wire seams;
component-owned current contracts are included instead. M3 notifications/site
recurrence, live application dogfood, VM executor research, broader recovery,
post-beta components and all ATProto work remain excluded.

## Blocking current product seams

1. [AG signed Systemd execution](https://github.com/unpingable/constellation-ag/issues/13):
   Docket always emits the signed V2 outer packet. AG's SystemdV2 execute and
   reconcile arms decode a bare six-field dispatch. The ordinary Jammy CLI
   accepts the plan but rejects the existing positive signed product vector at
   `custody`, before any effect mechanics. The generic plan's enrolled issuer,
   runtime-profile and persisted-custody verification has no equivalent
   Systemd-plan authorization binding. A selected current owner contract is
   needed; stripping the wrapper would bypass the intended boundary.
2. [Nightshift current plan identity](https://github.com/unpingable/constellation-nightshift/issues/6):
   current proposal compilation unconditionally derives work under AG's generic
   V1 plan domain. AG SystemdV2 derives it under the actual Systemd V2 schema.
   Equal canonical plan bytes produce different work identities. Supported
   current schemas and shared current vectors must be selected; publishing
   another old V1 fixture does not resolve this seam.

A bounded packaging repair lowers only the standalone executor's systemd
metadata floor to 249, whose source exposes its required interfaces. The daemon
package retains its separate >=252 credential-unit requirement and is excluded.
No authorization semantics or product runtime code was changed in this pass.

## Ordinary build/check results

All four required runtime lanes release-built offline with the pinned Jammy
image and Rust 1.94. All 13 shipped Rust executables resolve their loader and
libraries there; their maximum required GLIBC version is no newer than 2.35.
AG adapter/Systemd CLI/governed-loop/inspector tests and current signed transport
vectors passed. Docket library tests passed in debug and release, focused
intake/read/help tests passed, and its current CLI/library lint passed.
Nightshift canonical-runtime/resolver/export/decision-basis checks passed.
NQ profiles/system-contract/store checks and its official package/schema/payload
verifiers passed. No VM install, upgrade, effect or notification was exercised.

NQ runtime checks are **not green**: after one repair for a missing container
build-account entry, `nq-core` reports 192 passed, 8 failed and 1 ignored;
`admin_lifecycle` reports 1 passed and 7 failed. Remaining helper/runtime-path
refusals say `xattr-name list changed or is malformed` in this container.
Whether this is a container/filesystem limitation or a current-product
compatibility defect remains unresolved; no clean-VM result is inferred.
[Existing NQ recovery work](https://github.com/unpingable/constellation-nq/issues/3)
records the follow-up. No permission/custody check was relaxed.

NQ formatting passed. AG, Docket and Nightshift have preexisting format
check differences; Docket's all-target lint also fails on unused variables in
an experimental guest test. These remain recorded, without broad cleanup or
VM research. Two byte-equal builds and reproducible release promotion are not
claimed. The pinned local builder image has no captured registry/base digest.

## Stranger inspection entry point

The source-free partial archive contains packages, `candidate.json`,
`SHA256SUMS`, ABI/dependency records, current contract documents, this runbook,
the inert service fixture and an owner-input worksheet. No worktree, compiler,
Cargo cache, campaign evidence tree, historical fixture or private credential
is included. Package installers do not authorize an effect.

After receiving the archive and its owner-provided SHA256 sidecar, on a fresh
Ubuntu 22.04 VM:

```sh
sha256sum -c constellation-m2-jammy-20261001-partial.tar.gz.sha256
tar -xzf constellation-m2-jammy-20261001-partial.tar.gz
cd candidate
./inspect-candidate.sh
```

This verifies exact bytes and displays the disposition. It deliberately exits
nonzero for this blocked generation and performs no installation or effect.
There is **no accepted fresh-showing launch command for this generation**.
Do not substitute a C1 runner or historical browser controller. Once both
current seams are resolved, the release owner must prepare a new exact manifest,
complete the source-free installation/authority configuration and have the
candidate independently reviewed at promotion. The eventual occurrence needs
separate admission; this document grants none.

## Inputs: mechanical facts versus owner choices

Mechanical facts: executable paths/hashes from package inspection; Docket's
`--state`, `--trust`, `--standing-resolver`, `--executor` and
`--executor-config` options; executor plan identity from `ag-effectd plan-id`;
profile/descriptor identities from `nq profiles show`; helper executable hash
and production build-info; a fresh VM's machine ID/address, exact installed unit
hash and service-subject JCS preimage; request scope/vantage/policy digests; and
state locations chosen consistently with the runbook. No old campaign coordinates
or unrecorded remote state are needed to recover those facts.

Genuine owner choices remain:

- Docket execution-standing principal and currentness/revocation decision
  source ([existing hold](https://github.com/unpingable/constellation-docket/issues/3)).
  An identity-only fixture is not that source. AG's standing resolver speaks
  a different request/response contract and is not an implicit substitute.
- The approved current Systemd authorization/enrollment contract and closed
  Nightshift plan-schema selection from the two owning issues above.
- Any additional observer/config identity enrollment beyond the currently
  pinned executable/config/profile roots
  ([existing reconciliation work](https://github.com/unpingable/constellation-docket/issues/1)).
  Reconciliation standing is already decided: observe/settle the same attempt
  without current standing and **never redispatch**.
- Fresh showing admission and release-candidate promotion after those repairs:
  exact fixture occurrence, authority principals/mandates, TTL limits, issuer
  key identity, independent review and owner-held private-key custody. Public
  trust material must be derived from that admitted owner key; this generation
  contains no fabricated trust root or test-key enrollment.

The supplied `owner-inputs.json` is a worksheet, not an accepted runtime
configuration. Initial canary authority does not permit this task to launch a
new VM occurrence. No external provider credentials are needed for fixed M2.

## Inspection and recovery for the eventual showing

The source-free installation must keep target-local AG/Docket/executor state
at their admitted process/D-Bus boundaries. NQ evidence and Nightshift state
remain separate. Phosphor reads owner-labelled records and never launches work.
Keep one admitted attempt's issuance/custody/receipt and both post-observation
identities; neither temporal coincidence nor process exit creates an edge.

On interruption, inspect the original durable execution identity, exact AG
spend, `docket governed-loop inspect`, executor receipt/store and NQ diagnostic
artifacts. Reconcile the existing Docket issuance/attempt through its captured
executor/config binding. Do not mint another authorization, reset state,
redispatch an uncertain attempt or overwrite historical observations. Only a
separately admitted installation can choose exact inspection/recovery commands
because this generation's current executor transport is unresolved.

`agent_gov`, `nq-classic`, retired monorepos, WLP, predecessor bundles and old
application implementations are historical evidence only. They are not source
donors, current dependencies or fallback implementations.
