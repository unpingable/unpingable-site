# Install the prepared operational spine

This exact neutral prework cohort is bound by PACKAGES.json, installed-SHA256SUMS and QUALIFICATION-SUMMARY.json. The retained fresh-origin Ubuntu lifecycle and composed package/canary checks passed within that recorded scope. Workbench and human qualification remain later gates. Live enrollment still requires the owner’s explicit installation/authority choice.

## Requirements and artifacts

Use a fresh Ubuntu 22.04 amd64 system with systemd, root/sudo, Python 3.10 with its standard `sqlite3` module and the ordinary command-line tools used by [the day-two runbook](DAY-TWO-RUNBOOK.md). No Rust, compiler or source checkout is required. Have dependencies available locally before an offline installation. The selected standalone AG executor targets systemd 249 or later; the larger AG daemon/credential-unit package is a different installation and is not selected here.

Obtain the frozen release directory, `SHA256SUMS`, exact package/executable identity manifest, source-free documentation, `site-adapter/`, `scripts/enroll-canary-observation.sh` and `scripts/enroll-remediation.py` from the release page. Confirm the release page/manifest identity independently; a checksum downloaded with an untrusted file establishes correspondence only. Use SOURCE.json in the extracted bundle for its documentation commit and SHA256SUMS for exact bytes. Workbench/combined-human fields in RELEASE-DRAFT.md deliberately remain future inputs.

| Package | Prepared version | Purpose |
|---|---|---|
| nq-ng | 0.2.4 | NQ CLI/daemon/helpers |
| constellation-host-posture | 0.1.0+spine.20261004.1 | filesystem-capacity observation profile and status tools |
| constellation-nightshift | 0.1.0+spine.20261004.1 | observation-cycle runtime |
| constellation-attention | 0.1.0+spine.20261004.1 | attention evaluator |
| agent-governor-ng-operator-tools | 0.1.0+spine.20261004.1 | AG inspection, enrollment and loop tools |
| agent-governor-ng-systemd-executor | 0.1.0+spine.20261004.1 | selected target-local Systemd executor |
| constellation-docket | 0.1.0+spine.20261004.1 | custody and bounded standing resolvers |
| linear-accountant-inference | 0.1.0+spine.20261004.1 | accounting CLI; no stock enrolled |
| constellation-remediation | 0.1.0+spine.20261004.1 | deterministic consumer and unit observation resolver |

`pulse-m2-support` remains source material for a separate integration path and is not selected by this reference package manifest. Foreman is likewise outside the reference installed closure.

## Verify and install the selected packages

From the frozen release directory, verify the checksum manifest before installation:

```sh
sha256sum --check SHA256SUMS
```

Every required artifact must be named and pass. Missing artifacts, mismatched digests or unfilled manifest fields stop installation. Use the exact manifest filenames, for example:

```sh
sudo dpkg --install   nq-ng_0.2.4_amd64.deb   constellation-host-posture_0.1.0+spine.20261004.1_amd64.deb   constellation-nightshift_0.1.0+spine.20261004.1_amd64.deb   constellation-attention_0.1.0+spine.20261004.1_amd64.deb   agent-governor-ng-operator-tools_0.1.0+spine.20261004.1_amd64.deb   agent-governor-ng-systemd-executor_0.1.0+spine.20261004.1_amd64.deb   constellation-docket_0.1.0+spine.20261004.1_amd64.deb   linear-accountant-inference_0.1.0+spine.20261004.1_amd64.deb   constellation-remediation_0.1.0+spine.20261004.1_amd64.deb
sudo systemctl daemon-reload
```

Do not install a substitute system `nq` package over `/usr/bin/nq`; NQ-ng's declared conflict must be resolved visibly by the owner. Inspect the installed set and compare it to the exact manifest:

```sh
dpkg-query --show --showformat='${Package} ${Version} ${Architecture}\n'   nq-ng constellation-host-posture constellation-nightshift constellation-attention   agent-governor-ng-operator-tools agent-governor-ng-systemd-executor   constellation-docket linear-accountant-inference constellation-remediation
nq --version
nq --build-info
constellation-host-posture --build-info
constellation-attention --build-info
nightshift --version
ag-loopctl --version
la_inference version
```

Run `sha256sum --check installed-SHA256SUMS` from the bundle root to check all 22 installed native executables, including `ag-effectd` under `/usr/libexec/agent-governor-ng/`. A package version or crate version alone does not identify every build. Docket has no source-defined `--version` command; use its package and executable identity.

The packages create documented service accounts/directories and install disabled units or inert tools. They do not write live configuration, initialize NQ/AG/Docket books, admit helpers, install grants or start the operational loops. LA creates its root-owned default directory only. Confirm `nqd.service`, host-posture, attention and remediation are inactive and their timers are not enabled before enrollment. A pre-existing active installation is outside this fresh-system procedure; preserve its state and use the day-two workflow instead.

## Enroll the observation profile first

