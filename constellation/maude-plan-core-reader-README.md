# Maude Plan Core external-reader profile (candidate)

This candidate profile lets an external caller inspect a user-created local Plan
Core draft through Maude's supported `maude-plan --read-only inspect` command.
It is not AG, Phosphor, or a Maude-to-AG composition. It reads no
provider credential, starts no service, checks no blank plan, and grants no
authority to execute work.

## Exact public inputs

- Public Maude revision with explicit read-only mode:
  `7d196e2ab0e78cca46bd34af1ce6e9cbc9bf7fa6`.
- Python: 3.11 or newer.
- Public runtime dependencies from `pyproject.toml`: `textual>=1.0.0`,
  `pydantic>=2.6.0`, and `pyyaml>=6.0`. Do not install `.[dev]` or the optional
  `classic-rpc` extra: both are outside this read-only profile.

The source does not publish a locked Python requirements file. A fresh run must
record pip's public resolution report and installed package set; an offline run
may use only a previously recorded public package cache with matching hashes.

## Proposed fresh public-only qualification

Choose a new directory with enough free space. The source checkout is sparse: it has
the public package metadata and Plan Core import closure, not a copied full
worktree.

```sh
RUN=$(mktemp -d /tmp/maude-plan-reader.XXXXXX)
SRC="$RUN/maude"
MAUDE_REV=7d196e2ab0e78cca46bd34af1ce6e9cbc9bf7fa6
python3 -m venv "$RUN/venv"
git init "$SRC"
git -C "$SRC" remote add origin https://github.com/unpingable/maude.git
git -C "$SRC" sparse-checkout init --no-cone
git -C "$SRC" sparse-checkout set /pyproject.toml /README.md /src/maude/__init__.py /src/maude/plan/
git -C "$SRC" fetch --filter=blob:none --depth=1 origin "$MAUDE_REV"
git -C "$SRC" checkout --detach FETCH_HEAD
git -C "$SRC" rev-parse HEAD
"$RUN/venv/bin/python" -m pip install --report "$RUN/pip-install-report.json" -e "$SRC"
"$RUN/venv/bin/python" -m pip freeze --all >"$RUN/pip-freeze.txt"
"$RUN/venv/bin/maude-plan" --help | grep -- --read-only
```

Create a user-owned draft with an actual inspection goal; no check or lock is
needed for this profile:

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
