#!/usr/bin/env python3
"""Check the public family pages without credentials or private context."""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent


class Page(HTMLParser):
    def __init__(self, text: str):
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.title = ""
        self._in_title = False
        self.h1 = ""
        self._in_h1 = False
        self._nav_depth = 0
        self._nav_link: list[str] | None = None
        self.nav_links: list[tuple[str, str]] = []
        self.meta: list[dict[str, str | None]] = []
        self.canonicals: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "h1":
            self._in_h1 = True
        if tag == "nav":
            self._nav_depth += 1
        if tag == "a" and self._nav_depth:
            self._nav_link = [values.get("href") or "", ""]
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
        if tag == "h1":
            self._in_h1 = False
        if tag == "a" and self._nav_link is not None:
            href, label = self._nav_link
            self.nav_links.append((href, " ".join(label.split())))
            self._nav_link = None
        if tag == "nav" and self._nav_depth:
            self._nav_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_h1:
            self.h1 += data
        if self._nav_link is not None:
            self._nav_link[1] += data

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


def route_source_problems(root: Path = ROOT) -> list[str]:
    """Reject public file/directory basename collisions and validate the front door."""
    problems = []
    for html_path in sorted(root.rglob("*.html")):
        directory = html_path.with_suffix("")
        if directory.is_dir():
            problems.append(
                f"{html_path.relative_to(root)}: shadows the {directory.relative_to(root)}/ directory"
            )
    front = root / "constellation" / "index.html"
    if not front.is_file():
        problems.append("constellation/index.html: canonical front door is missing")
        return problems
    page = Page(front.read_text())
    if page.canonicals != ["https://unpingable.com/constellation/"]:
        problems.append("constellation/index.html: canonical route is not /constellation/")
    if not page.title.strip() or not page.h1.strip() or not page.nav_links:
        problems.append("constellation/index.html: title, H1, or navigation is missing")
    return problems


class RedirectRecorder(HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.redirects: list[tuple[int, str, str]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirects.append((code, req.full_url, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_route(url: str, method: str, follow: bool):
    recorder = RedirectRecorder()
    opener = build_opener(recorder if follow else NoRedirect())
    request = Request(url, method=method,
                      headers={"User-Agent": "Constellation-route-check/1"})
    try:
        with opener.open(request, timeout=20) as response:
            return response.status, response.geturl(), response.read(), recorder.redirects
    except HTTPError as error:
        return error.code, error.geturl(), error.read(), recorder.redirects


def check_live_routes(base_url: str, root: Path = ROOT) -> list[str]:
    """Compare all public route forms and request modes with the front door."""
    failures = []
    expected_bytes = (root / "constellation" / "index.html").read_bytes()
    expected_hash = hashlib.sha256(expected_bytes).hexdigest()
    expected = Page(expected_bytes.decode())
    canonical = "https://unpingable.com/constellation/"
    for route in ("/constellation", "/constellation/", "/constellation/index.html"):
        requested = base_url.rstrip("/") + route
        observations = {}
        for method in ("HEAD", "GET"):
            for follow in (False, True):
                label = f"{method} {'follow' if follow else 'no-follow'}"
                try:
                    observations[(method, follow)] = fetch_route(requested, method, follow)
                except Exception as error:
                    failures.append(f"{requested}: {label}: {type(error).__name__}: {error}")
                    continue
                status, final_url, body, redirects = observations[(method, follow)]
                chain = " -> ".join(str(item[0]) for item in redirects)
                chain = f"{chain} -> {status}" if chain else str(status)
                print(f"ROUTE {method} {route} {'follow' if follow else 'no-follow'} "
                      f"status={chain} final={final_url}")
        if ("GET", True) not in observations:
            continue
        status, final_url, body, redirects = observations[("GET", True)]
        actual = Page(body.decode())
        robots = actual.meta_value("name", "robots")
        checks = {
            "final status": status == 200,
            "canonical URL": actual.canonicals == [canonical],
            "title": actual.title.strip() == expected.title.strip(),
            "H1": actual.h1.strip() == expected.h1.strip(),
            "navigation": actual.nav_links == expected.nav_links,
            "rendered bytes": hashlib.sha256(body).hexdigest() == expected_hash,
            "robots metadata": robots == expected.meta_value("name", "robots"),
        }
        if route == "/constellation/":
            checks["rendered destination"] = final_url == canonical
        elif route == "/constellation" and redirects:
            checks["redirect destination"] = final_url == canonical
        for method in ("HEAD", "GET"):
            followed = observations.get((method, True))
            if followed:
                checks[f"{method} followed status"] = followed[0] == 200
            direct = observations.get((method, False))
            if direct:
                allowed = {200} if route != "/constellation" else {200, 301, 302, 307, 308}
                checks[f"{method} direct status"] = direct[0] in allowed
        for label, passed in checks.items():
            if not passed:
                failures.append(f"{requested}: {label} mismatch")
        nav = ", ".join(href for href, _ in actual.nav_links)
        print(f"PAGE {route} title={actual.title.strip()!r} h1={actual.h1.strip()!r} "
              f"canonical={actual.canonicals!r} robots={robots!r} nav=[{nav}] "
              f"sha256={hashlib.sha256(body).hexdigest()}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external", action="store_true",
                        help="also request public HTTPS destinations anonymously")
    parser.add_argument("--live-routes", action="store_true",
                        help="verify /constellation and /constellation/ against the published front door")
    parser.add_argument("--base-url", default="https://unpingable.com",
                        help="origin used by --live-routes")
    args = parser.parse_args()
    failures = []
    external: set[str] = set()
    checked = 0
    pages = sorted((ROOT / "constellation").rglob("*.html"))
    failures.extend(route_source_problems())
    pages += [ROOT / name for name in ("index.html", "about.html")]
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
        if not immutable_release:
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
    if args.live_routes:
        failures.extend(check_live_routes(args.base_url))
    for failure in failures:
        print(failure, file=sys.stderr)
    print(f"Checked {checked} references; {len(failures)} failures")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
