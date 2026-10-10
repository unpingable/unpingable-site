# Day-two operation and recovery

Before a change, record exact package/runtime identities, current evidence, boot identity, enrollment files, and keep a copy of `/etc/constellation-live-ecad` and `/var/lib/constellation-live-ecad` for recovery. Keep credentials and issuer/token material separately protected; ordinary evidence/download bundles contain none. Stop the relevant writer/collector before changing its package/store. Do not run two generations against one store.

The paragraph above names no commands. These documents give no command or destination for the record or the copy, name no unit to stop, and do not say whether anything must be stopped for the Workbench package change below; the upgrade and rollback blocks below stop nothing. None of it was exercised as a documented procedure. On a qualification guest of this package set (an earlier assembly of this candidate with the same packages and scripts), on the manual path, the two directories were copied by a method these documents do not give, nothing was stopped, and the upgrade and rollback blocks then ran as written with `dpkg` exit 0 and an empty audit. All such guests were agent-driven lab runs, not human evidence. Runs on the exact archive are recorded in `QUALIFICATION.json` beside the archive.

## Restart and reboot

On the prepared disposable Workbench exercise, restart the packaged Workbench and native reader normally. A browser refresh never renews evidence. Enabled collectors recover after reboot; the native reader must supply current **same-boot** observation before any claim or action. Never rerun the exclusive enrollment helper to repair restart or reboot. Existing apply claims and attempt history survive. Native stale/unsupported states are legitimate while collection has not recovered. After a reboot systemd starts enabled units itself; a `current` reading then describes unit state on the new boot, not a governed recovery or application health, and the attempt line under the status line says when an attempt was prepared in an earlier boot ([known issues](KNOWN-ISSUES.md)).

```sh
sudo systemctl restart constellation-workbench.service constellation-live-reader.service
systemctl status constellation-workbench.service nqd-ops.service constellation-live-reader.service
```

