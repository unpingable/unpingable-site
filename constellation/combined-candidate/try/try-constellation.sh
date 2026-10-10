#!/bin/bash
# Try the Constellation combined candidate on a fresh, disposable Ubuntu 22.04 VM with nginx as the governed service.
#
#   sudo ./try-constellation.sh --archive FILE_OR_URL --sha256 HEX [--nginx-debs DIR]
#        [--workbench-deb FILE --workbench-sha256 HEX --identity-override DIR]   (lab only, optional)
#
# Online (default): installs prerequisites and nginx with apt. Offline: pass --nginx-debs DIR holding the jammy nginx
# .deb set (see README.md); every other prerequisite must already be present (the Ubuntu cloud image has them).
# It verifies the archive hash and the archive's own SHA256SUMS, installs the eleven candidate packages, checks
# installed-SHA256SUMS, enrolls the packaged nginx.service as the governed unit (one-use, two-hour Start grant;
# refuses existing enrollment), waits for current native observation and prints where to look. Once per fresh VM.
# The candidate's own Workbench reads the per-enrollment unit name; the default path needs no other input. Lab only:
# --workbench-deb installs a different Workbench build over the candidate's and --identity-override supplies the
# matching RUNTIME-IDENTITIES.json and installed-SHA256SUMS. Those are lab inputs, not part of any candidate.
set -euo pipefail
die() { echo "try-constellation: $*" >&2; exit 1; }
say() { echo "== $*"; }
HERE=$(cd "$(dirname "$0")" && pwd)
ARCHIVE= SHA= NGINX_DEBS= WB_DEB= WB_SHA= OVERRIDE= WORK=/opt/constellation-try
while [ $# -gt 0 ]; do
  case $1 in
    --archive) ARCHIVE=${2:?}; shift 2 ;;
    --sha256) SHA=${2:?}; shift 2 ;;
    --nginx-debs) NGINX_DEBS=$(cd "${2:?}" && pwd); shift 2 ;;
    --workbench-deb) WB_DEB=$(realpath "${2:?}"); shift 2 ;;
    --workbench-sha256) WB_SHA=${2:?}; shift 2 ;;
    --identity-override) OVERRIDE=$(cd "${2:?}" && pwd); shift 2 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) die "unknown argument $1 (see --help)" ;;
  esac
done
[ -n "$ARCHIVE" ] && [ -n "$SHA" ] || die "--archive and --sha256 are both required (see --help)"
[[ $SHA =~ ^[0-9a-f]{64}$ ]] || die "--sha256 must be 64 lowercase hex characters"
if [ -n "$WB_DEB$WB_SHA$OVERRIDE" ]; then
  [ -f "$WB_DEB" ] && [[ $WB_SHA =~ ^[0-9a-f]{64}$ ]] && [ -f "$OVERRIDE/RUNTIME-IDENTITIES.json" ] && [ -f "$OVERRIDE/installed-SHA256SUMS" ] \
    || die "--workbench-deb, --workbench-sha256 and --identity-override (with RUNTIME-IDENTITIES.json and installed-SHA256SUMS) go together"
  echo "$WB_SHA  $WB_DEB" | sha256sum --check --quiet || die "workbench deb hash does not match --workbench-sha256"
fi
[ "$(id -u)" = 0 ] || die "run with sudo"
. /etc/os-release
[ "${VERSION_ID:-}" = 22.04 ] && [ "$(dpkg --print-architecture)" = amd64 ] || die "needs Ubuntu 22.04 amd64 (found ${PRETTY_NAME:-unknown})"
[ -e /var/lib/constellation-live-ecad ] && die "this VM is already enrolled; the exercise is one per fresh VM (nothing changed)"
[ -f "$HERE/enroll-service-fixture.py" ] || die "enroll-service-fixture.py must sit next to this script"
READER_DROPIN=/etc/systemd/system/constellation-live-reader.service.d
[ -e "$READER_DROPIN" ] && die "$READER_DROPIN already exists; use a fresh VM (nothing changed)"
# The loopback confinement of port 8081 below is a systemd IP filter; it needs the unified cgroup v2 hierarchy.
[ -f /sys/fs/cgroup/cgroup.controllers ] || die "needs the cgroup v2 unified hierarchy (systemd IPAddressDeny); nothing changed"

