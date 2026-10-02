# M2 clock enrollment: selected direction and incompatibility

Owner decision, October1: preserve Nightshift temporal standing; use one exact, evidence-backed local-VM clock source only if the current contract can consume ordinary verifiable synchronization state. Do not weaken `absolute_clock_quality_unqualified`, introduce a generic time authority, add external credentials/providers, or automatically narrow M2. The owner explicitly requires a stop if satisfaction requires materially new authority architecture.

Status: `CONSTELLATION_ALPHA2_BLOCKED_ON_OWNER_DECISION`. The selected direction is recorded. No compatible clock enrollment or new product clock source has been claimed.

## Bounded diagnosis

Read-only inspection on crow found active systemd-timesyncd, `NTPSynchronized=yes`, clocksource `tsc`, and an existing `ntp.ubuntu.com` source. One retained sample reports root distance3.523ms, offset+2.248ms and delay85.479ms; these are synchronization observations, not an enrolled Constellation clock-qualification decision. Read-only `adjtimex` used `modes=0`; no clock/configuration was changed and no new time-service connection was initiated. No fresh guest was launched, so no guest synchronization or host-to-guest error bound is claimed.

The Jammy [systemd249 implementation](https://github.com/systemd/systemd/blob/v249/src/timesync/timesyncd-manager.c#L223-L246) sets kernel `maxerror` and `esterror` to zero when adjusting the clock. Those fields cannot simply be copied as a proven zero UTC-error bound. NTP measurements can contribute evidence under an explicitly admitted qualification rule; the measurements do not establish that rule, its reference accuracy, guest transfer premises or currentness themselves.

## Exact current contract mismatch

| Current surface | What it consumes | Why clock enrollment alone is insufficient |
|---|---|---|
| [NQ v2 producer](https://github.com/unpingable/constellation-nq/blob/623a74760c5ea02c633aa97bdb15d52953e66616/crates/nq-core/src/engine.rs#L6479) | Local historical clock surface, currently always unqualified | There is no installed synchronization-evidence/qualification enrollment input. `Bounded` requires an exact qualification basis and inclusive symmetric UTC-error bound; copying a synchronization flag or replacing the unqualified tag supplies neither. |
| [Nightshift bare posture evaluator](https://github.com/unpingable/constellation-nightshift/blob/f891d88b2b0187284b0416a23ec6cb55c193c0f4/crates/nightshiftd/src/diagnostic_posture.rs#L1875) | NQ acquisition intervals and a bare evaluation instant | It intentionally refuses V2 Current even for a bounded source; it has no qualified evaluation/invocation clock or admitted comparison input. Existing strict carriers cannot accept an extra clock file by configuration. |
| [Live canonical Nightshift path](https://github.com/unpingable/constellation-nightshift/blob/f891d88b2b0187284b0416a23ec6cb55c193c0f4/crates/nightshiftd/src/canonical_runtime.rs#L962) | An already-qualified, exact live-query-bound present-support result | It calls `evaluate_posture_with_support`, not the bare evaluator. [Receiver-clock ticks and exclusive expiry](https://github.com/unpingable/constellation-nightshift/blob/f891d88b2b0187284b0416a23ec6cb55c193c0f4/crates/nightshiftd/src/currentness.rs#L70) validate the supplied authority result; they do not qualify host/guest synchronization or derive proposition support from it. |
| [Published Pulse support family](https://github.com/unpingable/constellation-monitor/blob/6543276e6315136a46607000d7a54765791a4898/docs/nq-host-load-pressure-support-v1.md) | Independent proposition-exact load-pressure evidence and receiver custody | Its closed family does not cover the M2 systemd/HTTP propositions or UTC accuracy. [Native predicate support](https://github.com/unpingable/constellation-monitor/blob/6543276e6315136a46607000d7a54765791a4898/docs/generic-project-predicate-support-v1.md) is likewise a closed family; it is not an arbitrary service/clock adapter. |

The earlier blocker explanation overstated the bare posture refusal as if it were the live canonical path. The canonical path already allows an independently qualified authority result. That correction does not make a synchronization snapshot an admissible result or establish a qualified M2 support family.

## Why this reaches the owner's stop condition

An ordinary root-owned enrollment file cannot close the current interfaces. Proceeding would require one of two distinct architectural changes:

- A versioned producer and consumer clock-qualification/comparison contract: select admitted UTC-reference and host/guest transfer premises, bind clock/boot generation and evidence, define bound validity/revocation, and expose qualified evaluation/recurrence comparison instead of the current bare instant.
- A new M2 proposition-exact qualified present-support authority using the existing canonical port, with its own source/receiver-clock qualification, acquisition/replay/expiry and exact systemd/HTTP semantic contract. Defining only a clock source does not define this authority's proposition support.

These are not mechanically recoverable paths or package flags. No such authority or accepted rule was supplied by existing forward source/configuration. The owner selected bounded clock enrollment and explicitly required a stop at materially new authority architecture; this review stops at that boundary. No implementation, weakened refusal, invented finite error, relabeled historical format, or narrower M2 showing was substituted.

## Preserved result and continuation

The four original repairs, their passing ordinary checks, exact five Jammy packages/fourteen binaries, and [retained source-free archive](ARCHIVE.md) remain unchanged. Six existing Nightshift clock-boundary tests and forty canonical-runtime tests had passed on these exact sources; no product source changed during this review, so no duplicate build/test occurrence was created. The prior archive predates this owner reply and retains its exact published hash; this current decision supersedes its unresolved-choice wording without changing its bytes.

No M2 VM/effect occurrence has run. Alpha2 is not accepted. [M2 #12](https://github.com/unpingable/unpingable-site/issues/12) and [NQ #3](https://github.com/unpingable/constellation-nq/issues/3) remain Blocked. Resume only with an explicit current architectural contract/premises or authority decision addressing the mismatch above; routine VM execution remains already authorized after resolution. Do not reopen C1, use retired source donors, or begin unrelated beta work.

## Superseding owner decision

The owner authorized Pulse-owned support for the exact fixed M2 systemd/HTTP propositions, based on fresh NQ acquisition and boot-bound bounded custody freshness. This resolves the missing support responsibility without a general clock/comparison contract or a UTC relabeling. See the current runbook and [Pulse contract](https://github.com/unpingable/constellation-monitor/blob/dev/operator-beta/docs/m2-nq-support-v1.md). The earlier clock-only stop remains historical provenance, not the current candidate gate.
