#!/bin/sh
set -eu
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] || { echo 'Run as the release operator with sudo.' >&2; exit 2; }
. /etc/os-release
[ "$ID:$VERSION_ID:$(dpkg --print-architecture)" = ubuntu:22.04:amd64 ] || { echo 'Requires Ubuntu 22.04 amd64.' >&2; exit 2; }
sha256sum -c SHA256SUMS
command -v python3 >/dev/null
command -v openssl >/dev/null
dpkg -i packages/*.deb
for bin in nq nightshift ag-loopctl docket docket-standing-resolver pulse-m2-support pulse-m2-support-resolver; do command -v "$bin" >/dev/null; done
/usr/libexec/agent-governor-ng/ag-effectd --help >/dev/null
nq --build-info
printf '%s\n' 'Installed inert packages. No standing, authority or effect was created.'
