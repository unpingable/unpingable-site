# Reviewed local copy: the `reviewed-local-copy/v1` cohort kit

This kit sets up one operation on one Debian 12 host: copy selected UTF-8 text
(at most 64 KiB) to a previously absent `result.txt` in an exclusive scratch
directory, after one bounded review and one explicit operator acceptance. It has
no arbitrary command field, notification requirement, scheduler, replacement
authority store or alternative provider route.

**Status.** This is candidate material, not a released or generally installable
suite. An earlier kit (0.2.0, with AG `e20c23a`) was qualified in one clean
Debian 12 VM (`cohort-clean-install/run-002`: 21 PASS, 0 FAIL, 0 not
exercised), installing only from the cohort artifacts and using the
qualification-only fixture review. This kit (0.3.0) repins AG to `58122ce` and
ships the evidence verifier. It is the kit that `cohort-clean-install/run-003`
exercises; a kit cannot carry its own qualification result, so that result is
recorded with the campaign, not here. These runs do not establish:

- a real-provider review (the real route has not been exercised);
- more than one occurrence per cohort;
- the driver's `upgrade`, `verify-retained` and `upgrade-status` commands as a
  newcomer path. They retire a settled cohort into a new one and were
  qualified separately (upgrade-continuity runs); this README does not cover
  them;
- a public download of the cohort bundle. Run-002 and run-003 used bundles
  composed by the qualification harness; this README describes the path those
  bundles took.

A newcomer run from these instructions is still pending. Treat anything this
README does not state as unsupported.

## Host requirements

The driver checks these and refuses (`host.*`) when one is missing:

- Debian 12 (`/etc/os-release` `debian:12`);
- `/usr/bin/python3.11` as a regular file, not a symlink. Debian 12 ships 3.11.2.
  Every kit command runs as `/usr/bin/python3.11 -I -S`. **Do not use
  `python3.12`**, `/usr/bin/python3` (a symlink) or a virtual environment;
- `/usr/bin/openssl` with Ed25519;
- `systemd-run`, `setpriv`, `dpkg` and `useradd` on the system path;
- root for `install`, `init`, `review`, `accept`, and for `status` and `evidence`
  once the cohort is initialized;
- at least 2 GiB and 10000 inodes free under `/opt` (install) and `/var/lib`
  (review).

Run-002 also relied on `memfd_create`, `libssl3` and `liblzma5`, which the Debian
12 genericcloud image provides. It used 2 vCPU and 4 GiB of memory.

The review also requires NQ to report the host load condition as
`explicitly_absent`. On a busy host the review refuses `observation.condition`
before any provider request.

## Cohort manifest pins

The driver sets up only the cohort `alpha-exit-rc` of profile
`reviewed-local-copy/v1`. The manifest (`constellation.cohort-manifest/v1`) must
name exactly these components. Compatibility means equality: version, source
commit **and** artifact digest must all match. There are no ranges and no
"newer is fine"; any other value refuses `pin.incompatible`.

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
| cohort-kit | 0.3.0 | the site commit in the kit's own `BUILD-INFO.json` | `cohort-kit-0.3.0.tar.gz` | the digest your manifest names (see below) |

The kit cannot print its own commit or digest, because both change with every
file in it, including this README. The manifest you were given names them, and
`install` checks that they agree with the kit (below). Run-002's manifest
(`822afd2b…`) named the earlier kit 0.2.0 and AG `e20c23a`; this driver refuses
it.

AG `58122ce` enrolls new executables: `ag-loopctl` sha256 `af5fe488…` and
`ag-standing-resolver` sha256 `7a42b5ea…`. The driver measures the installed
bytes when it seals the runtime profile, reseals the standing launcher over the
resolver and writes `ag_loopctl` into the Nightshift cycle config, so nothing is
copied by hand.

Beyond the table, `install` checks:

- **The kit pins itself.** The manifest's cohort-kit commit must equal the kit's
  `BUILD-INFO.json`, every kit file must match its recorded digest, and the
  installed driver must be byte-equal to the driver you are running. The kit row
  is self-describing, so a kit built from any other commit has a different
  digest and needs its own manifest entry.
- **Switchyard** must report `installed_closure_matches_provenance: true` and
  canonical revision `299609cda100ccf8701d5619ac78499f8bddd303`.
