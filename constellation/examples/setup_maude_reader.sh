#!/usr/bin/env bash
# Install only the pinned public Plan Core consultation profile in a new directory.
set -euo pipefail
if test "$#" -ne 1; then echo "usage: bash setup_maude_reader.sh NEW_DIRECTORY" >&2; exit 2; fi
destination=$1
test ! -e "$destination" || { echo "destination already exists; preserve it" >&2; exit 2; }
example_dir=$(cd "$(dirname "$0")" && pwd)
source_revision=7d196e2ab0e78cca46bd34af1ce6e9cbc9bf7fa6
python3 -c 'import sys; assert sys.version_info[:2] == (3, 12), "this wheel lock requires CPython 3.12"'
test "$(uname -s)" = Linux
test "$(uname -m)" = x86_64
mkdir -p "$destination"
destination=$(cd "$destination" && pwd)
git init "$destination/source"
git -C "$destination/source" remote add origin https://github.com/unpingable/maude.git
git -C "$destination/source" sparse-checkout init --no-cone
git -C "$destination/source" sparse-checkout set /pyproject.toml /README.md /src/maude/__init__.py /src/maude/plan/
git -C "$destination/source" fetch --filter=blob:none --depth=1 origin "$source_revision"
git -C "$destination/source" checkout --detach FETCH_HEAD
test "$(git -C "$destination/source" rev-parse HEAD)" = "$source_revision"
python3 -m venv "$destination/venv"
"$destination/venv/bin/python" -m pip --isolated install --no-cache-dir --only-binary=:all: --require-hashes --index-url https://pypi.org/simple \
  --report "$destination/dependencies-report.json" -r "$example_dir/maude-plan-reader-requirements.txt"
"$destination/venv/bin/python" -m pip --isolated install --no-deps --no-build-isolation \
  --report "$destination/source-install-report.json" -e "$destination/source"
"$destination/venv/bin/python" -m pip check
"$destination/venv/bin/python" -m pip freeze --all > "$destination/installed-versions.txt"
printf 'Installed source %s; no plan or provider request was created.\n' "$source_revision"
printf 'CLI: %s/venv/bin/maude-plan\n' "$destination"
