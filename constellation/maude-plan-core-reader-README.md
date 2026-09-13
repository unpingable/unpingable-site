# Maude Plan Core external-reader profile (candidate)

This candidate profile lets an external caller inspect a user-created local Plan
Core draft through Maude's supported `maude-plan --read-only inspect` command.
It is not AG, Phosphor, or a Maude-to-AG composition. It reads no
provider credential, starts no service, checks no blank plan, and grants no
authority to execute work.

## Exact public inputs

- Public Maude revision with explicit read-only mode:
  `7d196e2ab0e78cca46bd34af1ce6e9cbc9bf7fa6`.
- Tested environment: Linux x86_64, Ubuntu 24.04.4, CPython 3.12.3, pip 24.0.
  The supplied wheel lock targets CPython 3.12 on Linux x86_64; other platforms
  and Python minors are not qualified by this profile.
- Public runtime dependencies from `pyproject.toml`: `textual>=1.0.0`,
  `pydantic>=2.6.0`, and `pyyaml>=6.0`. Do not install `.[dev]` or the optional
  `classic-rpc` extra: both are outside this read-only profile.

The adjacent `examples/maude-plan-reader-requirements.txt` fixes the public
runtime and build-backend dependencies by version and wheel SHA-256. Setup uses
that lock with no private extras and no separate build-dependency resolution.
This profile lock does not change Maude's independent package version.

## Set up the public-source example

From the documentation repository checkout, choose a new directory with enough
free space (the measured installation is about 60 MiB; allow 150 MiB). The setup
script refuses an existing destination. It installs the public package metadata
and Plan Core source, not the entire Maude application. Other Maude entry points
in package metadata are outside this sparse profile. Installing it creates no
draft and contacts no model.

```sh
PARENT=$(mktemp -d /tmp/maude-plan-reader.XXXXXX)
RUN="$PARENT/profile"
bash constellation/examples/setup_maude_reader.sh "$RUN"
```

Create a user-owned draft with an actual inspection goal; no check or lock is
needed for this profile:

```text
setup caller -> Maude CLI new -> caller-owned Plan Core store
external reader -> Maude CLI --read-only inspect -> same store
external reader <- exact revision and check/lock summary <- Maude
```

```sh
STORE="$RUN/plans.sqlite"
WORKSPACE="$RUN/user-workspace"
mkdir "$WORKSPACE"
"$RUN/venv/bin/maude-plan" --store "$STORE" new --draft-id user-draft \
  --goal 'Inspect the current local plan before answering a maintenance question' \
  --workspace "$WORKSPACE" --author external-caller
python3 constellation/examples/read_maude_plan.py \
  --maude-plan "$RUN/venv/bin/maude-plan" --store "$STORE" --draft-id user-draft
```

The adapter invokes exactly one read-only `inspect`, avoiding a separate
list→inspect invocation race. It accepts only `maude.plan-revision/v1` and
`maude.plan-lifecycle-projection/v1`, binds the selected current revision to the
requested draft ID, hard-bounds each CLI pipe at 1 MiB while it is read, and
validates the check summary and optional lock ID. A Plan Core `inspect` assembles
its projection through separate database reads, so even one invocation can mix
observation times while a concurrent writer advances the draft. A consistent
aggregate profile therefore requires quiescent writers; returned identifiers
bind the records read, not a present-state assertion. It emits `available` or
`unavailable` with a bounded reason. The current CLI does not publish a typed
absence result, so a refused inspect is not relabeled as absence. Re-run the
adapter in a new process against the same store and compare its JSON output to
verify SQLite persistence across caller restart. Invalid JSON, unknown schema,
over-bound output, timeout, unavailable program, and command refusal remain
distinct outcomes; do not construct a replacement value.

## Qualification scope

A successful fresh-environment run establishes only that the pinned public
source can create a user-owned draft and that this adapter can inspect its
current revision through the supported CLI after restart while writers are
quiescent. It does not establish
checker success, a lock, compiler availability, live runtime state, external
truth, authority, execution, or compatibility with AG/Phosphor.
