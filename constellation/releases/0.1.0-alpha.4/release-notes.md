# Constellation integration 0.1.0-alpha.4

Run the connected-cache C profile on one disposable local Docker host: prepare
closed public inputs, acquire and evaluate a recorded cache observation, make
one bounded refresh attempt, inspect the retained result, then make a separate
bounded teardown attempt. Start with the versioned
[guide](https://unpingable.com/constellation/releases/0.1.0-alpha.4/guide.html)
and release
[manifest](https://unpingable.com/constellation/releases/0.1.0-alpha.4/manifest.json).

This alpha pins a tested composition, rather than synchronizing component
versions. It requires public Maude, NQ, Nightshift, AG, Docket and Pulse source
cuts at the exact revisions in the manifest, Rust 1.94, CPython 3.12, Docker
29.1.3/Compose 5.0.0 and the pinned container image. It has no model-provider
credential requirement. All source acquisition and native builds are caller
work; the finite runtime uses the selected local Docker daemon.

The synthetic runtime fixture root is deliberately required to be a fresh path
below `/tmp`. Put the durable manager/control record and retained custody
outside `/tmp` before launch. This separation was exercised by the release
newcomer case; `/tmp` remains unsuitable for evidence that must survive the
fixture lifecycle.

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

The release recovery record includes two pre-effect refusals: one stopped when
the NQ helper detected an unsafe ancestor for its runtime root, and one stopped
when synthetic evidence was placed outside `/tmp`. Neither created a governed
attempt. The corrected clean-public-only newcomer case then completed 53
retained stages, two settlements, exact NQ result/successor admission, and
separate teardown; its copied existing-root invocation refused before a later
stage or Docker call. There were no provider calls or automatic retries.

This release excludes general ECAD/design-flow readiness, federation, a public
multi-tenant service, live human notification delivery, a physical cache target,
and application production migration. Alpha support is best effort, with no
guaranteed response time.
