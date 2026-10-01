# Operator and supported adapter API

Run from the repository root with Python 3.10 or later and no dependencies:

```sh
python3 -B -m tools.integration_contract.cli validate contract.json
python3 -B -m tools.integration_contract.cli preflight contract.json \
  --assessment-time 2030-01-02T00:00:00Z
python3 -B -m tools.integration_contract.cli --human preflight contract.json \
  --assessment-time 2030-01-02T00:00:00Z
python3 -B -m tools.integration_contract.cli repair-query contract.json \
  --category composition --changes implementation
```

The timestamp above is an example, not a measurement. Choose and retain the
actual explicit assessment time. From `constellation/`, set `PYTHONPATH=..`
and use paths relative to that directory. `--human` precedes the subcommand.

| Result | Meaning and next action |
| --- | --- |
| Exit 2, `valid: false` | Input/validation refusal (or argparse usage error). Repair the exact reported field; do not act on a partially interpreted document. |
| `validate`, exit 0 | Declaration is structurally valid. No evidence authentication, operational readiness or effect authority follows. |
| `preflight`, exit 0 | Assessment completed, **including when operations are blocked**. Inspect individual operation dispositions and blocker codes; never use process success as admission. |
| `integrationComplete: false` | Structurally valid but incomplete draft. Repair `integrationBlockers`, including any missing/partial source-derived interface closure, before claiming a completed declaration handoff. |
| `integrationComplete: true` | The declared source-derived interface closure and its wiring are complete under the bounded checks; `readinessHolds` may still block every runtime operation. V1 cannot prove the prose sources were interpreted completely. Not acceptance or execution authority. |
| `blocked` | One or more declared obligations are unmet/unknown. Resolve every blocker only for the affected operation. |
| `permitted-by-declared-contract` | No declared blocker for this local operation; native/platform authority and real resource admission still apply. |
| `ready-for-existing-authority-check` | External/production checklist has no declared blocker; the named existing authority must still check and admit it. |
| Repair query exit 0 | Query was evaluated. Inspect `allowedByDeclaredStandingRepairAuthority` and `requiresExistingOwnerDecision`; exit status is not a permission decision. |

Preflight does not return an accepted occurrence or an execution outcome.
Indeterminate is an outcome declared in the contract for uncertainty after
execution/response loss. Unknown preconditions appear as scoped blockers before
execution. Reconcile the original identities with the native procedure; do not
rerun the effect because output was lost. Preserve raw evidence unchanged.

JSON is the complete result; human text includes interface-closure presence,
completeness, blocker/hold counts, global integration-blocker details and a
concise operation/blocker summary. A global blocker is not hidden merely because
it does not belong to one declared operation. `integrationBlockers` and `readinessHolds`
partition `diagnostics`; both remain in operation blockers. See the specification
for the exact completeness codes. A missing binding is composition work; an
unresolved bound principal or grant is a readiness hold. Bind known logical roles
without changing their unknown statuses or asserting principal allowlists.
Retain JSON for the invocation, credential/evidence/issuer/custody checklists,
owed outputs, owner decisions, autonomous repairs, resource and cleanup
restrictions, and assessment provenance/limits. Reconciliation, raw
interpretation, rollback and outcome definitions remain in the input contract,
so retain it alongside output.

For runtime work, inspect `executionBoundaryChecklist`. Confirm the baseline
operation identity, any exact separately mediated observation primitive, closed
population/PID/user/procfs coverage with its binding receipts, fail-closed rule,
the binding receipt's exact operation/fact/primitive/domain role, logical authority references and
independent custody. A special effect mechanism is an authority-bound delegated
executor, not an observation or custody label. A point census is not a
producer-slot reservation. Exclusion through dispatch requires an exact shared
mechanism honored by every producer and an exact externally accepted attempt
binding. Attempt, acquire and hold receipts must match their declared issuer,
acceptance authority and distinct external authority-evidence receipt. Acquire
precedes observation and hold continues through dispatch. Handoff and release are
distinct owed outputs in predecessor order; they must not be pre-populated or
used as current prerequisites. `EXECUTION_BOUNDARY_UNRESOLVED` is a
readiness hold; `EXECUTION_BOUNDARY_MISSING` is incomplete integration wiring.

## Supported Python surface

Import these names from `tools.integration_contract`, not private helpers:

