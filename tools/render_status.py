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


def validate(data: dict) -> None:
    """Reject incomplete records before changing any generated page."""
    for field in ("name", "intro", "acceptance", "demonstrated", "evaluation", "availability", "release", "scope"):
        if not isinstance(data["current"].get(field), str) or not data["current"][field].strip():
            raise ValueError(f"current.{field}: nonempty text required")
    for record in [data["current"], data["absd"], *data["objects"]]:
        for link in record.get("links", record.get("evidence", [])):
            url = link["url"]
            if ":" in url and not url.startswith("https://"):
                raise ValueError("Only HTTPS external links are accepted")
    ids = [o["id"] for o in data["objects"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate ledger identities")


def content(data: dict, key: str, target: pathlib.Path) -> str:
    record = data["absd"] if key.startswith("absd") else data["current"]
    def links():
        result = []
        for link in record["links"]:
            url = link["url"]
            if not url.startswith("https://"):
                url = os.path.relpath(ROOT / url, target.parent).replace(os.sep, "/")
            result.append(f'<a href="{esc(url)}">{esc(link["label"])}</a>')
        return " &middot; ".join(result)
    if key == "home":
        return f'<li><a href="constellation/">Constellation</a><span>{esc(record["intro"])} {esc(record["name"])}. {esc(record["acceptance"])} {esc(record["demonstrated"])} {esc(record["evaluation"])} {esc(record["availability"])} {esc(record["release"])}</span></li>'
    if key == "absd-home":
        return f'<li><a href="https://absd.dev">ABSD</a><span>{esc(record["intro"])}</span></li>'
    if key == "absd":
        return f'<p><strong>{esc(record["name"])}</strong></p><p>{esc(record["intro"])}</p><p>{links()}</p>'
    heading = f'<h2 id="summary">Summary as of {esc(data["as_of"])}</h2>' if key == "summary" else ""
    lines = [heading, f'<p>{esc(record["intro"])}</p>', f'<p><strong>{esc(record["name"])}</strong></p>']
    for field, label in [("acceptance", "Acceptance"), ("demonstrated", "Demonstrated"), ("evaluation", "Human evaluation"), ("availability", "Availability"), ("release", "Release notice"), ("scope", "Scope")]:
        lines.append(f'<p><strong>{label}:</strong> {esc(record[field])}</p>')
    lines.append(f'<p>{links()}</p>')
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify, do not write")
    args = parser.parse_args()

    data = json.loads(SOURCE.read_text())
    validate(data)
    targets = {TARGET: splice(TARGET.read_text(), render(data))}
    for relative, key in [("index.html", "home"), ("index.html", "absd-home"),
                          ("constellation/index.html", "project"),
                          ("constellation/status.html", "summary"),
                          ("constellation/absd.html", "absd")]:
        target = ROOT / relative
        page = targets.get(target, target.read_text())
        begin, end = f"<!-- CONTENT:{key}:BEGIN -->", f"<!-- CONTENT:{key}:END -->"
        if page.count(begin) != 1 or page.count(end) != 1:
            raise ValueError(f"{relative}: expected exactly one {key} marker pair")
        start, stop = page.index(begin), page.index(end) + len(end)
        targets[target] = page[:start] + begin + "\n" + content(data, key, target) + "\n" + end + page[stop:]
    stale = [str(p.relative_to(ROOT)) for p, text in targets.items() if p.read_text() != text]
    if args.check:
        if stale:
            print("Stale generated content: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("All mutable content and ledger blocks are up to date")
        return 0
    for path, text in targets.items():
        if path.read_text() != text:
            path.write_text(text)
    print("Rendered mutable content and status ledger")
    return 0


if __name__ == "__main__":
    sys.exit(main())