export DEBIAN_FRONTEND=noninteractive
mkdir -p "$WORK"; chmod 755 "$WORK"
case $ARCHIVE in
  https://*|http://*) say "downloading $ARCHIVE"; curl -fsSL --proto '=https,http' -o "$WORK/candidate.tar.gz" "$ARCHIVE"; ARCHIVE=$WORK/candidate.tar.gz ;;
  *) [ -f "$ARCHIVE" ] || die "archive not found: $ARCHIVE" ;;
esac
say "verifying archive sha256"
echo "$SHA  $ARCHIVE" | sha256sum --check --quiet || die "archive hash does not match --sha256; stopped before extraction"
top=$(tar --list --gzip --file "$ARCHIVE" | sed -n 1p | cut -d/ -f1)
[[ $top =~ ^[A-Za-z0-9._-]+$ ]] || die "unexpected archive layout"
CAND=$WORK/$top
[ -e "$CAND" ] && die "$CAND already exists; use a fresh VM"
tar --extract --gzip --no-same-owner --file "$ARCHIVE" --directory "$WORK"
(cd "$CAND" && sha256sum --check --quiet SHA256SUMS) || die "candidate SHA256SUMS check failed"

if [ -z "$NGINX_DEBS" ]; then
  say "installing prerequisites and nginx with apt (online path)"
  apt-get update -q
  apt-get install -y -q python3 adduser systemd util-linux openssl libc6 libgcc-s1 sudo coreutils curl ca-certificates nginx