- **The App Server** is identified by its `build-info.json` `executable_sha256`,
  because the binary cannot report its own commit.
- Every other executable must report the pinned version and commit through
  `--build-info`, and must be a release build.

## Newcomer path

`<bundle>` is the directory holding `cohort-manifest.json`, `SHA256SUMS` and the
nine artifacts. `<kit>` is where you extract the cohort kit. `<id>` is a fresh
cohort id: 3 to 40 lowercase letters, digits and hyphens.

Each command prints one JSON object. A refusal exits 2 and prints
`{"code":…,"command":…,"detail":…,"result":"refused"}`. The step's record
directory holds `*.started.json`, `*.stdout`, `*.stderr` and `*.finished.json` for
every child it ran, with its exact argv, exit status and output.

### 1. Check the bundle and extract only the kit

```sh
cd <bundle> && sha256sum --check --strict SHA256SUMS
mkdir <kit>
tar -xzf <bundle>/cohort-kit-0.3.0.tar.gz -C <kit> --no-same-owner
DRIVER="/usr/bin/python3.11 -I -S <kit>/cohort-kit-0.3.0/setup/constellation_cohort.py"
$DRIVER --version        # constellation-cohort 0.3.0
```

Optionally, run the kit's unit tests, for the driver and for the evidence
verifier:

```sh
/usr/bin/python3.11 -I -S -B <kit>/cohort-kit-0.3.0/setup/test_constellation_cohort.py -v
/usr/bin/python3.11 -I -S -B <kit>/cohort-kit-0.3.0/setup/test_verify_cohort_evidence.py -v
```

### 2. Verify the manifest and install

```sh
sudo $DRIVER verify-manifest --manifest <bundle>/cohort-manifest.json --artifacts <bundle>
sudo $DRIVER install --cohort <id> --manifest <bundle>/cohort-manifest.json --artifacts <bundle>
```

`verify-manifest` writes nothing, and it does not need root. It prints
`"qualified_cohort":"alpha-exit-rc"`. `install` checks everything again, installs
the NQ package (or verifies an identical installed one with `dpkg --verify`) and
extracts each other artifact under `/opt/constellation/cohorts/<id>/`. It then
checks the build info of all 18 executables and writes `installed.json`
create-once. A wrong digest, missing artifact or unsafe tar member refuses before
anything is written.

### 3. Initialize the cohort

For the fixture route (qualification only; see below):

