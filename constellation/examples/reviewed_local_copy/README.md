# Reviewed local copy: the `reviewed-local-copy/v1` cohort kit

This kit sets up one operation on one Debian 12 host. After one bounded review
and one explicit operator acceptance, it writes one fixed line of UTF-8 text
to a file that must not exist yet:

- the text is `Constellation cohort <id> reviewed copy.` and a newline, so
  its length depends on the cohort id (43 bytes for `qual-a`);
- the destination is `/var/lib/constellation/cohorts/<id>/scratch/result.txt`.

`init` fixes both, from the cohort id, when it compiles the cohort's plan. The
operator does not choose the text, a source file or the destination. The plan
format allows up to 64 KiB of text in an exclusive scratch directory; this
driver always uses its one fixed line. The kit has no arbitrary command field,
notification requirement, scheduler, replacement authority store or
alternative provider route.

**Status.** This is candidate material, not a released or generally installable
suite. Kit 0.4.0 fixes the findings of the lane H hostile review and the lane H
newcomer run against kit 0.3.0 (see "What 0.4.0 changed"). Its qualification
runs are recorded with the campaign, not here, because a README cannot carry
its own result. These runs do not establish:

- a real-provider review (the real route has not been exercised);
- more than one occurrence per cohort;
- the driver's `upgrade`, `verify-retained` and `upgrade-status` commands as a
  newcomer path. They retire a settled cohort into a new one and were
  qualified separately; this README does not cover them;
- a public download of the cohort bundle. The qualification bundles were
  composed by the qualification harness; this README describes the path those
  bundles took.

Treat anything this README does not state as unsupported.

## Published digests: check these before running any kit code

The bundle carries a `SHA256SUMS`, but it sits next to the files it describes,
so it only proves the files agree with each other. Whoever hands you a bundle
can regenerate it. The anchor is these values, published with this page:

| File | sha256 |
|---|---|
| `cohort-manifest.json` | `PENDING-MANIFEST-SHA256` |
| `cohort-kit-0.4.0.tar.gz` | `PENDING-KIT-SHA256` |

The kit was built from site commit `PENDING-KIT-COMMIT`. Rebuilding it from
that commit with `setup/build_cohort_kit.py` gives the same bytes.

**This anchor is only as good as the page you read it on.** Read it from the
site repository or its published page over an authenticated channel, not from
a copy that came with the bundle. The kit does not contain this README, for
exactly this reason: a file inside the kit cannot state the kit's digest.

Step 1 below compares the two files with these values using `sha256sum` alone.
Only then does any kit code run. From there, the manifest pins every other
artifact by digest, and the driver refuses a kit that differs in any byte from
the one the manifest names (see "What `verify-manifest` and `install` check").

## Words used here

The components, each a separate release pinned below:

- **NQ** (`nq-ng`): the host observation service. It reports whether the host
  is under load.
- **Pulse**: signs NQ's observation as time-limited support evidence.
- **Maude**: the plan. It compiles the copy into a sealed plan and ships the
  executor that writes `result.txt`.
- **Nightshift**: admits the plan to AG with the current observation.
  **Foreman** (part of Nightshift) prepares and holds the one review request.
- **Switchyard** and the **App Server** (a pinned Codex app-server build):
  send the review request to the model provider and verify the answer.
- **AG**: the authority gate. It records the review, decides, and issues a
  signed, time-limited permission.
- **Docket**: custody of the effect. It checks AG's permission and standing,
  runs the Maude executor once, and records the settlement.

The terms:

- **cohort**: one install plus one setup, named by `<id>`. It runs one
  operation once.
- **occurrence**: that one run of the operation.
- **binding** (`binding_id`): the digest that ties the sealed plan to this
  occurrence.
- **candidate**: the retained, verified review waiting for the operator
  (`record-review-input.json`), named by its sha256.
- **genesis**: the first record of the cohort's AG store. It pins the programs
  and inputs AG will trust.
- **issuance**: AG's signed permission for this one effect, with a not-after
  time. **spend**: AG using it, once.
- **standing**: Docket's short-lived grant that someone may execute now.
- **custody**, **attempt**, **settlement**: Docket holding the effect, running
  it once, and recording how it ended.
- **program counter**: AG's current step. `settled_observation_required` means
  the effect settled, and a fresh observation would be needed for anything
  further. The operator has nothing to do there.
- **fixture**: the loopback stand-in for the provider, used for qualification
  only.

## Host requirements

The driver checks these and refuses (`host.*`) when one is missing:

- Debian 12 (`/etc/os-release` `debian:12`);
- `/usr/bin/python3.11` as a regular file, not a symlink. Debian 12 ships 3.11.2.
  Every kit command runs as `/usr/bin/python3.11 -I -S`. **Do not use
  `python3.12`**, `/usr/bin/python3` (a symlink) or a virtual environment;
