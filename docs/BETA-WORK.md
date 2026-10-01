# unpingable-site beta work

Planning only, recorded 2026-10-01. Work below is not started by publication of this plan. Source, package, installation, runtime and composition standing remain separate.

## Current state

Start from [`dev/operator-beta`](https://github.com/unpingable/unpingable-site/tree/dev/operator-beta), canonical product reconciliation at `e2474d683147bac676c55db6c08b2d626336e09f`. Documentation commits after that point do not select a different product base or transfer predecessor qualification.

Integration Contract V1, invocation provenance, execution boundaries, validator/preflight and reusable vectors are published here alongside the public site. Sealed campaign outputs and unfinished site drafts are excluded.

## Scope and exclusions

This plan routes current requirements and evidence needed for future bounded work. It does not resume alpha qualification, launch providers, mutate a deployment or implement product changes. Target-specific configuration and operational facts belong in program/application records; component documentation describes abstract interfaces only.

`agent_gov`, Classic NQ (`nq-classic`), retired monorepos, predecessor product lines and historical application implementations are historical/migration evidence only. They are not forward source donors, dependencies or instructions to restore removed APIs. Retired WLP compatibility remains excluded. Record a current requirement if old evidence suggests missing functionality; require an explicit owner decision before any revival.

## PA-11: Define hermetic builder and installable release closure

`RELEASE_ENGINEERING` · **Required for operator-beta** · Project: Ready.

Problem: Source publication does not supply a complete current installable cohort or source-to-byte standing.

Intended outcome: Specify pinned Ubuntu 22.04 builder/toolchain/dependency snapshots, component payload closure, inert install, isolated reproduction, outside-in verification and source-free composition inputs.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: Component release plans; [PA-06](https://github.com/unpingable/cartography/issues/7) certificates; A2 OS baseline.

Acceptance/evidence: Two reproducible builds where claimed, exact source/output identities, ABI checks and install/upgrade/rollback evidence for the advertised profile; no campaign script dependency.

Owner decisions: Release owner names the profile, exact artifact generation and resource envelope.

Owning issue: [PA-11](https://github.com/unpingable/unpingable-site/issues/12).

## PA-12: Expose exact runtime source and build identity

`RELEASE_ENGINEERING` · **Required for operator-beta** · Project: Ready.

Problem: Version strings alone cannot identify installed bytes.

Intended outcome: Define consistent source/build identity requirements and owner-specific read interfaces, without imposing a common runtime store.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: [PA-11](https://github.com/unpingable/unpingable-site/issues/12) builder identity and each packaged component.

Acceptance/evidence: Each packaged binary reports exact source/build identity tied to its release manifest; unknown identity remains explicit.

Owner decisions: None beyond a bounded work order.

Owning issue: [PA-12](https://github.com/unpingable/unpingable-site/issues/13).

## IC-01: Plan Integration Contract evolution and common interfaces

`PROGRAM_DESIGN` · **Useful during beta; not gating** · Project: Backlog.

Problem: Current V1 and execution boundaries are published; evolution needs current consumer ownership and explicit version boundaries.

Intended outcome: Specify changes only from named current producers/consumers with closed interface tables, invocation provenance, effect authority and upgrade/supersession rules.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: Current V1; [PA-03](https://github.com/unpingable/cartography/issues/4) and [PA-04](https://github.com/unpingable/cartography/issues/5); component-local semantic ownership.

Acceptance/evidence: Consumer-owned golden/conformance vectors and positive/refusal cases; no universal common schema or promotion by validator success.

Owner decisions: None beyond a bounded work order.

Owning issue: [IC-01](https://github.com/unpingable/unpingable-site/issues/2).

## IC-02: Reassess shared identity-vector maintenance candidates

`QUALIFICATION_INFRASTRUCTURE` · **Useful during beta; not gating** · Project: Backlog.

Problem: Existing four-law candidate contains historical consumers and older issuance identity; new AG/Docket V2 vectors already cover the current bridge.

Intended outcome: Inventory named current consumers before adding any remaining shared corpus; retain existing vectors and classify superseded laws instead of copying historical carriers.

Scope/exclusions: Do not revive V1 issuance, retired WLP or campaign managed-file code to justify a vector obligation.

Dependencies: Program release scope and current component contracts.

Acceptance/evidence: Each adopted normative cross-repository law has pinned vectors exercised by its actual consumers; absent consumers produce no compatibility obligation.

Owner decisions: Named consumer drift or scheduled carrier change is the entry condition.

Owning issue: [IC-02](https://github.com/unpingable/unpingable-site/issues/11).

## DOC-01: Maintain public beta architecture and cross-repository discovery

`DOCUMENTATION` · **Useful during beta; not gating** · Project: Backlog.

Problem: Published Integration source and finished guides coexist with held site drafts; current plans need a discoverable public index.

Intended outcome: Link current product claim, component plans, contracts and operator runbooks from public architecture docs; retain unfinished presentation drafts pending owner selection.

Scope/exclusions: Documentation links and normal public plans; no release of held status-page/prototype work.

Dependencies: [PA-02](https://github.com/unpingable/cartography/issues/3) and [PA-10](https://github.com/unpingable/cartography/issues/11); component plans; existing site draft issue #14.

Acceptance/evidence: All links resolve to current development refs and owning issues; no stale qualification standing or private target facts.

Owner decisions: None beyond a bounded work order.

Owning issue: [DOC-01](https://github.com/unpingable/unpingable-site/issues/9).
