# Connected-cache public input example

This helper fills the two closed input documents consumed by Maude's
`generate_connected_cache_example.py`. It measures caller-selected executable
bytes; it does not download, build, initialize, authorize, or execute anything.

Use clean detached public checkouts at the revisions embedded in
`make_inputs.py`. Build the named binaries with each repository's locked build
instructions, place the eleven regular executables in one directory under the
filenames listed in `PROGRAMS`, and create a copied (not symlinked) Python
virtual environment for Maude. The Maude checkout must be exactly
`0d5b6c91102b1088818d0493c687f9f23db7684e`.

The pinned repositories are:

- `https://github.com/unpingable/maude.git` for Maude;
- `https://github.com/unpingable/constellation-nq.git` for all three NQ programs;
- `https://github.com/unpingable/constellation-nightshift.git` for Nightshift,
  its observation resolver, and the Pulse integration;
- `https://github.com/unpingable/constellation-ag.git` for AG and its Standing
  resolver; and
- `https://github.com/unpingable/constellation-docket.git` for Docket.

Use each repository's `Cargo.lock` and package-specific build commands. The
system `docker` and `openssl` programs must also be copied as regular files into
the program directory. Source checkout, successful compilation, and matching
filenames alone are insufficient: this helper records the exact resulting
bytes, and Maude checks those pins again during preparation.

The role digest is an input, not invented by this helper. Obtain it from the
exact public Nightshift role definition selected for the run and verify it
before preparation.

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
  --role-digest sha256:REPLACE_WITH_VERIFIED_64_HEX \
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

The profile deliberately labels Standing as synthetic. The debug identity flag
is explicit and is not a deployment recommendation. Fresh IDs prevent accidental
reuse; they do not authenticate a human, grant permission, or establish current
cache health. Preserve the generated files and inspect an uncertain run before
using another root.
