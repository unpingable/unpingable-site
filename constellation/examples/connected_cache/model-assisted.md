# Model-assisted connected-cache tutorial

This page joins two already separate public interfaces:

1. Maude's opt-in, bounded Plan Edit Proposal flow can ask a selected model for
   a scoped edit, show its exact semantic diff, and—only after a separate caller
   decision—save one ordinary Plan Core successor.
2. The connected-cache driver can compile an exact checked and locked Plan Core
   revision through its closed cache workflow when the caller supplies a
   byte-pinned accepted bundle and Plan Core store.

Neither step grants the next one. A provider completion is not acceptance;
acceptance is not a check; a passing check is not a lock; a lock is not a
handoff; and compilation is not standing, authorization, execution, or
settlement.

## Choose which path you are following

### Reproduce the existing accepted fixture

One retained qualification used a proposal produced through the enrolled
OpenRouter route, followed later by an explicit user acceptance, a fresh
structural check with zero findings, and a lock of the accepted revision. The
proposal changed exactly one field: it removed one duplicated dependency from
`pn_continued.depends_on`; no other plan field, node, order, work, criterion, or
declared path changed.

The retained accepted plan digest is
`sha256:bae29715069c298263314057a8681e71903d49eb29b7536a25f69671baddd83e`
and its lock is
`sha256:d2b6350eeab1fba4fa1265e13c7793a76991d1bf8478c1f267941dc447aca07d`.
The portable accepted bundle and Plan Core database are supplied below with
exact SHA-256 values. The historical accepted run completed, and a separate
public-only accepted-mode reproduction completed 55 retained stages, two
successful settlements, exact result admission, a fresh successor observation,
and final project absence. The accepted fixture is an optional authoring route
into the released `connected-cache-c` alpha.4 profile; it is not a separate
provider or family-wide release.

Public input locations are:

```text
https://unpingable.com/constellation/examples/connected_cache/accepted-plan/manifest.json
https://unpingable.com/constellation/examples/connected_cache/accepted-plan/accepted-bundle.json
https://unpingable.com/constellation/examples/connected_cache/accepted-plan/accepted-plan.sqlite
```

The reviewed bundle SHA-256 is
`1fa0f621556484c916da8127083bf42e2a54646954de096a872d39d7d7abb441`;
the reviewed store SHA-256 is
`a9ceed5a625dcbc8708301b4aaac58c2ef0a4b394127b7cae953316e0503f4de`.
Fetch into new caller-owned paths, enforce bounded regular files, and check
these hashes before using the accepted-mode command below. The adjacent
manifest repeats the bindings and the explicit nonauthority/privacy scope.

The accepted bundle carries an opaque acceptance reference. The compiler
checks its binding to the locked revision, but the Plan Core store does not
authenticate the person behind that reference. Publication may accurately say
that the source qualification recorded a separate user acceptance; it must not
claim that possession or successful compilation of the bundle authenticates a
human.

Reusing these byte-pinned files makes no provider request and does not ask a
newcomer to manufacture another acceptance. It verifies portable accepted-mode
preparation, compilation, governed execution, retained-result inspection, and
teardown for the exact existing fixture.

### Make your own fresh model-assisted revision

A fresh user supplies all of the following:

- a clean, pinned Maude source checkout and the separately pinned Switchyard
  source/runtime required by Maude's OpenRouter authoring guide;
- a fresh Plan Core, presentation, proposal, and Switchyard state location;
- an explicit nonsecret provider profile fixing provider, model, account label,
  limits, timeout, concurrency, retry/fallback policy, and spend reservation;
- a dedicated private credential file by absolute pathname, owned by that user
  and mode `0600`; and
- a bounded task, exact proposal scope, separate authorization for one billable
  contact, and a person prepared to review the resulting diff.

The credential is an input by reference. Do not copy its contents into a plan,
command transcript, issue, acceptance record, bundle, or tutorial artifact.
Starting the design server merely enrolls the route; it neither reads the
credential eagerly nor authorizes a contact.

Follow the pinned Maude `docs/OPENROUTER-AUTHORING.md` launch commands. Open the
Maude-owned `/phosphor/design` draft, select the exact document, node, or current
finding scope, describe the permitted edit, select `enrolled-switchyard`, and
submit only after authorizing that one contact. There is no automatic retry or
fallback. After a timeout, cancellation, or uncertain transport result, inspect
the retained generation and Switchyard state before deciding anything further.