```sh
sudo $DRIVER init --cohort <id> --review-route fixture-review --fixture-port <port>
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
4. It compiles and validates the Maude plan and prepares the AG, Docket and
   Nightshift ports.
5. It writes a per-cohort NQ config at `/etc/nq/cohort-<id>.toml` (root:nq 0640)
   with its store at `/var/lib/nq/cohort-<id>/`. It then runs `nq init` and
   admits the one watcher in NQ's capability-bearing unit.

It takes no observation, makes no provider request and creates no effect.

### 4. Review

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
5. sends **exactly one** bounded provider request;
6. runs the independent native review verifier.

It stops before acceptance, with 0 grants and 0 effects, and prints
`candidate_sha256`. `review` is a create-once claim: a second `review` on the
same cohort refuses `review.exists`.

The provider request must start while both the observation and the Pulse
support have at least 230000 ms left. In run-002 it started about 11 s after the
observation, and the whole review took 14.4 s.

### 5. Read the candidate, then accept it

```sh
sudo $DRIVER status --cohort <id>
```

`status` is strictly read-only. It shows:

- the review verdict, the counters (all still 0) and the review body;
- `review.candidate_sha256`;
- the path of the candidate, which is
  `/var/lib/constellation/cohorts/<id>/review/review-001/record-review-input.json`.

Read the candidate. Then accept it by naming that exact digest:

```sh
sudo $DRIVER accept --cohort <id> --candidate-sha256 sha256:<64 hex from status>
```

Acceptance is the operator's own step, and the driver has no auto-accept
option. Accept runs one durable unit that records the review in AG, creates a
Docket standing grant of at most 60 s, and runs AG's finite runner. The Maude
executor then creates `result.txt` once. The continuation makes no provider
request.

- If the digest is wrong, accept refuses `accept.candidate_mismatch` and records
  nothing. The retained candidate stays acceptable.
- A second `accept` refuses `accept.exists`.
- The result reports `human_attestation: false`. The acceptance is an operator
  transition, not a signed human attestation.

### 6. Inspect

```sh
sudo $DRIVER status --cohort <id>
```

After a successful accept, `status` shows:

- AG at `settled_observation_required` with settlement outcome `success`;
- replay counts of 1 spend, 1 Docket attempt and 1 settlement;
- `result_file` with the exact bytes, sha256, `matches_plan: true`, and a
  scratch directory that holds only `result.txt`.

### 7. Export and verify evidence

```sh
sudo $DRIVER evidence --cohort <id> --output /absolute/fresh/directory
```

The output directory must not exist yet. It receives:

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
sudo /usr/bin/python3.11 -I -S <kit>/cohort-kit-0.3.0/setup/verify_cohort_evidence.py \
  --evidence /absolute/fresh/directory
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
`fixture-deterministic-reviewer-not-independent`.

- `init` writes the codex home `codex-home-fixture-review/` with a loopback
  `openai_base_url` and a generated dummy key
  (`fixture-not-a-credential-<hex>`). No credential is involved.
- The fixture is not a manifest component and not part of the product. Run-002
  shipped it in the bundle under
  `qualification-only/fixture-review-tooling-7b04e8d8cf99.tar.gz` (sha256
  `168c4e57a7cb3d431ee2f9cb3b546c0d51f97a4781313522fa28f42b39964b8a`) and
  started it before `review`:

  ```sh
  tar -xzf <bundle>/qualification-only/fixture-review-tooling-7b04e8d8cf99.tar.gz -C <fixture-dir> --no-same-owner
  /usr/bin/python3.11 -I <fixture-dir>/fixture-review-tooling/fixture_responses_endpoint.py \
    --port <port> --mode accepted --log <fixture-dir>/requests.jsonl --ready-file <fixture-dir>/ready.json
  ```

  It binds 127.0.0.1 only. The port must equal `init --fixture-port`. If nothing
  is listening, `review` refuses `fixture.unreachable`.

### Real provider: the operator's acceptance step

A real-provider review is the operator's acceptance step for this cohort. It has
not been run. Nothing in run-002 exercised it, and the API-key credential form
below has not been tried against the real provider.

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
  `review.paid_request` before any request. The flag allows exactly one billable
  request.

## Limitations found by the closure lanes

- **One cohort, one occurrence.** `init`, `review` and `accept` are create-once
  for each cohort. The driver has no retry, re-review or second-occurrence
  command. A refused review, an expired issuance or a lost unit all need a new
  cohort id, with a fresh `install` and `init`, or a new disposable host. The
  driver also has no recovery command. After a lost unit, inspect with `status`
  and the record directory, and do not rerun the step.
- **Expired issuance.** AG's v2 issuance carries a signed not-after. A spend that
  misses it is refused `issuance_not_current` and never reaches Docket. The
  occurrence cannot be revived, so use a new cohort.
- **NQ DEFECT-2: the verified-replica read path.** NQ 0.2.0 has no documented
  read path for an account other than `nq`. The `constellation` account cannot
  run `nq diagnostics qualify` on NQ's store (`/etc/nq` is 0750 root:nq and
  `/var/lib/nq` is 0700). The driver works around this during `review`:
  1. As `nq`, it takes a verified `nq backup`.
  2. It restores the backup with `nq restore` into
     `/var/lib/constellation/cohorts/<id>/observation/nq-replica/`.
  3. It enrolls that replica in Nightshift.
  4. It refuses `observation.replica` unless the replica's `qualify` output is
     byte-identical to the live store's.

  This is a named, open NQ defect. The workaround is accepted for this cohort
  only.
- **Docket local-mode refusal names.** With the shipped local standing
  resolver, standing refusals do not use the D4 name
  `governed-execution-standing-absent`. Docket's `accept` reports them as local
  resolver refusals, and they fail closed before custody:
  - `process-refused:refused/error: local-standing-absent` (absent standing);
  - `…local-standing-future` (future-dated standing);
  - `…local-standing-ambiguous` (duplicate grants);
  - `…local-standing-operator-enrollment-mismatch` (operator mismatch).

  These local-mode names are the documented surface, and no mapping is applied.
- **Evidence verification.** As described in step 7, the published alpha.6
  `verify-evidence.py` cannot run against a cohort export, so use the kit's
  `setup/verify_cohort_evidence.py`.
- **AG read-only exit 3.** AG `58122ce`'s read-only commands (`inspect`,
  `status`, `replay`, `history` and the rest) verify the store against public
  material only and never open the issuer private key. When an enrolled file
  is absent they still verify everything else, print their normal JSON, name
  the absent files on stderr (`enrolled file unavailable: {…}`) and exit 3.
  The driver never treats exit 3 as success: for a live cohort `status` and
  `evidence` refuse `ag.enrolled_file_unavailable` naming the files.
- **Supervised Maude sessions are unsupported in this release.** This means the
  classic RPC, the TUI and agent_governor. The Maude artifact also does not
  ship the plan CLI or `public-nq-host-bootstrap.py`.
- **Stale-review diagnostics.** A review that does not match the cohort's
  binding is refused (`review.refused`) by the caller's own check, before the
  native verifier runs. It writes no candidate. The caller's terminal names phase
  `record-review-custody` instead of the projection step that refused.

### Refusal codes you may meet

| Code | Meaning |
|---|---|
| `pin.incompatible` | A manifest value differs from `alpha-exit-rc`; the detail names the field |
| `artifact.missing`, `artifact.ambiguous` | No file, or more than one file, in `--artifacts` carries a pinned digest |
| `build_info.*` | An installed executable does not report its pinned identity |
| `host.unsupported`, `host.missing_tool`, `host.not_root`, `host.storage` | Host requirement not met |
| `cohort.exists` | Install or init was already done for this id; use a fresh id |
| `cohort.not_installed`, `cohort.not_initialized` | A step ran out of order |
| `fixture.port`, `fixture.unreachable` | The fixture port is missing, was given for the real route, or nothing is listening |
| `review.paid_request` | The real route needs `--paid-request-allowed` |
| `observation.condition` | NQ did not report the host load condition as `explicitly_absent` |
| `observation.replica` | The NQ replica's qualification differs from the live store's (DEFECT-2 path) |
| `review.refused` | The caller or the native verifier refused the review; no candidate was written |
| `review.exists`, `accept.exists` | The create-once step already ran for this cohort |
| `review.not_ready` | No retained, passing review to accept |
| `accept.candidate`, `accept.candidate_mismatch` | The digest is malformed, or is not the retained candidate |
| `accept.refused` | The continuation refused; see its records |
| `evidence.output` | The output path is not absolute, or already exists |
| `ag.enrolled_file_unavailable` | AG's read-only check exited 3: a file its genesis profile enrolls is absent; the detail names it |

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
| `setup/constellation_cohort.py` | The setup driver (stdlib only, `/usr/bin/python3.11 -I -S`) |
| `setup/test_constellation_cohort.py` | The driver's unit tests |
| `setup/cohort_plan_inputs.py` | Builds the plan inputs with Maude's constructors from `maude-plan.pyz` |
| `setup/prepare_review_inputs.py` | Drafts and seals the five Foreman inputs with `nightshift-foreman provider-seal-inputs` |
| `setup/verify_cohort_evidence.py`, `setup/test_verify_cohort_evidence.py` | The independent evidence verifier (step 7) and its unit tests |
| `prepare_plan.py`, `prepare_local_ports.py`, `prepare_owner.py`, `prepare_finite_run.py`, `seal_admission.py`, `enroll_caller.py`, `prepare_review_candidate.py` | Plan, port, owner, admission, caller-enrollment and finite-run preparation, run by the driver directly or through the caller modules |
| `reviewed_action.py`, `continue_reviewed_action.py` | The caller: `--preflight-only` and `--review-only` in the review unit, and `--accept-and-execute` in the accept unit. The caller's `--execute`, `--inspect` and `--recover-run` modes are not wrapped by the driver and were not exercised in run-002 |

The driver runs every kit module as
`/usr/bin/python3.11 -I -S -c 'import sys; sys.path[:0]=[…]; import M; M.main(sys.argv[1:])'`.
On 3.11, `-I` implies `-P`, so the kit directories go on the path explicitly.
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
  fixtures for response loss and interruption. Run-002 did not exercise them,
  and the cohort does not enroll them.

See [PUBLICATION-SCOPE.md](PUBLICATION-SCOPE.md) for what may and may not be
published from this directory.
