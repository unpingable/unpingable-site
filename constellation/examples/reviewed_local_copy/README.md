# Reviewed local copy: an external caller candidate

This example connects existing native interfaces for one operation: copy selected
UTF-8 text (at most 64 KiB) to a previously absent `result.txt` in an exclusive
scratch directory. It has no arbitrary command field, notification requirement,
scheduler, replacement authority store, or alternative provider route.

This is **candidate glue**, not a released, newcomer-qualified deployment. Local
tests exercise its parsing, scheduling, failure boundaries and recovery routing.
They do not establish a real accepted provider review, native authority, a copy,
or interruption recovery. A fresh installation still needs native provisioning,
exact enrolled program/configuration identities, and a separately admitted real
qualification. No captured review or private deployment files ship here.

## Ownership and order

The operator admits one durable manager for this complete finite chain:

1. Maude's caller-owned Plan Core store supplies a checked, locked,
   deterministically compiled `maude.governed-plan-binding/v1` and sealed executor
   plan. Neither compilation nor this caller confers permission.
2. Nightshift `cycle run-config` admits that exact handoff to an already initialized
   AG V2 genesis using current NQ observation and Pulse support. The native AG
   command is `record-proposal ... --plan-binding ...`, not an authorization.
3. Foreman prepares one bounded request. Switchyard performs local preflight and
   exactly one existing-AppServer review. The independent native review verifier
   authenticates the result against the retained Switchyard and Foreman stores.
4. AG records the review and resolves standing. Its permission preflight binds the
   exact occurrence, work, binding, reviewer and genesis profile; it grants nothing.
5. The explicitly authorized operator command creates a Docket standing grant for
   at most 60 seconds, never beyond the original review expiry.
6. AG's native V2 finite runner owns the durable program counter, protected
   decision, authorization consumption and Docket attempt. It does not repeat the
   already completed Nightshift admission. Docket owns execution custody; the
   Maude executor owns its attempt journal and exclusive file creation.
7. Native AG/Docket inspection joins custody and settlement. The caller separately
   checks the regular file's exact bytes. That check is not a fresh NQ judgment of
   a postcondition.

Review enforcement is not merely a caller preflight. AG's V2 genesis enrolls
`shared_admission`; `fresh_shared_gate` verifies the stored plan and current accepted
review again before each protected decision and authorization consumption.
`commit_shared_consequence` commits the transition and exact binding/review gate
atomically. Store reopening verifies gate coverage and joins. Removing or changing
a gate must make native replay fail closed. The V1 catalog alone does not supply
this law; this caller refuses a V1 genesis.

## Public sources and deployment boundary

[source-pins.json](source-pins.json) lists exact public source revisions, not
interchangeable binary hashes. Build from those checkouts using their native
locked tooling; preserve source/export provenance and the installed interpreter,
launcher, configuration and program closure. Do not silently substitute an older
binary because its command name matches.

Relevant native surfaces are:

| Component | Public entrypoint / contract |
| --- | --- |
| Maude | `docs/REVIEWED-LOCAL-COPY.md`; `maude.plan.reviewed_local_copy`; explicit validator/executor roles in `tools/build_reviewed_local_copy_validator.py` |
| Nightshift / Foreman | `runtime/`; `cycle run-config`, `recover-config`, `sync-ag`; Foreman's provider admission/prepare/record commands |
| NQ / Pulse | NQ's native configuration, `init`, watcher admission and local diagnostics; the pinned Pulse load-support integration and closed resolver launcher |
| AG | `ag-loopctl` V2 runtime profile, `record-review`, `permission-preflight`, `run`, `inspect`; `crates/ag-app/src/bin/ag-loopctl.rs` and `crates/ag-store/src/campaign.rs` |
| Docket | `docs/governed-runtime/local-execution-standing.md`, executor transport V1; `standing-grant`, `inspect`, `standing-snapshot` |
| Switchyard | Installed `switchyard-provider-runner` and `switchyard-review-verifier` commands; internal Python modules are not an SDK |
| AppServer | `codex-rs/rust-toolchain.toml`; build in `codex-rs` with `cargo build --locked -p codex-app-server --bin codex-app-server` |

Use a release AG binary (`cargo build --locked --release -p ag-app --bin
ag-loopctl`), since initialization and repeated verification consume real time.
Build Maude's validator and executor separately with the explicit fixed Python
interpreter and source revision; the validator package cannot execute work.

The AppServer source pin is public. Its deployment-owned CLI home, credential
reference and model/provider selection must be explicitly authorized and enrolled
in the backend and reviewer configuration. This example neither reads credential
values nor copies a home or unrelated configuration. Build provenance is not
authorization to contact a provider. Use the same selected route throughout; no
fallback, automatic approval response, recursive workers or semantic retries.