On collector failure, keep the unit/effect state intact and inspect its service/journal and native refusal. For an ordinary stopped collector, start the existing `nqd-ops.service` and require fresh native evidence. This does not resolve a capacity refusal: no same-VM recovery is supplied (there is no resize command, and NQ's archive rollover does not work with this NQ package). Preserve the records you need and use a new VM. Restarting the collector or rebooting at the ceiling may leave it restarting in a loop; this was not tested. The human negative-control fixture stops collection until the published freshness deadline has passed; it changes neither clocks nor tolerances. Restarting collection is an operator action, not a completed governed repair. This candidate's NQ refuses writes that cannot fit its admitted envelope. Do not increase limits, shorten the horizon, delete records or repeatedly restart to bypass a refusal; see [known issues](KNOWN-ISSUES.md). These documents give no command that shows the envelope or the latest report sequence, and the installed NQ guide describes `nqd.service`, not the `nqd-ops` instance run here ([known issues](KNOWN-ISSUES.md#nq-bounded-retention-with-a-finite-ceiling-issue-27-remains-open)). The retired 8 October archive had a distinct `status=25/XFSZ` restart failure.

## Upgrade and rollback boundary

Use the exact current packages under `packages/` and the supplied Workbench package-only upgrade under `upgrade/`, with their checksum manifests. The accepted historical nine-package NQ 0.2.4 predecessor remains in private recovery custody and is not included in this candidate: its dated operator documents contain private machine labels. This omission does not change native rollback semantics or imply that an arbitrary older package is safe. Package versions alone are insufficient identity.

The prepared human exercise uses the exact package-only upgrade fixture in `upgrade/` and UPGRADE-FIXTURE.json. Workbench .1 and .2 have the same accepted source and identical runtime payload; their Debian package versions differ. On the existing enrolled exercise VM, from the verified candidate directory:

```sh
sudo dpkg --install upgrade/constellation-workbench_0.1.0+release.20261010.2_all.deb
sudo dpkg --audit
sudo systemctl restart constellation-workbench.service
dpkg-query -W constellation-workbench
sha256sum --check installed-SHA256SUMS
```

For an ordinary stopped collector, use `sudo systemctl start nqd-ops.service`, then wait for fresh native same-boot evidence. **Exception:** a capacity refusal is not repaired by restarting collection. Preserve the store and use the stop/reconciliation guidance below. Roll back only Workbench:

```sh
sudo dpkg --install packages/constellation-workbench_0.1.0+release.20261010.1_all.deb
sudo dpkg --audit
sudo systemctl restart constellation-workbench.service
sha256sum --check installed-SHA256SUMS
```

Inspect current native state and retained attempts in Workbench after each operation. No new enrollment or grant is created. This is an honest package-only upgrade/rollback, not proof of arbitrary semantic generation migration. Semantic/helper executable inode replacement may invalidate NQ admission. Preserve prior store/admission; follow native refusal and the documented generation/re-admission boundary rather than editing receipts.

The supplied rollback is Workbench .2 → .1 on the same accepted runtime generation. Historical whole-spine rollback requires separately verified release-approved predecessor package and protected state custody; it is not a command available from this candidate. Downgrading NQ alone while the current live reader requires NQ >=0.2.5 is invalid. Stop the relevant writers and reconcile pending effects before any separately authorized semantic downgrade.

The bundled reference day-two runbook describes the historical reference path's filesystem/posture generation, new-store, retained-state rollback and bad-upgrade procedures. That path starts `constellation-host-posture.service` and has not been run with this NQ package; do not use it with this candidate ([known issues](KNOWN-ISSUES.md)). A post-effect rollback is not guaranteed merely because package rollback succeeds. Current evidence and independent effect reconciliation decide recovery.

## Failed or interrupted enrollment

A failed `try/` run may have installed packages, started services or partially enrolled the action. Do not rerun it, remove an apply claim or delete collision paths. `APPLY_INCOMPLETE_RECONCILIATION_REQUIRED` means the protected enrollment claim exists without a successful terminal record. No general enrollment repair is supplied. Stop further action and retain the exact error, service journals, config and enrollment/attempt records for operator review. Use a separately admitted fresh VM only after the old occurrence and any possible effect have been reconciled; a fresh VM does not settle the old one.

For interrupted `authorize`, `dispatch` or `poll`, first use `sudo python3 scripts/native-action.py recover` from the correct candidate working directory while the reader remains available. It reconciles the existing native attempt; it does not issue a new dispatch. If that result is unresolved or refused, preserve the records and request review. Do not substitute a new enrollment or manual Start for settlement.

## End the session

End the session the same day you start it; this candidate is for supervised sessions of up to four hours ([known issues](KNOWN-ISSUES.md)). Finish or reconcile any existing governed attempt before withdrawing the documented disposable enrollment. Grant expiry alone does not stop observation, revoke already issued standing or undo an action. On the known completed/reconciled enrollment, this exact marker prevents future new grant standing; then disable only its reader, Workbench and collector:

```sh
sudo install -o root -g root -m 0600 /dev/null /etc/constellation-live-ecad/standing/grant.revoked
sudo systemctl disable --now constellation-live-reader.service constellation-workbench.service nqd-ops.service
```

The marker affects future resolver checks. It does not invalidate already issued standing, erase attempt history, cancel a dispatched action or reverse its effect. Disabling services alone is not grant revocation. Stop the deliberately selected fixture separately: `sudo systemctl stop nginx.service` on the primary path, **or** `sudo systemctl stop constellation-beta-http-fixture.service` on the manual study path. Do not stop both or unrelated reference collectors.

Observed after these commands on the qualification guests of this package set (one run of each path):

- The reader, Workbench and `nqd-ops` were disabled and inactive, with no failed units. The Workbench page on port 18861 and the native API on port 8081 stopped answering (connection refused on the try path; on the manual path nothing listened on either port and 18861 refused the connection), so the attempt line and `/api/attempt` can no longer be read. On the try path the AG record was still readable as root with `sudo ag-loopctl inspect --database /var/lib/constellation-live-ecad/ag/campaign.sqlite` and `history`.
- The two commands in the block do not stop or disable the enrolled unit. After the separate stop the unit was inactive and still **enabled**: `nginx.service` on the try path, `constellation-beta-http-fixture.service` on the manual path. An enabled unit is started by systemd at the next boot ([known issues](KNOWN-ISSUES.md#a-reboot-restores-units-outside-governance)); no reboot was made after session end, and these documents give no command to disable the unit.
- State files remained. On the try path every file under `/etc/constellation-live-ecad` and `/var/lib/constellation-live-ecad` had the same hash as before, and the only addition was the empty `grant.revoked`; the NQ store under `/var/lib/nq-ops` remained. On the manual path the grant-use file and AG record were intact.
- The effect of `grant.revoked` on a later resolver check was not tested.

Retain protected tokens/issuer material and state only while an identified recovery dependency needs them; do not put private material in ordinary shared evidence. After the attempt is reconciled and required records are safely retained, the operator can discard this disposable VM. Stopping is not deletion, package removal is not settlement, and no automatic credential/data-erasure procedure is supplied. The trial has no hosted participant account to cancel. Optional separately configured external accounts need their own revocation procedure.

## Removal

The session-end commands above stop this enrollment before package removal. For this fresh isolated VM only, the exact eleven candidate package names come from PACKAGES.json:

```sh
sudo dpkg --remove agent-governor-ng-operator-tools agent-governor-ng-systemd-executor constellation-attention constellation-docket constellation-host-posture constellation-live-observation constellation-nightshift constellation-remediation constellation-workbench linear-accountant-inference nq-ng
```

This removes packages, not enrollment records, credentials or pending attempts. It does not remove Ubuntu nginx or authorize stopping other services.

Observed after this command on the try-path qualification guest of this package set (`dpkg` exit 0, with three "directory not empty so not removed" warnings); removal was not run on the manual path and no reboot followed:

- **Unit files written by enrollment remain:** `/etc/systemd/system/nqd-ops.service` and `/etc/systemd/system/constellation-live-reader.service`, both disabled and pointing at removed binaries, and the `loopback.conf` drop-in.
- **The working copy remains:** `/opt/constellation-try`.
- **Configuration and state directories remain:** `/etc/nq` (`nqd-ops.toml`), `/etc/constellation-workbench`, `/etc/constellation-live-ecad`, `/var/lib/constellation-live-ecad` (including the private issuer keys and operator token; all files hash-identical to before removal) and the NQ store in `/var/lib/nq-ops`.
- **Service users remain:** `nq`, `nq-helper`, `nightshift` and `constellation-workbench`.
- **Package records:** six packages stay in dpkg's removed-with-configuration state (`rc`); Ubuntu nginx stays installed and enabled.
- **`ag-loopctl` is gone,** with the `nq` and `docket` binaries. The retained attempt can no longer be inspected with `ag-loopctl` on that VM, and no installed tool reads the retained AG or Docket stores. Inspect and copy what you need before removal.

These documents give no command that removes any of the items above. Keep required protected state for recovery; do not use purge as rollback. Discarding the reconciled disposable VM is the simpler endpoint than repairing a partial installation.
