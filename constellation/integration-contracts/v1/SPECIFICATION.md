# Integration Contract V1 specification

`constellation.integration/v1` describes one finite integration as JSON data.
The supported adapter is a contract instance consumed by the public validation
and preflight API. It has no commands, callbacks, dynamic imports, predicates,
plugin discovery, scheduling, receipt verifier, or execution capability.
The separate `constellation.integration-profiles/v1` format is not V1 input.

V1 grants no target-effect authority. A valid declaration records obligations;
a recorded receipt describes evidence; an existing owner grants authority.
These three facts remain separate even when every declarative check passes.
Neither an accepted label, a pathname, a digest, source compilation, passing
tests nor a prepared candidate constitutes an accepted release. Issuer honesty,
deployment identity and actual receipt verification remain caller/owner duties.

The [schema](schema.json) defines shape. The Python validator additionally
enforces references and the rules below. Shared vectors are normative observable
examples, including refusals. Opaque strings are not a general instruction
language. V1 does not prove that free-text claims or supplied facts are true.

## Identity and scope

`integration` names its ID, short purpose, and intended consumers. Each
collection's IDs are unique within that integration. Output identities are
`integration-id/local-id`; matching short names in separate integrations never
join. References select a particular collection within this contract. `imports`
must be empty: cross-contract resolution is unsupported and fails closed, even
if a source contract pin is supplied. Do not copy another integration's gate
merely because its name or campaign is familiar.

`sources` records exact source/protocol/procedure/policy locators and pins.
`pinned` requires a pin; `unverified` requires a reason. V1 never dereferences
these locators, verifies pins, or infers a dependency from their presence.
If an unresolved source prevents an operation, represent that requirement with
an explicitly scoped gate and receipt. Source inventory alone is not a gate.

`interfaceClosure` is the source-derived finite inventory for the integration.
Its `basisSourceRefs` names the exact source set from which the author derived
the supported interface. The remaining lists inventory every owner/role,
authority, operation, gate, credential class, receipt/evidence object,
operation-scoped resource rule, privacy rule and cleanup rule declared by this
contract. Every referenced ID must exist. Preflight makes an omitted declared
object an `INTERFACE_CLOSURE_INCOMPLETE` integration blocker. A structurally
valid older draft may omit `interfaceClosure`, but then preflight reports
`INTERFACE_CLOSURE_MISSING` and `integrationComplete` is false.
An explicit JSON `null` is not omission: validation refuses it as `TYPE_OBJECT`
at `interfaceClosure`, and preflight returns no partial result.

The inventory is deliberately not a second workflow language. It provides a
closed, inspectable checklist against pinned target sources. V1 cannot parse
prose or prove that an author discovered every target element. Independent
review must compare the closure to the source-defined causal chain: upstream
configuration, producers, intake/receivers and separately custodied native
objects remain part of an integration even when the named final consumer is
read-only. Distinct credential classes and distinct evidence/receipt objects
must not be collapsed merely because one later command consumes them all.
When declared objects are absent from the closure, both JSON and human preflight
output identify the incomplete closure; neither may describe the partial list as
inventorying every declared object.

`owners` distinguishes resolved identity from unresolved identity and names the
existing boundary. `authorities` separately distinguishes established from
unresolved authority. A repository name or current operator does not establish
acceptance ownership. Authority kinds are local work, storage, compute, local
effect (`effect`), external effect, production effect, privacy, acceptance and
cleanup. They are not interchangeable. An effect operation must reference its
matching effect authority kind; cleanup requires cleanup authority.

For invocation provenance, an `owner` ID is also the bounded logical principal
identifier. This reuse does not define a UID, account, role hierarchy or general
operating-system identity model. Each authority's `authorizedPrincipalRefs` is
an explicit invocation allowlist. `ownerRef` identifies who owns the authority;
it never makes that owner an authorized invoker. An empty allowlist records that
no invoking principal has been established.

## Operations, gates and credentials

