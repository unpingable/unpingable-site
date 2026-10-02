# Fresh two-VM M2 showing

Use two fresh local Ubuntu 22.04 amd64 VMs, each with Python3, OpenSSL, systemd and ordinary Debian base packages. Give the controller private network access to target port18080. The operator must have sudo on both. No provider credentials, Internet runtime dependency or development checkout is needed.

Verify the archive sidecar hash, extract it on both VMs and enter `candidate`. Run `./inspect-candidate.sh` then `sudo ./install.sh` on each. Installation is inert: no authority, enrollment or effect is installed. Keep all files at one root-controlled absolute path.

On the target:

```sh
sudo ./m2.py prepare-target --run-id UNIQUE_FRESH_M2_ID
sudo ./m2.py run-target
```

Preparation installs only the fixed inactive/disabled `constellation-beta-http-fixture.service`, builds exact subject/configuration from installed VM/unit bytes and generates fresh VM-local issuer custody. Run performs fresh NQ baseline and Pulse-owned fresh corroborating acquisition; Nightshift consumes its normal qualified-support port and produces canonical observation/proposal custody. AG validates observation/standing, spends one exact issuance, and Docket consumes the enrolled operator-owned execution-standing projection before dispatching the signed envelope to the current Systemd executor. The only effect is starting that non-production unit. Docket must settle success and a new NQ unit observation must independently establish loaded/active/running/disabled.

Copy only `/var/lib/constellation-m2/subject.json` from target to controller (public subject). On the controller:

```sh
sudo ./m2.py prepare-controller --subject /ABSOLUTE/subject.json --endpoint http://TARGET_PRIVATE_IPV4:18080/healthz
sudo ./m2.py observe-controller
```

Controller NQ must establish status200, exact shipped body hash and no redirect. Pulse separately acquires a fresh HTTP sample and emits Current exact-proposition support. Target and controller results are required separately. Receipts do not substitute for either postcondition; no aggregate health, causation or exactly-once claim is made.

## Inspection and recovery

Read `/var/lib/constellation-m2/target-result.json` and controller `controller-result.json`; command stdout/stderr/exit records, exact NQ artifacts and Pulse receipts are adjacent. Capture OS/kernel/machine/boot identities, installed package versions and exact candidate hashes. `nightshift --store /var/lib/constellation-m2/nightshift.sqlite --help` identifies the read-only canonical inspection surface. Docket's retained inspection is in `docket-inspection.stdout`.

Never repeat run-target on an existing occurrence. On interruption, inspect the original durable VM producer and AG spend/Docket attempt before changing authority. Reconcile the same captured executor/configuration; do not redispatch an uncertain attempt. Preserve failed occurrences; changed product generations require fresh VMs/occurrences. Pulse resolve never refreshes its exclusive60s boot-bound receipt, and an interrupted acquisition claim remains spent.

## Authority and limits

Pulse owns only these fixed M2 local Jammy support families. Root-controlled exact NQ binary/config, machine/boot/subject/profile/question/baseline bytes and immutable receipt bind the evidence. Fresh acquisition is evidence; the explicit Pulse support rule earns Current. NQ UTC quality remains unqualified. This proves neither NTP accuracy nor general cross-VM time comparison. Same-root/OS/NQ correctness and exclusive local deployment ownership are premises; no independent failure-domain or remote-attestation claim is made.

Docket consumes/enforces the owner-controlled principal/currentness/revocation projection; AG owns one-use effect authority. Pulse/NQ do not grant execution authority. No external model/provider, Switchyard invocation, notifications, M3 application work, VM-executor research or broad release qualification is included. Retired agent_gov/nq-classic/WLP and predecessor/campaign implementations remain excluded.

Candidate preparation is not Alpha2. Alpha2 requires both successful fresh VM paths and published exact source/package/candidate/result identities.

## Source-labelled read view

After the target occurrence, start the installed read-only Phosphor surface on target:

```sh
sudo systemd-run --unit=constellation-m2-readview /usr/bin/ag-operator-ui --campaign-root /var/lib/constellation-m2/campaigns --ag-loopctl /usr/bin/ag-loopctl --nightshift-bin /usr/bin/nightshift --nightshift-store /var/lib/constellation-m2/nightshift.sqlite --docket-bin /usr/bin/docket --docket-state /var/lib/constellation-m2/docket --bind 127.0.0.1:8417
```

Use an exact pinned SSH tunnel for localhost8417 or inspect locally. `/` and `/api/v1/campaigns` give the index; use its exact locator token for `/campaign/TOKEN` and `/api/v1/campaigns/TOKEN`. UI HTTP responsiveness is liveness, not a governed-effect/postcondition result. AG/Nightshift/Docket sections remain source-labelled; optional unavailable sources do not become positive facts. Fresh NQ unit/HTTP postconditions remain separate exact result records. Stop only this read-only unit when inspection ends.

[Alpha2 result](ALPHA2.md) records the accepted exact candidate. A future run uses a fresh identity and obeys the current owner admission; acceptance does not authorize production or unrelated scenarios.
