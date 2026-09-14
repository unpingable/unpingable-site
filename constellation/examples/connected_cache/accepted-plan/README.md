# Public accepted-cache input fixture candidate

This exporter validates one already accepted, checked and locked generic
synthetic-cache Plan Core store and its closed accepted bundle, then copies the
exact bytes into a new public fixture directory. It never contacts a provider,
creates an acceptance, modifies the source store, compiles, authorizes, or
executes work.

This is deliberately a frozen-fixture exporter, not a general database
sanitizer: it accepts only the two independently reviewed source hashes recorded
in the program. The bundle's `acceptance_ref` is an opaque caller assertion. It preserves the
identity used by the accepted-mode qualification but does not authenticate the
accepting person. The exported database contains only the generic cache plan,
two revisions, two structural check receipts and one lock receipt. The exporter
refuses a store for which the operator has not established quiescence, wrong
source hash, wrong selected identity,
non-current plan, missing current passing check, or mismatched lock.

Absent WAL/SHM sidecars are required but do not prove the absence of a concurrent
writer. Stop writers first. The exporter measures the source, validates a
private immutable snapshot, then rechecks the source pathname, bytes and
sidecars before writing the candidate.

Run with the pinned Maude source on `PYTHONPATH`; publish the generated
`accepted-bundle.json`, `accepted-plan.sqlite`, and `manifest.json` together.
