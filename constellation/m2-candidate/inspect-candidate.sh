#!/bin/sh
set -eu
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS
python3 - <<'PY'
import json
from pathlib import Path
m = json.loads(Path('candidate.json').read_text())
print(m['disposition'])
for item in m['blockers']:
    print(item['id'] + ': ' + item['summary'])
raise SystemExit(0 if m['disposition'] == 'M2_RELEASE_CANDIDATE_READY_FOR_FRESH_SHOWING' else 1)
PY
