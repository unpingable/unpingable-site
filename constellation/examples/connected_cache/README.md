# Connected-cache public input example

This helper fills the two closed input documents consumed by Maude's
`generate_connected_cache_example.py`. It measures caller-selected executable
bytes; it does not download, build, initialize, authorize, or execute anything.

The tested host is Linux x86-64 (Ubuntu 24.04), Python 3.12.3, with Git,
Rustup, a C compiler/linker, OpenSSL, a user systemd manager and Docker Compose.
Do not run on a shared production Docker daemon. Reserve space before building;
the setup also requires 60 GiB free on the owner filesystem and `/data` when
present. Builds may take several minutes: use your durable build manager and
retain its source pins and logs if your terminal may disconnect.

Use clean detached public checkouts at the revisions embedded in
`make_inputs.py`. One copyable source setup is:

```bash
EXAMPLE_WORK=/absolute/caller-owned/connected-cache-example
test "${EXAMPLE_WORK#/}" != "$EXAMPLE_WORK"
test ! -e "$EXAMPLE_WORK"
mkdir -m 700 "$EXAMPLE_WORK"

MAUDE="$EXAMPLE_WORK/maude"
NQ="$EXAMPLE_WORK/constellation-nq"
NIGHTSHIFT="$EXAMPLE_WORK/nightshift-2db475b"
PULSE_SOURCE="$EXAMPLE_WORK/nightshift-d91b214"
AG="$EXAMPLE_WORK/constellation-ag"
DOCKET="$EXAMPLE_WORK/constellation-docket"
PROGRAMS="$EXAMPLE_WORK/programs"
VENV="$EXAMPLE_WORK/maude-venv"
INPUT_PARENT="$EXAMPLE_WORK/records"
INPUTS="$INPUT_PARENT/inputs"
OWNER_PARENT="$EXAMPLE_WORK/owner"
RUN="$OWNER_PARENT/run"
INPUT_HELPER="$EXAMPLE_WORK/make_inputs.py"
LABEL=my-cache-check
EXECUTION_ACCOUNT=$(id -un)
test "$(id -u)" -ne 0

git clone https://github.com/unpingable/maude.git "$MAUDE"
git -C "$MAUDE" checkout --detach 0d5b6c91102b1088818d0493c687f9f23db7684e
git clone https://github.com/unpingable/constellation-nq.git "$NQ"
git -C "$NQ" checkout --detach d3089a9787a27c50faf1e3f393a88f8e64bd412d
git clone https://github.com/unpingable/constellation-nightshift.git "$NIGHTSHIFT"
git -C "$NIGHTSHIFT" checkout --detach 2db475b0bb8be5e3afa7ac6c95e2ab1f73a9ceb4
git clone https://github.com/unpingable/constellation-nightshift.git "$PULSE_SOURCE"
git -C "$PULSE_SOURCE" checkout --detach d91b214cd22afd5585fcd259d22463d08d606b58
git clone https://github.com/unpingable/constellation-ag.git "$AG"
git -C "$AG" checkout --detach 5c8b22b77193798f25298b02758ac3caa3a8fe24
git clone https://github.com/unpingable/constellation-docket.git "$DOCKET"
git -C "$DOCKET" checkout --detach c49ad8d0f26fb2a13b9dbafdde84d7abfe1f867b
```

The pinned repositories are:

- `https://github.com/unpingable/maude.git` for Maude;
- `https://github.com/unpingable/constellation-nq.git` for all three NQ programs;
- `https://github.com/unpingable/constellation-nightshift.git` for Nightshift,
  its observation resolver, and the Pulse integration;
- `https://github.com/unpingable/constellation-ag.git` for AG and its Standing
  resolver; and
- `https://github.com/unpingable/constellation-docket.git` for Docket.

The verified public-source cohort used Rust 1.94.0. Install/select that exact toolchain
and use each checkout's locked dependency graph:

