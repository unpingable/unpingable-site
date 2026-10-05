# Operator legibility at the presentation boundary

Legibility must be architecturally earned, and must not be discarded at the final serialization boundary. A notification can be mechanically correct and still fail its human recipient. The Labelwatch monitoring incident illustrates this reusable product rule: an exact condition key is valuable correlation machinery, not the primary interruption message. Product context is not a machine hostname.

Keep five concepts distinct:

| Concept | Purpose |
|---|---|
| Condition identity | Exact stable key for deduplication, trigger/resolve correlation and evidence lookup; preserve unchanged |
| Operator summary | Affected product/service and what happened, before internal component names |
| Operational consequence | What cannot be trusted or which obligation may be at risk; do not infer an underlying failure from missing evidence |
| Operator action | Next useful bounded diagnostic step or runbook; advice does not grant an effect |
| Epistemic qualifier | What is known/unknown, and exactly which proposition a clear/resolve establishes |

A useful rendering is:

> **Labelwatch monitoring data is stale**
>
> Constellation has not received current evidence for 6 minutes.
>
> **Impact:** Checks depending on this input cannot currently be trusted. Their state is unknown, not healthy.
>
> **Action:** Inspect `nqd` and the acquisition path; confirm fresh evidence before interpreting the saved check.
>
> Correlation ID: `constellation:labelwatch:nq:evaluator-input-unavailable:nqd.stale`

The age in that example must come from the actual evidence/currentness contract, never an invented renderer estimate. A deployment supplies its product label and appropriate runbook; the renderer must not guess them from a hostname or an opaque ID.

A resolve must retain the scope of the trigger:

> **Labelwatch database-health monitoring restored.** The saved check is producing usable evidence again. This resolves the monitoring failure; it does not establish that an underlying database fault has been repaired.

## Current implementation and bounded repair direction

Monitor attention has stable condition keys, distinct observation states, evidence references/notes and registry fields for the condition, operator action, escalation reason and response class. NQ delivery retains native condition/dedup identity and custody. These should be preserved when producing human text. Current technical trigger summaries and status ID/note rows do not consistently expose the available consequence/action information. This is a presentation gap, not a reason to change evaluator truth semantics or condition keys.

Trace the current attention intent summary and its NQ delivery rendering before a presentation repair. Render a human summary, consequence and next step from qualified registry/domain context, with exact ID in secondary details. Slack should distinguish trigger from resolve rather than prefixing restored monitoring as a new interruption. PagerDuty's trigger summary/details and matching resolve must retain native dedup semantics; a protocol branch that transports only a resolve dedup key must not be documented as carrying a new human recovery claim. Workbench/status should retain raw evidence and correlation while foregrounding the same bounded human interpretation.

This documentation capture does not claim those renderer improvements already ship, add a domain-context publisher or alter notification protocols. A future bounded presentation change must verify actual current-path examples of observation loss/restoration and underlying obligation failure/clear. If a particular source/registry cannot distinguish those propositions, expose that absence as unknown or a real schema/design gap; prose cannot manufacture it. Product context/runbook enrollment may be missing even where the core state contract is sufficient.

## Operator language

| Native term | Human meaning |
|---|---|
| `unknown` | Available evidence cannot establish this condition's truth; it is not a healthy result |
| `indeterminate` | Evaluation could not reach a justified conclusion; inspect the reason and evidence gap |
| `stale` | The evidence is too old or otherwise outside its qualified time/boot boundary for this use |
| `clear` | Qualified current evidence clears the specific proposition; absence, removal or unreadability does not clear it |
| `resolved` | The corresponding notification lifecycle is closed for that proposition; monitoring restoration alone does not prove service repair |

A page may demand human attention because an obligation cannot be evaluated, rather than because its underlying service is proved failed. Keep that distinction in summaries, resolves, runbooks and UI. Do not hide uncertainty behind friendly prose or require knowledge of the internal component graph to understand the interruption.

## Formalization consideration

Proposition: presentation preserves exact identity, source proposition, uncertainty and trigger/resolve scope while adding qualified human context. Current typed-state/registry inspection and named examples are sufficient for this bounded design capture; no new runtime/wire semantics are introduced. Unknown domain labels, missing source distinctions and dedup-only resolve transports limit what can be rendered. A future renderer correction should use deterministic paired trigger/resolve and unknown-hold controls. Integration owner owns this decision; component source/tests remain authoritative.

## Current-path trace and genuine context gap

The current attention engine uses native v1 delivery for Slack/Discord/local notices and v2 for PagerDuty pages. This is active supported installation behavior, not a compatibility-only obligation. The intent summary becomes human text in Monitor’s `constellation-attention/src/intent.rs`; NQ’s `nq-app/src/notification.rs` renders the summary at its transport boundary. Native v1 Slack notices currently use an “Attention required” prefix even for a resolve. PagerDuty v2 trigger carries summary/details; its resolve carries the exact dedup key, not a new explanatory recovery body. The live status adapter currently exposes condition ID and notes.

The registry already carries `condition`, `operator_action`, `escalation_reason` and `operator_response`; qualified observation state distinguishes Present/Clear/Unknown/Removed. A missing/unknown input holds the earlier underlying condition and does not manufacture a clear. These fields can improve generic consequence/action text without an evaluator redesign. The contract does **not** currently supply a generic owner-authored product/domain label or consequence mapping for every bounded machine token. That is a real context/design gap for domain-specific summaries, not permission for a renderer to infer “Labelwatch” from an opaque key. A bounded presentation follow-up should first use existing registry semantics and explicitly supplied context, qualify paired observation-loss/restoration and obligation-failure/clear messages, and retain raw IDs for correlation.

Current source references: [Monitor intent](https://github.com/unpingable/constellation-monitor/blob/ea7438aa6dc365525a614620c5e091ee9643522e/crates/constellation-attention/src/intent.rs), [Monitor engine](https://github.com/unpingable/constellation-monitor/blob/ea7438aa6dc365525a614620c5e091ee9643522e/crates/constellation-attention/src/engine.rs), [NQ delivery](https://github.com/unpingable/constellation-nq/blob/996f2ca9c5b1c7bb148d9cf9e818432b6f860936/crates/nq-app/src/notification.rs). Exact immutable inspection receipts are separately retained by the private Program; these source links establish the implementation being described, not a claim that the presentation repair ships.