For the current fresh installation, follow [DAY-TWO-RUNBOOK.md, section 2](DAY-TWO-RUNBOOK.md#2-initial-enrollment), with the already installed NQ 0.2.4 cohort. Do not reinstall its section-1 NQ 0.2.3 baseline. Use that document's sandboxed `nq-helper-run` wrapper and exact configuration/admission/ownership procedure, not an unsandboxed helper shortcut.

Record the actual machine/filesystem identity, NQ store genesis, first artifact, admitted profile and host-posture policy generation. Choose the unique local issuance shown in the runbook. Its source, build and qualification-result identities remain pinned to this exact package cohort; the issuance label grants no effect authority. Stop if the host-posture sample still contains `REPLACE` fields. The required order is NQ test/admit/acquire, host-posture enroll, prepare-qualification, preflight, then start. Qualification-input records must be included by this exact package cohort; do not borrow an unrelated old qualification result.

The host-posture retention example (`maximum_occurrences = 2048` at 60 seconds, about 34 hours) is a qualification default. A long-running installation needs an owner-approved retention/rotation envelope. The runner owns acquisition in this profile; `nqd.service` stays inactive. Do not start two owners of the same watcher/store.

Install the included Nightshift site adapter exactly as runbook section 2.3 describes, with a fixed `SITE_EPOCH` and the current artifact's `producer.node_id` as `NIGHTSHIFT_NQ_SOURCE_ID`. The adapter uses a pinned internal NQ store-table read; it is deployment glue, not a supported general API. Filesystem-capacity support is unknown by construction: Nightshift's `Incomplete (support_not_current)` is expected and must remain visible.

For attention, use runbook section 2.4's local inbox and `network_enabled = false`. The notice directory is `nq:nq` mode 0711; each delivery file is 0600. Keep the page route omitted for the observation-only profile. Check configuration, run one explicit evaluator pass and inspect its report/state and delivery outcome before enabling any timer. Exit 3 means not-current input, refused delivery or dropped trigger; it does not mean healthy. The day-two exercise intentionally leaves the evaluator timer disabled.

## Optional bounded canary enrollment

Observation enrollment creates no effect authority. The supplied `scripts/enroll-remediation.py` is a root-run reference enrollment helper, not a read-only inspector or an idempotent repair tool. It writes live files and generates issuer material; inspect the intended layer and preserve any existing enrollment before invoking it. Never execute it against a populated system to make a refusal disappear.

From the extracted bundle root, on a separately admitted fresh disposable canary host, first enroll its observation layer with the supplied helper:

```sh
sudo bash scripts/enroll-canary-observation.sh
```

This fresh-only observation helper supplies the harmless canary, separate ops-store watcher admission/collection and local attention profile. It grants no effect, supplies no model credential and keeps external notification delivery disabled. It is separate from the filesystem-capacity runner/store above. Its exact frozen implementation is included in the bundle checksum manifest; QUALIFICATION-SUMMARY.json identifies the source-free exercise and finite one-use test grant. The filesystem profile and canary attention profile were selected separately in qualification.

If the owner explicitly chooses bounded action enrollment after useful current canary observation is established, run the separate layers:

```sh
sudo python3 scripts/enroll-remediation.py ag-docket
sudo python3 scripts/enroll-remediation.py grant reference 3 24
sudo python3 scripts/enroll-remediation.py consumer-config
```

`grant reference 3 24` means a new named grant, maximum three uses, 24-hour lifetime and a new use journal. It is an owner decision, not a recommended universal production budget. The reference helper targets one `attention-canary.service`, `svc-attention-canary`, current machine identity and reference site, with a 30-second observation schedule and 90-second resolver window; the independently enforced NQ testimony and AG currentness rules remain unchanged. `ag-docket` pins the inactive/failed start plans, distinct active postcondition basis, resolver identities and runtime profile. Save only its public `IDENT` records in ordinary evidence; never export private issuer material.

Keep the consumer timer disabled until the separate observation helper, action enrollment and their exact current checks succeed. Do not invent an ops daemon unit, repoint the filesystem observation runner or reuse a different store's admission. A disabled named page route neither supplies a routing key nor authorizes network delivery.

Validate the exact existing enrollment with:

```sh
sudo constellation-remediation-consumer --config /etc/constellation-remediation/consumer.toml --check-config
sudo ag-loopctl verify-runtime-profile --runtime-profile /etc/constellation-remediation/runtime-profile.json
```

Only after these checks and the owner's explicit activation choice:

```sh
sudo systemctl enable --now constellation-remediation-consumer.timer
```

This enables the already enrolled deterministic canary workflow. Inspect current observation, local attention and the consumer journal before inducing any bounded canary condition. A failed current check blocks activation; do not enable the timer as a way to fix enrollment.

No `[model]` enrollment, provider key or model-decider drop-in is required for deterministic v1. Optional v2 is a separate owner action covered by its installed documentation; do not enable it to complete this installation.

Workbench remains a pending integration. Its artifact, address, access procedure and release identity must be supplied by the combined release; component CLI installation is not proof that Workbench is installed or healthy.