```python
from tools.integration_contract import (
    ContractParseError, ContractValidationError,
    load_contract, loads_contract, validate_contract, preflight, repair_query,
)

document = load_contract("contract.json")
validate_contract(document)
result = preflight(document, assessment_timestamp="2030-01-02T00:00:00Z")
repairs = repair_query(document, category="composition", changed_boundaries=[])
```

`load_contract(path)` performs one bounded stable regular-file read, rejects a
final symlink and duplicate JSON keys, and caps input at 1 MiB.
`loads_contract(bytes_or_string)` applies the same JSON/size checks to supplied
UTF-8 content. `validate_contract(document)` returns the checked mapping;
`preflight` and `repair_query` validate before deriving their JSON-compatible
results. Validation exceptions expose `code`, `field`, and a message; parse
exceptions expose `code` and a message. Keep supplied mappings free from
concurrent mutation; do not modify a document or returned nested checklist while
another caller uses it. Results may share nested values with their input.

If `interfaceClosure` is present it must be an object. JSON `null` is a typed
validation refusal (`TYPE_OBJECT`), not an omitted legacy closure, and both the
API and CLI refuse it before preflight derivation.

Adapters may map a caller's already selected, non-secret facts into one ordinary
V1 document and pass it to these functions. This API performs no target discovery,
artifact-path reads, environment credential inspection, receipt authentication,
command execution, network access or writes. It does not infer acceptance from
another schema. The integration owner must review any mapping's actual meaning.

A small application adapter should select operation results by their exact
qualified identity, retain the full diagnostics and no-authority statement, and
present or return them. It must not automatically dispatch a native command from
a preflight label. Target-specific execution and verification remain separately
admitted native workflows. No extra manifest or executable adapter format is
required; there is no dynamic loading API.

## Practical refusals

`INVOCATION_*` identifies a missing, unresolved or unauthorized logical caller
or invocation authority. `CREDENTIAL_PRINCIPAL_MISMATCH` keeps credential scope
independent from consumer and authority matching. Neither an authority's owner
nor an operation's consumer fills an invocation binding. `GATE_*` and `TIME_*`
identify only the named gate's operations. An unrelated preparation operation
may still proceed within a structurally valid declaration.

`INVOCATION_AUTHORITY_KIND` validation refusal means the selected invocation
authority has an incompatible kind; adding a separate matching authority does
not fix the binding. Correct it under the existing runtime contract and retain
unknown identity, authorization or credential states as holds.

Unsupported clocks require their native
owner/verifier, not a guessed UTC conversion. `CREDENTIAL_*` means readiness,
purpose, consumer, authority or verification is missing; never substitute a
storage key for a signing or effect credential. `EVIDENCE_*` identifies the
missing/unchecked receipt or issuer. `RESOURCE_*` requires the applicable
filesystem/operation envelope and current resource-owner assessment, not a
different filesystem's free-space sample. `CLEANUP_*` requires actual
regenerability and custody. `OWNER_DECISION_UNRESOLVED` is only as valid as the
encoded owner decision: ordinary reference wiring belongs in autonomous repair.

Do not widen a scope or weaken an acceptance criterion to clear a blocker.
`EVIDENCE_SCOPE_GATE_*` means a runtime receipt prerequisite lacks
the existing gate partition that binds its negative scope; it does not replace
the receipt's positive consumer allowlist. This applies before acceptance, even
to missing/template/prepared receipts: declare the future acceptance gate now.
A `prerequisite-source` gate cannot substitute for `required-evidence`.
The prerequisite closure includes receipts introduced only by an applicable
gate and their transitive issuer-authority evidence. Each consumed
receipt in that closure needs covering required-evidence scope of its own.
Record the existing owner's actual new fact in a successor contract assessment;
retain prior inputs and outputs as historical evidence. Local preparation of a
candidate does not clear a release or production gate.

`INTERFACE_CLOSURE_MISSING` means the contract predates or omitted the finite
source-derived inventory. `INTERFACE_CLOSURE_INCOMPLETE` means at least one
declared owner/role, authority, operation, gate, credential, receipt, resource,
privacy or cleanup object is absent from that inventory. Repair the inventory
from the pinned target sources; do not auto-copy the current collections and
declare success, because the defect may be an omitted upstream operation or
native object.

`EXECUTION_BOUNDARY_MISSING` means an operation omitted the explicit null or
runtime boundary. Do not respond by running an entire observer as UID 0. Keep
ordinary observations under the normal identity and isolate only the smallest
fact whose visibility requires mediation. Other `EXECUTION_BOUNDARY_*`
refusals prevent platform identity from becoming logical authority, custody,
historical convention or durable resource exclusion.
