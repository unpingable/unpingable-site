#!/usr/bin/env python3
"""Render the public Constellation component list from components.json."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "constellation" / "components.json"
TARGET = ROOT / "constellation" / "components.html"
BEGIN = "<!-- COMPONENTS:BEGIN generated from components.json by tools/render_constellation.py -->"
END = "<!-- COMPONENTS:END -->"
REQUIRED = {
    "id", "name", "relationship", "implementation_form", "role", "role_detail",
    "refuses", "maturity", "maturity_label", "section", "availability", "url", "use",
}
SECTIONS = (
    ("core", "Core components", "The components exercised together in the alpha.6 governed-action profile."),
    ("optional", "Optional and supporting components", "Each is usable on its own; none is required for every workflow."),
    ("design", "Design only", "Named and documented, not implemented."),
)
ARCHIVE = "archive"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def validate(data: object) -> list[dict[str, str]]:
    if not isinstance(data, dict) or data.get("schema") != "constellation.components/v2":
        raise ValueError("components.json must use constellation.components/v2")
    components = data.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("components.json must contain components")
    seen: set[str] = set()
    sections = {key for key, _, _ in SECTIONS} | {ARCHIVE}
    for component in components:
        if not isinstance(component, dict) or set(component) != REQUIRED:
            raise ValueError("each component must contain exactly the public component fields")
        required_text = REQUIRED - {"url"}
        if not all(isinstance(component[field], str) and component[field].strip() for field in required_text):
            raise ValueError("component fields must be non-empty strings")
        if component["section"] not in sections:
            raise ValueError(f"unknown component section {component['section']!r}")
        if component["id"] in seen:
            raise ValueError("component ids must be unique")
        if component["url"] is not None and (
            not isinstance(component["url"], str)
            or not component["url"].startswith("https://github.com/unpingable/")
        ):
            raise ValueError("component URLs must be public unpingable GitHub URLs or null")
        seen.add(component["id"])
    return components


def render_item(item: dict[str, str]) -> str:
    name = f'<a href="{esc(item["url"])}">{esc(item["name"])}</a>' if item["url"] else esc(item["name"])
    return f'''      <article id="{esc(item["id"])}">
        <h3>{name}</h3>
        <p>{esc(item["role"])}</p>
        <dl>
          <dt>Boundary</dt><dd>{esc(item["refuses"])}</dd>
          <dt>Maturity</dt><dd>{esc(item["maturity_label"])}</dd>
        </dl>
        <details>
          <summary>Details</summary>
          <dl>
            <dt>Precise role</dt><dd>{esc(item["role_detail"])}</dd>
            <dt>Relationship</dt><dd>{esc(item["relationship"])}</dd>
            <dt>Implementation</dt><dd>{esc(item["implementation_form"])}</dd>
            <dt>Maturity in full</dt><dd>{esc(item["maturity"])}</dd>
            <dt>Available now</dt><dd>{esc(item["availability"])}</dd>
            <dt>When to use it</dt><dd>{esc(item["use"])}</dd>
          </dl>
        </details>
      </article>'''


def render(data: object) -> str:
    components = validate(data)
    groups = []
    for key, heading, intro in SECTIONS:
        items = [item for item in components if item["section"] == key]
        if not items:
            continue
        body = "\n".join(render_item(item) for item in items)
        groups.append(f'''      <h2 id="{key}">{heading}</h2>
      <p>{intro}</p>
{body}''')
    archived = ", ".join(
        f'<a href="archive.html#classic-lineage">{esc(item["name"])}</a>'
        for item in components if item["section"] == ARCHIVE
    )
    archive_note = (
        f"\n      <p>Historical and classic-lineage entries ({archived}) are on the "
        f'<a href="archive.html">archive</a> page.</p>' if archived else ""
    )
    sections = "\n".join(groups)
    return f'''{BEGIN}
    <main id="main">
      <h1>Components</h1>
      <p class="lede">The Constellation map in boring nouns: what each component does, what it will not do, and how mature it is.</p>
      <p>This is a public source map, not a claim that every component is installed, live, or needed for every workflow. Constellation is compositional; choose the smallest supported composition on the <a href="integration.html">integration</a> page. Dated claims are on the <a href="status.html">status</a> page.</p>
{sections}{archive_note}
      <section class="note" aria-label="Task-oriented source navigation">
        <h2>Choose a source for the task</h2>
        <p>Need to formalize or check a supplied claim? Read the <a href="https://github.com/unpingable/verifier/blob/main/HOWTO.md">Verifier HOWTO</a>. It is an optional bounded check of supplied input, not authority.</p>
        <p>Resuming a workflow with explicit retained-memory records? Read the <a href="https://github.com/unpingable/constellation-continuity/blob/main/docs/SESSION-LIFECYCLE-HOWTO.md">Continuity lifecycle guide</a> and <a href="https://github.com/unpingable/spine/blob/main/HOWTO.md">Spine's declared-source guide</a>. Those guides do not select work, infer currentness, or authorize action.</p>
      </section>
    </main>
    {END}'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify, do not write")
    args = parser.parse_args()
    data = json.loads(SOURCE.read_text())
    block = render(data)
    page = TARGET.read_text()
    if BEGIN not in page or END not in page:
        print(f"{TARGET}: generated markers not found", file=sys.stderr)
        return 2
    start, stop = page.index(BEGIN), page.index(END) + len(END)
    updated = page[:start] + block + page[stop:]
    if args.check:
        if updated != page:
            print(f"{TARGET}: component list is stale", file=sys.stderr)
            return 1
        print(f"{TARGET}: component list is up to date")
        return 0
    TARGET.write_text(updated)
    print(f"{TARGET}: rendered {len(validate(data))} components")
    return 0


if __name__ == "__main__":
    sys.exit(main())
