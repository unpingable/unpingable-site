# Authoring a new integration

Create one JSON contract from current component contracts and the concrete
objective. First establish a named live consumer with a manifest, import,
entrypoint or command port. Historical examples alone do not establish an
operational dependency. Keep only source facts needed by the new integration;
do not transcribe campaign history or embed an operator prompt in descriptions.

The supported adapter is the JSON file itself. A handwritten instance is often
enough. If an existing application needs code, use the public Python API in
[OPERATIONS.md](OPERATIONS.md) to consume that file. There is no plugin registry
or need to implement a new executor. Native target commands stay in their own
documented interfaces and require their existing admission.

1. Start from [starter.json](starter.json), an explicitly fictional, unverified
   preparation/release example. Change its identity and consumers, replace all
   example locators with current source pins, and derive the finite
   `interfaceClosure` from the target sources before deciding that the last
   consumer command is the whole integration. Begin at the named consumer and
   walk backward through every native transition and separately custodied object
   required to make its input exist. Include configuration/deployment,
   acquisition, intake, reconciliation and cleanup transitions when the target
   sources define them. A read-only final consumer does not erase the producer
   and intake chain. Inventory each distinct logical principal, authority,
   credential class, gate, receipt/evidence object and operation-scoped resource
   rule. In particular, keep a producer signing identity distinct from
   outgoing-storage, intake-storage and consumer read/invocation credentials;
   keep native producer evidence, receiver custody and consumer result receipts
   separate when the target does. Every collection ID in the completed contract
   must appear in `interfaceClosure`; preflight reports omitted declarations as
   `INTERFACE_CLOSURE_INCOMPLETE`. The closure's source basis is a reviewable
   claim, not proof that V1 interpreted prose, so independent qualification must
   still compare it to the pinned target sources.
   Remove inapplicable example rows and all references to them. Do not start by
   copying an accepted record, prior integration output or positive conformance
   fixture.
2. Separate preparation, local/native effects, external/production effects,
   read-only reconciliation and cleanup. Mark each operation `source-only` or
   `runtime`. Source-only preparation uses a null invocation binding. Every
   runtime operation names its logical invoking principal and required invocation
   authority. Once the logical role and compatible authority are declared, bind
   their references even while the principal or authority remains unresolved.
   That wiring asserts neither a resolved identity nor a grant: leave statuses
   and allowlists honest. A null runtime binding is a structurally valid
   **incomplete draft**, not a completed integration or an owner-fact substitute.
   If the logical role itself cannot yet be identified, retain that draft state.
   Required receipts are
   inputs; produced receipts are outputs owed later. An output cannot be its own
   prerequisite.
   Select the invocation authority kind from the specification's runtime-kind
   table; required storage, acceptance or privacy authorities cannot fill that
   binding. Runtime read-only reconciliation requires local-work; runtime local
   preparation permits local-work or compute.
   Also set `executionBoundary: null` for source-only work. For every runtime
   operation, identify the baseline and actual platform identity and capabilities
   or exact service mediation, and each load-bearing visibility fact. Name its
   interfaces, observation claim kind, closed population/PID/user/procfs
   coverage profile, exact domain-binding receipts, complete-or-refuse
   disposition, temporal scope,
   receipt and downstream claim. Keep logical authority references and receipt
   custody separate from Unix identity. If only one fact requires broader
   visibility, retain the ordinary operation identity and declare the smallest
   bounded delegated primitive with exact digest/package/service identity,
   argv/service binding, invoking principal, capabilities, typed coverage and
   receipts. For all-owner coverage, the binding receipt's single typed role
   must repeat the exact operation, fact, primitive identity and closed coverage
   domain. The operation always remains at baseline. Bind a special effect
   mechanism as a `delegatedExecutor` to an existing logical authority; never
   express it as an observation or custody fact. Output custody never justifies
   observer privilege. A point-in-time census does not reserve a producer slot;
   continuing exclusion needs an exact shared mechanism, complete producer
   participation, an externally accepted pinned attempt binding for the exact
   runtime effect operation, and a typed phase chain. Acquisition and hold are
   current accepted inputs with exact expected issuer, acceptance authority and
   a distinct externally accepted authority-evidence receipt. Acquisition must
   precede the observation and its receipt role binds that predicate; hold
   continues through dispatch. Handoff and release are distinct missing outputs
   owed by the bound operation, never current prerequisites.
   Unknown facts use `status: unresolved` with a reason and remain readiness
   holds rather than guessed privilege requirements.