else
  say "installing nginx from $NGINX_DEBS (offline path)"
  for pkg in python3 adduser systemd util-linux openssl libc6 libgcc-s1 sudo coreutils curl ca-certificates; do
    dpkg-query --show --showformat='${Status}' "$pkg" 2>/dev/null | grep -q 'install ok installed' || die "offline path: prerequisite $pkg is not installed"
  done
  [ -f "$NGINX_DEBS/SHA256SUMS" ] && (cd "$NGINX_DEBS" && sha256sum --check --quiet SHA256SUMS)
  dpkg --install "$NGINX_DEBS"/*.deb
fi
systemctl is-active --quiet nginx.service || die "nginx did not start after installation"

say "installing the candidate packages"
(cd "$CAND" && dpkg --install packages/*.deb)
audit=$(dpkg --audit); [ -z "$audit" ] || die "dpkg --audit reports: $audit"
(cd "$CAND" && sha256sum --check --quiet installed-SHA256SUMS) || die "installed-SHA256SUMS check failed"
ENROLL_ARGS=()
if [ -n "$WB_DEB" ]; then
  say "LAB: replacing the candidate's Workbench with $(basename "$WB_DEB") (not part of the candidate)"
  dpkg --install "$WB_DEB"
  audit=$(dpkg --audit); [ -z "$audit" ] || die "dpkg --audit reports: $audit"
  sha256sum --check --quiet "$OVERRIDE/installed-SHA256SUMS" || die "override installed-SHA256SUMS check failed"
  ENROLL_ARGS=(--runtime-identities "$OVERRIDE/RUNTIME-IDENTITIES.json")
fi

# The native reader/action API (constellation-live-reader.service) binds port 8081 on every guest interface.
# GET /api/read, /api/attempt, /api/enrollment need no credential; only POST /api/actions needs the operator token.
# Confine it to loopback persistently with a systemd drop-in, written before enrollment starts the reader.
say "confining port 8081 to loopback (systemd drop-in $READER_DROPIN/loopback.conf)"
install -d -m 755 "$READER_DROPIN"
printf '[Service]\nIPAddressDeny=any\nIPAddressAllow=localhost\n' > "$READER_DROPIN/loopback.conf"
chmod 644 "$READER_DROPIN/loopback.conf"
systemctl daemon-reload
# Belt and braces only (does not persist across reboot); the drop-in is what keeps 8081 private.
if command -v iptables >/dev/null; then iptables -C INPUT -p tcp --dport 8081 ! -i lo -j DROP 2>/dev/null || iptables -I INPUT -p tcp --dport 8081 ! -i lo -j DROP || true; fi

say "enrolling nginx.service as the governed unit (one-use Start grant, two hours)"
receipt=$(python3 "$HERE/enroll-service-fixture.py" --candidate "$CAND" --admit-disposable-unit-start "${ENROLL_ARGS[@]}")
echo "$receipt" > "$WORK/enrollment-receipt.json"

# Stop (and take the reader down) unless the drop-in is in force and a non-loopback request to 8081 fails.
reader_exposed() { systemctl disable --now constellation-live-reader.service >/dev/null 2>&1 || true; die "$*; constellation-live-reader.service stopped and disabled, port 8081 closed; the VM is enrolled but unusable, discard it"; }
show=$(systemctl show -p DropInPaths,IPAddressDeny,IPAddressAllow constellation-live-reader.service)
grep -qx "DropInPaths=.*$READER_DROPIN/loopback.conf.*" <<<"$show" && grep -qx 'IPAddressAllow=127.0.0.0/8 ::1/128' <<<"$show" \
  && grep -qx 'IPAddressDeny=0.0.0.0/0 ::/0' <<<"$show" || reader_exposed "the loopback drop-in is not in force for the reader ($show)"

say "waiting for current native observation (up to 3 minutes)"
state=none
for _ in $(seq 1 90); do
  state=$(curl -fsS --max-time 10 http://127.0.0.1:8081/api/read 2>/dev/null | python3 -c 'import json,sys; o=json.load(sys.stdin)["observations"]; print(o[0]["currentness"]["state"] if o else "absent")' 2>/dev/null || echo unavailable)
  [ "$state" = current ] && curl -fsS --max-time 10 -o /dev/null http://127.0.0.1:18861/api/cohort && break
  sleep 2
done
[ "$state" = current ] || die "no current native observation after 3 minutes (last: $state); inspect: journalctl -u nqd-ops -u constellation-live-reader -u constellation-workbench"
# 127.0.0.1:8081 has just answered; the same request on every other local address must not.
for addr in $(hostname -I); do
  [[ $addr == *:* ]] && addr="[$addr]"
  curl -fsS -o /dev/null --max-time 3 "http://$addr:8081/api/read" 2>/dev/null && reader_exposed "port 8081 answered on $addr"
done
expires=$(python3 -c 'import json,sys,datetime; print(datetime.datetime.fromtimestamp(json.load(sys.stdin)["expires_at_unix_ms"]/1000,datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))' <<<"$receipt")
http=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1/ || true)
ip=$(hostname -I | awk '{print $1}'); user=${SUDO_USER:-ubuntu}
cat <<MSG

Constellation is observing and governing nginx on this VM.

Port 8081 (native API) is confined to this VM's loopback by $READER_DROPIN/loopback.conf (survives reboot).

Workbench (read-only):  http://127.0.0.1:18861/operator.html     plan: /plan.html   JSON: /api/cohort
  It listens on this VM's loopback only. From your laptop:
    ssh -N -L 18861:127.0.0.1:18861 $user@$ip        then open http://127.0.0.1:18861/operator.html
    Multipass: add your key first, e.g.
      multipass exec NAME -- bash -c "echo '\$(cat ~/.ssh/id_ed25519.pub)' >> ~/.ssh/authorized_keys"
    and use user ubuntu with the address from 'multipass info NAME'.

What is observed: systemd state of nginx.service, the unit the Ubuntu package installed (unchanged).
  Unit active is not service healthy: nginx HTTP is NOT instrumented by Constellation here.
  (A plain curl of http://127.0.0.1/ just now returned $http; that is not Constellation evidence.)

Break nginx and watch the loop:
    sudo systemctl stop nginx

Then recover through the governed native API: one use only, grant expires $expires.
    The exact commands are in $HERE/README.md (and $CAND/OPERATIONS.md).
MSG
