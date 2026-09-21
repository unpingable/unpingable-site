# Reviewed local-copy public publication scope

This package is public candidate material and local component qualification
tooling. It is not a provider request, reviewer verdict, standing grant, or a
released deployment.

## Included product material

- The closed caller wiring and input validators in this directory.
- `source-pins.json`, which fixes the public source cohort.
- `prepare_public_python_closure.py`, its durable manager wrapper, and
  `requirements-public.lock`. The lock has 17 binary-wheel entries and is the
  hash-checked closure for Switchyard `1c82e719cf358728d0262ae11138fb13fefe0cae`.
- The public Maude source pin `0d5b6c91102b1088818d0493c687f9f23db7684e`.
- Deterministic local controls, including the response-withheld transport
  fixture.

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
| Closure | `requirements-public.lock` must be installed offline with `--require-hashes`, without system site packages, followed by `pip check` and the two installed help paths |

No placeholder in this static material may be supplied to a review command.
The occurrence owner must prepare and seal the complete fresh packet first;
the root review owner alone admits the later review.

## Physical uncertainty scope

`drop_success_response.py` is a retained-success response-loss fixture only:
it runs an already enrolled executor once, retains its local collector record,
withholds the completed response, and requires same-attempt native
reconciliation. It is not a substitution for the earlier interruption between
file fsync and durable success journal commit. Maude `d532efd` now supplies a
separately built and pinned `executor-interruption-qualification` artifact for
that deterministic cut. The artifact exits 75 only after result and directory
fsync and before the success record; its read-only reconciliation remains
indeterminate and it must never repeat the copy. These component checks do not
establish the still-required Docket-owned composed occurrence.
