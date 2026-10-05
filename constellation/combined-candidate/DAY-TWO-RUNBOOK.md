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

Use the exact current and predecessor packages under `packages/` and `rollback/`, with their respective checksum manifests. The predecessor is the accepted neutral nine-package 0.2.4 spine, not a second Workbench generation. The current candidate adds Workbench/live observation and NQ 0.2.5. Package versions alone are insufficient identity.

For the later human exercise, the supplied owner setup starts from the predecessor's inert packages on a fresh VM; the participant upgrades to the eleven-package combined set before explicit fixture enrollment. Reinstalling the exact combined packages after enrollment is an identity-preserving restart/recovery check; do not call it a new semantic generation. Semantic/helper executable inode replacement may invalidate NQ admission. Preserve prior store/admission; follow the native refusal and documented generation/re-admission boundary rather than editing receipts.

A rollback to 0.2.4 requires stopping Workbench, its native reader and ops collector, preserving exact configuration/store/attempt records and protected credential custody, removing `constellation-workbench` and `constellation-live-observation` without purging state, then installing the exact predecessor package set. The newer reader's declared dependency requires NQ >=0.2.5: **downgrading NQ alone is invalid**. Workbench is deliberately unavailable on that predecessor. Do not continue a pending governed attempt through downgrade; reconcile it first. Re-upgrade reinstalls the exact combined set; retained fixture enrollment must not be reapplied. A native helper-generation refusal requires explicit owner reconciliation/re-admission within the same bounded observer, not automatic authority renewal.

```sh
sudo systemctl stop constellation-workbench.service constellation-live-reader.service nqd-ops.service
sudo dpkg --remove constellation-workbench constellation-live-observation
sudo dpkg --install rollback/*.deb
sudo dpkg --audit
```

The bundled reference day-two runbook supplies the accepted filesystem/posture generation, new-store, retained-state rollback and bad-upgrade procedures. A post-effect rollback is not guaranteed merely because package rollback succeeds. Current evidence and independent effect reconciliation decide recovery.
