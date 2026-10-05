# Day-two operation and recovery

Before a change, record exact package/runtime identities, current evidence, boot identity, enrollment files and owner-managed rollback/state custody. Keep credentials and issuer/token material separately protected; ordinary evidence/download bundles contain none. Stop the relevant writer/collector before changing its package/store. Do not run two generations against one store.

## Restart and reboot

On the prepared disposable Workbench exercise, restart the packaged Workbench and native reader normally. A browser refresh never renews evidence. Enabled collectors recover after reboot; the native reader must supply current **same-boot** observation before any claim or action. Never rerun the exclusive enrollment helper to repair restart or reboot. Existing apply claims and attempt history survive. Native stale/unsupported states are legitimate while collection has not recovered.

```sh
sudo systemctl restart constellation-workbench.service constellation-live-reader.service
systemctl status constellation-workbench.service nqd-ops.service constellation-live-reader.service
```

On collector failure, keep the unit/effect state intact and inspect its service/journal and native refusal. Start the existing `nqd-ops.service` and require fresh native evidence. The human negative-control fixture stops collection until the published freshness deadline has passed; it changes neither clocks nor tolerances. Restarting collection is an operator action, not a completed governed repair.

## Upgrade and rollback boundary

Use the exact current packages under `packages/` and the supplied Workbench package-only upgrade under `upgrade/`, with their checksum manifests. The accepted historical nine-package NQ 0.2.4 predecessor remains in private recovery custody and is not redistributed in this public release set: its dated operator documents contain private machine labels. This omission does not change native rollback semantics or imply that an arbitrary older package is safe. Package versions alone are insufficient identity.

The prepared human exercise uses the exact package-only upgrade fixture in `upgrade/` and UPGRADE-FIXTURE.json. Workbench .1 and .2 have the same accepted source and identical runtime payload; their Debian package versions differ. On the existing enrolled exercise VM, from the verified candidate directory:

```sh
sudo dpkg --install upgrade/constellation-workbench_0.1.0+release.20261005.2_all.deb
sudo dpkg --audit
sudo systemctl restart constellation-workbench.service
dpkg-query -W constellation-workbench
sha256sum --check installed-SHA256SUMS
```

Recover a stale collector with `sudo systemctl start nqd-ops.service`, then wait for fresh native same-boot evidence. Roll back only Workbench:

```sh
sudo dpkg --install packages/constellation-workbench_0.1.0+release.20261005.1_all.deb
sudo dpkg --audit
sudo systemctl restart constellation-workbench.service
sha256sum --check installed-SHA256SUMS
```

Inspect current native state and retained attempts in Workbench after each operation. No new enrollment or grant is created. This is an honest package-only upgrade/rollback, not proof of arbitrary semantic generation migration. Semantic/helper executable inode replacement may invalidate NQ admission. Preserve prior store/admission; follow native refusal and the documented generation/re-admission boundary rather than editing receipts.

The supplied rollback is Workbench .2 → .1 on the same accepted runtime generation. Historical whole-spine rollback requires separately verified owner-approved predecessor package and protected state custody; it is not a command available from this public download. Downgrading NQ alone while the current live reader requires NQ >=0.2.5 is invalid. Stop the relevant writers and reconcile pending effects before any separately authorized semantic downgrade.

The bundled reference day-two runbook supplies the accepted filesystem/posture generation, new-store, retained-state rollback and bad-upgrade procedures. A post-effect rollback is not guaranteed merely because package rollback succeeds. Current evidence and independent effect reconciliation decide recovery.

## Removal

Reconcile a pending governed attempt first. Stop the owner-enabled Workbench,
its separately enrolled native reader/collector, attention and remediation
services/timers before removing their packages. Package removal does not
remove/revoke enrollment or credentials, settle an attempt or erase state.
Keep protected state for recovery; do not treat purge as rollback. Never stop
an unrelated collector merely because it has a similar service name.