Native deployment setup remains explicit, not invented by `enroll_caller.py`:

- Prepare fresh Plan Core/AG/Nightshift/NQ/Pulse/Docket/executor coordinates and
  exclusive scratch. The exact scratch pathname is part of Maude's binding and
  work identity; changing it requires a newly compiled plan and review.
- Prepare the native V2 profile ports with Maude validator, review requirement/verifier,
  Nightshift, observation resolver, standing resolver, Docket and executor pins.
  Allocate the owner observation coordinate and prepare static ports, plan and
  genesis before taking fresh observations. Identity allocation is not evidence.
  The later sealer binds the actual posture/diagnostic to that same coordinate.
  Use a local-copy policy catalog with `delivery.not_required`, since no delivery
  is requested; retain all other forbidden-state checks. A catalog is not authority.
- Initialize a fresh NQ store and admit its watcher before the first supported
  local diagnostic. This example chooses exactly one initial acquisition, not a
  successor workflow. Do not append a second initial diagnostic or refresh an
  expired timestamp. Any successor must use its distinct native protocol.
- Produce actual Pulse support and retain its native receipt. Seal a Nightshift
  cycle request carrying the exact Maude binding and original observation time.
  Configure the existing observation resolver's TTL to 300000 ms and a compatible
  AG maximum. The original NQ clock and Pulse boot clock remain independent.
- Prepare exact native Foreman packet/admission/profile/policy/requirement inputs,
  reviewer enrollment, backend and source provenance. Review material must bind
  the actual plan and acceptance conditions, not private logs or a claimed verdict.

These are real native inputs, not substitutes for authentic stores or evidence.
The example intentionally does not infer their schemas from sample JSON, create
an accepted review, manufacture Pulse evidence or bypass local credential setup.
Native provisioning of a complete fresh public cohort is still a qualification
prerequisite; a passing caller-only test is not that prerequisite.

The selected NQ/Pulse pair is explicitly `d3089a9` / `d91b214`. Their exact profile
semantic identity, native read/query adapter files and launcher must be enrolled
together. An older NQ artifact or Pulse profile is not interchangeable with this
pair. Native pre-provider qualification must exercise this pair with the selected
shared Nightshift/AG cohort; source compatibility alone is insufficient.

### Prepare the native Maude handoff

The selected public Maude revision also contains reusable host setup helpers in
`qualification/synthetic_cache/`: `public-nq-host-bootstrap.py` writes the explicit
watcher configuration, `helpers/cache-host-bootstrap.py acquire` runs one actual
native diagnostic/export/qualification, and its `construct` command produces a
posture-only request from that artifact. Their CLI help lists exact arguments.
These host-only operations do not request cache work. Do not invoke their `cycle`
command here: the reviewed caller owns the single later Nightshift admission.

Either compile with the real posture request's `observation_id`, or explicitly
preallocate the owner coordinate in the static plan and use the sealer's named
allocation option below. Do not label allocation as an observed fact.
After native plan/owner preparation,
`prepare_pulse_support.py` from that same public directory can create fresh Pulse
enrollment and a closed launcher for this exact artifact/posture request. It
creates no measurement. The separately admitted Pulse `produce` and `ingest`
commands must retain their actual receipt before admission.

`prepare_plan.py` consumes a caller-selected native `maude.plan-document/v1`
PlanDocument and canonical `ReviewedLocalCopyInputsV1` bytes. Use the public Maude
constructors/serialization from the pinned source, not abbreviated sample JSON.
The inputs name the actual campaign, UUID occurrence, program, subject, scope,
observation, absolute scratch and selected UTF-8 bytes. This helper does not invent
these coordinates or claim its observation is current.

```sh
python3.12 prepare_plan.py --document /absolute/input/plan-document.json \
  --compiler-inputs /absolute/input/local-copy-inputs.json \
  --draft-id draft_REPLACE_WITH_FRESH_NATIVE_DRAFT_ID \
  --output /absolute/fresh/maude-plan
```

It creates a fresh native DraftStore, records the real Plan Core check, locks and
compiles through `compile_and_bind_reviewed_local_copy`, then independently
validates the stored result using the public read-only validator. Its output
includes `binding.json`, `compiled-handoff.json`, the exact native
`validator-config.json`, an `executor-config.json` with a fresh empty attempt-state
directory, and preparation records. It never creates `result.txt`.
An occupied output or scratch refuses; no previous plan store is copied.
The optional native preparation test runs when the pinned Maude package is
installed and is explicitly a local component fixture, not current NQ evidence.

### Assemble the native protected owner