- `/usr/bin/openssl` with Ed25519;
- `systemd-run`, `setpriv`, `dpkg`, `dpkg-deb`, `dpkg-query` and `useradd` on
  root's path (`/usr/sbin:/usr/bin:/sbin:/bin`; `useradd` is in `/usr/sbin`, so
  a normal account's `which` may not find it);
- root for every command except `verify-manifest` and `upgrade-status`;
- at least 2 GiB and 10000 inodes free under `/opt` (install) and `/var/lib`
  (review).

The qualification guests also relied on `memfd_create`, `libssl3` and
`liblzma5`, which the Debian 12 genericcloud image provides. They used 2 vCPU
and 4 GiB of memory.

The review also requires NQ to report the host load condition as
`explicitly_absent`. On a busy host the review refuses `observation.condition`
before any provider request, and the cohort is spent.

## Cohort manifest pins

The driver sets up only the cohort `alpha-exit-rc` of profile
`reviewed-local-copy/v1`. The manifest (`constellation.cohort-manifest/v1`) must
name exactly these components. For the eight component rows, compatibility is
equality of version, source commit **and** artifact digest; there are no
ranges and no "newer is fine", and any other value refuses `pin.incompatible`.

| Component | Version | Source commit | Artifact | sha256 |
|---|---|---|---|---|
| nq | 0.2.0 | `dbe29d81ba84061b08fec285f1218ec2145c65bc` | `nq-ng_0.2.0_amd64.deb` | `9e953e88d1f79cffd03e97b530199459b5e45ead55ea4ba7d5066e0851008d7b` |
| maude | 0.1.0 | `75d4dc1df1934cfc797c48c528d314804938eaae` | `maude-reviewed-local-copy-0.1.0.tar.gz` | `f88b5823f6a7bc6ff1c9645daff6312eec5234559bb735d25db589e1904f7357` |
| nightshift | 0.1.0 | `30c89fe17723a7b9d77b19fd650aadb0a784748d` | `nightshift-0.1.0-30c89fe-linux-amd64.tar.gz` | `cffbea38c4718c480fd9c0b5c41c28331d52132205a3e16f2fda2e572467a254` |
| pulse | 0.1.0 | `30c89fe17723a7b9d77b19fd650aadb0a784748d` | `pulse-nq-load-support-0.1.0-30c89fe-linux-amd64.tar.gz` | `51e85b97f44504240044f3b666d6fb3602270939102676e65798f4cecd405c61` |
| ag | 0.1.0 | `58122cec1ca8de35a1d146bf7987f8e69f49a040` | `ag-0.1.0-linux-amd64.tar.gz` | `bc53b836d7207493bbe35f0b380475641603caf3aedea6e8bcd3c9c0dea6ab5c` |
| docket | 0.1.0 | `3093def030a5151d2e7b956eafb73d0c16f8c735` | `docket-0.1.0-linux-amd64.tar.gz` | `6596315fcdb92fd881d6c0f2159eb912ee9c96b99a58fdc5ddea5e11a192c81b` |
| switchyard | 0.2.0 | `1c82e719cf358728d0262ae11138fb13fefe0cae` | `switchyard-0.2.0-1c82e719cf35.tar.gz` | `be418f76e9f5f8239d457137b19ff771d562d89a85ccda5b4ccfdc0049f665c1` |
| app-server | 0.0.0 | `97b0acd5ce2ccb3c87a763606696c35a450947f6` | `codex-app-server-97b0acd5ce2c-linux-amd64.tar.gz` | `9999bd8e75607071e1e43d9829fea253593f95323dff3a6e690b9d52433e2cd9` |
| cohort-kit | 0.4.0 | `PENDING-KIT-COMMIT` (see "Published digests") | `cohort-kit-0.4.0.tar.gz` | `PENDING-KIT-SHA256` |

The driver cannot hold the kit row itself, because the kit's commit contains
the driver. The kit row is instead bound as described below, and the whole
manifest is anchored by the published manifest digest.

AG `58122ce` enrolls new executables: `ag-loopctl` sha256 `af5fe488…` and
`ag-standing-resolver` sha256 `7a42b5ea…`. The driver measures the installed
bytes when it seals the runtime profile, reseals the standing launcher over the
resolver and writes `ag_loopctl` into the Nightshift cycle config, so nothing is
copied by hand.

### What `verify-manifest` and `install` check

- **Every artifact is read once.** The driver hashes each artifact's bytes and
  then parses, extracts or installs exactly those bytes, never the pathname
  again. A file swapped after it was located refuses `artifact.changed`.
