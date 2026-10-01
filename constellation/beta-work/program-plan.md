# Constellation program beta work

Planning only, recorded 2026-10-01. Work below is not started by publication of this plan. Source, package, installation, runtime and composition standing remain separate.

## Current state

Cartography owns program decisions and cross-component rationale; this reviewed public documentation projection is hosted in the existing public-site repository. Linked Cartography issues and the Constellation Program Project remain private owner coordination. The complete requirements are written here; reading private evidence is not an execution prerequisite.

Start from [`dev/operator-beta`](https://github.com/unpingable/cartography/tree/dev/operator-beta), canonical product reconciliation at `f90d59fdaa80d6580fd0d9a1254e8c93f1f07555`. Documentation commits after that point do not select a different product base or transfer predecessor qualification.

The source-publication record identifies one coherent public forward line per component. Program mapping and release rationale remain here; component implementation plans live with their owning repositories.

## Scope and exclusions

This plan routes current requirements and evidence needed for future bounded work. It does not resume alpha qualification, launch providers, mutate a deployment or implement product changes. Target-specific configuration and operational facts belong in program/application records; component documentation describes abstract interfaces only.

`agent_gov`, Classic NQ (`nq-classic`), retired monorepos, predecessor product lines and historical application implementations are historical/migration evidence only. They are not forward source donors, dependencies or instructions to restore removed APIs. Retired WLP compatibility remains excluded. Record a current requirement if old evidence suggests missing functionality; require an explicit owner decision before any revival.

## PA-01: Review semantic registry ownership and adoption

`PROGRAM_DESIGN` · **Useful during beta; not gating** · Project: Blocked.

Problem: The offline draft separates rule ownership, evidence, assessment, relationships and qualification; registry maintainer and owner acceptance remain unassigned.

Intended outcome: Record maintainer, review jurisdiction, freshness cadence, public projection and immutable supersession decisions before any adoption.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: Program release scope and current component contracts.

Acceptance/evidence: Review scoped AG one-use, Nightshift non-actuation and NQ refusal examples; retain unknown ancestry and distinct formal/correspondence/qualification axes; validate representations and false-transfer refusals.

Owner decisions: Maintainer, edge reviewers, acceptance procedure and reviewed public projection must be selected.

Owning issue: [PA-01](https://github.com/unpingable/cartography/issues/2).

## PA-02: Publish a current component catalog and discovery map

`DOCUMENTATION` · **Useful during beta; not gating** · Project: Backlog.

Problem: Repository decomposition leaves component identity, responsibilities and interface ownership difficult to discover.

Intended outcome: Index current repositories/forward refs, responsibilities and non-responsibilities, produced/consumed contracts, evidence homes and lifecycle authority.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: Program release scope and current component contracts.

Acceptance/evidence: Every catalog entry has an owning public repository and current contract link; absent consumers stay absent; no retired runtime obligations.

Owner decisions: None beyond a bounded work order.

Owning issue: [PA-02](https://github.com/unpingable/cartography/issues/3).

## PA-03: Establish program ADR and supersession discipline

`PROGRAM_DESIGN` · **Useful during beta; not gating** · Project: Backlog.

Problem: Cross-component decisions need discoverable current status without erasing prior reasoning.

Intended outcome: Define bounded ADR records with owner, affected concepts/components, scope and reciprocal supersession links.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: Program release scope and current component contracts.

Acceptance/evidence: Demonstrate one supersession retaining historical scope and a current decision index.

Owner decisions: Decision owners must approve the procedure; documentation does not silently establish policy.

Owning issue: [PA-03](https://github.com/unpingable/cartography/issues/4).

## PA-04: Map requirements to scoped evidence and bounded change impact

`PROGRAM_DESIGN` · **Useful during beta; not gating** · Project: Backlog.

Problem: Historical proof, source constraints, tests and runtime receipts support different claims at different identities.

Intended outcome: Map requirement-to-evidence edges and compute conservative NEEDS_ASSESSMENT cones without globally discarding unrelated standing.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: [PA-01](https://github.com/unpingable/cartography/issues/2) registry decisions; component-owned definitions and reusable certificate design.

Acceptance/evidence: Six examples: implementation-only, semantic strengthening, interface, formalization, packaging and runtime-environment changes identify stale and retained assessments.

Owner decisions: Semantic owners approve edge scopes; registry adoption remains separate.

Owning issue: [PA-04](https://github.com/unpingable/cartography/issues/5).

## PA-05: Design a bounded integration train

`RELEASE_ENGINEERING` · **Useful during beta; not gating** · Project: Backlog.

Problem: Composition drift should be detected before a large release campaign.

Intended outcome: Specify one lightweight known-good composition, exact subjects/results, finite resources, admission and stop rules; do not schedule or launch it.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: Current Integration V1, packaged component identities and [PA-07](https://github.com/unpingable/cartography/issues/8) process decisions.

Acceptance/evidence: A proposed train exercises exact interface/schema closure and records limitations without claiming whole-product qualification.

Owner decisions: Train owner, cadence and admitted composition require selection.

Owning issue: [PA-05](https://github.com/unpingable/cartography/issues/6).

## PA-06: Define promotion lifecycle and reusable qualification certificates

`RELEASE_ENGINEERING` · **Useful during beta; not gating** · Project: Backlog.

Problem: Source, bytes, package, ABI, install, enrollment, runtime, composition and journey standing must remain distinct.

Intended outcome: Design immutable scoped certificates plus prepared/reviewed/qualified/promoted/superseded/retired transitions; exact input changes invalidate only dependent edges.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: [PA-04](https://github.com/unpingable/cartography/issues/5) impact model; component release plans; Integration V1 execution boundaries.

Acceptance/evidence: Certificate specimens bind source, lock, builder, output, scope, procedure, occurrence, review, limitations and supersession; branch/merge never implies promotion.

Owner decisions: Release owners select certificate authority and review jurisdiction.

Owning issue: [PA-06](https://github.com/unpingable/cartography/issues/7).

## PA-07: Select a durable owner for qualification harness and process tooling

`QUALIFICATION_INFRASTRUCTURE` · **Useful during beta; not gating** · Project: Blocked.

Problem: Reusable process lessons have no established product-tooling maintainer; copying campaign implementations would invent architecture.

Intended outcome: Choose an existing natural owner, or retain Cartography decision custody; specify a fixed-goal state machine, apparatus/product failure classes, one bounded repair, one authorized occurrence per claim generation, promotion-boundary review, durable reconciliation, resource closeout and derived current-state projection.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: Owner-approved amendment A3 and authority/resource boundaries.

Acceptance/evidence: Owner decision names repository/owned paths; design refusal cases for recursive apparatus objectives, unauthorized retries and silent evidence rewriting; current projection derives from append-only history.

Owner decisions: Tooling home/maintainer genuinely unresolved; no new repository or generic framework is selected.

Owning issue: [PA-07](https://github.com/unpingable/cartography/issues/8).

## PA-08: Define bounded archaeology and custody disposition practice

`POST_BETA_HARDENING` · **Post-beta** · Project: Backlog.

Problem: Reproducible substrate and durable evidence need different disposition, and obsolete compatibility claims need named consumers.

Intended outcome: Document ownership/dependency review and explicit dispositions for build output, worktrees, retained evidence and obsolete claims; no deletion or estate-wide job.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: Program release scope and current component contracts.

Acceptance/evidence: Examples retain unique history and replay dependencies while identifying exact disposable substrate; missing ownership stays unresolved.

Owner decisions: None beyond a bounded work order.

Owning issue: [PA-08](https://github.com/unpingable/cartography/issues/9).

## PA-09: Document bounded agent work contracts

`DOCUMENTATION` · **Useful during beta; not gating** · Project: Backlog.

Problem: Delegated engineering needs explicit owned paths, authority limits, stop conditions and publication expectations.

Intended outcome: Define a concise reusable work-order checklist covering goal, owned paths, semantic boundaries, exclusions, artifacts, resource envelope, review and commit/push disposition.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: Authority granularity principle and [PA-07](https://github.com/unpingable/cartography/issues/8) process decisions.

Acceptance/evidence: Example contract cannot grant authority from tooling availability or override platform controls.

Owner decisions: None beyond a bounded work order.

Owning issue: [PA-09](https://github.com/unpingable/cartography/issues/10).

## PA-10: Keep the canonical beta objective and owner decisions visible

`DOCUMENTATION` · **Required for operator-beta** · Project: Ready.

Problem: The September dated objective was invisible from an active campaign branch.

Intended outcome: Publish a current objective summary and links to exact basis/amendment; maintain M1-M5 requirements, dates and owner decisions separately from evidence chronology.

Scope/exclusions: Limit changes to the named outcome; preserve existing semantic and authority boundaries.

Dependencies: Program release scope and current component contracts.

Acceptance/evidence: A fresh public clone can locate product claim, October 16 showing, December 18 beta, Ubuntu 22.04 baseline, scope exclusions and owning plans.

Owner decisions: None beyond a bounded work order.

Owning issue: [PA-10](https://github.com/unpingable/cartography/issues/11).

## LA-01: Record deferred Linear Accountant integration trigger

`POST_BETA_HARDENING` · **Post-beta** · Project: Blocked.

Problem: Linear Accountant remains a frozen conserved-capacity reference boundary; no new beta consumer has been established.

Intended outcome: Keep a decision record requiring a real current consumer before any new transport/persistence/integration slice; component plan records the freeze.

Scope/exclusions: No WLP compatibility, policy/budget engine or predecessor dispatcher donor.

Dependencies: Program release scope and current component contracts.

Acceptance/evidence: Named dispatcher consumer and exact conservation/receipt acceptance before thaw; absent trigger means no implementation.

Owner decisions: A current consumer trigger and owner-approved thaw are required.

Owning issue: [LA-01](https://github.com/unpingable/cartography/issues/12).

## PA-13: Plan observation-profile generation rotation and site-adapter maintenance

`RELEASE_ENGINEERING` · **Required for operator-beta** · Project: Ready.

Problem: Owner records report the initial installed profile, unattended recurrence and live delivery; finite journal/publication capacity creates a generation-rotation duty and the site adapter still emits empty prior recurrence records.

Intended outcome: Keep generation rotation/re-enrollment, prior-slot record carriage, slot-aligned cadence and restart evidence in deployment-owned plans, without moving target glue into components.

Scope/exclusions: Cartography owns coordination and site-adapter planning; actual target configuration remains deployment/application scope. No active ATProto/PDS/Phlogiston work.

Dependencies: [NS-01](https://github.com/unpingable/constellation-nightshift/issues/4) reusable boundary; [MO-01](https://github.com/unpingable/constellation-monitor/issues/10) runtime limits; NQ delivery/replay; application-owned deployment facts.

Acceptance/evidence: A bounded later work order names exact deployment generation, capacity envelope, continuity/re-enrollment and rollback evidence; no reboot, service change or send is authorized by this plan.

Owner decisions: Each operational effect requires its own owner admission; no provider-backup requirement is reintroduced after the recorded waiver.

Owning issue: [PA-13](https://github.com/unpingable/cartography/issues/13).

## Component relationships

The [distributed work register](index.md) links owning repository plans and issues. PA-11/12 provide release identity and closure; AG/Docket own authorization and execution custody, NQ owns diagnostic/replay meaning, Nightshift/Foreman temporal/provider custody, Monitor/Pulse present reliance, and Switchyard provider receipt export. These edges do not assign common semantic ownership or transfer qualification. Optional authoring, standing, continuity and conserved-capacity roles join only through named current consumers.

## Registry review basis

The inspected offline draft separates concept, scoped rule, evidence, assessment, relationship and qualification entities. Its schema/validator enforce identity/reference structure and forbidden transfers; they cannot prove semantics or owner authority. Rules remain RULE_ONLY; formal coverage, implementation correspondence and qualification are separate axes. Identity drift yields NEEDS_ASSESSMENT, not semantic divergence. A public adoption must select reviewed scope and omit private host/campaign metadata. Raw unreviewed fixtures are not published or made runtime dependencies by this plan.

## Process rationale

The alpha retrospective and October 1 independent review identified coordination cost from recursively qualifying apparatus and hiding the product objective in chronological records. Future process design preserves exact scoped evidence while implementing amendment A3: one bounded apparatus repair-and-review cycle, one authorized occurrence per claim generation, owner reopening for another occurrence, and independent review at promotion boundaries. A compact derived current projection accompanies immutable history; neither replaces source or semantic owners.
