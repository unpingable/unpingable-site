# Day-two runbook: install, enroll, restart, upgrade, roll back

Historical accepted spine recipe, supplied for reference configuration details. Run commands from the **combined candidate root**, not this reference subdirectory. Install packages using the main INSTALLATION.md and current PACKAGES.json; the historical nine-package table/explicit install command and 0.2.3→0.2.4 qualification examples below are not the combined install/upgrade path. Main DAY-TWO-RUNBOOK.md defines the exact supplied 0.2.4 predecessor ↔ 0.2.5 combined boundary. No historical qualification record is rewritten or required reading.
This lifecycle walkthrough uses retained NQ 0.2.3 as the starting generation and current 0.2.4 as the successor. For a fresh current installation, use INSTALLATION.md; this walkthrough is also the prepared upgrade/rollback procedure.

Target: one Ubuntu 22.04 amd64 host, root access, no build tools, no source, no network needed after the packages are copied on.
Everything below is what `run-daytwo.py` does over ssh on a throwaway VM; the driver and this file are meant to agree. If they disagree, the driver is what was exercised.

## What is operator-edited, and what is not

Installing the packages writes no configuration. These files are written or edited by the operator (the driver writes them with the values shown):

- `/etc/nq/nq.toml`: one watcher on the root filesystem (machine-id, filesystem UUID, mountpoint), plus one `local_file` notice route when the evaluator is used. Per host.
- `/etc/constellation-host-posture/host-posture.toml`: rendered from `constellation-host-posture example-config`, then edited: `service_uid` (the `nq` uid), `mountpoint_label`, `issuance_id`, and the `installed-vN` policy ids. The source/build record in it comes from the package itself; the retention envelope (`maximum_occurrences = 2048` at 60 s is about 34 hours) is the package's qualification default and is NOT a production retention claim. A production host needs an owner-approved envelope and rotation plan before deployment.
- `/etc/nightshift/observation-cycle.env`, `/usr/local/lib/nightshift/*`, and the two systemd drop-ins: site glue (the observation-profile site adapter in `site-adapter/`), not shipped in any package. `NIGHTSHIFT_NQ_SOURCE_ID` must equal the artifact's `producer.node_id` and is edited at every re-enrollment. `SITE_EPOCH` is chosen once and never changed.
- `/etc/constellation-attention/attention.toml` and one systemd drop-in (only if the evaluator is installed). Qualification profile only: local inbox notice route, no page route, `network_enabled = false`. Production routes and their secrets are out of scope here.

## Prerequisites

- Ubuntu 22.04 amd64, systemd, `sudo`, `python3` (3.10), `sqlite3` python module (stdlib). No cargo/rustc/gcc.
- In one directory: `nq-ng_0.2.3_amd64.deb`, `nq-ng_0.2.4_amd64.deb` (for the upgrade), `constellation-host-posture_*.deb`, `constellation-nightshift_*.deb`, optionally `constellation-attention_*.deb`, and `SHA256SUMS` naming every one of them.
- The Nightshift site adapter files (`tick.sh latest_artifact.py build_request.py 10-site.conf observation-cycle.env.template`).
- Run as root. Below, `ART=/root/daytwo/artifacts` and `ST=/root/daytwo/state`.

```sh
export ART=/root/daytwo/artifacts ST=/root/daytwo/state RET=/root/daytwo/retained
mkdir -p $ART $ST $RET            # copy the debs, SHA256SUMS and the adapter files in
```

## Helper wrapper

`watcher test`, `watcher admit` and `diagnostics execute` are run from root inside a systemd sandbox as the `nq` account. Install this file verbatim as `/usr/local/libexec/nq-helper-run` (mode 0755):