- **Every extracted file is checked** against the member it came from, and the
  extracted tree must hold nothing else (`artifact.extracted_mismatch`). Where
  the component publishes digests, they must agree too
  (`artifact.receipt_mismatch`): the `SHA256SUMS` inside AG, Docket and Maude
  (which must list every other file), the binaries in Nightshift's and Pulse's
  `BUILD-INFO.json`, and the App Server's `build-info.json`.
- **The kit is bound to the driver you are running.** The manifest names the
  kit tarball's digest and commit. The driver reads that tarball and refuses:
  - any member its `BUILD-INFO.json` does not list, and any link or special
    member (`kit.unlisted_member`, `artifact.unsafe_member`);
  - a listed file that is missing or has another digest;
  - a placeholder commit such as 40 zeros, a `BUILD-INFO.json` commit other
    than the manifest's, or a manifest commit other than the one stamped into
    the running driver when the kit was built (`pin.kit_commit`);
  - a tarball whose driver differs from the running driver
    (`kit.driver_differs`). A driver run from a source checkout has no stamped
    commit and refuses `kit.unreleased_driver`.

  This proves the running driver is the one inside the kit the manifest names.
  It cannot prove the manifest itself is genuine: that is step 1's job.
- **NQ.** If `nq-ng` is not installed, the driver installs it with `dpkg` from
  a private root-only copy of the verified bytes. If it is already installed,
  the driver compares every file, link and conffile in the pinned package with
  the installed one, and parses the `dpkg --verify` output line by line (dpkg
  can report a changed file and still exit 0). Any difference, another
  version, or a half-installed package refuses `nq.installed_mismatch` before
  anything is written. The same comparison runs after a fresh install.
- **Switchyard** must report `installed_closure_matches_provenance: true` and
  canonical revision `299609cda100ccf8701d5619ac78499f8bddd303`.
- **The App Server** is identified by its `build-info.json` `executable_sha256`,
  because the binary cannot report its own commit.
- Every other executable must report the pinned version and commit through
  `--build-info`, and must be a release build. `--build-info` is an identity
  report, not an integrity check: integrity comes from the pinned digests
  above.

## Newcomer path

`<bundle>` is the directory holding `cohort-manifest.json`, `SHA256SUMS`, the
nine artifacts and `qualification-only/`. `<id>` is a fresh cohort id: 3 to 40
lowercase letters, digits and hyphens. The steps extract the kit to
`/opt/constellation/kit` as root, so that nothing an unprivileged account can
change runs as root.

Each command prints one JSON object on one line (`status --pretty` indents it).
A refusal exits 2 and prints
`{"code":…,"command":…,"detail":…,"result":"refused"}`. The step's record
directory holds `*.started.json`, `*.stdout`, `*.stderr` and `*.finished.json` for
every child it ran, with its exact argv, exit status and output.

### 1. Check the bundle against the published digests, then extract the kit

No kit code runs in this step. Compare the two files with the values in
"Published digests" (copy them from the page, not from the bundle):

```sh
cd <bundle>
sha256sum --check --strict <<'EOF'
PENDING-MANIFEST-SHA256  cohort-manifest.json
PENDING-KIT-SHA256  cohort-kit-0.4.0.tar.gz
EOF
```

Both lines must say `OK`. If either fails, stop: the bundle is not the
published one. Then, optionally, `sha256sum --check --strict SHA256SUMS` checks
the other files for transport damage (the driver checks them by digest in step
2 either way).

```sh
sudo mkdir -p -m 0755 /opt/constellation/kit
sudo tar -xzf <bundle>/cohort-kit-0.4.0.tar.gz -C /opt/constellation/kit --no-same-owner
DRIVER="/usr/bin/python3.11 -I -S /opt/constellation/kit/cohort-kit-0.4.0/setup/constellation_cohort.py"
$DRIVER --version        # constellation-cohort 0.4.0
```

Optionally, run the kit's unit tests, for the driver and for the evidence
verifier:

```sh
/usr/bin/python3.11 -I -S -B /opt/constellation/kit/cohort-kit-0.4.0/setup/test_constellation_cohort.py -v
/usr/bin/python3.11 -I -S -B /opt/constellation/kit/cohort-kit-0.4.0/setup/test_verify_cohort_evidence.py -v
```

### 2. Verify the manifest and install

```sh
$DRIVER verify-manifest --manifest <bundle>/cohort-manifest.json --artifacts <bundle>
sudo $DRIVER install --cohort <id> --manifest <bundle>/cohort-manifest.json --artifacts <bundle>
```

`verify-manifest` needs no root and writes nothing. It prints
`"qualified_cohort":"alpha-exit-rc"` and the kit it bound
(`"running_driver_is_the_kit_driver":true`). `install` checks everything again
before its first write, then installs the NQ package (or checks an installed
one, above) and extracts each other artifact under
`/opt/constellation/cohorts/<id>/`. It then checks the build info of all 18
executables and writes `installed.json` create-once. A refusal before the
first write leaves the host unchanged.

