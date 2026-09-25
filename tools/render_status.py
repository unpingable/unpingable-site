#!/usr/bin/env python3
"""Render status.json into the ledger block of constellation/status.html.

The ledger on the status page is generated, not hand-maintained: status.json is
the canonical source for every object's kind, status, bounded claim,
verification date, evidence and promotion condition. Editing the HTML directly
is the drift this script exists to prevent.

    python3 tools/render_status.py           # rewrite the status page in place
    python3 tools/render_status.py --check    # exit 1 if the status page is stale

The block is delimited by the BEGIN/END markers below. Everything between them
is replaced wholesale. Relative evidence URLs in status.json are written
from the site root and rebased onto the status page's directory.
"""

from __future__ import annotations

import argparse
import html
import os
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "status.json"
TARGET = ROOT / "constellation" / "status.html"

BEGIN = "<!-- STATUS:BEGIN generated from status.json by tools/render_status.py -->"
END = "<!-- STATUS:END -->"

KIND_ORDER = ["composition", "artifact", "exhibit", "proposition"]


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def rebase(url: str) -> str:
    """Rewrite a root-relative site path so it resolves from TARGET."""
    if url.startswith(("http://", "https://", "#", "/")):
        return url
    path, sep, fragment = url.partition("#")
    rebased = os.path.relpath(ROOT / path, TARGET.parent).replace(os.sep, "/")
    if path.endswith("/"):
        rebased += "/"
    return rebased + sep + fragment


def render_row(obj: dict) -> str:
    kind = obj["kind"]
    verified = obj.get("verified")
    verified_line = (
        f'verified {esc(verified)}' if verified else "not verifiable — nothing built"
    )

    evidence = " &middot; ".join(
        f'<a href="{esc(rebase(e["url"]))}"'
        + (' target="_blank" rel="noopener"' if e["url"].startswith("http") else "")
        + f'>{esc(e["label"])}</a>'
        for e in obj.get("evidence", [])
    )

    return f"""      <article class="ledger-row" id="status-{esc(obj['id'])}">
        <h3>{esc(obj['name'])}</h3>
        <p><span class="badge{' accent' if kind == 'composition' else ' dashed' if kind == 'proposition' else ''}">{esc(kind)}</span> <span class="badge">{esc(obj['status'])}</span></p>
        <p>{esc(obj['claim'])}</p>
        <dl class="pairs">
          <dt>{verified_line}</dt><dd>{esc(obj['verified_by'])}</dd>
          <dt>evidence</dt><dd>{evidence}</dd>
          <dt>promotion</dt><dd>{esc(obj['promotion'])}</dd>
        </dl>
      </article>"""


def render(data: dict) -> str:
    objects = sorted(
        data["objects"],
        key=lambda o: (KIND_ORDER.index(o["kind"]), data["objects"].index(o)),
    )
    rows = "\n".join(render_row(o) for o in objects)
    return f"""{BEGIN}
    <div class="ledger">
{rows}
    </div>
    <p class="fine">Ledger as of {esc(data['as_of'])}. Generated from
      <a href="{esc(rebase('status.json'))}">status.json</a> by <code>tools/render_status.py</code> in the
      <a href="https://github.com/unpingable/unpingable-site" target="_blank" rel="noopener">site repository</a>;
      it is a dated statement, not a live panel. A row moves only by an explicit
      editorial act &mdash; a passing test may satisfy a promotion condition, but it does
      not promote the claim.</p>
    {END}"""


def splice(page: str, block: str) -> str:
    start = page.index(BEGIN)
    stop = page.index(END) + len(END)
    return page[:start] + block + page[stop:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify, do not write")
    args = parser.parse_args()

    data = json.loads(SOURCE.read_text())
    page = TARGET.read_text()

    if BEGIN not in page or END not in page:
        print(f"{TARGET.name}: status markers not found", file=sys.stderr)
        return 2

    updated = splice(page, render(data))

    if args.check:
        if updated != page:
            print(f"{TARGET.name}: status ledger is stale — run tools/render_status.py")
            return 1
        print(f"{TARGET.name}: status ledger up to date")
        return 0

    if updated == page:
        print(f"{TARGET.name}: already up to date")
        return 0

    TARGET.write_text(updated)
    print(f"{TARGET.name}: status ledger rendered ({len(data['objects'])} objects)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