`operations` is a finite set of local preparation, local effect, external effect,
production effect, read-only reconciliation and cleanup declarations. Each names
its consumer, purpose and required authority, credential, input receipt,
resource and privacy references. `producedReceiptRefs` names owed output
evidence, which cannot satisfy its own producer. A receipt has at most one
declared producer. A gate cannot require an output of an operation it blocks.

Every operation explicitly declares `executionClass`. `source-only` is limited
to `local-preparation` and requires `invocationBinding: null`. A `runtime`
operation uses either a binding with `principalRef` and `authorityRef`, or a null
binding that produces `INVOCATION_BINDING_MISSING` for that operation. The bound
role and authority references are declaration wiring: once both are declared,
bind them even if identity, owner or authority status remains unresolved. Null
is allowed for an incomplete draft, not a completed integration handoff. The bound
authority must also be required by the operation. Preflight separately checks
principal resolution, authority resolution, the authority principal allowlist,
and every required credential's principal allowlist. Read-only reconciliation
and runtime-classified preparation are not exempt. Source review, authority
ownership, a consumer string and credential presence cannot supply the binding.

The bound authority's kind must match the declared runtime operation:

| Runtime operation kind | Allowed invocation authority kind |
| --- | --- |
| local-effect | effect |
| external-effect | external-effect |
| production-effect | production-effect |
| cleanup | cleanup |
| read-only-reconciliation | local-work |
| local-preparation | local-work or compute |

An incompatible kind is a hard `INVOCATION_AUTHORITY_KIND` refusal even if the
authority is required and its principal allowlist matches. A separate matching
effect authority elsewhere in the operation does not make a storage, acceptance
or privacy authority its invocation grant. This is a bounded contract-kind rule,
not an OS privilege or account model. Principal authorization and credential
readiness remain independent checks after kind compatibility.

Each gate names an owner, kind, recorded status and disposition, required
receipts, and both `blocks` and `doesNotBlock`. Those lists must be disjoint and
partition all operations. A satisfied gate requires at least one receipt.
`doesNotBlock` exempts only that gate: it cannot cancel another prerequisite.
Preflight reports every applicable blocker separately. Unresolved facts remain
valid data so that a production hold does not hide independent preparation.

### Runtime execution boundary

Every completed operation explicitly carries `executionBoundary`: source-only
work uses JSON `null`; runtime work uses an object. Older documents may omit the
field and remain parseable, but preflight reports `EXECUTION_BOUNDARY_MISSING`
and `integrationComplete` is false. An unresolved runtime boundary is declared
with `status: unresolved` and an exact reason; that is a readiness hold rather
than permission to guess the platform identity.

The boundary separates technical visibility, logical authority, effect
execution, and output custody. The operation identity and capabilities always
equal its declared baseline. Technical visibility names exact interfaces, a
typed claim kind, and typed coverage: a closed population profile, closed
PID/user/procfs domain, complete-or-refuse disposition and exact domain-binding
receipt references. A producer-absence claim mechanically requires the
`all-owner-uids`, bound host PID namespace, bound initial user namespace and
all-PID hidepid-zero-or-refuse profile; an invoking-owner sample or partial
procfs view cannot satisfy it even when primitive and fact repeat the same
description. Each all-owner domain-binding receipt has one typed role that
repeats the exact operation, fact, delegated primitive identity and full closed
coverage domain; an unrelated accepted receipt cannot be relabelled as this
evidence. A separately mediated observation
primitive uses an exact digest/package/service identity and binds argv where
applicable, invoking principal, execution identity, capabilities, typed
coverage and receipts. Fact and primitive coverage must match exactly; opaque
text such as “whatever is installed” is not identity or coverage.
`authoritySemantics` must match `invocationBinding`; a UID, account, capability
or service does not convey logical authority. `outputCustody` separately names
the writer, owner, mode, pathname replacement boundary and receipts. Output
ownership cannot justify observation privilege. If a bounded delegated
primitive supplies broader visibility, the main operation retains its baseline
identity and capabilities. A special effect mechanism is instead a
`delegatedExecutor` bound to the current operation and one of its existing
logical authorities; it is never an observation fact or custody convention.
Historical `campaignConvention` entries cannot establish a technical requirement.