Review the returned proposal's exact base revision and digest, target and
allowed fields, ordered operations, before/after values, semantic diff, and
provider/model record. The rationale is explanatory only; the operations define
the proposed change. Invalid, out-of-scope, stale, substituted, or malformed
output refuses without a successor revision.

If the proposal is acceptable, use **Accept changes into draft** once. That
explicit action creates an ordinary successor through Plan Core's
expected-revision compare-and-swap. It records an actor label as provenance, not
proof of a person's authenticated identity. Then, as distinct actions:

1. open **Checks** and check the exact successor;
2. inspect its current receipt and resolve every finding you require resolved;
3. inspect the semantic diff from its predecessor; and
4. lock the exact revision intended for the cache compiler.

The headless read side can confirm the resulting records without mutation:

```sh
PYTHONPATH="$MAUDE/src" "$VENV/bin/python" -m maude.plan.cli \
  --store "$PLAN_STORE" --read-only inspect "$DRAFT_ID"
```

The current local-Compose compiler is closed and cache-specific. It does not
compile arbitrary prose. A fresh plan must retain the supported cache document
shape and supply the explicit typed compiler inputs. To enter accepted mode, a
caller must construct the published accepted-bundle contract from that exact
locked revision and retain both the quiescent Plan Core database and bundle as
bounded regular files. There is currently no public end-user command that
turns an arbitrary locked browser draft plus an actor label into a portable,
human-authenticated accepted bundle.

## Prepare the connected run

First complete the public connected-cache README's source, executable, Python,
Docker, storage, and fresh-root checks. Run its checksum-pinned `make_inputs.py`
and `generate_connected_cache_example.py` commands. The execution account must
resolve through the local passwd database; for the documented debug
same-identity exercise use the actual non-root caller account together with the
explicit debug flag.

Preparation still creates no acquisition, authorization, Docker transition, or
provider call:

```sh
"$VENV/bin/python" "$MAUDE/qualification/synthetic_cache/prepare_connected_cache_run.py" \
  --config "$INPUT_PARENT/setup.json"
```

Before starting, record the exact accepted inputs and refuse mutable or
ambiguous coordinates:

```sh
ACCEPTED_DIR="$INPUT_PARENT/accepted-plan"
test ! -e "$ACCEPTED_DIR"
mkdir -m 700 "$ACCEPTED_DIR"
ACCEPTED_BUNDLE="$ACCEPTED_DIR/accepted-bundle.json"
ACCEPTED_STORE="$ACCEPTED_DIR/accepted-plan.sqlite"
ACCEPTED_BUNDLE_SHA256=1fa0f621556484c916da8127083bf42e2a54646954de096a872d39d7d7abb441
ACCEPTED_STORE_SHA256=a9ceed5a625dcbc8708301b4aaac58c2ef0a4b394127b7cae953316e0503f4de
curl --fail --silent --show-error --max-time 30 --max-filesize 1048576 \
  https://unpingable.com/constellation/examples/connected_cache/accepted-plan/accepted-bundle.json \
  --output "$ACCEPTED_BUNDLE"
curl --fail --silent --show-error --max-time 30 --max-filesize 67108864 \
  https://unpingable.com/constellation/examples/connected_cache/accepted-plan/accepted-plan.sqlite \
  --output "$ACCEPTED_STORE"

test -f "$ACCEPTED_BUNDLE" && test ! -L "$ACCEPTED_BUNDLE"
test -f "$ACCEPTED_STORE" && test ! -L "$ACCEPTED_STORE"
test ! -e "${ACCEPTED_STORE}-wal" && test ! -e "${ACCEPTED_STORE}-shm"
printf '%s  %s\n' "$ACCEPTED_BUNDLE_SHA256" "$ACCEPTED_BUNDLE" | sha256sum --check
printf '%s  %s\n' "$ACCEPTED_STORE_SHA256" "$ACCEPTED_STORE" | sha256sum --check
```

Keep writers stopped: absence of WAL/SHM sidecars alone does not establish
quiescence, human acceptance or permission.

