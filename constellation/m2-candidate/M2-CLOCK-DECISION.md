# M2 temporal authority decision required

Direct dependent product boundary discovered while closing the four original M2 blockers, 2026-10-01. This is neither a packaging failure nor a new qualification objective.

## Published facts

- NQ `623a74760c5ea02c633aa97bdb15d52953e66616`, `crates/nq-core/src/engine.rs`: the live diagnostic builder sets `ClockQualificationV2::Unqualified`, code `absolute_clock_quality_unqualified`; the local Linux wall clock has no qualified finite UTC-error bound.
- Nightshift `f891d88b2b0187284b0416a23ec6cb55c193c0f4`, `crates/nightshiftd/src/diagnostic_posture.rs`: unqualified source/dependency intervals return `ClockUnqualified`; every v2 diagnostic also lacks an identified, qualified evaluation clock or admitted comparison relation.
- Nightshift's published [NQ Diagnostic Consumer v2 decision](https://github.com/unpingable/constellation-nightshift/blob/f891d88b2b0187284b0416a23ec6cb55c193c0f4/docs/working/decisions/NQ-DIAGNOSTIC-CONSUMER-V2.md) explicitly retains both refusals. Its recurrence carrier likewise lacks a qualified invocation clock/comparison relation.
- Existing ordinary product tests `unqualified_v2_source_clock_preserves_the_producer_reason` and `bounded_v2_source_clock_cannot_earn_current_against_bare_evaluation_time` pass. Six clock-boundary tests passed from the exact forward export. No V1 emission, fabricated finite bound or relaxed refusal was substituted.

## Smallest owner decision

Choose which current observation authority M2 should consume:

1. Preserve Nightshift temporal Current as part of M2 and adopt an explicit evidence-backed producer/receiver clock or comparison enrollment contract for the local VMs. The owner selects the authority/premises; the smallest product implementation must preserve unqualified/unknown/comparison refusal. Merely changing NQ's tag or configuring NTP does not satisfy the current consumer contract.
2. Keep current unqualified-clock facts and explicitly authorize a bounded M2 path based on fresh local acquisition evidence, excluding Nightshift temporal acceptance from that showing. The exact narrower claim and observation authority must be recorded before implementation/execution.

Neither alternative is inferred from routine VM setup authority. The existing published design rejects an implicit cross-clock comparison; changing that semantic authority boundary requires the owner decision.

Tracking: [NQ #3](https://github.com/unpingable/constellation-nq/issues/3) and [installable M2 closure #12](https://github.com/unpingable/unpingable-site/issues/12). The original Docket standing, AG signed Systemd, Nightshift work-identity and NQ xattr defects are repaired; this is the sole newly exposed owner boundary. The unfinished deployment draft remains local and is not supported product tooling or a new campaign framework.
