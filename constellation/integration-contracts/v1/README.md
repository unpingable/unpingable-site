# Integration Contract V1

Start with [authoring a new integration](AUTHORING.md), then use the
[operator and adapter API guide](OPERATIONS.md). The current
[specification](SPECIFICATION.md) defines the semantic contract;
the ordinary validator tests cover the reusable contract boundary. Historical qualification records are maintained separately.
These source documents stand alone for a new target and require no campaign
history, prior integration output or internal qualification fixture. V1 remains
provisional for usability acceptance until independent review and a distinct
fresh-integrator qualification pass.

The current pre-beta shape requires explicit runtime invocation provenance.
Operations classify themselves as `source-only` or `runtime`; runtime operations
bind a logical principal from `owners` to one required authority. Authorities and
credentials carry separate principal allowlists. A null runtime binding is valid
draft data but makes `integrationComplete` false and blocks that operation.
Bind declared logical roles and compatible authorities even while unresolved;
retain actual identity/grant uncertainty as readiness holds. Authority ownership is never an implicit
invocation grant.

The successor shape also makes the runtime permission boundary explicit. Every
operation carries `executionBoundary`: source-only work uses `null`, while
runtime work keeps the operation at baseline and separates typed technical
visibility, authority-bound effect mechanisms, logical authority, receipt
custody and historical convention. Missing runtime boundaries are incomplete wiring;
unresolved platform facts are honest readiness holds. The all-UID census vector
demonstrates the intended least-privilege form: an ordinary observer consumes
one structured, identity-bound, fail-closed census primitive, while custody
remains separate and the point-in-time result does not claim producer-slot
reservation. Its coverage receipt carries one typed role binding the exact
operation, fact, primitive identity and closed PID/user/procfs domain; a generic
accepted receipt cannot stand in for that role. Durable reservation requires an
exact shared exclusion honored by every relevant producer, an externally
accepted pinned attempt binding,
accepted current acquisition/hold inputs, and distinct handoff/release outputs
owed by the exact target operation in predecessor order. Attempt, acquisition
and hold evidence name their exact expected issuer, acceptance authority and
distinct externally accepted authority-evidence receipt. Acquisition precedes
the observation and the hold continues through dispatch.

It also requires a source-derived `interfaceClosure` before a declaration can be
complete. Derive that inventory from the complete causal target path, not from
the objects the author happened to add. A final read-only consumer still depends
on the configuration, producer, intake, credential classes, native evidence,
receiver custody and resource scopes established by its pinned target sources.
Preflight exposes the resolved closure and refuses to call missing or partial
inventory complete. V1 does not introspect prose, so independent review still
checks the inventory against those sources.

`constellation.integration/v1` is one declarative integration per JSON file.
It records scoped prerequisites, evidence dispositions and existing authority
boundaries. It is not the older `constellation.integration-profiles/v1`
format, an execution engine, an issuer authenticator or an effect grant.

All local IDs are qualified by `integration.id` in resolved output. The V1
shape reserves `imports` for explicit integration/object IDs and pinned source
contracts, but this bounded implementation rejects non-empty imports. It does
not claim to resolve or scope-block an imported dependency.

The JSON Schema describes document shape. The stdlib Python validator also
enforces duplicate identities, reference integrity, gate scope consistency,
non-interchangeable authority kinds, credential consumer/scope, typed receipt
facts, owner-choice shape and provenance requirements. `issuerOwnerRef` names
the owner identity; the separate `issuerAuthorityRef` names its existing
acceptance boundary. Explicitly
unresolved facts are valid document content and become operation-scoped
preflight diagnostics. `externally-accepted` is only a recorded legacy
disposition: every output says that V1 did not verify it and grants no effect
authority.

Every receipt used by a runtime prerequisite also needs a
`required-evidence` gate covering that dependent operation. This reuses the
gate's complete `blocks`/`doesNotBlock` partition as negative scope while
preserving the receipt's positive `downstreamConsumers` allowlist. Produced
evidence may be missing or prepared: declare its eventual acceptance scope before
runtime consumption. `prerequisite-source` is not a substitute. Produced-only
receipts do not create a prerequisite edge, and unrelated source-only
preparation remains independent.

An operation's `requiredReceiptRefs` are inputs. `producedReceiptRefs` are owed
outputs and do not satisfy or block their own producer; a gate that creates such
a self-dependency is invalid. Missing output evidence remains visible in the
resolved `producedEvidence` checklist and may gate later consumers. Receipt
basis, artifact identity and custody each carry a typed state, so sentinel prose
cannot make an incomplete record externally accepted.

When an existing issuer acceptance authority itself declares receipt evidence,
preflight follows only that finite receipt/issuer-authority dependency graph.
Missing, template or unresolved support blocks the affected consumers, and a
cycle produces an explicit diagnostic. This bounded walk does not interpret
signatures or create a new authority system.

From the repository root:

```sh
python3 -B -m tools.integration_contract.cli validate \
  constellation/integration-contracts/v1/starter.json

python3 -B -m tools.integration_contract.cli preflight \
  constellation/integration-contracts/v1/starter.json \
  --assessment-time 2030-01-02T00:00:00Z

python3 -B -m tools.integration_contract.cli repair-query \
  constellation/integration-contracts/v1/starter.json \
  --category composition --changes authority
```

The module lives in the repository-root `tools/` directory. If an operator
handoff instead prescribes the repository's `constellation/` directory as the
working directory, expose its parent as the module root and use the contract
path relative to `constellation/`:

```sh
PYTHONPATH=.. python3 -B -m tools.integration_contract.cli validate \
  integration-contracts/v1/starter.json

PYTHONPATH=.. python3 -B -m tools.integration_contract.cli preflight \
  integration-contracts/v1/starter.json \
  --assessment-time 2030-01-02T00:00:00Z
```

Running the module without `PYTHONPATH=..` from that child directory is not a
supported entrypoint because Python cannot discover the sibling `tools/`
package. The repository-root commands above remain the primary entrypoint.

The contract loader reads at most 1 MiB, rejects duplicate keys and non-finite
JSON numbers, requires
a stable regular file and does not follow the final pathname if it is a
symlink. Preflight never opens artifact references, fetches a URI, reads a
credential, runs a command or changes a store.

Validation and preflight behavior are independently conformance-qualified.
Those checks cover shape and reference refusals, invocation-authority kinds,
complete consumed-receipt scope, produced-only exclusion, dependency cycles and
complete wiring versus honest runtime holds. Test data and expected outcomes are
maintainer inputs, not authoring templates or fresh-worker inputs.

Preflight JSON and human output distinguish structurally valid drafts from
complete interface closure and declaration wiring using `integrationComplete`.
`integrationBlockers`
lists composition defects; `readinessHolds` lists remaining fact/authority/
credential/resource holds. Both still block their scoped operations. A completed
handoff needs complete wiring plus the separate qualification/custody obligations;
no completeness result grants authority or authenticates a fact.

Every completed V1 document includes `interfaceClosure`; every operation uses
`executionClass`, `invocationBinding`, and explicit `executionBoundary`, and
authorities/credentials use
`authorizedPrincipalRefs`. Empty allowlists preserve unknown
grants; null runtime bindings preserve incomplete drafts. Migration must not
infer identities or grants from names or prose. The fictional starter has
complete wiring and unresolved release/cleanup holds; it is a structural example,
not a completed target integration template.
No stable cross-repository compatibility guarantee is claimed.