## Invoke accepted mode once

Use the same durable user-systemd envelope and resource limits as the public
connected-cache README, adding all four accepted-input arguments:

```sh
systemd-run --user --unit="$MANAGER" --collect \
  --property=Type=oneshot --property=TimeoutStartSec=2400 \
  --property=TimeoutStopSec=10 --property=KillMode=control-group \
  --property=MemoryMax=2G --property=TasksMax=256 --property=Restart=no \
  "$VENV/bin/python" "$MAUDE/qualification/synthetic_cache/run_connected_cache.py" \
  --context "$RUN/context.json" --execute \
  --accepted-bundle "$ACCEPTED_BUNDLE" \
  --accepted-bundle-sha256 "$ACCEPTED_BUNDLE_SHA256" \
  --accepted-store "$ACCEPTED_STORE" \
  --accepted-store-sha256 "$ACCEPTED_STORE_SHA256"
```

The driver snapshots and rechecks the accepted bytes, prepares explicit
qualification and teardown compiler inputs using the retained NQ observations,
and compiles both actions through the pinned cache compiler. It does not contact
the proposal provider or authenticate the acceptance reference. Runtime
permission remains separately resolved by the synthetic development governance
path.

## Inspect, recover, and clean up

Wait until the original manager is inactive with no main process. Follow the
pinned public `qualification/synthetic_cache/OPERATIONS.md` commands using paths
resolved from `context.json`:

- inspect the checkpoint, numbered started/finished/uncertain files, and
  terminal;
- inspect both exact NQ artifacts, both Nightshift handoffs, AG state, and both
  Docket issuances;
- bound and inspect the separate result NQ artifact; and
- list containers and networks filtered by the exact Compose project label.

Acceptance requires more than process exit zero: terminal phase must be
`verified_local_composition`, both Docket attempts must be demonstrably settled
successfully, the exact past result must be admitted, and final exact-project
container and network inventories must be empty. Nightshift can retain
`awaiting_ag` at its handoff boundary; read downstream outcome from AG and
Docket. Owner queries make no logical transition, although SQLite SHM mtimes
may change without byte changes.

Read the result diagnostic's claim name, condition effect, and summary
together. The fixed detector names the failure condition
`expected_synthetic_cache_result_missing`; therefore `condition:
explicitly_absent` means the expected result is present, not missing. Confirm
that the summary says the exact past attempt reported the fixed expected
result, then require the same artifact ID in the stage 32 `admitted_report`
provenance. This is receipt-bound testimony about that exact past executor
attempt, not a post-teardown observation or a claim of current cache health.

The driver's second occurrence is the separately governed teardown. Do not
delete a workspace to imitate it. If a terminal or finish is missing, preserve
the original root, database sidecars, manager identity, stage records, input
pins, and executor evidence; inspect the last started stage and its owning
component. Never resubmit or repeat teardown merely to obtain a cleaner record.
If reconciliation cannot establish the original outcome, report it as
indeterminate. Cleanup is only for the exact disposable caller-owned root after
attempts are reconciled and the exact Docker project is absent.

## What a newcomer can verify without another billable request

With published accepted-bundle and accepted-store bytes, a newcomer can verify
their hashes, inspect the locked Plan Core revision and receipts, exercise the
accepted compiler path, run the connected disposable occurrence under the
documented authority boundary, inspect every retained owner, test existing-root
refusal, and confirm current exact-project absence. The newcomer can also use
Maude's deterministic proposal fixtures to learn scope/diff/accept/recheck/lock
behavior without contacting a provider.

Without another provider call, the newcomer cannot independently reproduce the
provider's upstream response, current pricing/routing, remote cancellation, or
the original person's acceptance act. The retained proposal and acceptance
records establish what this fixture says happened under their respective local
owners; the opaque acceptance reference is not human authentication.

## Limits of the existing result

The retained live contact used an explicitly authorized single OpenRouter
request, no retry or fallback, and produced a scope-bound proposal before the
later user decision. The accepted portable run completed the connected path and
teardown. These are finite historical results. They do not establish present
provider behavior, present cache health, a released Standing service, generic
model usefulness, arbitrary-plan compilation, production readiness, or
authority for another provider request or cache occurrence.