```sh
install -d -m 0755 /usr/local/libexec
cat > /usr/local/libexec/nq-helper-run <<'WRAPPER_EOF'
#!/bin/bash
# /usr/local/libexec/nq-helper-run  --  run /usr/bin/nq as nq inside the systemd-run helper sandbox.
# usage: nq-helper-run 'READWRITE PATHS' -- nq-args...
#   e.g. nq-helper-run '/var/lib/nq /run/nq' -- --config /etc/nq/nq.toml --json watcher admit fs-data-capacity
# Needed because `watcher test`, `watcher admit` and `diagnostics execute` must run as root-launched
# but nq-owned, sandboxed processes (the same envelope as the packaged nqd unit).
set -eu
rw=${1:?usage: nq-helper-run 'READWRITE PATHS' -- nq-args...}
shift
[ "${1:-}" = "--" ] || { echo "usage: nq-helper-run 'READWRITE PATHS' -- nq-args..." >&2; exit 64; }
shift
exec systemd-run --quiet --wait --pipe --collect \
  --property=User=nq --property=Group=nq --property=UMask=0077 --property=NoNewPrivileges=yes --property=PrivateTmp=yes \
  --property='TemporaryFileSystem=/tmp:rw,nosuid,nodev,noexec,mode=1777,size=64M /var/tmp:rw,nosuid,nodev,noexec,mode=1777,size=64M' \
  --property=ProtectSystem=strict --property=ProtectHome=yes --property=ProtectClock=yes --property=ProtectControlGroups=yes \
  --property=ProtectKernelLogs=yes --property=ProtectKernelModules=yes --property=ProtectKernelTunables=yes \
  --property=ProtectHostname=yes --property=RestrictNamespaces=yes --property=RestrictRealtime=yes \
  --property=RestrictSUIDSGID=yes --property=LockPersonality=yes --property=RemoveIPC=yes --property=KeyringMode=private \
  --property=SystemCallArchitectures=native --property='RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6' \
  --property=ReadOnlyPaths=/etc/nq --property="ReadWritePaths=$rw" \
  --property='CapabilityBoundingSet=CAP_SETUID CAP_SETGID CAP_CHOWN CAP_KILL' \
  --property='AmbientCapabilities=CAP_SETUID CAP_SETGID CAP_CHOWN CAP_KILL' \
  --property=LimitNOFILE=4096 --property=LimitFSIZE=1G --property=LimitCORE=0 --property=TasksMax=256 \
  --property=MemoryMax=2G --property=MemorySwapMax=0 --property=CPUQuota=200% \
  -- /usr/bin/nq "$@"
WRAPPER_EOF
chmod 0755 /usr/local/libexec/nq-helper-run
H1() { /usr/local/libexec/nq-helper-run "/var/lib/nq /run/nq" -- "$@"; }
NQ()  { sudo -u nq /usr/bin/nq --config /etc/nq/nq.toml "$@"; }
```

## 1. Fresh install

```sh
cd $ART
for f in *.deb; do awk -v f="$f" '{n=$2; sub(/^\*/,"",n); sub(/^.*\//,"",n); if (n==f) print $1 "  " f}' SHA256SUMS | sha256sum -c -; done
dpkg -i nq-ng_0.2.3_amd64.deb constellation-host-posture_*.deb constellation-nightshift_*.deb constellation-attention_*.deb   # drop the last if absent
dpkg -l 'nq-ng' 'constellation-*'
nq --version; nq --build-info
constellation-host-posture --build-info
nightshift --version
constellation-attention --build-info   # may print usage only: the evaluator has no build-info yet
systemctl is-active nqd.service        # must NOT be active: the runner owns acquisition
```

Record the output. The packages create the `nq`, `nq-helper` and `nightshift` accounts, the host-posture and Nightshift directory layout, and install units disabled. `/etc/nq` is `0750 root:nq`; leave it so.

## 2. Initial enrollment

2.1 NQ configuration and store. Replace nothing by hand: the values come from the host.

