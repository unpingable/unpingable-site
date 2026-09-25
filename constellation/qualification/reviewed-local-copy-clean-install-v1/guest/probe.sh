#!/bin/sh
# Record the clean guest's facts the cohort driver depends on, as one JSON line.
# Read-only. Absent tools are reported as null, never installed.
set -eu
digest() { if [ -e "$1" ]; then printf '"sha256:%s"' "$(sha256sum "$1" | cut -d' ' -f1)"; else printf null; fi; }
has() { if command -v "$1" >/dev/null 2>&1; then printf true; else printf false; fi; }
pymod() { if /usr/bin/python3 -I -c "import $1" >/dev/null 2>&1; then printf true; else printf false; fi; }
. /etc/os-release
printf '{"os":"%s:%s",' "$ID" "$VERSION_ID"
printf '"kernel":"%s",' "$(uname -r)"
printf '"python3":"%s",' "$(/usr/bin/python3 -c 'import sys; print(sys.version.split()[0])')"
printf '"python3_target":"%s",' "$(readlink -f /usr/bin/python3)"
printf '"python311_sha256":%s,' "$(digest /usr/bin/python3.11)"
printf '"python312_present":%s,' "$(if [ -e /usr/bin/python3.12 ]; then printf true; else printf false; fi)"
printf '"openssl":"%s",' "$(openssl version 2>/dev/null || true)"
printf '"openssl_ed25519":%s,' "$(if openssl genpkey -algorithm Ed25519 -outform DER -out /dev/null 2>/dev/null; then printf true; else printf false; fi)"
printf '"systemd":"%s",' "$(systemctl --version | head -1)"
printf '"tools":{"systemd-run":%s,"setpriv":%s,"runuser":%s,"dpkg":%s,"useradd":%s,"sqlite3":%s,"pip3":%s,"git":%s,"cargo":%s},' \
  "$(has systemd-run)" "$(has setpriv)" "$(has runuser)" "$(has dpkg)" "$(has useradd)" "$(has sqlite3)" "$(has pip3)" "$(has git)" "$(has cargo)"
printf '"python_modules":{"venv_ensurepip":%s,"yaml":%s,"sqlite3":%s,"jsonschema":%s},' \
  "$(pymod ensurepip)" "$(pymod yaml)" "$(pymod sqlite3)" "$(pymod jsonschema)"
printf '"tarfile_data_filter":%s,' "$(if /usr/bin/python3 -I -c 'import tarfile; tarfile.data_filter' >/dev/null 2>&1; then printf true; else printf false; fi)"
printf '"memfd_create":%s,' "$(if /usr/bin/python3 -I -c 'import os; os.close(os.memfd_create("probe"))' >/dev/null 2>&1; then printf true; else printf false; fi)"
printf '"root_free_kib":%s}\n' "$(df -Pk / | awk 'NR==2{print $4}')"
