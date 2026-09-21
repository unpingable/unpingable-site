#!/usr/bin/env python3
"""Check the public family pages without credentials or private context."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent


class Page(HTMLParser):
    def __init__(self, text: str):
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.title = ""
        self._in_title = False
        self.meta: list[dict[str, str | None]] = []
        self.canonicals: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            self.meta.append(values)
        if tag == "link" and values.get("rel") == "canonical" and values.get("href"):
            self.canonicals.append(values["href"])
        if values.get("id"):
            self.ids.add(values["id"])
        for field in ("href", "src"):
            if values.get(field):
                self.links.append(values[field])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data

    def meta_value(self, field: str, value: str) -> str | None:
        for attrs in self.meta:
            if attrs.get(field) == value:
                return attrs.get("content")
        return None


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
    pages = sorted((ROOT / "constellation").rglob("*.html"))
    pages += [ROOT / name for name in ("index.html", "about.html", "constellation.html")]
    for path in pages:
        parsed = Page(path.read_text())
        for href in parsed.links:
            checked += 1
            problem = local_problem(path, href)
            if problem:
                failures.append(f"{path.relative_to(ROOT)}: {href}: {problem}")
            if href.startswith("https://"):
                external.add(href.split("#", 1)[0])
        relative = path.relative_to(ROOT)
        immutable_release = "releases" in relative.parts
        if not parsed.title.strip():
            failures.append(f"{relative}: missing title")
        # Immutable release pages retain their published bytes and hashes. The
        # mutable entry points supply current descriptions and social previews.
        if not immutable_release and not parsed.meta_value("name", "description"):
            failures.append(f"{relative}: missing description")
        if not immutable_release and len(parsed.canonicals) != 1:
            failures.append(f"{relative}: expected one canonical URL")
        if not immutable_release and path.name != "constellation.html":
            for field, value in (("property", "og:title"),
                                 ("property", "og:description"),
                                 ("property", "og:url"),
                                 ("name", "twitter:card")):
                if not parsed.meta_value(field, value):
                    failures.append(f"{relative}: missing {value}")
    sitemap = ET.parse(ROOT / "sitemap.xml")
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for node in sitemap.findall("sm:url/sm:loc", namespace):
        url = node.text or ""
        if not url.startswith("https://unpingable.com/"):
            failures.append(f"sitemap.xml: non-canonical URL {url}")
            continue
        pathpart = urlsplit(url).path
        target = ROOT / pathpart.lstrip("/")
        if target.is_dir() or pathpart.endswith("/"):
            target /= "index.html"
        if not target.is_file():
            failures.append(f"sitemap.xml: missing destination {url}")
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
