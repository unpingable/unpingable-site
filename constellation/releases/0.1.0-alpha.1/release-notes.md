# Constellation integration 0.1.0-alpha.1

Read a local Maude plan from your own caller, inspect its recorded revision,
handle an unavailable answer, and resume inspection without recreating the plan.
No account, provider key, background service or effect executor is required.

Start with the [Plan consultation guide](https://unpingable.com/constellation/releases/0.1.0-alpha.1/guide.html).
It includes setup from public source, the bounded CLI caller, expected output,
refusal and recovery cases, lifecycle instructions and the support route.
The [manifest](https://unpingable.com/constellation/releases/0.1.0-alpha.1/manifest.json)
pins Maude, the example kit, schemas, environment and hashed public dependencies.

## Supported scope

- Profile: `maude-plan-consultation/v1`; required component: Maude.
- Tested: Linux x86-64, Ubuntu 24.04.4, CPython 3.12.3, pip 24.0, SQLite 3.45.1.
- Real caller-created disposable plan and actual read-only owner inspection;
  no substituted owner, synthetic standing or model provider in this profile.
- Public clean reproduction and an independent public-only newcomer run passed
  creation, read, restart, refusal, unavailable-program handling and same-store
  recovery. Component boundary tests are separate from those real runs.

## Material limitations

Keep writers quiescent: inspection is not a transaction-wide snapshot. A recorded
revision is not external truth, legitimate reliance, permission or execution.
Parse JSON `availability`; an unavailable answer also exits zero. No automatic
retry occurs. The CLI does not provide typed absence. SQLite read-only mode can
involve sidecars. Partial-clone Git operations can require network even after
installation; the installed reader and local pathname inspection do not.

Backup restoration, migration, rollback and other platforms are not qualified.
AG/Docket governed actions, the connected cache workflow, model-assisted
authoring, general ECAD/design-flow and federation are outside this release.
Those separate campaign deliverables are not waived by this profile's release.

Component versions remain independent: Maude remains version 2.4.0. This alpha
identifies a tested composition while interfaces may change; it is not a claim
of family-wide maturity. Support is best effort without a guaranteed response
time. See the [release policy](https://unpingable.com/constellation/release-policy.html)
for immutable snapshots and separate documentation corrections.
