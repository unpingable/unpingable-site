# Install the combined candidate

Obtain the archive and its adjacent SHA256 file from the owner-approved release page. Do not use the historical alpha source recipes. From the download directory, verify and extract the exact neutral candidate before following the commands below; the release page supplies its exact archive basename.

```sh
sha256sum --check constellation-release-hygiene-candidate-20261005.tar.gz.sha256
tar --extract --gzip --file constellation-release-hygiene-candidate-20261005.tar.gz
cd constellation-release-hygiene-candidate-20261005
```

Use fresh Ubuntu 22.04 amd64 with systemd 249+, Python 3.10 standard library, sudo/root, coreutils, util-linux and OpenSSL. No checkout, compiler or developer directory is required. For an online fresh machine, install `python3`, `adduser`, `systemd`, `util-linux`, `openssl`, `libc6`, `libgcc-s1`, `sudo`, `coreutils`, `curl` and `ca-certificates` from Ubuntu22.04 before installing the verified local packages.

```sh
sudo apt-get update
sudo apt-get install python3 adduser systemd util-linux openssl libc6 libgcc-s1 sudo coreutils curl ca-certificates
```

For offline installation, supply the corresponding Ubuntu packages separately. The Constellation archive does not redistribute an operating system. Verify the candidate identity against the owner-approved download record, then run from its extracted directory:

```sh
sha256sum --check SHA256SUMS
sudo dpkg --install packages/*.deb
sudo dpkg --audit
sha256sum --check installed-SHA256SUMS
```

PACKAGES.json records the eleven exact packages and dependency declarations. RUNTIME-IDENTITIES.json records installed runtime bytes and source revisions. NQ is 0.2.5 for this combined candidate; native spine executables retain their accepted bytes; corrected package metadata, dependencies and operator docs have new package revisions. Package installation does not create effect grants, provider enrollment or a working cohort. Workbench remains inactive until configuration exists and the owner explicitly enables it.

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