`prepare_owner.py --help` lists explicit native file/port arguments. It combines
the Maude binding, deployment-selected native reviewer config, Nightshift config
and Docket root enrollment into a fresh V2 catalog, review requirement, Nightshift
config, AG enrollment and genesis. Issuer/key locators stay references; this helper
does not open key bytes. The Nightshift input must already select the exact
observation resolver and intended runtime-profile output pathname. A differing
previous shared-review requirement refuses rather than being overwritten.

Native setup then remains explicit:

```sh
"$AG" seal-runtime-profile-v2 \
  --enrollment /absolute/owner/runtime-profile-enrollment-v2.json \
  --output /absolute/deployment/runtime-profile.json
"$AG" verify-runtime-profile-v2 --runtime-profile /absolute/deployment/runtime-profile.json
"$AG" init-v2 --database /absolute/deployment/ag.sqlite \
  --genesis /absolute/owner/genesis-v1.json \
  --runtime-profile /absolute/deployment/runtime-profile.json
```

Use the exact same profile pathname selected in the Nightshift input. These
commands must be locally qualified on the installed public cohort before a paid
review; the helper's output status explicitly says seal/verify/init are required.
No execution input or accepted review is generated during owner preparation.

### Seal the observed admission request

```sh
python3.12 seal_admission.py --binding /absolute/fresh/maude-plan/binding.json \
  --posture-request /absolute/observation/posture-request.json \
  --output /absolute/deployment/cycle-request.json
```

The sealer checks the original request identity and exact compiled handoff,
requires the same work/occurrence, and attaches only native
`proposal` and `reviewed_plan_binding` fields before computing the new request
identity. By default it requires the same observation ID. With the explicit
`--use-plan-observation-identity` option, it assigns the statically preallocated
plan observation coordinate to the actual posture. That ID is a native owner
coordinate, not a replacement artifact identity. Neither mode changes
`evaluated_at`, policy, actual diagnostic bytes, support inputs or timestamps.
The complete runtime admission still belongs to native Nightshift/AG, not this
wire projection. A changed plan observation coordinate requires recompilation
and fresh preparation rather than substitution under an existing plan binding.

## Enroll and inspect the caller configuration

Create a JSON layout with schema `constellation.reviewed-local-copy-caller/v1`.
The object must contain exactly `schema`, `programs`, `inputs`, `paths`, `review`
and `operator`. All file locators are absolute and deployment-owned.

- `programs`: paths for `ag`, `nightshift`, `foreman`, `provider`,
  `review_verifier`, `docket`, `pulse`, `app_server`.
- `inputs`: paths for `binding`, `cycle_request`, `nightshift_config`,
  `runtime_profile`, `review_requirement`, `review_verifier_config`,
  `executor_config`, `backend`, `packet`, `admission`, `profile`, `policy`,
  `provider_requirement`, `source_provenance`, `pulse_query`, `pulse_retention`.
  Here `profile` is the Foreman provider profile, not the AG runtime profile.
- `paths`: native mutable locators `ag_database`, `foreman_database`,
  `switchyard_database`, `docket_state`, `ag_mandates`.
- `review`: fresh native `run_id`, `work_item`, `dispatch_id`, `adapter_process`,
  `app_server_session_identity`; `operator` is the admitted local operator identity.

`pulse_query` is the native closed resolver query. `pulse_retention` projects only
the retained native receipt's `evidence_id`, `received_at.clock_id` and
`expiry_tick_ms`; copy those values unchanged. It is a comparison input, not a
replacement for Pulse's signed evidence, receiver receipt or boot clock.

```sh
python3.12 enroll_caller.py --layout /absolute/deployment/layout.json \
  --output /absolute/deployment/caller.json
python3.12 reviewed_action.py --config /absolute/deployment/caller.json \
  --output /absolute/deployment/unused-output --preflight-only
```

Enrollment replaces each program/input locator with `{ "path": ..., "sha256":
"sha256:..." }`, checks the native cross-references and uses exclusive output
creation. It neither rewrites mismatching native pins nor invokes native programs.
`--preflight-only` is deliberately **local static checking**, not a full native
admission/currentness qualification. Help and malformed CLI arguments launch no
child. A failed enrollment output remains evidence; use a fresh output identity.

## Retain review before accepting or executing

The review transition has its own supported stop. It performs native admission,
provider preflight, at most one provider request, Foreman evidence derivation and
custody, and the independent native verifier. It retains the candidate
`record-review-input.json`, then stops:

```sh
python3.12 reviewed_action.py --config /absolute/deployment/caller.json \
  --output /absolute/deployment/review-001 --review-only
```