### 3. Initialize the cohort

For the fixture route (qualification only; see "Review routes"). The port is
any free TCP port from 1024 to 65535 on 127.0.0.1; the qualification runs used
18431:

```sh
sudo $DRIVER init --cohort <id> --review-route fixture-review --fixture-port 18431
```

For the real provider route:

```sh
sudo $DRIVER init --cohort <id> --review-route real
```

`init` runs once for each cohort and refuses `cohort.exists` if repeated. It
does the following:

1. It creates the `constellation` system account if it is absent.
2. It creates the synthetic identities and keys, including a fresh Ed25519 AG
   issuer key. No operator secret is involved.
3. It creates a cohort-owned codex home.
4. It compiles and validates the Maude plan, which fixes the text and the
   destination above, and prepares the AG, Docket and Nightshift ports.
5. It writes a per-cohort NQ config at `/etc/nq/cohort-<id>.toml` (root:nq 0640)
   with its store at `/var/lib/nq/cohort-<id>/`. It then runs `nq init` and
   admits the one watcher in NQ's capability-bearing unit.

It takes no observation, makes no provider request and creates no effect.

### 4. Fixture route only: start the loopback fixture

Skip this step on the real route. The fixture stands in for the provider. It
is qualification-only tooling, not part of the product, and it ships in the
bundle under `qualification-only/`. Run it as your normal (unprivileged)
account, in the background, on the port you gave `init`:

```sh
FIXTURE=$HOME/cohort-fixture
mkdir -p "$FIXTURE"
tar -xzf <bundle>/qualification-only/fixture-review-tooling-7b04e8d8cf99.tar.gz -C "$FIXTURE" --no-same-owner
nohup /usr/bin/python3.11 -I "$FIXTURE"/fixture-review-tooling/fixture_responses_endpoint.py \
  --port 18431 --mode accepted --log "$FIXTURE"/requests.jsonl --ready-file "$FIXTURE"/ready.json \
  > "$FIXTURE"/fixture.out 2>&1 &
for i in $(seq 50); do [ -s "$FIXTURE"/ready.json ] && break; sleep 0.1; done; cat "$FIXTURE"/ready.json
```

It is ready when `ready.json` exists; it holds
`{"bind":"127.0.0.1","mode":"accepted","model":"gpt-5.6-terra","port":18431}`.
It binds 127.0.0.1 only. `requests.jsonl` logs each request it answers. If
nothing listens on the port, `review` refuses `fixture.unreachable` before
claiming the review. Stop it after `review` (step 5) with
`pkill -f fixture_responses_endpoint.py`. The tarball's other files
(`run-fixture-review.sh`, `make_fixture_review_inputs.py`,
`check_fixture_review.py`) are component qualification tools; this path does
not use them.

### 5. Review

```sh
sudo $DRIVER review --cohort <id>                          # fixture route
sudo $DRIVER review --cohort <id> --paid-request-allowed   # real route
```

The review runs as one transient `systemd-run` system unit: 600 s, no restart,
bounded tasks and memory, and an explicit environment. It:

1. takes one fresh NQ observation;
2. prepares Pulse support;
3. seals, verifies and initializes the AG genesis (genesis happens here, not in
   `init`, because it pins facts that exist only after the observation);
4. runs Nightshift admission and Foreman custody;
5. makes exactly one bounded **review request** (one model turn that
   generates the review). The pinned App Server first sends one
   **non-generating warm-up** on the same connection (see "Provider requests");
6. runs the independent native review verifier.

It stops before acceptance, with 0 grants and 0 effects. It prints the
candidate digest and an `acceptance` block (step 6). `review` is a
create-once claim: a second `review` on the same cohort refuses
`review.exists`.

The review request must start while both the observation and the Pulse
support have at least 230000 ms left. In the qualification runs it started
5 to 11 s after the observation, and the whole review took 9 to 15 s.

### 6. Read what acceptance will do, then accept within 5 minutes

**You have 5 minutes from the review to accept.** The review expires 300 s
after it was made (`acceptance.deadline.accept_before`), and the continuation
then needs about 10 s. Leave yourself at least 30 s. After the deadline the
cohort cannot execute: `accept` refuses `review.expired` and records nothing,
and the only way on is a fresh cohort id.

```sh
sudo $DRIVER status --cohort <id> --pretty
```

`status` is strictly read-only. Its `acceptance` block is what you are
judging:

- `will_write`: the destination `path`, the size in `bytes`, and the `text`
  itself, decoded. `bound_by_plan: true` means it is exactly what the sealed
  plan binds;
- `review`: the verdict, the reviewer id, the route and the reviewer's
  findings. On the fixture route the verdict is scripted, and `note` says so;
