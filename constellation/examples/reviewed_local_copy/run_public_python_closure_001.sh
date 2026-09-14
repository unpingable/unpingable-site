#!/bin/bash
# Root-admitted durable envelope for the isolated public Python closure.
set -euo pipefail
umask 077
export PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1

readonly here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
readonly producer="$here/prepare_public_python_closure.py"
readonly pins="$here/source-pins.json"
usage() { echo "usage: $0 --unit UNIT --owner ABSOLUTE_OWNER --records ABSOLUTE_RECORDS --switchyard ABSOLUTE_SOURCE --maude ABSOLUTE_SOURCE [--python ABSOLUTE_PYTHON]" >&2; exit 2; }
unit= owner= records= switchyard= maude= python=/usr/bin/python3.12
while (($#)); do
    case "$1" in
        --unit|--owner|--records|--switchyard|--maude|--python) test $# -ge 2 || usage; key=${1#--}; printf -v "$key" '%s' "$2"; shift 2 ;;
        *) usage ;;
    esac
done
test -n "$unit" -a -n "$owner" -a -n "$records" -a -n "$switchyard" -a -n "$maude"
case "$owner:$records:$switchyard:$maude:$python" in /*:/*:/*:/*:/*) ;; *) usage ;; esac
readonly unit owner records switchyard maude python
readonly lock="$records.owner.lock"

test -n "${INVOCATION_ID:-}"
test ! -e "$owner"
test ! -e "$records"
test "$(df -B1 --output=avail "$(dirname "$owner")" | tail -n1)" -ge 64961380352
test "$(df -B1 --output=avail "$(dirname "$records")" | tail -n1)" -ge 64961380352
test "$(df --output=iavail "$(dirname "$owner")" | tail -n1)" -ge 10000
test "$(df --output=iavail "$(dirname "$records")" | tail -n1)" -ge 10000
test "$(git -C "$switchyard" rev-parse HEAD)" = 1c82e719cf358728d0262ae11138fb13fefe0cae
test -z "$(git -C "$switchyard" status --porcelain)"
test "$(git -C "$maude" rev-parse HEAD)" = 0d5b6c91102b1088818d0493c687f9f23db7684e
test -z "$(git -C "$maude" status --porcelain)"

exec 9>"$lock"
flock -n 9
mkdir -m 700 "$records"
exec >"$records/run.log" 2>&1
finish() {
    code=$?
    printf '{"unit":"%s","invocation_id":"%s","exit_code":%s,"producer_root":"%s","provider_calls":0,"grants":0,"executor_calls":0,"next":"inspect original manager and owner records; no reinstall or restart"}\n' \
      "$unit" "$INVOCATION_ID" "$code" "$owner" >"$records/terminal.json"
    sync -f "$records/terminal.json"
    exit "$code"
}
trap finish EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
printf '{"unit":"%s","host":"%s","invocation_id":"%s","cwd":"%s","producer":"%s","owner":"%s","sources":{"switchyard":"1c82e719cf358728d0262ae11138fb13fefe0cae","maude":"0d5b6c91102b1088818d0493c687f9f23db7684e"},"allocation_limit_bytes":536870912,"memory_limit_bytes":1073741824,"tasks_limit":64,"timeout_seconds":600,"restart":"no","network_transition":"bounded public wheel download only","next":"inspect original unit, manager log, and owner stages without restarting"}\n' \
  "$unit" "$(hostname)" "$INVOCATION_ID" "$PWD" "$producer" "$owner" >"$records/checkpoint.json"
sha256sum "$0" "$producer" "$pins" "$python" >"$records/inputs.sha256"
sync -f "$records/checkpoint.json"
"$python" -B "$producer" --owner "$owner" --switchyard "$switchyard" --maude "$maude" --python "$python" --unit "$unit"
du -s -B1 "$records" "$owner" >"$records/allocation-final.txt"