```sh
systemd-tmpfiles --create /usr/lib/tmpfiles.d/nq.conf
MID=$(cat /etc/machine-id); UUID=$(findmnt -no UUID /); FST=$(findmnt -no FSTYPE /)
install -d -m 0700 -o nq -g nq /var/lib/nq /var/lib/nq/admissions
install -d -m 0711 -o nq -g nq /var/lib/nq-attention-inbox      # only with the evaluator
cat > /etc/nq/nq.toml <<EOF
schema = "nq.config.v1"
database_path = "/var/lib/nq/nq.db"
socket_path = "/run/nq/nqd.sock"
admissions_dir = "/var/lib/nq/admissions"
helper_runtime_dir = "/run/nq/helpers"

[[notification_routes]]
reference = "attention-test"
transport = "local_file"
local_inbox_directory = "/var/lib/nq-attention-inbox"
timeout_ms = 10000
max_response_bytes = 1024

[[watchers]]
instance_id = "fs-data-capacity"
carrier = "stdio"
subject = "host-filesystem:$MID/$UUID"
capability_ceiling = ["read_machine_identity", "read_mount_table", "read_filesystem_statistics"]
checkpoint_policy = "disabled"

[watchers.command]
executable = "/usr/lib/nq/helpers/nq-host-resource-helper"
args = []
env = {}
execution_account = "nq-helper"
working_directory = "/usr/lib/nq/helpers"

[watchers.profile]
id = "nq.host_filesystem_capacity"
version = 1

[watchers.scope]
kind = "host_filesystem"
value = { schema = "nq.host_filesystem_scope.v1", machine_id = "$MID", filesystem_uuid = "$UUID", filesystem_type = "$FST", mountpoint = "/" }

[watchers.vantage]
kind = "local"
value = {}

[watchers.schedule]
interval_seconds = 60
jitter_seconds = 0
deadline_ms = 30000
retry_backoff_seconds = 30
max_retry_backoff_seconds = 300

[watchers.resources]
max_response_bytes = 1048576
max_stderr_bytes = 65536
max_observations = 1
max_address_space_bytes = 536870912
max_cpu_seconds = 60
max_processes = 32
max_open_files = 128
max_file_bytes = 67108864
EOF
chown root:root /etc/nq/nq.toml; chmod 0644 /etc/nq/nq.toml
NQ --json config check
NQ --json init
H1 --config /etc/nq/nq.toml --json watcher test fs-data-capacity      # expect "outcome": "tested"
H1 --config /etc/nq/nq.toml --json watcher admit fs-data-capacity     # expect "outcome": "activated"
H1 --config /etc/nq/nq.toml --json diagnostics execute fs-data-capacity > $ST/initial-artifact.gen1.json
python3 - <<'EOF'
import json; a=json.load(open('/root/daytwo/state/initial-artifact.gen1.json'))
print(a['artifact_id'], a['profile_semantic_id'], a['producer']['node_id'])
EOF
```

The `node_id` (`nq-store-genesis:<uuid>`) is this store generation's identity. Record it.

2.2 Host-posture enrollment (order matters: enroll, prepare-qualification, preflight, run).

```sh
HPD=/etc/constellation-host-posture; HPC=$HPD/host-posture.toml; Q=/usr/lib/constellation-host-posture/qualification
ISSUANCE=constellation-spine:$(python3 -c 'import uuid;print(uuid.uuid4())')  # unique local issuance; source/build/results remain package-pinned
install -d -m 0750 -o root -g nq $HPD
install -d -m 0700 -o nq -g nq /var/lib/constellation-host-posture
install -d -m 0755 $Q
constellation-host-posture example-config |
  sed -e "s/^service_uid = .*/service_uid = $(id -u nq)/" -e 's|^mountpoint_label = .*|mountpoint_label = "/"|' \
      -e "s|^issuance_id = .*|issuance_id = \"$ISSUANCE\"|" > $HPC
grep -n REPLACE $HPC && echo "STOP: placeholders left"        # must print nothing
chown root:nq $HPC; chmod 0640 $HPC
install -m 0640 -o root -g nq $ST/initial-artifact.gen1.json $HPD/initial-artifact.json
constellation-host-posture enroll $HPC $HPD/initial-artifact.json
chown root:nq $HPD/filesystem-capacity.profile.json; chmod 0640 $HPD/filesystem-capacity.profile.json
constellation-host-posture prepare-qualification $HPC $Q/filesystem-capacity
chown -R root:nq $Q/filesystem-capacity; chmod 0750 $Q/filesystem-capacity; chmod 0640 $Q/filesystem-capacity/*
sudo -u nq constellation-host-posture preflight $HPC
systemctl daemon-reload; systemctl enable constellation-host-posture.service
systemctl start constellation-host-posture.service
journalctl -u constellation-host-posture --no-pager -o cat | grep 'projection state'     # wait up to ~5 min for state=healthy
```

2.3 Nightshift. From the extracted bundle, copy the supplied adapter files into the current working directory (`cp site-adapter/* .`), then:

