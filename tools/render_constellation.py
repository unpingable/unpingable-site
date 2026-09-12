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
    "id", "name", "relationship", "implementation_form", "role", "maturity",
    "availability", "url", "use",
}


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def validate(data: object) -> list[dict[str, str]]:
    if not isinstance(data, dict) or data.get("schema") != "constellation.components/v1":
        raise ValueError("components.json must use constellation.components/v1")
    components = data.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("components.json must contain components")
    seen: set[str] = set()
    for component in components:
        if not isinstance(component, dict) or set(component) != REQUIRED:
            raise ValueError("each component must contain exactly the public component fields")
        required_text = REQUIRED - {"url"}
        if not all(isinstance(component[field], str) and component[field].strip() for field in required_text):
            raise ValueError("component fields must be non-empty strings")
        if component["id"] in seen:
            raise ValueError("component ids must be unique")
        if component["url"] is not None and (
            not isinstance(component["url"], str)
            or not component["url"].startswith("https://github.com/unpingable/")
        ):
            raise ValueError("component URLs must be public unpingable GitHub URLs or null")
        seen.add(component["id"])
    return components


def render(data: object) -> str:
    components = validate(data)
    rows = "\n".join(
        f'''      <article id="{esc(item["id"])}">
        <h2>{f'<a href="{esc(item["url"])}">{esc(item["name"])}</a>' if item["url"] else esc(item["name"])}</h2>
        <p>{esc(item["role"])}</p>
        <dl>
          <dt>Relationship</dt><dd>{esc(item["relationship"])}</dd>
          <dt>Implementation</dt><dd>{esc(item["implementation_form"])}</dd>
          <dt>Maturity</dt><dd>{esc(item["maturity"])}</dd>
          <dt>Available now</dt><dd>{esc(item["availability"])}</dd>
          <dt>When to use it</dt><dd>{esc(item["use"])}</dd>
        </dl>
      </article>'''
        for item in components
    )
    return f'''{BEGIN}
    <main id="main">
      <h1>Components</h1>
      <p class="lede">A public source map, not a claim that every component is installed, live, or needed for every workflow.</p>
{rows}
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
