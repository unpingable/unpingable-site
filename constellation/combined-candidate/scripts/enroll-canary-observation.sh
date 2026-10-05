#!/bin/bash
# Explicit fresh reference observation enrollment. No action grant is created.
set -Eeuo pipefail
[ "$(id -u)" = 0 ] || { echo 'root required'; exit 1; }
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
UNIT=attention-canary.service
INSTANCE=svc-attention-canary
NQCONF=/etc/nq/nqd-ops.toml
INBOX=/var/lib/nq-ops-attention-test-inbox
ATTCONF=/etc/constellation-attention/attention.toml
for path in /etc/systemd/system/$UNIT /lib/systemd/system/$UNIT /etc/systemd/system/nqd-ops.service "$NQCONF" "$ATTCONF" /var/lib/nq-ops /run/nq-ops /var/lib/constellation-attention/state.json /var/lib/constellation-attention/report.json; do
  [ ! -e "$path" ] && [ ! -L "$path" ] || { echo "existing enrollment: $path; preserve and inspect it"; exit 1; }
done
NQ() { setpriv --reuid=nq --regid=nq --init-groups -- /usr/bin/nq --config "$NQCONF" "$@"; }
NQH() { /usr/libexec/constellation-remediation/nq-ops-as-nq --config "$NQCONF" "$@"; }
step() { echo "$*"; }
ident() { echo "IDENT $1=$2"; }
wait_until() { local limit=$1; shift 2; local end=$((SECONDS+limit)); until "$@" >/dev/null 2>&1; do (( SECONDS < end )) || { echo 'current evaluation unavailable'; return 1; }; sleep 5; done; }
step "2.0 harmless canary unit (enabled, Type=simple sleep)"
cat > /lib/systemd/system/$UNIT <<'UNITEOF'
[Unit]
Description=Constellation attention canary (harmless; remediation target)

[Service]
Type=simple
ExecStart=/bin/sleep infinity

[Install]
WantedBy=multi-user.target
UNITEOF
systemctl daemon-reload; systemctl enable --now "$UNIT"; systemctl show -p ActiveState,UnitFileState "$UNIT"
step "2.1 NQ ops-style store: nqd-ops.service, /etc/nq/nqd-ops.toml, /var/lib/nq-ops"
sed -e 's|/etc/nq/nq.toml|/etc/nq/nqd-ops.toml|g' -e 's|^StateDirectory=.*|StateDirectory=nq-ops nq-ops/admissions nq-ops/backups|' \
    -e 's|^RuntimeDirectory=nq$|RuntimeDirectory=nq-ops|' -e 's|/run/nq/helpers|/run/nq-ops/helpers|g' \
    -e 's|^ReadWritePaths=/var/lib/nq /run/nq|ReadWritePaths=/var/lib/nq-ops /run/nq-ops|' \
    -e 's|^RequiresMountsFor=/var/lib/nq|RequiresMountsFor=/var/lib/nq-ops|' -e 's|^SyslogIdentifier=nqd|SyslogIdentifier=nqd-ops|' \
    -e 's|^Description=.*|Description=NQ-ng operations store (ops-style; remediation qualification)|' \
    /usr/lib/systemd/system/nqd.service > /etc/systemd/system/nqd-ops.service
grep -n 'nq-ops\|nqd-ops' /etc/systemd/system/nqd-ops.service
install -d -m 0750 -o root -g nq /etc/nq
install -d -m 0700 -o nq -g nq /var/lib/nq-ops /var/lib/nq-ops/admissions
install -d -m 0751 -o nq -g nq /run/nq-ops; install -d -m 0711 -o nq -g nq /run/nq-ops/helpers
install -d -m 0711 -o nq -g nq "$INBOX"
python3 "$SCRIPT_DIR/enroll-remediation.py" nq-config
chown root:nq "$NQCONF"; chmod 0640 "$NQCONF"
NQ --json config check | tail -3
if [ ! -e /var/lib/nq-ops/nq.db ]; then
  NQ --json init | tail -3
  NQH --json watcher test "$INSTANCE" | tail -c 600; echo
  NQH --json watcher admit "$INSTANCE" | grep -E '"outcome"' | head -2
fi
systemctl daemon-reload; systemctl enable --now nqd-ops.service
has_eval() { NQ --json evaluations export --limit 5 | python3 "$SCRIPT_DIR/check-canary-evidence.py"; }
wait_until 120 "first canary evaluation" has_eval
NQ --json evaluations export --limit 2 | python3 -c 'import json,sys;d=json.load(sys.stdin);print(json.dumps(d["records"][-1])[:700])'
step "2.2 evaluator: local_file notice route, pagerduty page route (network disabled), canary remediation target"
install -d -m 0755 /etc/constellation-attention
python3 "$SCRIPT_DIR/enroll-remediation.py" attention-config
install -d -m 0755 /etc/systemd/system/constellation-attention.service.d
printf '[Service]\nReadWritePaths=%s\n' "$INBOX" > /etc/systemd/system/constellation-attention.service.d/local-inbox.conf
systemctl daemon-reload
setpriv --reuid=nq --regid=nq --init-groups -- constellation-attention check-config --config "$ATTCONF" | tail -5
systemctl start constellation-attention.service
ident attention.first_pass_exit "$(systemctl show -p ExecMainStatus --value constellation-attention.service)"
systemctl enable --now constellation-attention.timer
