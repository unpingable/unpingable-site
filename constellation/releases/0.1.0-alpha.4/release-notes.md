# Constellation integration 0.1.0-alpha.4

Run the connected-cache C profile on one disposable local Docker host: prepare
closed public inputs, acquire and evaluate a recorded cache observation, make
one bounded refresh attempt, inspect the retained result, then make a separate
bounded teardown attempt. Start with the versioned [guide](guide.html) and
release [manifest](manifest.json).

This alpha pins a tested composition, rather than synchronizing component
versions. It requires public Maude, NQ, Nightshift, AG, Docket and Pulse source
cuts at the exact revisions in the manifest, Rust 1.94, CPython 3.12, Docker
29.1.3/Compose 5.0.0 and the pinned container image. It has no model-provider
credential requirement. All source acquisition and native builds are caller
work; the finite runtime uses the selected local Docker daemon.

The profile uses synthetic authoring, synthetic Standing inputs and a
caller-asserted role reference. Those inputs are intentionally visible and do
not establish external provenance, current cache condition, general permission,
or a production authority service. A settlement records an exact attempt; it
does not itself establish a later condition or authorize another effect.

The post-settlement supervisor-interruption qualification is deliberately
scoped: it verified two already-settled occurrences and retained reconciliation
records after the supervising process stopped. It does **not** establish a
general resume facility, interrupted-action recovery, or a reason to repeat an
uncertain occurrence.

This release excludes general ECAD/design-flow readiness, federation, a public
multi-tenant service, live human notification delivery, a physical cache target,
and application production migration. Alpha support is best effort, with no
guaranteed response time.