`leastPrivilegeAlternative` records whether the claim is available directly to
the ordinary identity, through one bounded delegated primitive, or not at all.
The main observer remains at its baseline identity when a delegated primitive
is sufficient, and broader privilege is refused.

Every visibility fact refuses incomplete coverage. A point-in-time all-UID
process census establishes only absence at that instant; it does not reserve a
producer slot. Only `reserved-through-dispatch` with a structured shared
exclusion may set `establishesExclusion: true`. It binds the exact lock, lease or
scheduler slot, owner, complete relevant and honoring producer sets, and an
externally accepted attempt identity for one exact relevant runtime effect
operation. The attempt identity is pinned to a declared source and receipt and
is accepted by an owner distinct from the attempt supervisor. The attempt,
acquisition and hold declarations also name the exact expected receipt issuer,
its established acceptance authority and a distinct current externally accepted
authority-evidence receipt named by that authority. Receipt issuer fields must
match those declarations. V1 validates these exact declared links but does not
authenticate the issuers or grant effect authority; selecting another anchor by
coherently changing the accepted contract produces a different contract identity
that requires source review.

Mechanism identity and phase predicates use closed structured forms. Acquisition
precedes the load-bearing observation, and current hold continues through
dispatch. Their receipt roles repeat the exact predicates. Acquisition and hold
are accepted current inputs. Handoff and release are distinct
missing outputs owed by the bound operation; they must not pre-exist or appear
in a current operation/gate prerequisite. Every phase has one distinct receipt,
one role, exact direction and availability, and the exact immediately preceding
receipt. One summary receipt cannot witness multiple phases. Handoff targets the
bound relevant runtime effect operation. A stale attempt, observation receipt,
admission authority alone, arbitrary lifecycle prose or future output relabelled
as a current input is not shared exclusion. Admission requiring continuing
serialization consumes the current attempt/acquisition/hold facts and records
handoff/release as owed transition evidence rather than stretching a census
receipt.

An optional `timeBoundary` names a not-before instant, a clock contract and its
recorded assessment. Only `rfc3339-utc` is interpreted; assessment time is always
explicit. Both the explicit time and recorded assessment must reach the
boundary. Unsupported clocks or malformed boundary times are unresolved, scoped
diagnostics. A reached time never satisfies evidence or owner requirements.
Do not translate opaque receiver ticks into UTC or merge clocks by field name.

Credentials contain non-secret purpose, readiness (`present`, `absent`,
`unverified`), scope verification, authorized consumers, authorized logical
principals, granted and explicitly denied authority references, and
evidence/source references. A requirement must match purpose, operation consumer,
invoking principal and granted authority exactly. Present bytes alone do not
establish scope. Storage authorization cannot satisfy compute, effect or
sequencing obligations. V1 does not read credential material.

## Evidence and assessment

Every receipt names `schemaType`, `issuerOwnerRef`, `issuerAuthorityRef` (an
acceptance authority belonging to that issuer), evidence basis, artifact
identity, custody, retention and downstream operation consumers. Basis,
artifact and custody have separate typed statuses. Dispositions are `missing`,
`template`, `retained-unverified`, `externally-accepted`, and `failed`.
Externally accepted requires all three facts recorded, a resolved issuer and
established acceptance authority for dependent operations to proceed.
Missing/template/unchecked records never satisfy requirements. A retained
candidate remains retained-unverified until its existing acceptance process
produces the actual disposition; prose saying "prepared" cannot promote it.

Preflight follows the finite receipt-to-issuer-authority evidence dependency
graph, checking downstream consumer scope and rejecting cycles as scoped
blockers. It never authenticates an issuer or runs an external verifier.
`owners[].evidenceRefs` records identity provenance; it is not an additional
recursive owner-authorization graph. Put operative evidence obligations in
authorities, credentials, gates or operation inputs.