- `deadline`: `accept_before` (UTC), `seconds_remaining` and `expired`;
- `candidate_sha256` and a ready `accept_command`.

The raw candidate is
`/var/lib/constellation/cohorts/<id>/review/review-001/record-review-input.json`;
the `acceptance` block decodes it for you. If you agree that this text should
be written to that path, accept it by naming that exact digest:

```sh
sudo $DRIVER accept --cohort <id> --candidate-sha256 sha256:<64 hex from status>
```

Acceptance is the operator's own step, and the driver has no auto-accept
option. Accept runs one durable unit that records the review in AG, creates a
Docket standing grant of at most 60 s, and runs AG's finite runner. The Maude
executor then creates `result.txt` once. The continuation makes no provider
request. Its output repeats what was accepted (`accepted`) and what was
written (`result_file`).

- If the digest is wrong, accept refuses `accept.candidate_mismatch` and records
  nothing. The retained candidate stays acceptable until its deadline.
- A second `accept` refuses `accept.exists`.
- The result reports `human_attestation: false`. The acceptance is an operator
  transition, not a signed human attestation.

### 7. Inspect

```sh
sudo $DRIVER status --cohort <id> --pretty
```

After a successful accept, `status` shows:

- AG at `settled_observation_required` with settlement outcome `success`;
- `counters`: the current counts from AG's native replay (1 spend, 1 Docket
  attempt and 1 settlement) and 1 result file. `review.counters_at_review` is
  the snapshot taken when the review finished, all 0, and it stays that way;
- `result_file` with the exact bytes, sha256, `matches_plan: true`, and a
  scratch directory that holds only `result.txt`.

`result.txt` is owned by `constellation`, mode 0600, in a 0700 directory, so
reading it needs `sudo`.

### 8. Export and verify evidence

```sh
sudo $DRIVER evidence --cohort <id> --output /var/tmp/<id>-evidence
```

The output directory must be absolute and must not exist yet. It is created
root-owned with mode 0700, so copying it off the host needs `sudo`. It
receives:

- the driver and caller records, and the plan, owner, deployment, observation
  and port inputs;
- online SQLite backups of the AG, Foreman, Switchyard, Nightshift, Docket and
  plan stores;
- native AG and Docket inspection;
- `JOIN.json`, and a `SHA256SUMS` over all files.

The export copies no codex home, so it contains no credential file. The driver's
join checks that the binding, occurrence, accepted candidate, v2 issuance
(`not_after` later than the spend), AG and Docket custody, attempt, settlement
and standing snapshot all agree, with exactly one spend, attempt and settlement.

Then check the export independently with the kit's own verifier,
`setup/verify_cohort_evidence.py`, not the published alpha.6
`verify-evidence.py`:

```sh
sudo /usr/bin/python3.11 -I -S /opt/constellation/kit/cohort-kit-0.4.0/setup/verify_cohort_evidence.py \
  --evidence /var/tmp/<id>-evidence
```

It ships in the kit tarball, so its digest is in the kit's `BUILD-INFO.json`
and it needs nothing else from the site repository. It imports nothing from the
driver, runs no component binary and uses no network. It does not trust
`JOIN.json`. It:

- rechecks every `SHA256SUMS` digest, and fails on a missing listed file;
- recomputes the joins itself;
- recomputes the AG issuance identity and verifies its Ed25519 signature with
  `/usr/bin/openssl` against the key the exported Docket trust names;
- checks that `result.txt` holds exactly the plan's reviewed bytes;
- requires the same checks to refuse when a different plan digest is
  substituted.

It prints one JSON line and exits 0 only when `"result":"passed"`. A malformed
or incomplete export fails with exit 1 and names the reason.

The published alpha.6 `constellation/releases/0.1.0-alpha.6/verify-evidence.py`
cannot run against a cohort export. Its objective leg needs a Maude
`PlanDocument` reader for `ag-operator-ui`, and that reader is not packaged.

## Review routes

### Fixture review: qualification only

The `fixture-review` route qualifies install, wiring, custody, authority and
effect. It does **not** qualify review independence. Its reviewer id is
`fixture-deterministic-reviewer-not-independent`, and its verdict is scripted.

- `init` writes the codex home `codex-home-fixture-review/` with a loopback
  `openai_base_url` and a generated dummy key
  (`fixture-not-a-credential-<hex>`). No credential is involved.
- The fixture is not a manifest component and not part of the product. It is
  `qualification-only/fixture-review-tooling-7b04e8d8cf99.tar.gz` (sha256
  `168c4e57a7cb3d431ee2f9cb3b546c0d51f97a4781313522fa28f42b39964b8a`), started
  as in step 4.

### Real provider: the operator's acceptance step