```bash
rustup toolchain install 1.94.0 --profile minimal
export CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0
cargo +1.94.0 build --locked --manifest-path "$NQ/Cargo.toml" -p nq-app --bin nq
cargo +1.94.0 build --locked --manifest-path "$NQ/Cargo.toml" \
  -p nq-host-helper -p nq-synthetic-cache-result-helper
cargo +1.94.0 build --locked --manifest-path "$NIGHTSHIFT/Cargo.toml" -p nightshiftd \
  --bin nightshift --bin nightshift-observation-resolver
cargo +1.94.0 build --locked --manifest-path "$AG/Cargo.toml" -p ag-app \
  --bin ag-loopctl --bin ag-standing-resolver
cargo +1.94.0 build --locked --manifest-path "$DOCKET/Cargo.toml" -p gwr-local --bin docket
cargo +1.94.0 build --locked \
  --manifest-path "$PULSE_SOURCE/integrations/pulse-nq-load-support/Cargo.toml" \
  --bin pulse-nq-load-support
```

Install regular copies under the exact names consumed by the closed Maude
schema (the program names are defined in `make_inputs.py`, not its `--help`):

```bash
mkdir -m 700 "$PROGRAMS"
install -m 0555 "$NQ/target/debug/nq" "$PROGRAMS/nq"
install -m 0555 "$NQ/target/debug/nq-host-helper" "$PROGRAMS/nq-host-helper"
install -m 0555 "$NQ/target/debug/nq-synthetic-cache-result-helper" \
  "$PROGRAMS/nq-synthetic-cache-result-helper"
install -m 0555 "$NIGHTSHIFT/target/debug/nightshift" "$PROGRAMS/nightshift"
install -m 0555 "$NIGHTSHIFT/target/debug/nightshift-observation-resolver" \
  "$PROGRAMS/nightshift-observation-resolver"
install -m 0555 "$AG/target/debug/ag-loopctl" "$PROGRAMS/ag-loopctl"
install -m 0555 "$AG/target/debug/ag-standing-resolver" "$PROGRAMS/ag-standing-resolver"
install -m 0555 "$DOCKET/target/debug/docket" "$PROGRAMS/docket"
install -m 0555 "$PULSE_SOURCE/integrations/pulse-nq-load-support/target/debug/pulse-nq-load-support" \
  "$PROGRAMS/pulse-nq-load-support"
install -m 0555 "$(command -v docker)" "$PROGRAMS/docker"
install -m 0555 "$(command -v openssl)" "$PROGRAMS/openssl"
```

Source checkout, successful compilation, and matching filenames alone are
insufficient: this helper records the exact resulting bytes, and Maude checks
those pins again during preparation. The tested runtime tuple is Docker client
and server 29.1.3, Compose 5.0.0, project `maude-cache-birthday`, and image
`python:3.13-alpine@sha256:46ee549c88617e9bc8acb843a326f1a5c0fa5608d7f9703509efe6d53b55f318`.

Maude requires Python 3.11 or later and declares `textual>=1.0.0`,
`pydantic>=2.6.0`, and `pyyaml>=6.0`. Create a regular copied interpreter and
install the exact detached Maude checkout (record the resolved package set):

```bash
mkdir -m 700 "$INPUT_PARENT"
python3 -m venv --copies "$VENV"
"$VENV/bin/python" -m pip install -e "$MAUDE"
"$VENV/bin/python" -m pip freeze > "$INPUT_PARENT/python-requirements.txt"
```

The role digest is an explicit local synthetic-fixture assertion, not a claim
that Nightshift published or authenticated a role definition. The public-source
qualification used `sha256:` followed by 64 lowercase `e` characters together
with role ID `nightshift-role:cache-bootstrap-host` and version `1`. Copy that
value only when reproducing this same synthetic profile, and record it as
caller asserted. The later AG profile seal checks internal consistency; it
does not turn the assertion into external provenance.