The positive `downstreamConsumers` allowlist remains an independent check. In
addition, each receipt that is an actual prerequisite of a
runtime operation must be referenced by a `required-evidence` gate whose
`blocks` includes that operation. The gate's existing `blocks`/`doesNotBlock`
partition supplies negative scope; V1 adds no second receipt-scope vocabulary.
Runtime prerequisite edges include direct operation inputs plus receipts from
every gate whose `blocks` contains that operation, authority, credential,
privacy-authority, cleanup-custody, invocation-authority and transitive
issuer-authority evidence. A receipt introduced only by an owner, source or time
gate still needs its own covering required-evidence gate; issuer-authority
dependencies of gate evidence do too. This declaration obligation applies before
acceptance, including missing, template, retained-unverified and failed receipts:
each must eventually become externally accepted to satisfy its consumer.
`prerequisite-source` is not an acceptance-scope substitute.
Merely producing a receipt is not consumption, and gates for other operations
do not introduce dependencies. Source-only preparation's independent prerequisite
set excludes gate references so a broad gate cannot justify its own inclusion
of otherwise unrelated preparation.
Missing or mis-scoped gates yield `EVIDENCE_SCOPE_GATE_MISSING` or
`EVIDENCE_SCOPE_GATE_INCOMPLETE` only on dependent runtime operations; unrelated
source-only preparation remains independent. The dependency walk is finite and
cycle-safe, while receipt verification reports cycles separately.

## Derived integration completeness

Preflight returns `declarationValid: true` for a structurally valid document,
including drafts. It separately derives `integrationComplete` from declaration
closure and wiring. This is false if `integrationBlockers` contains any of:

- `INTERFACE_CLOSURE_MISSING` or `INTERFACE_CLOSURE_INCOMPLETE`
- `INVOCATION_BINDING_MISSING`
- `EXECUTION_BOUNDARY_MISSING` or `EXECUTION_BOUNDARY_AUTHORITY_MISMATCH`
- `EVIDENCE_SCOPE_GATE_MISSING` or `EVIDENCE_SCOPE_GATE_INCOMPLETE`
- `EVIDENCE_CONSUMER_SCOPE_MISMATCH`
- `EVIDENCE_ISSUER_AUTHORITY_CYCLE`
- `CLEANUP_RULE_MISSING`

These are composition defects, not missing runtime facts. All other scoped
diagnostics form `readinessHolds`, including unresolved principals/authorities,
absent or unverified credentials, unmet gates, missing/unaccepted evidence,
unknown resource assessments and owner decisions. The two arrays partition
`diagnostics`; operation `blockers` and dispositions still include both classes.
A complete declaration can therefore have every runtime operation blocked.
Hard validation refusals still produce no preflight result.

Completeness is derived from the interface closure and wiring, not an accepted
input field. It is necessary for a
completed declaration handoff, not proof of omitted requirements, current target
facts, external acceptance, terminal handoff custody or permission to execute.
The adapter cannot determine whether the pinned prose was interpreted
completely or whether a free-text owner question is genuinely necessary.
Independent review and fresh-integrator qualification remain separate acceptance
requirements.

## Assessment validity

`assessment` names recorded time, provenance source, optional source pin,
verification and limitations. `caller-verified-index` requires a caller-supplied
pin but is not authenticated by V1. An unverified assessment blocks local
effects and cleanup. External/production operations can at most become
`ready-for-existing-authority-check`; even a verified index grants no authority.
Assessment time does not refresh source measurements or existing receipts.

## Resources, privacy and custody

Each `resourceRules` entry names the exact resource/filesystem, purpose, scope,
unit, minimum reserve, expected allocation and applicable operations. Operation
references must agree exactly with applicability. A rule is met only when the
recorded status is `meets` and observed availability is at least
`minimum + expectedAllocation`, with measurement time and provenance.
Unknown measurements block applicable operations. No rule is inferred from a
pathname, another filesystem, or another integration. V1 neither checks mounts,
measurement freshness, inodes, aggregate tenants nor omitted rules. The caller
must admit a complete, current resource envelope before actual allocation.