```sh
install -d -m 0755 /usr/local/lib/nightshift /etc/systemd/system/nightshift-observation-cycle.service.d /etc/systemd/system/nightshift-observation-cycle.timer.d
install -m 0755 tick.sh latest_artifact.py build_request.py /usr/local/lib/nightshift/
install -d -m 0750 -o nq -g nq /var/lib/nightshift /var/lib/nightshift/cycles
install -m 0644 10-site.conf /etc/systemd/system/nightshift-observation-cycle.service.d/10-site.conf
printf '[Timer]\nOnBootSec=\nOnUnitActiveSec=\nOnCalendar=*-*-* *:00/5:00\n' > /etc/systemd/system/nightshift-observation-cycle.timer.d/10-slot-grid.conf
sed -e "s|^SITE_EPOCH=.*|SITE_EPOCH=$(date -u +%Y-%m-%dT00:00:00Z)|" observation-cycle.env.template > /etc/nightshift/observation-cycle.env
NODE=$(python3 -c "import json;print(json.load(open('$ST/initial-artifact.gen1.json'))['producer']['node_id'])")
sed -i "s|^NIGHTSHIFT_NQ_SOURCE_ID=.*|NIGHTSHIFT_NQ_SOURCE_ID=$NODE|" /etc/nightshift/observation-cycle.env
systemctl daemon-reload
systemctl start nightshift-observation-cycle.service; systemctl show -p Result --value nightshift-observation-cycle.service   # success
systemctl enable --now nightshift-observation-cycle.timer
```

A Nightshift posture of `Incomplete (support_not_current)` is expected on this stack: no support family exists for filesystem capacity.

2.4 Evaluator (only if its package is installed). Write the configuration below, then add the single drop-in, which replaces the unit's `ReadWritePaths` because this layout has one NQ store and no `/var/lib/nq-ops`:

```sh
install -d -m 0755 /etc/constellation-attention /etc/systemd/system/constellation-attention.service.d
cat > /etc/constellation-attention/attention.toml <<'EOF'
schema = "constellation.attention_config.v1"
site = "daytwo"
state_path = "/var/lib/constellation-attention/state.json"
command_timeout_seconds = 90

[nq]
program = "/usr/bin/nq"
config = "/etc/nq/nq.toml"

[routes]
notice_route = "attention-test"
notice_transport = "local_file"
network_enabled = false

[[inputs.host_posture]]
label = "root"
publication_root = "/var/lib/constellation-host-posture/status"

[inputs.nq_status]
label = "nqd"
source = "evaluation_history"
command = ["/usr/bin/nq", "--config", "/etc/nq/nq.toml", "--json"]
window_records = 300
max_age_seconds = 300
stale_after_seconds = 180

[inputs.nightshift]
label = "observation"
store_path = "/var/lib/nightshift/nightshift.sqlite"
EOF
chmod 0644 /etc/constellation-attention/attention.toml
printf '[Service]\nReadWritePaths=\nReadWritePaths=/var/lib/constellation-attention /var/lib/nq /var/lib/nightshift /var/lib/nq-attention-inbox\n' \
  > /etc/systemd/system/constellation-attention.service.d/10-daytwo.conf
systemctl daemon-reload
sudo -u nq constellation-attention check-config --config /etc/constellation-attention/attention.toml
systemctl start constellation-attention.service; systemctl show -p ExecMainStatus --value constellation-attention.service
ls -l /var/lib/constellation-attention/report.json
```

Exit 0 is a clean pass. Exit 3 means an input was not current or a delivery was not accepted; record it. The driver accepts 3 unless run with `--strict-evaluator`. The evaluator timer is deliberately not enabled in this scenario.

## 3. Restart and reboot

```sh
systemctl reboot
# after the host is back:
journalctl -b -u constellation-host-posture --no-pager -o cat | grep 'projection state'    # healthy again (allow ~5 min)
systemctl is-active nightshift-observation-cycle.timer
systemctl start constellation-attention.service; systemctl show -p ExecMainStatus --value constellation-attention.service
H1 --config /etc/nq/nq.toml --json doctor | python3 -c 'import json,sys; print("healthy =", json.load(sys.stdin).get("healthy"))'
```