```bash
curl --fail --silent --show-error \
  https://raw.githubusercontent.com/unpingable/unpingable-site/7386df1c36a13f7fba6208e1896e22e99b8e3b7c/constellation/examples/connected_cache/make_inputs.py \
  --output "$INPUT_HELPER"
echo "afb7df5f35ef24bf14128220c52792b94365f6081a6f8ef4fccf2fd8a6ecf862  $INPUT_HELPER" | sha256sum --check
mkdir -m 700 "$OWNER_PARENT"
test ! -e "$INPUTS"
test ! -e "$RUN"
"$VENV/bin/python" \
  "$INPUT_HELPER" \
  --output "$INPUTS" \
  --maude-source "$MAUDE" \
  --nq-source "$NQ" \
  --nightshift-source "$NIGHTSHIFT" \
  --ag-source "$AG" \
  --docket-source "$DOCKET" \
  --pulse-source "$PULSE_SOURCE" \
  --program-dir "$PROGRAMS" \
  --python "$VENV/bin/python" \
  --pulse-launcher-sealer "$PULSE_SOURCE/integrations/pulse-nq-load-support/tools/seal-pulse-support-resolver-launcher.py" \
  --role-digest sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee \
  --label "$LABEL"
```

Then invoke the published Maude caller with the retained files:

```bash
"$VENV/bin/python" "$MAUDE/qualification/synthetic_cache/generate_connected_cache_example.py" \
  --output "$INPUT_PARENT/setup.json" \
  --root "$RUN" \
  --maude-source "$MAUDE" --program-dir "$PROGRAMS" \
  --python "$VENV/bin/python" \
  --pulse-launcher-sealer "$PULSE_SOURCE/integrations/pulse-nq-load-support/tools/seal-pulse-support-resolver-launcher.py" \
  --install-manifest "$INPUTS/connected-cache-install.json" \
  --profile "$INPUTS/connected-cache-profile.json" \
  --execution-account "$EXECUTION_ACCOUNT" --allow-same-identity-in-debug
```

The execution account must resolve to an existing local account. This debug
example deliberately uses your current non-root account; the explicit flag
permits that same identity, but does not create an account or waive its lookup.

Prepare the fresh owner, then execute through the bounded public driver:

```bash
"$VENV/bin/python" "$MAUDE/qualification/synthetic_cache/prepare_connected_cache_run.py" \
  --config "$INPUT_PARENT/setup.json"

MANAGER="connected-cache-$LABEL-$(date -u +%Y%m%dT%H%M%SZ)-$$"
printf '%s\n' "$MANAGER" > "$INPUT_PARENT/manager-unit.txt"
systemd-run --user --unit="$MANAGER" --collect \
  --property=Type=oneshot --property=TimeoutStartSec=2400 \
  --property=TimeoutStopSec=10 --property=KillMode=control-group \
  --property=MemoryMax=2G --property=TasksMax=256 --property=Restart=no \
  "$VENV/bin/python" "$MAUDE/qualification/synthetic_cache/run_connected_cache.py" \
  --context "$RUN/context.json" --execute
```

The Docker socket gives the driver authority over the host Docker daemon; an
OS namespace around the caller does not remove that boundary. Verify the exact
image is already present and that no containers or networks carry Compose
project label `maude-cache-birthday` before starting. The driver performs two
occurrences: qualification, followed by the separately governed teardown.

Wait for `systemctl --user show "$MANAGER.service"` to report inactive with no
main process, then read `$RUN/records/connected-run/terminal.json`. Exit zero is
necessary but is not acceptance. Follow the exact read-only NQ, AG, Docket, result
owner, Docker-label, interruption, and retention commands in the pinned
Maude file `qualification/synthetic_cache/OPERATIONS.md`. Successful teardown
requires both final label inventories to be empty; do not infer cleanup from an
absent workspace. If the manager or driver terminal is missing, preserve the
owner and inspect/reconcile it—do not rerun either occurrence to manufacture a
new terminal record. Disposable local records may be removed only after that
inspection and under the caller's own retention policy; the public driver has
no broad cleanup command.

The profile deliberately labels Standing as synthetic. The debug identity flag
is explicit and is not a deployment recommendation. Fresh IDs prevent accidental
reuse; they do not authenticate a human, grant permission, or establish current
cache health. This is a development example, not a released profile. Preserve
the generated files and inspect an uncertain run before using another root.