A real-provider review is the operator's acceptance step for this cohort. It has
not been run, and the API-key credential form below has not been tried against
the real provider.

- `init --review-route real` creates
  `/var/lib/constellation/cohorts/<id>/codex-home-real/` (constellation, 0700),
  holding only `config.toml`. That file sets
  `cli_auth_credentials_store = "file"` and no `openai_base_url`.
- The reviewer id is `cohort-<id>-independent-reviewer`. The route is provider
  `openai`, model `gpt-5.6-terra`, through the pinned App Server.
- **The operator places the credential.** The driver never reads, writes or
  copies it. Use the API-key form, a single-key JSON object:

  ```json
  {"OPENAI_API_KEY":"<your key>"}
  ```

  Write it as `auth.json` in that codex home, owned by `constellation` with mode
  0600. For example, run the following and paste the object on standard input:

  ```sh
  sudo -u constellation sh -c 'umask 077; cat > /var/lib/constellation/cohorts/<id>/codex-home-real/auth.json'
  ```

  This key bills the API organization. **Never commit `auth.json` or its value**,
  and never copy it into evidence, a bundle, logs or an issue. The `evidence`
  export does not include the codex home.
- `review` then needs `--paid-request-allowed`. Without it, the review refuses
  `review.paid_request` before any request.

### Provider requests: one review request and one warm-up

The review makes one generating request, but that is not the only message the
App Server sends to the provider. The pinned App Server (Codex `97b0acd`)
opens a Responses WebSocket and, when its session starts, sends a
`response.create` with `generate: false` before the review turn
(`codex-rs/core/src/session_startup_prewarm.rs`, and `prewarm_websocket` in
`codex-rs/core/src/client.rs`). That warm-up carries the session's base
instructions and tool definitions but no review input, and it asks for no
output. The built-in `openai` provider enables WebSockets, so the real route
sends it too. The fixture logs it as a request with `"warmup":true`, next to
the one review request.

Whether the provider bills a `generate: false` request, for example for its
input tokens, has not been verified. Until it is, count the real route as one
billable review request plus one warm-up of unknown cost. The driver does not
change this behaviour. It belongs to the App Server and its route (owner: lane
E), and it is recorded as a beta item.

## Trust boundary: the operator's host account

Governance in this kit protects the effect against the review agent and the
worker processes. It does **not** protect against someone who controls the
`constellation` account (or root) on the operator's host. That account holds
the AG issuer key, the AG and Docket stores and the scratch directory, and it
runs Docket, which runs the Maude executor as a child process. Anyone who can
act as that account can run the executor directly with the sealed plan and
write `result.txt` without an AG issuance or Docket custody, or simply write
the file. The hostile review demonstrated this (its finding F4).

This is a property of the local deployment, not a gap the driver can close on
its own. Docket's executor transport starts the executor as its own child,
under its own account (Docket `3093def`, `invoke_json_with_deadline` in
`crates/gwr-local/src/governed_loop.rs`), so any wrapper Docket can start, the
same account can start. A separate effect account would need the executor to
verify a Docket- or AG-signed token, or the governance keys and stores to live
under accounts the operator's account cannot reach. Both are component
changes, recorded as beta items. Treat the host account as trusted.

## Limitations found by the closure lanes

- **One cohort, one occurrence.** `init`, `review` and `accept` are create-once
  for each cohort. The driver has no retry, re-review or second-occurrence
  command. A refused review, an expired review or issuance, or a lost unit all
  need a new cohort id, with a fresh `install` and `init`, or a new disposable
  host. The driver also has no recovery command. After a lost unit, inspect
  with `status` and the record directory, and do not rerun the step.
- **Expired review or issuance.** `accept` refuses an expired review
  (`review.expired`) without recording anything. AG's v2 issuance carries a
  signed not-after, and a spend that misses it is refused
  `issuance_not_current` and never reaches Docket. Neither can be revived, so
  use a new cohort.
- **The local trust boundary** above: the `constellation` account can produce
  the effect directly.
- **The warm-up request** above: the real route sends one non-generating
  warm-up before the review request, and its cost is unverified.
- **NQ's read path for the cohort account.** NQ 0.2.0 has no documented read
  path for an account other than `nq`, so the `constellation` account cannot
  read NQ's store directly. During `review` the driver has `nq` take a verified
  backup, restores it into
  `/var/lib/constellation/cohorts/<id>/observation/nq-replica/`, and refuses
  `observation.replica` unless the copy's `qualify` output is byte-identical to
  the live store's. This is an open NQ defect (DEFECT-2), accepted for this
  cohort only.
- **Docket local-mode refusal names.** With the shipped local standing
  resolver, a standing refusal reads
  `process-refused:refused/error: local-standing-absent` (or `-future`,
  `-ambiguous`, `-operator-enrollment-mismatch`). These fail closed before
  custody.
