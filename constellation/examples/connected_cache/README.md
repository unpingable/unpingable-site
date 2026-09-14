# Connected-cache public input example

This helper fills the two closed input documents consumed by Maude's
`generate_connected_cache_example.py`. It measures caller-selected executable
bytes; it does not download, build, initialize, authorize, or execute anything.

Use clean detached public checkouts at the revisions embedded in
`make_inputs.py`. One copyable source setup is:

```bash
git clone https://github.com/unpingable/maude.git maude
git -C maude checkout --detach 0d5b6c91102b1088818d0493c687f9f23db7684e
git clone https://github.com/unpingable/constellation-nq.git nq
git -C nq checkout --detach d3089a9787a27c50faf1e3f393a88f8e64bd412d
git clone https://github.com/unpingable/constellation-nightshift.git nightshift
git -C nightshift checkout --detach 2db475b0bb8be5e3afa7ac6c95e2ab1f73a9ceb4
git clone https://github.com/unpingable/constellation-nightshift.git pulse-source
git -C pulse-source checkout --detach d91b214cd22afd5585fcd259d22463d08d606b58
git clone https://github.com/unpingable/constellation-ag.git ag
git -C ag checkout --detach 5c8b22b77193798f25298b02758ac3caa3a8fe24
git clone https://github.com/unpingable/constellation-docket.git docket
git -C docket checkout --detach c49ad8d0f26fb2a13b9dbafdde84d7abfe1f867b
```

The pinned repositories are:

- `https://github.com/unpingable/maude.git` for Maude;
- `https://github.com/unpingable/constellation-nq.git` for all three NQ programs;
- `https://github.com/unpingable/constellation-nightshift.git` for Nightshift,
  its observation resolver, and the Pulse integration;
- `https://github.com/unpingable/constellation-ag.git` for AG and its Standing
  resolver; and
- `https://github.com/unpingable/constellation-docket.git` for Docket.

With a pinned Rust toolchain capable of building those revisions, use their
locked dependency graphs. These are the narrow program builds:

```bash
cargo build --locked --manifest-path nq/Cargo.toml -p nq-app --bin nq
cargo build --locked --manifest-path nq/Cargo.toml \
  -p nq-host-helper -p nq-synthetic-cache-result-helper
cargo build --locked --manifest-path nightshift/Cargo.toml -p nightshiftd \
  --bin nightshift --bin nightshift-observation-resolver
cargo build --locked --manifest-path ag/Cargo.toml -p ag-app \
  --bin ag-loopctl --bin ag-standing-resolver
cargo build --locked --manifest-path docket/Cargo.toml -p gwr-local --bin docket
cargo build --locked \
  --manifest-path pulse-source/integrations/pulse-nq-load-support/Cargo.toml \
  --bin pulse-nq-load-support
```

Copy the resulting binaries to a fresh directory under the exact names shown
by `make_inputs.py --help`/`PROGRAMS`. Copy the selected system `docker` and
`openssl` executables there as regular files named `docker` and `openssl`.
Source checkout, successful compilation, and matching filenames alone are
insufficient: this helper records the exact resulting bytes, and Maude checks
those pins again during preparation. The tested runtime tuple is Docker client
and server 29.1.3, Compose 5.0.0, project `maude-cache-birthday`, and image
`python:3.13-alpine@sha256:46ee549c88617e9bc8acb843a326f1a5c0fa5608d7f9703509efe6d53b55f318`.

Maude requires Python 3.11 or later and declares `textual>=1.0.0`,
`pydantic>=2.6.0`, and `pyyaml>=6.0`. Create a regular copied interpreter and
install the exact detached Maude checkout (record the resolved package set):

```bash
python3 -m venv --copies /absolute/copied-venv
/absolute/copied-venv/bin/python -m pip install -e /absolute/maude
```

The role digest is an explicit local synthetic-fixture assertion, not a claim
that Nightshift published or authenticated a role definition. The public 084
qualification used `sha256:` followed by 64 lowercase `e` characters together
with role ID `nightshift-role:cache-bootstrap-host` and version `1`. Copy that
value only when reproducing this same synthetic profile, and record it as
caller asserted. The later AG profile seal checks internal consistency; it
does not turn the assertion into external provenance.

```bash
python3 constellation/examples/connected_cache/make_inputs.py \
  --output /absolute/fresh/input-records \
  --maude-source /absolute/maude \
  --nq-source /absolute/constellation-nq \
  --nightshift-source /absolute/nightshift-at-2db475b \
  --ag-source /absolute/constellation-ag \
  --docket-source /absolute/constellation-docket \
  --pulse-source /absolute/nightshift-at-d91b214 \
  --program-dir /absolute/installed-programs \
  --python /absolute/copied-venv/bin/python \
  --pulse-launcher-sealer /absolute/nightshift/integrations/pulse-nq-load-support/tools/seal-pulse-support-resolver-launcher.py \
  --role-digest sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee \
  --label my-cache-check
```

Then invoke the published Maude caller with the retained files:

```bash
"$PYTHON" "$MAUDE/qualification/synthetic_cache/generate_connected_cache_example.py" \
  --output /absolute/records/setup.json \
  --root /absolute/fresh/run-root \
  --maude-source "$MAUDE" --program-dir /absolute/installed-programs \
  --python "$PYTHON" --pulse-launcher-sealer /absolute/sealer.py \
  --install-manifest /absolute/fresh/input-records/connected-cache-install.json \
  --profile /absolute/fresh/input-records/connected-cache-profile.json \
  --execution-account local-example-account --allow-same-identity-in-debug
```

Prepare the fresh owner, then execute through the bounded public driver:

```bash
"$PYTHON" "$MAUDE/qualification/synthetic_cache/prepare_connected_cache_run.py" \
  --config /absolute/records/setup.json

systemd-run --user --unit=connected-cache-example --collect \
  --property=Type=oneshot --property=TimeoutStartSec=2400 \
  --property=TimeoutStopSec=10 --property=KillMode=control-group \
  --property=MemoryMax=2G --property=TasksMax=256 --property=Restart=no \
  "$PYTHON" "$MAUDE/qualification/synthetic_cache/run_connected_cache.py" \
  --context /absolute/fresh/run-root/context.json --execute
```

The Docker socket gives the driver authority over the host Docker daemon; an
OS namespace around the caller does not remove that boundary. Verify the exact
image is already present and that no containers or networks carry Compose
project label `maude-cache-birthday` before starting. The driver performs two
occurrences: qualification, followed by the separately governed teardown.

After terminal completion, follow the exact read-only NQ, AG, Docket, result
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
