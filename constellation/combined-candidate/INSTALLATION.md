# Install the combined candidate

Use fresh Ubuntu 22.04 amd64 with systemd 249+, Python 3.10 standard library, sudo/root, coreutils, util-linux and OpenSSL. No checkout, compiler or developer directory is required. Have the declared dependencies available before offline installation. Verify the candidate identity against the owner-approved download record, then run from its extracted directory:

```sh
sha256sum --check SHA256SUMS
sudo dpkg --install packages/*.deb
sudo dpkg --audit
```

PACKAGES.json records the eleven exact packages and dependency declarations. RUNTIME-IDENTITIES.json records installed runtime bytes and source revisions. NQ is 0.2.5 for this combined candidate; unchanged spine components retain their accepted package bytes. Package installation does not create effect grants, provider enrollment or a working cohort. Workbench remains inactive until configuration exists and the owner explicitly enables it.

## Prepared local operator exercise

The supplied enrollment helper is limited to a **fresh, explicitly admitted disposable private VM**. It creates one harmless `sleep infinity` unit, a native NQ unit watcher, one exact governed Start capability and a one-use two-hour grant. This is action enrollment, not an observation-only mode. It refuses existing enrollment; do not delete refusal records or reapply after interruption. A partial application requires owner reconciliation.

Do not run it on an existing reference/production installation. Reference deterministic remediation and the local Workbench exercise share executor bindings and an ops-store pathname. They require separate fresh installation occurrences. Keep guest port 8081 private: its native reader/action API binds all guest interfaces. No network PagerDuty route or provider credential is configured by this exercise.

After verification and the owner's explicit choice of this bounded exercise, from the candidate directory:

```sh
sudo python3 scripts/enroll-local-fixture.py --candidate "$PWD" --admit-disposable-unit-start
```

Wait for current native observation. Open **http://127.0.0.1:18861/operator.html** in the VM browser, or use an explicitly admitted loopback-only VM port forward. The plan is at `/plan.html`. A process being active is insufficient: inspect source identity, boot, native judgment and gaps. The exercise observes systemd unit state; **HTTP/application health is not instrumented**.

## Reference operational spine

For the existing filesystem profile, observation-cycle adapter, attention evaluator and separately admitted deterministic canary, use the bundled reference documentation. Its accepted install/day-two standing is retained. Replace its package table with this candidate's PACKAGES.json; it is not the Workbench fixture enrollment. Do not enable two owners of the same watcher/store. V1 is the reference/default remediation policy. V2 requires separate owner-approved budget, provider custody and capability activation.
