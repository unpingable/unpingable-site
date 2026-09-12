#!/usr/bin/env python3
"""Check the public family pages without credentials or private context."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


class Page(HTMLParser):
    def __init__(self, text: str):
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        for field in ("href", "src"):
            if values.get(field):
                self.links.append(values[field])


def local_problem(page: Path, href: str, root: Path = ROOT) -> str | None:
    url = urlsplit(href)
    if url.scheme or url.netloc:
        return None
    target = ((root / unquote(url.path).lstrip("/")) if url.path.startswith("/")
              else (page.parent / unquote(url.path)) if url.path else page).resolve()
    if not target.is_relative_to(root.resolve()):
        return "link leaves the site tree"
    if target.is_dir():
        target /= "index.html"
    if not target.is_file():
        return "missing local destination"
    if url.fragment and target.suffix == ".html":
        if unquote(url.fragment) not in Page(target.read_text()).ids:
            return "missing local anchor"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external", action="store_true",
                        help="also request public HTTPS destinations anonymously")
    args = parser.parse_args()
    failures = []
    external: set[str] = set()
    checked = 0
    for path in sorted((ROOT / "constellation").glob("*.html")):
        for href in Page(path.read_text()).links:
            checked += 1
            problem = local_problem(path, href)
            if problem:
                failures.append(f"{path.relative_to(ROOT)}: {href}: {problem}")
            if href.startswith("https://"):
                external.add(href.split("#", 1)[0])
    if args.external:
        for url in sorted(external):
            try:
                # No account configuration, authorization headers or cookie jar.
                request = Request(url, headers={"User-Agent": "Constellation-public-link-check/1"})
                with urlopen(request, timeout=20) as response:
                    if response.status != 200:
                        failures.append(f"{url}: HTTP {response.status}")
                    print(f"HTTP {response.status} {url}")
            except Exception as error:
                failures.append(f"{url}: {type(error).__name__}: {error}")
    for failure in failures:
        print(failure, file=sys.stderr)
    print(f"Checked {checked} references; {len(failures)} failures")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