- **AG read-only exit 3.** AG's read-only commands (`inspect`, `status`,
  `replay`, `history` and the rest) exit 3 when a file their genesis enrolls
  is absent, after verifying everything else. The driver never treats that as
  success: `status` and `evidence` refuse `ag.enrolled_file_unavailable`,
  naming the files.
- **Supervised Maude sessions are unsupported in this release.** This means the
  classic RPC, the TUI and agent_governor. The Maude artifact also does not
  ship the plan CLI or `public-nq-host-bootstrap.py`.
- **Stale-review diagnostics.** A review that does not match the cohort's
  binding is refused (`review.refused`) by the caller's own check, before the
  native verifier runs. It writes no candidate. The caller's terminal names phase
  `record-review-custody` instead of the projection step that refused. Read
  `review/review-001/terminal.json` first.

### Refusal codes you may meet

| Code | Meaning |
|---|---|
| `pin.incompatible` | A manifest value differs from `alpha-exit-rc`; the detail names the field |
| `pin.kit_commit` | The kit commit is a placeholder, or differs from the commit stamped into the driver you are running |
| `kit.unlisted_member`, `kit.missing_member`, `kit.member_digest` | The kit tarball holds a file its `BUILD-INFO.json` does not list, lacks one it lists, or has one with another digest |
| `kit.driver_differs`, `kit.unreleased_driver` | You are not running the driver from the kit the manifest names; extract it from the checked tarball (step 1) |
| `artifact.missing`, `artifact.ambiguous` | No file, or more than one file, in `--artifacts` carries a pinned digest |
| `artifact.changed` | An artifact changed between being located and being read; nothing was used |
| `artifact.unsafe_member`, `artifact.extracted_mismatch`, `artifact.receipt_mismatch` | A tar member is unsafe, an extracted file differs from its member, or a component's own digests disagree |
| `nq.installed_mismatch`, `nq.package` | The installed `nq-ng` differs from the pinned package (the detail names the files), or the package is not the pinned one |
| `build_info.*` | An installed executable does not report its pinned identity |
| `host.unsupported`, `host.missing_tool`, `host.not_root`, `host.storage`, `host.permission` | Host requirement not met; `host.not_root` means run it with `sudo` |
| `cohort.exists` | Install or init was already done for this id; use a fresh id |
| `cohort.not_installed`, `cohort.not_initialized` | A step ran out of order |
| `fixture.port`, `fixture.unreachable` | The fixture port is missing, was given for the real route, or nothing is listening |
| `review.paid_request` | The real route needs `--paid-request-allowed` |
| `observation.condition` | NQ did not report the host load condition as `explicitly_absent` |
| `observation.replica` | The NQ replica's qualification differs from the live store's (DEFECT-2 path) |
| `review.refused` | The caller or the native verifier refused the review; no candidate was written. Start with `review/review-001/terminal.json` |
| `review.exists`, `accept.exists` | The create-once step already ran for this cohort |
| `review.not_ready` | No retained, passing review to accept |
| `review.expired` | The review's 5 minutes passed before `accept`; nothing was recorded; use a fresh cohort |
| `accept.candidate`, `accept.candidate_mismatch` | The digest is malformed, or is not the retained candidate |
| `accept.refused` | The continuation refused; see its records |
| `evidence.output` | The output path is not absolute, or already exists |
| `ag.enrolled_file_unavailable` | AG's read-only check exited 3: a file its genesis profile enrolls is absent; the detail names it |

## What 0.4.0 changed

Kit 0.3.0 (`85ab6d2c…`, manifest `874943a9…`) is superseded, and this driver
refuses its manifest. The changes answer the lane H hostile review and
newcomer run:

- the published digests, and a step 1 that runs no kit code; the README is no
  longer inside the kit;
- the exhaustive kit binding with a stamped commit, and kit modules appended
  after the standard library;
- artifacts hashed and used from the same bytes, with every extracted file
  checked;
- an installed `nq-ng` compared file by file with the pinned package;
- `status` and `accept` show the text, destination, size, review findings and
  deadline; `accept` refuses an expired review; `status` separates the
  review-time counters from the current ones; `status` as a non-root account
  refuses `host.not_root` instead of failing with a traceback;
- `--help` documents every option and lists no internal command;
- this README: the fixture step, the words list, the trust boundary and the
  warm-up request.

## What the driver runs underneath

The driver composes the caller glue in this directory with the components' own
commands, in a fixed order. The ownership it relies on is:

1. Maude's caller-owned Plan Core store supplies a checked, locked,
   deterministically compiled `maude.governed-plan-binding/v1` and a sealed
   executor plan. Neither compilation nor this caller confers permission.