3. Name existing owners and authority kinds from current docs. Add each
   authority's explicit invoking-principal allowlist; do not infer it from the
   authority owner or operation consumer. Where identity, invocation or
   acceptance authority is unknown, declare it unresolved and hold only runtime
   consumers. A missing deployment configuration is not evidence of a grant.
4. Add each gate with explicit positive and negative scope over every operation.
   Every receipt consumed by a runtime prerequisite needs a `required-evidence`
   gate for its eventual acceptance, even while missing, template, prepared or
   failed. Declare that scope now; `prerequisite-source` is not a substitute.
   Cover the dependent runtime operations; leave unrelated
   source-only preparation in `doesNotBlock`. Match credential purpose, consumer,
   invoking principal and authority. Record only non-secret metadata and mark
   absent or unchecked scope honestly. Avoid importing gates from neighboring
   integrations. Cross-contract imports are unsupported.
   Include receipts reached only through an applicable gate and its
   issuer-authority dependencies in this scope review. A gate for another
   operation or an output merely owed by this operation is not a prerequisite.
5. Describe each receipt's schema, issuer, actual evidence basis, artifact
   identity, custody, retention and downstream consumers. Keep template and
   candidate records unaccepted. Add the target's success/refusal/indeterminate
   definitions, exact reconciliation procedure and retained identities.
   Add `semanticRoles` only for roles the receipt actually proves. Each receipt
   carries at most one execution-boundary role. Coverage roles bind the exact
   operation, fact, primitive identity and closed domain. Exclusion roles bind mechanism,
   attempt binding, owner, producer set, phase ordinal, immediate predecessor,
   direction, availability, predicate and exact producer. Do not relabel an observation,
   stale attempt or future output as current lifecycle evidence.
6. Add resource rules only for their actual filesystem and operation scopes,
   using the applicable reserve and expected allocation. If measurement or
   envelope is unknown, use an unknown assessment. Add custody-gated cleanup,
   rollback limits and applicable privacy/egress rules. Empty arrays mean no
   declared requirement and must be justified by the target scope.
7. Record existing repair authority. List ordinary wiring defects as autonomous
   repairs. Use owner questions only for a genuine unresolved protected choice
   or missing owner-supplied fact. Pin the assessment's provenance separately;
   do not mark it caller-verified merely because the file validates.
8. Validate and run preflight at an explicit time. `validate` success and a zero
   preflight exit status do not mean the integration is complete. Require
   `integrationComplete: true` for a completed declaration handoff; inspect and
   repair every `integrationBlockers` entry under standing authority. A missing
   `interfaceClosure` or `executionBoundary` is a valid legacy-draft omission
   but cannot be complete. Keep
   unresolved facts in `readinessHolds`; do not fabricate evidence or grants to
   remove them. If wiring cannot be finished, label the deliverable an incomplete
   draft. Examine every operation's scoped blockers, and retain the exact
   input bytes, pins and resulting JSON. Test at least one permitted preparation
   and one refused effect/cleanup path appropriate to this integration.

Read the [specification](SPECIFICATION.md) for field meanings and limits. The
starter deliberately permits only fictional preparation/reconciliation while
release and cleanup remain blocked despite `integrationComplete: true`. Its
unresolved operator is bound separately from the release authority owner, with
empty invocation allowlists. Its source policy is not authority for real
work. No receipt in it records an actual acceptance.

Do not "fix" a red preflight by changing unknown evidence to accepted. The
bounded deliverable may be a usable adapter with a correctly held production
operation. Acceptance of that adapter and permission to operate production are
separate events. Use [QUALIFICATION.md](QUALIFICATION.md) to test whether a fresh
integrator can derive this behavior from the product documentation alone.