`privacyEgress` declares data class, recipients, purpose, enrollment scope,
privacy authorities, retention, unknowns, applicable operations and disposition.
Only those operations are held by unresolved privacy. An empty list means no
declared egress obligation, not an inferred privacy grant.

`cleanupRules` names regenerable object classes, exact cleanup operation scope,
and custody prerequisite receipts. Missing rules, nonregenerable classes or
unsatisfied custody refuse cleanup independently of job success. This does not
prove any pathname disposable: actual cleanup must resolve ownership, live
consumers, mounts, links, backing dependencies and unique custody under existing
authority. Unknown or evidence-bearing objects remain retained.
`rollback` separately identifies reversible/compensable effects, a source
procedure reference and retained-state limits. Compensation need not erase data.

## Outcomes, recovery and repair

Exactly three `outcomes` define success, refusal and indeterminate with required
evidence. They are declarations, not verdicts computed by preflight. Process
exit is not acceptance. Response loss is not proof that no effect occurred.
`reconciliation` names retained occurrence/attempt/issuance identities, whether
redispatch is forbidden, and an exact source procedure. Follow the same original
identities after supervisor loss; do not manufacture a retry or new acquisition.

`rawEvidence.immutable` must be true. Interpretation/duplicate rules name their
source and scope; V1 never normalizes raw evidence, deduplicates by timestamps,
or transforms an input series. A derived interpretation is a separate artifact.

`repairAuthority` references the existing standing policy and allowed bounded
categories (`composition`, `implementation`, `test`, `documentation`). The five
protected boundaries are semantics, authority, privacy, production state and
acceptance criteria. A repair affecting any protected boundary requires its
existing owner decision even if called composition work. The repair query checks
declared changes, not code behavior or caller honesty.

`autonomousRepairs` holds ordinary missing implementation, wiring and tests.
Do not turn filenames, cache locations or established retry mechanics into owner
questions. `ownerDecisions` contains only unresolved real decisions: a `choice`
requires at least two distinct materially different contract-compatible options,
evidence that does not select one, rationale and owner boundary. Static checks
can prove only distinct strings, not materiality. An `owner-supplied-fact` instead
names the missing fact, why only that owner can supply it, bounded evidence
search and affected operations; it has no fabricated alternative identities.
Every listed owner decision blocks its affected operations until resolved.

## Refusal boundary

Malformed JSON, duplicate keys, oversized/nonregular inputs, unsupported
version/imports, unknown fields, wrong types (including boolean numbers),
duplicate identities, dangling references and contradictory scopes are hard
validation refusals. Correctly shaped unknown facts produce scoped preflight
blockers. The [operator guide](OPERATIONS.md) defines commands, exit status and
the public adapter API. No V1 result overrides platform or existing permissions.

## Pre-beta migration

The still-pre-beta V1 shape requires every completed declaration to add
`interfaceClosure`, derived from its current source basis before mapping the
target chain into collections. A missing closure stays a valid incomplete draft;
do not auto-populate it from the already-authored collections because that would
simply restate any omission. It also requires every authority and credential to
add `authorizedPrincipalRefs`, and every operation to add `executionClass`,
`invocationBinding`, and explicit `executionBoundary` (`null` for source-only
work). A missing boundary stays parseable only as an incomplete legacy draft.
Documents missing the older required fields fail closed with
`FIELD_MISSING`. Do not infer allowlists or bindings from `ownerRef`, `consumer`,
prose, source review or credential presence. Keep unknown grants as empty allowlists.
Bind a declared logical runtime role to its compatible required authority even
when resolution and authorization remain unknown. If the role or binding cannot
yet be declared, null remains valid but `integrationComplete` is false.
All runtime receipt prerequisites need gate scope before acceptance, not only
after evidence becomes available. Rerun preflight after any migration and repair
wiring without promoting evidence or inventing authority facts. The starter
demonstrates complete wiring with honest holds. Unknown bindings are never
silently inferred, and prior output is not current output. The API version string
is unchanged because no accepted stable release or named cross-repository runtime
consumer exists; the repository CLI, schema, starter and conformance checks are
the current in-repository consumers.
No cross-repository runtime adoption is claimed.