## 4. Upgrade 0.2.3 -> 0.2.4: the generation boundary

The 0.2.3 to 0.2.4 change preserves the catalog and schema. Cross-build store continuity remains unqualified. Use the conservative fresh-generation path: archive with the old binary, retain its store and admissions together, initialize and admit the successor, and re-enroll the posture generation. Skipping the new posture qualification must refuse; a successful old-store probe is not a continuity qualification.

1. Stop the timer, runner and evaluator: `systemctl stop nightshift-observation-cycle.timer nightshift-observation-cycle.service constellation-attention.timer constellation-attention.service constellation-host-posture.service`; confirm `pgrep -x nq` is empty.
2. Snapshot the posture-side state (it is restored on rollback; the NQ store is retained by move, below):
   `tar -C / --numeric-owner -cpf $RET/pre-up.tar etc/constellation-host-posture usr/lib/constellation-host-posture/qualification var/lib/constellation-host-posture etc/nightshift var/lib/nightshift etc/constellation-attention var/lib/constellation-attention etc/nq/nq.toml`
3. Note the live store's newest artifact id (`LATEST`): `sudo -u nq python3 -c "import sqlite3;c=sqlite3.connect('file:/var/lib/nq/nq.db?mode=ro',uri=True);print(c.execute('select artifact_id from diagnostic_artifact_commitments order by artifact_sequence desc limit 1').fetchone()[0])"`
4. Archive with the OLD binary and verify with the archived binary: `install -d -m 0750 -o nq -g nq /var/lib/nq/archives; A=/var/lib/nq/archives/archive-up; NQ --json admin archive --destination $A; sudo -u nq $A/bin/nq admin archive-verify $A`. Record `sha256sum $A/db/nq.db $A/bin/nq`.
5. Install: `dpkg -i $ART/nq-ng_0.2.4_amd64.deb; systemctl daemon-reload; nq --version`.
6. Record `NQ --json diagnostics qualify "$LATEST"` and its exit status. It may succeed or refuse for this unchanged catalog; neither outcome substitutes for the supported fresh-generation steps below.
7. Retain the old store (moved, never edited): `R=/var/lib/nq/generations/retained-up; install -d -m 0700 -o nq -g nq /var/lib/nq/generations $R; mv /var/lib/nq/nq.db* $R/; mv /var/lib/nq/admissions $R/admissions; install -d -m 0700 -o nq -g nq /var/lib/nq/admissions`. Append a line to `/var/lib/nq/generations/PROVENANCE.txt`.
8. `NQ --json init`, then re-admit (admission is bound to the new binary and is root-only): the `watcher test` / `watcher admit` / `diagnostics execute` commands of 2.1, saving the artifact as `$ST/initial-artifact.up.json`. Run `NQ --json diagnostics qualify <artifact_id>` and the doctor check.
9. Re-enroll host-posture. Bump the policy ids (`sed -i 's/installed-v1/installed-v2/g' $HPC`), move the old profile aside, `constellation-host-posture enroll` with the NEW artifact, then a NEW `prepare-qualification` into a fresh directory (move `$Q/filesystem-capacity` aside first), same chown/chmod as 2.2, then `sudo -u nq constellation-host-posture preflight $HPC`. Without the new qualification package preflight reports `Ambiguous`, not `QualifiedAndMatched`. Keep `/var/lib/constellation-host-posture` where it is: moving the runner state root breaks preflight.
10. Set `NIGHTSHIFT_NQ_SOURCE_ID` in `/etc/nightshift/observation-cycle.env` to the new artifact's `producer.node_id`.
11. Evaluator: move `/var/lib/constellation-attention` aside so it starts from a fresh state directory.
12. Start the runner and wait for `projection state=healthy`; run one Nightshift cycle; `systemctl start nightshift-observation-cycle.timer`; run one evaluator pass; run the doctor check.

Post-upgrade: `time NQ --json admin validate --full`, `time NQ --json status export`, one Nightshift cycle, one evaluator pass.

## 5. Rollback from a bad upgrade

Everything needed is retained: the old `.deb`, the archived store (and its own binary), the moved-aside store, and the posture snapshot. Nothing is rebuilt.

