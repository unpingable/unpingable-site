# Try Constellation on one unit

## What this is

Constellation observes one systemd unit on a private Ubuntu VM and checks whether the observation is fresh and from the current boot. If current evidence shows the unit inactive or failed, explicit command-line steps can request one pre-enrolled Start. AG checks permission; Docket records the execution and settlement. AG's `completed` state additionally requires a fresh observation of the unit active again; it does not by itself mean the governed Start succeeded, which is the settlement outcome Workbench prints beside the state ([known issues](KNOWN-ISSUES.md)). **Unit active is not application or HTTP health.** Workbench displays these records in read-only web pages.

This is a prepared candidate: not approved, not published, not distributed and not Beta Candidate 1. The human newcomer study is prepared and has not been run. Use it only for a **supervised session of up to four hours on a disposable VM, ended the same day**; nothing here claims unattended operation. The remediation consumer is installed disabled, nothing in these guides enables it, and every Start is requested step by step by an operator. Installing packages alone enables no exercise; enrollment starts its services and creates the limited action grant.

## Start here

Follow [Installation: primary nginx trial](INSTALLATION.md#primary-nginx-trial), then [Operations](OPERATIONS.md) and [ending the session](DAY-TWO-RUNBOOK.md#end-the-session). The `try/` script installs and observes Ubuntu's `nginx.service`; nginx HTTP is not instrumented. It also confines the native API to loopback. A failed or interrupted enrollment must not be rerun on the same VM.

The [manual sleep-unit path](INSTALLATION.md#manual-alternative-and-human-study) is an alternative for the separately prepared [human study](HUMAN-OPERABILITY.md). Choose one path per fresh VM. The paths share enrollment/store locations and cannot be combined. Read [Known issues](KNOWN-ISSUES.md) before either path.

## Artifact identity and NQ limits

This candidate is `constellation-canonical-candidate-20261010` (archive `constellation-canonical-candidate-20261010.tar.gz`). Eight of its eleven packages are byte-identical to the earlier candidates'. The other three are `nq-ng 0.2.5+qualification.retention.20261010.2`, NQ with bounded retention (issue #27 remains open), its bytes unchanged from the bounded-retention qualification build; `constellation-remediation 0.1.0+release.20261010.1`, native binaries unchanged, with resource limits added to its NQ maintenance wrapper; and `constellation-workbench 0.1.0+release.20261010.1` (the package-only upgrade fixture is `.2`, with an identical runtime payload).

NQ provides dependency-aware expiry, a persisted capacity envelope and controlled capacity refusal. Permanent identity commitments and protected dependencies still consume a finite envelope. On this trial the store grows at a planning figure of about 27 MB per hour and, by arithmetic from that figure, reaches its 1 GiB per-file ceiling after roughly 40 hours, before anything is old enough to expire, so the seven-day retention target is never reached here. [Known issues](KNOWN-ISSUES.md) describes what happens at the ceiling.

The archive SHA256 is on the release record beside the archive (`ARTIFACT.json` and the `.sha256` file); this guide does not embed its own archive hash. Qualification of this exact archive is recorded in `QUALIFICATION.json` beside the archive, not in these documents. Component qualification carried from predecessors does not by itself establish this assembled candidate's integration or human usability.

Predecessor history: two earlier archives are not this candidate. `constellation-successor-candidate-20261008.tar.gz`, SHA256 `0bdea16eea36a8e6b5dd2ccf0b511c8812008d6a1ec5f6ff811c6726ccc69070`, is retired as a release candidate; it contains NQ 0.2.5 without retention. A 10 October supervised archive (SHA256 beginning `af17c59b`) is superseded by this candidate. Do not install this candidate's packages over the 8 October candidate: the `nq-ng` version here sorts below that candidate's, and its store would need an `nq admin upgrade` that this candidate neither documents nor qualifies.

Adjacent checksums establish byte consistency, not independent release authentication. No download is available and no authentication channel is supplied; obtain the exact artifact identity through the release approver before executing anything.

## Reference

[Support](SUPPORT.md), [glossary](GLOSSARY.md), [integration contract](WORKBENCH-INTEGRATION-CONTRACT.md) and the bundled `reference/` documents explain the components and advanced paths. The `reference/` documents describe a different, historical installation path that initialises NQ outside the bounded wrapper and has not been run with this NQ package; do not use that path, or `scripts/enroll-canary-observation.sh`, with this candidate. Operational EDA is the developing composition and analysis approach behind Workbench; historical `operational_ecad` command/schema identifiers remain. Optional model-backed remediation and Kubernetes observation are separate from this first trial.

Licensing: [distribution](DISTRIBUTION.md), [license](LICENSE), [notices](NOTICE), [third-party inventory](THIRD-PARTY-LICENSES.md). Redistribute native packages with the complete notices.
