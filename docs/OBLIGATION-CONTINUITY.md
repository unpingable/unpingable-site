# Stateful incident follow-through

An unresolved consequence is state, not prose. Incident closure may end the emergency; it must not erase the promises made because of it.

This is a Constellation architecture requirement and operating-process lesson, recorded on 2026-10-05. It does not claim a shipping obligation registry, tracker connector, automatic prerequisite evaluator or new notification capability. External trackers remain the execution ledger. Constellation should preserve why each consequential entry exists, and whether observed reality still makes it relevant.

## Three distinct closures

| Closure | What it establishes |
|---|---|
| Service recovery | The immediate production fault is no longer active, within the observed postcondition |
| Incident closure | The event is sufficiently understood, evidence retained and immediate operational risks bounded |
| Corrective-action closure | Every resulting obligation is satisfied by evidence, deliberately superseded or explicitly retired with rationale |

An incident can close while successor work remains open. The incident record must point to that work rather than remaining open indefinitely or implying that every consequence has disappeared. Accepted debt remains `DEFERRED` with a revisit condition; accepting the delay does not prove satisfaction.

At incident, acceptance-campaign, architectural-spike or deployment closeout, consequential unfinished work requires an explicit handoff:

`finding → successor obligation → authoritative work item → observable status → evidence-backed closure`

Document supersession, branch completion/deletion, repository changes, session loss, silence and age cannot implicitly discharge an obligation.

## Minimal obligation contract

The authoritative backing may initially be an issue/project system. The logical contract is independent of its vendor and must carry:

| Field | Meaning |
|---|---|
| Stable identity | Exact correlation key surviving moves and renamed tracker items |
| Origin | Incident/campaign/finding and evidence identities |
| Statement | What remains unfinished or promised; distinguish desired future state from an already observed result |
| Domain and consequence | Affected systems and consequence of non-completion |
| Owner and tracker | Owning project/role and authoritative work-item reference |
| State | `OPEN`, `BLOCKED`, `DEFERRED`, `IN_PROGRESS`, `SATISFIED`, `SUPERSEDED` or `RETIRED` |
| Prerequisites and forcing conditions | What prevents progress and what should cause renewed attention |
| Closure contract | Required evidence, explicit satisfaction/retirement condition and decision owner |
| Supersession | Successor identity, rationale and transferred residual obligations |
| Review | Last meaningful review/observation, evidence and accepted next review condition or horizon |

These are semantic fields, not a proposed new wire schema or database implementation. Unknown ownership, missing closure evidence and an unavailable tracker must remain visible. A tracker issue marked closed is an observed tracker event, not automatic `SATISFIED`. Satisfaction requires the closure evidence; supersession names the successor; retirement records an explicit decision and rationale. A later general statement such as “storage is healthy” cannot erase a narrower unfinished migration promise.

An obligation is an evidence-bearing promise: compare the promised proposition with current observed state. Retain the mismatch until completion evidence or an explicit supersession/retirement decision resolves it. Changes to scope, owner or closure criteria need an attributable decision; they must not silently rewrite the original promise.

## Completeness, not conversational salience

Search and memory optimize relevance. An obligation query must account for every unresolved entry in its declared scope. A useful result includes scope, observation time, backing-source identity, pagination/completeness and unavailable sources. “None found” is not “none outstanding” when coverage is incomplete. This is a bounded completeness claim over enrolled sources, not knowledge of every promise anyone has ever made.

The proposed process invariants are:

- At lane start, enumerate unresolved obligations for the affected systems.
- At incident opening, evaluate potentially matching forcing conditions against evidence.
- At incident/campaign closeout, give every newly created consequential obligation an owner, tracker and disposition.
- When a deployment changes a prerequisite, revisit relevant blocked/deferred obligations.
- When a tracker item closes, inspect closure evidence or an explicit supersession/retirement decision.

These hooks belong in a future bounded implementation/workflow qualification. They are not satisfied by an agent remembering to run a semantic search, and they are not implemented merely by publishing this note.

## Context memory is a cache, not the ledger

Continuity-backed context reconstruction is a cache role: it can preserve synthesized explanation and relationships, but relevance-based retrieval cannot establish the complete set of unresolved obligations. Agent context is the working set. A cache miss may make reconstruction slower; it must not alter obligation state, satisfy a promise or suppress a mandatory scoped query.

Keep responsibilities explicit:

- Component source, issues and Projects carry their authoritative source/execution state; a future obligation registry must name its authoritative backing and synchronization limits.
- Cartography and component documentation retain explanation, evidence relationships and ownership boundaries.
- Continuity helps reconstruct context; it is not authoritative project or obligation execution state.
- Agent context holds the current working set.

This distinction does not retire Continuity or erase its separately specified memory/custody guarantees. It limits the authority assigned to context retrieval. Do not create another independent status ledger whose state can diverge silently from the execution tracker.

Memory tells you what you were thinking. State tells you what you still owe.

## Age, prerequisites and forcing conditions

Distinguish intentional deferral, a real blocker, an abandoned obligation, an elapsed review horizon and a forcing condition that has become true. A blocker disappearing is evidence for reconsideration, not permission to perform a new action. Record the match, uncertainty and required owner disposition. Ticket age alone must not page or grant action authority.

The Labelwatch retention incident supplies the architectural lesson. Qualified historical-storage work elsewhere in the portfolio and an application-specific deferred transition can coexist; portfolio qualification does not prove that the application completed that transition. Storage pressure or a reader/retention incident should make relevant lifecycle promises visible for review. The exact application obligation, existing deployed archive design and migration trigger must be checked in its owning records before choosing a repair. This note neither declares a particular migration trigger satisfied nor prescribes an unapproved storage replacement.

An operator reviewing the incident later should be able to determine what was repaired immediately, what remained, why deferral was safe, where it is tracked, what would require reconsideration, whether that event occurred and what evidence will finally discharge the obligation. Reconstructing old chats is a failed handoff.

## Qualification and formalization consideration

Proposition: for a declared enrolled scope, unresolved consequential obligations survive incident closure, context-cache loss and tracker/repository moves; terminal disposition requires closure evidence or an attributable supersession/retirement decision. Scope excludes arbitrary unenrolled promises and assumes trustworthy evidence/owner identity. Incomplete source coverage, ambiguous migration lineage, contradictory tracker events and unavailable evidence must produce an incomplete/unknown result rather than a false empty or satisfied result.

This documentation-only change introduces no runtime transitions. Prose, current-source reconciliation and independent review are sufficient for capture. A future implementation should use a small transition model plus shared deterministic vectors for closure-with-open-successor, closed-item-without-proof, cache omission, incomplete enumeration, supersession and changed-prerequisite cases. It must separately qualify correspondence to its authoritative tracker. The integration owner owns this capture decision; it authorizes no new runtime or incident repair.

Related: [operator legibility](OPERATOR-LEGIBILITY.md). A visible obligation must retain its exact identity while explaining consequence, next step and uncertainty in operator language.