2. Nightshift `cycle run-config` admits that exact handoff to an initialized AG
   V2 genesis, using the current NQ observation and Pulse support. The native AG
   command is `record-proposal ... --plan-binding ...`, which is not an
   authorization.
3. Foreman prepares one bounded request (120 s, 32768 output bytes).
   Switchyard performs local preflight and exactly one App Server review. The
   independent native review verifier authenticates the result against the
   retained Switchyard and Foreman stores.
4. On the operator's accept, AG records the review and resolves standing. Its
   permission preflight binds the exact occurrence, work, binding, reviewer and
   genesis profile, and it grants nothing.
5. The continuation creates a Docket standing grant for at most 60 s, never
   beyond the review's expiry.
6. AG's native V2 finite runner owns the durable program counter, the protected
   decision, authorization consumption and the Docket attempt. Docket owns
   execution custody. The Maude executor owns its attempt journal and the
   exclusive file creation.
7. Native AG and Docket inspection joins custody and settlement. The caller
   separately checks the exact bytes of `result.txt`. That check is not a fresh
   NQ judgment of a postcondition.

Review enforcement is not only a caller preflight. AG's V2 genesis enrolls
`shared_admission`, and `fresh_shared_gate` verifies the stored plan and the
current accepted review again before each protected decision and authorization
consumption. `commit_shared_consequence` commits the transition and the exact
binding and review gate atomically. Reopening the store verifies gate coverage
and joins. Removing or changing a gate makes native replay fail closed. This
caller refuses a V1 genesis.

| File | Role in the cohort |
|---|---|
| `setup/constellation_cohort.py` | The setup driver (stdlib only, `/usr/bin/python3.11 -I -S`); the released copy has its kit commit stamped in |
| `setup/test_constellation_cohort.py` | The driver's unit tests |
| `setup/cohort_plan_inputs.py` | Builds the plan inputs with Maude's constructors from `maude-plan.pyz` |
| `setup/prepare_review_inputs.py` | Drafts and seals the five Foreman inputs with `nightshift-foreman provider-seal-inputs` |
| `setup/verify_cohort_evidence.py`, `setup/test_verify_cohort_evidence.py` | The independent evidence verifier (step 7) and its unit tests |
| `prepare_plan.py`, `prepare_local_ports.py`, `prepare_owner.py`, `prepare_finite_run.py`, `seal_admission.py`, `enroll_caller.py`, `prepare_review_candidate.py` | Plan, port, owner, admission, caller-enrollment and finite-run preparation, run by the driver directly or through the caller modules |
| `reviewed_action.py`, `continue_reviewed_action.py` | The caller: `--preflight-only` and `--review-only` in the review unit, and `--accept-and-execute` in the accept unit. The caller's `--execute`, `--inspect` and `--recover-run` modes are not wrapped by the driver and were not exercised |

The driver runs every kit module as
`/usr/bin/python3.11 -I -S -c 'import sys; sys.path.extend([…]); import M; M.main(sys.argv[1:])'`.
On 3.11, `-I` implies `-P`, so the kit directories go on the path explicitly.
They are appended after the standard library, so a kit file named like a
standard module (for example `setup/json.py`) can never shadow it, and no kit
module is named like one.
The hand-run B004-era procedure has been retired. It invoked each of these
scripts with `python3.12`, from source builds, with a caller layout written by
hand. Running the scripts by hand is not a supported newcomer path. Their `--help`
and module docstrings remain the reference for their arguments.

## Retired pre-cohort material

These files remain in the directory, but they are not part of the cohort path.
None of them is a cohort pin.

- **`source-pins.json`** lists the source revisions of the pre-cohort
  candidate: Maude `c1fce17`, NQ `d3089a9`, Pulse `d91b214`, AG `4dafc1a`,
  Docket `fbcacc1`, and Nightshift and Foreman `58639a9`. The cohort manifest
  above supersedes it. NQ 0.2.0 changed the `nq.host` profile semantic id, so
  that NQ and Pulse pair is not interchangeable with the cohort's.
- **`run_public_python_closure_001.sh`, `prepare_public_python_closure.py` and
  `requirements-public.lock`** build a Switchyard Python closure from source.
  They are marked retired and have no default interpreter (their earlier
  `python3.12` default is gone; Debian 12 does not ship it). The
  cohort does not use them: the Switchyard artifact ships its installed closure,
  and `install` checks it against its provenance. The site repository's
  `tools/test_reviewed_local_copy_example.py` controls also predate the driver.
- **`drop_success_response.py`** and Maude `c1fce17`'s
  `executor-interruption-qualification` artifact are component qualification
  fixtures for response loss and interruption. The cohort runs do not
  exercise them, and the cohort does not enroll them.

See [PUBLICATION-SCOPE.md](PUBLICATION-SCOPE.md) for what may and may not be
published from this directory.