A bad upgrade is simulated in the driver by doing steps 1-8 and 10 of section 4 but skipping the new `prepare-qualification` in step 9. `preflight` must then fail (typically `Ambiguous`), and `systemctl start constellation-host-posture` must refuse to start. If either succeeds, the failure was not detected: stop.

Rollback:

1. Stop everything (`systemctl stop ...` as in section 4 step 1). Snapshot the abandoned posture state for forensics (`tar ... $RET/aborted.tar`, same path list).
2. `dpkg -i $ART/nq-ng_0.2.3_amd64.deb; systemctl daemon-reload; nq --version` (must read 0.2.3).
3. Put the stores back: move the new store (`nq.db*` and `admissions`) to `/var/lib/nq/generations/abandoned-<ts>/`, then move `$R/nq.db*` and `$R/admissions` back into `/var/lib/nq/`.
4. Restore the posture snapshot: remove the listed paths (`rm -rf /etc/constellation-host-posture /usr/lib/constellation-host-posture/qualification /var/lib/constellation-host-posture /etc/nightshift /var/lib/nightshift /etc/constellation-attention /var/lib/constellation-attention /etc/nq/nq.toml`), then `tar -C / --numeric-owner -xpf $RET/pre-up.tar`. This returns the previous profile, qualification package, runner state, Nightshift source id and evaluator state together; restoring only some of them leaves a mixed generation. `systemctl daemon-reload`.
5. Re-admit and re-enroll. A rollback is NOT a pure restore: reinstalling the old package gives the helper binaries new inodes, so the restored admission reports `binary drift for /usr/lib/nq/helpers/nq-host-resource-helper: inode` (doctor `healthy: false`; the runner's acquisitions are refused). Re-admitting changes the vantage, which the old host-posture profile pinned (`artifact_pin_mismatch ... vantage differs from the enrolled identity`), and the old policy generation id cannot be rebound (`policy_generation_rebound`). So, on the restored store:
   - `H1 --config /etc/nq/nq.toml --json watcher test fs-data-capacity` then `... watcher admit fs-data-capacity`.
   - `diagnostics execute` refuses a non-fresh instance, so take the artifact with `H1 --config /etc/nq/nq.toml --json diagnostics acquire-next-local --acquisition-id rollback-1 fs-data-capacity > $ST/initial-artifact.rollback.json`.
   - Bump the policy ids (`installed-vN` to `installed-vN+1` in `$HPC`), `constellation-host-posture enroll`, new `prepare-qualification` (move the old package aside), `preflight`.
   The store genesis id and `profile_semantic_id` come back unchanged from generation 1.
6. Verify: `NQ --json diagnostics qualify "$LATEST"` succeeds again; doctor healthy; start the runner and wait for healthy; one Nightshift cycle; one evaluator pass; `NIGHTSHIFT_NQ_SOURCE_ID` equals the `producer.node_id` of `$ST/initial-artifact.gen1.json`.
7. Retry the upgrade as a fresh occurrence (section 4 again). It creates a new genesis id; do not reuse the abandoned one.

## 6. Identities to record

After each section: `dpkg -l 'nq-ng' 'constellation-*'`; `nq --version`, `nq --build-info`, `constellation-host-posture --build-info`, `nightshift --version`, `sha256sum` of the installed binaries; per store generation: initial artifact id, `producer.node_id` (store genesis id), `profile_semantic_id`; the host-posture profile file sha256 and its policy generation line; each archive's `db/nq.db` and `bin/nq` sha256 and the `archive-verify` result; the `PROVENANCE.txt` contents; the value of `NIGHTSHIFT_NQ_SOURCE_ID`; the timings of `admin validate --full` and `status export`.

## Driver

```sh
./run-daytwo.py --artifacts /path/to/artifacts --work /path/to/work --record /path/to/record
./check-syntax.sh        # py_compile plus bash -n on every embedded guest script
```

`record/NN-<step>.log` holds each step's timestamped output; `record/RESULT.json` holds per-step status and identities. A failing step stops the run and leaves the VM running; the ssh command is printed and stored in RESULT.json.

## Optional integrations

- PagerDuty (interruption channel with separate production and test services): `integrations/pagerduty/README.md`, helper `integrations/pagerduty/pagerduty-provision.py`.