The terminal `constellation.review-only-result/v1` reports the verifier's actual
accepted or rejected result and zero grants, spends, Docket attempts, executor
calls, and effects. Even an accepted result is only a candidate for later human
or operator acceptance. This mode cannot record the review into AG, create a
standing mandate, create a Docket grant, invoke the finite runner, or copy a file.
Response loss remains attached to this one original provider request; inspect and
reconcile its retained owner rather than repeating it.

## Admit one execution, then reconcile the original

Only after operator review of the installed closure, currentness budget, storage
reserve, provider allowance and bounded physical operation should a durable
manager invoke:

```sh
python3.12 reviewed_action.py --config /absolute/deployment/caller.json \
  --output /absolute/deployment/attempt-001 --execute
```

Use the deployment's durable service manager, not an interactive background job.
The caller requires its `INVOCATION_ID`, takes an owner lock and writes create-once
started/finished/checkpoint records. A suitable manager envelope is one invocation,
600 seconds, no restart, bounded tasks/memory and a reserved records directory.
Persist unit identity, exact command/source/config hashes, resource bounds and
inspection commands before launch. Configure writable temporary/state directories
and reserve storage across all owners, not just this caller's files.

Immediately before the paid call, both original NQ observation and Pulse support
must retain at least **230000 ms**. The worker request is exactly 120 seconds /
32768 output bytes; local provider preflight has 30 seconds and provider collection
150 seconds. Review lifetime is at most 300000 ms from the actual provider end,
not projection time. The permission and finite-run deadlines can only shorten it.
Slow preparation or a refused currentness gate requires explicit new preparation,
not a timestamp edit or automatic new review.

On response loss or supervisor loss, inspect the original manager and native
stores first. A missing finished record establishes an unresolved stage, not
permission to repeat it. `--inspect` is read-only native inspection. Only if the
original finite run was actually invoked, explicit recovery can call:

```sh
python3.12 reviewed_action.py --config /absolute/deployment/caller.json \
  --output /absolute/deployment/recovery-001 \
  --recover-run /absolute/deployment/attempt-001
```

Recovery verifies the original run/config bytes, preserves the original deadline,
and invokes only inspect → same native `ag run` input → inspect. It cannot create
a review, standing mandate or grant. AG's durable state decides whether to settle,
wait or refuse. Before `finite-run.started.json`, this recovery mode refuses; use
the existing native owner's inspection/reconciliation protocol, not a rerun of
the complete caller. In particular, unknown provider execution never triggers a
second request.

## Qualification boundaries

### Isolated public Python closure

Before an installed Switchyard component check, use a fresh durable manager and
the exact source pins in `source-pins.json`. The manager-owned,
caller-configured `run_public_python_closure_001.sh` wrapper is deliberately a bounded
pre-provider preparation: it checks the fresh owner, storage reserve and clean
public source revisions; downloads only its fixed binary wheel set once with no
retries; writes the resulting hash lock; and then builds and installs offline
with no system site packages. Its installed checks are `pip check`, interpreter
origin guards, and the two Switchyard CLI help paths. It creates no reviewer
request, grant, or local-copy effect. A manager loss is reconciled from its
checkpoint, terminal record, and the original owner root; never replace the
wheel lock or reinstall that occurrence. Supply explicit absolute `--unit`,
`--owner`, `--records`, `--switchyard`, and `--maude` coordinates from the
caller-owned durable-manager configuration; the distributed wrapper has no
campaign-local pathname defaults.

Run the public-only controls from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3.12 -B -m unittest discover \
  -s tools -p test_reviewed_local_copy_example.py -v
```

Schedule tests use clearly labeled substitution frames. Other tests execute only
harmless local JSON-producing programs. Required real installed-cohort cases
remain: accepted exact review and copy; rejected/stale/mismatched review without
permission; durable protected-gate replay refusal; admission-response loss with
native status-only recovery; one copy under duplicate/success-response-loss
reconciliation; and interruption after creation before the durable success record.

`drop_success_response.py` supports the **retained-success response-loss** case.
Enroll a fixed launcher supplying `--executor`, `--sha256`, `--records`, followed
by Docket's operation/config arguments. Its program hash differs from the normal
executor and must be enrolled before the test. It forwards `plan-id`/`reconcile`,
runs `execute` at most once, retains native stdout and deliberately returns 74
without forwarding that completed response. Docket/AG must reconcile the same
attempt and receipt; no new grant, issuance or copy is allowed.

This wrapper cannot establish interruption **before** the success journal commit.
That distinct qualification needs an explicit deterministic cut at the executor's
post-file-fsync/pre-success-record boundary. A reserved attempt then reconciles
as indeterminate and never repeats the copy. Do not relabel terminal replay or
post-success response loss as this earlier interruption case.
