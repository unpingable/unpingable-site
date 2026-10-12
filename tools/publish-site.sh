#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
case "${1:-check}" in
  generate)
    python3 tools/render_status.py
    python3 tools/render_constellation_meta.py
    python3 tools/render_constellation.py
    ;;
  check) ;;
  diff)
    git diff --check
    exec git diff
    ;;
  preview)
    "$0" check
    git diff --stat
    exec python3 -m http.server 8000 --bind 127.0.0.1
    ;;
  publish)
    "$0" check
    test -z "$(git status --porcelain)" || { echo 'Commit the reviewed changes before publishing' >&2; exit 1; }
    test "$(git branch --show-current)" = main || { echo 'Publishing requires the reviewed main branch' >&2; exit 1; }
    git push origin main
    exit
    ;;
  *) echo 'Usage: tools/publish-site.sh generate|check|diff|preview|publish' >&2; exit 2 ;;
esac
python3 tools/render_constellation.py --check
python3 tools/render_constellation_meta.py --check
python3 tools/render_status.py --check
python3 tools/check_constellation.py
xmllint --noout sitemap.xml
git diff --check
