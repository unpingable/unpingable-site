#!/bin/sh
# Site adapter: newest NQ artifact -> sealed Nightshift cycle request + resolver binding.
set -eu
D=${SITE_CYCLES_DIR:-/var/lib/nightshift/cycles}
ID=$(/usr/local/lib/nightshift/latest_artifact.py "$SITE_NQ_DB" "$SITE_NQ_INSTANCE")
/usr/bin/nq --config "$NIGHTSHIFT_NQ_CONFIG" diagnostics export "$ID" > "$D/artifact.json"
exec /usr/local/lib/nightshift/build_request.py "$D/artifact.json" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SITE_EPOCH" "$SITE_CADENCE" "$SITE_ADMISSIBLE" "$NIGHTSHIFT_NQ_SOURCE_ID" "$D"
