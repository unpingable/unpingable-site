# Reviewed local-copy public publication scope

This package is public candidate material and local component qualification
tooling. It is not a provider request, reviewer verdict, standing grant, or a
released deployment.

## Included product material

- The closed caller wiring and input validators in this directory.
- The cohort setup driver and its helpers in `setup/`. The driver accepts only
  the `reviewed-local-copy/v1` cohort `alpha-exit-rc` that it pins, and it runs
  under `/usr/bin/python3.11 -I -S` on Debian 12. The component pins are the
  cohort manifest's, listed in the site's `README.md` for this directory. They
  are not the pins in `source-pins.json`.
- `README.md` is published with the site but is not in the cohort-kit tarball:
  it states the published digests of the kit and the manifest, which a file
  inside the kit cannot do.
- Retired pre-cohort material, kept for its history and not part of the cohort
  path:
  - `source-pins.json`, the pre-cohort source revisions, including Maude
    `c1fce17a529c4f73d23012b22b7f1a2a3ee666a7`;
  - `prepare_public_python_closure.py`, its durable manager wrapper and
    `requirements-public.lock`. The lock has 17 binary-wheel entries and is the
    hash-checked closure for Switchyard
    `1c82e719cf358728d0262ae11138fb13fefe0cae`. Both scripts are marked
    retired and require an explicit `--python`; their earlier `python3.12`
    default is gone.
- Deterministic local controls, including the response-withheld transport
  fixture.

The evidence verifier `setup/verify_cohort_evidence.py` and its tests are
product material: they ship in the cohort-kit tarball. The loopback review
fixture is qualification-only tooling and is not part of this directory or of
the cohort-kit tarball.

Do not publish deployment-owned mutable stores, native observation records,
manager logs, credential references, private keys, review outputs, or a copy
result. Those are occurrence evidence, not product inputs.

## Static full-chain review contract

The next review occurrence must bind fresh values for run ID, work item,
dispatch ID, adapter process, AppServer session identity, Plan Core occurrence,
NQ observation, Pulse receipt/query, Foreman packet/admission/profile/policy,
and the enrolled program hashes. This package supplies only the fixed contract:

| Boundary | Exact static contract |
| --- | --- |
| Plan | `maude.reviewed-local-copy/v1` binding; selected bytes limited to 64 KiB; destination exactly `result.txt` |
| Admission | Nightshift `cycle run-config` with a V2 AG profile and the sealed exact binding |
| Review | Foreman bounded 120-second, 32768-byte request; Switchyard installed `provider-runner` and `review-verifier`; no semantic retry or approval response |
| Permission | AG V2 `shared_admission` rechecks the stored binding and accepted review before protected decision and consumption |
| Effect | Docket standing grant is bounded by the original review expiry; Maude executor creates the exclusive result once |
| Closure | The installed Switchyard artifact must report `installed_closure_matches_provenance: true` and canonical revision `299609c`; every other executable must report its pinned version and commit |

No placeholder in this static material may be supplied to a review command.
The occurrence owner must prepare and seal the complete fresh packet first;
the root review owner alone admits the later review.

## Physical uncertainty scope

`drop_success_response.py` is a retained-success response-loss fixture only:
it runs an already enrolled executor once, retains its local collector record,
withholds the completed response, and requires same-attempt native
reconciliation. It is not a substitution for the earlier interruption between
file fsync and durable success journal commit. Maude `c1fce17` now supplies a
separately built and pinned `executor-interruption-qualification` artifact for
that deterministic cut. The artifact exits 75 only after result and directory
fsync and before the success record; its read-only reconciliation remains
indeterminate and it must never repeat the copy. These component checks do not
establish a reviewed AG-owned occurrence. A bounded Docket/Maude qualification
did exercise the measured program with one real Docket-local grant, one
indeterminate custody attempt and same-attempt reconciliation without another
execution. Its ephemeral signer was transport qualification, not AG judgment;
the reviewed shared occurrence and public-only reproduction remain required.
