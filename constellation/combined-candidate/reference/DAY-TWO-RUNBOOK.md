# Reference filesystem observation enrollment

Run from the verified combined candidate root as root on a separately admitted
fresh Ubuntu22.04 VM. Install current `packages/*.deb` using ../INSTALLATION.md
first. No source checkout or internal driver is required. Do not combine this
filesystem profile with the exclusive Workbench local unit enrollment on the
same stores/bindings. Workbench currently shows the documented bounded unit
cohort; this reference profile uses its own native status/CLI surfaces.

```sh
export ART="$PWD"
export ST=/var/lib/constellation-installation/state
export RET=/var/lib/constellation-installation/retained
install -d -m 0700 "$ST" "$RET"
```

The host filesystem/machine/profile identities come from the actual VM. Choose
the finite retention envelope and preserve owner-managed state. Helpers run
inside the documented sandbox below. Installing a package alone grants no
observation admission or effect authority.

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

Exit 0 is a clean pass. Exit 3 means an input was not current or a delivery was not accepted; record it. Do not reinterpret exit3 as a healthy pass. The evaluator timer is deliberately not enabled in this scenario.

## 3. Restart and reboot

```sh
systemctl reboot
# after the host is back:
journalctl -b -u constellation-host-posture --no-pager -o cat | grep 'projection state'    # healthy again (allow ~5 min)
systemctl is-active nightshift-observation-cycle.timer
systemctl start constellation-attention.service; systemctl show -p ExecMainStatus --value constellation-attention.service
H1 --config /etc/nq/nq.toml --json doctor | python3 -c 'import json,sys; print("healthy =", json.load(sys.stdin).get("healthy"))'
```


## Generation changes and recovery

Use the current [combined day-two runbook](../DAY-TWO-RUNBOOK.md). It binds
the exact supplied predecessor/current package sets and Workbench upgrade
fixture. The earlier0.2.3→0.2.4 qualification is retained as historical evidence;
it is not a command path in this download. An old-store compatibility probe
does not establish live cross-generation continuity or post-effect rollback.
