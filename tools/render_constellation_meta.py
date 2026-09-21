#!/usr/bin/env python3
"""Render consistent metadata for mutable Constellation documentation pages."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
BASE = "https://unpingable.com/constellation/"
IMAGE = "https://unpingable.com/og-card.png"
PAGES = {
    "index.html": (
        "Constellation — governance and execution custody",
        "Constellation is a governance and execution-custody layer for automated work. Start with the verified 0.1.0-alpha.6 walkthrough.",
        BASE,
    ),
    "understand.html": (
        "How Constellation works",
        "Understand Constellation's observation, judgment, authority, execution-custody and reconciliation boundaries.",
        BASE + "understand.html",
    ),
    "components.html": (
        "Constellation components",
        "Verified public source, responsibilities, maturity and availability for Constellation components.",
        BASE + "components.html",
    ),
    "integration.html": (
        "Constellation integration",
        "Choose the smallest evidence-backed Constellation composition for consultation, attention or one governed action.",
        BASE + "integration.html",
    ),
    "recipes.html": (
        "Constellation integration recipes",
        "Runnable public Constellation recipes with exact prerequisites, substitutions, recovery behavior and limits.",
        BASE + "recipes.html",
    ),
    "after-first-run.html": (
        "After the first Constellation run",
        "Supported lifecycle, retention, backup, recovery and upgrade limits for released Constellation profiles.",
        BASE + "after-first-run.html",
    ),
    "start.html": (
        "Start with Constellation",
        "Start with the verified alpha.6 walkthrough, public component source and earlier scoped Constellation tutorials.",
        BASE + "start.html",
    ),
    "notifications.html": (
        "Human notifications — Constellation",
        "What Constellation's local and deterministic notification paths establish, and why live delivery remains unqualified.",
        BASE + "notifications.html",
    ),
    "troubleshooting.html": (
        "Troubleshooting Constellation alpha profiles",
        "Inspect, preserve and report problems in released Constellation profiles without blindly repeating uncertain work.",
        BASE + "troubleshooting.html",
    ),
    "objective-saved-check-read.html": (
        "Objective saved-check read — Constellation",
        "Read one retained saved check beside an exact authored objective with the pinned public alpha.3 composition.",
        BASE + "objective-saved-check-read.html",
    ),
    "phosphor-reader.html": (
        "Phosphor external reader demonstration",
        "Reproduce the public AG-hosted Phosphor display and inspect its deterministic corpus through a bounded reader.",
        BASE + "phosphor-reader.html",
    ),
    "queue-attention.html": (
        "Read a queue and retain attention — Constellation",
        "Run the bounded public Monitor, NQ, Pulse and Nightshift queue-attention example and inspect its limits.",
        BASE + "queue-attention.html",
    ),
    "release-policy.html": (
        "Constellation integration release policy",
        "How immutable Constellation integration profiles pin tested compositions while component versions remain independent.",
        BASE + "release-policy.html",
    ),
    "saved-check-attention.html": (
        "Saved-check attention — Constellation",
        "Run one disposable SQLite saved check, retain attention and deliver one local operator-inbox file.",
        BASE + "saved-check-attention.html",
    ),
    "governed-improvement.html": (
        "Governed recursive improvement — research note",
        "A deferred research direction for improving governed campaign processes without moving their authority boundaries.",
        BASE + "governed-improvement.html",
    ),
}

NAVIGATION = (
    ("index.html", "Constellation", "index.html"),
    (None, "Alpha.6 walkthrough", "releases/0.1.0-alpha.6/guide.html"),
    ("components.html", "Components", "components.html"),
    ("integration.html", "Integration", "integration.html"),
    ("recipes.html", "Recipes", "recipes.html"),
    ("after-first-run.html", "Operations", "after-first-run.html"),
    ("start.html", "Source and tutorials", "start.html"),
    ("troubleshooting.html", "Troubleshooting", "troubleshooting.html"),
)


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def head(title: str, description: str, canonical: str) -> str:
    return f'''<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="unpingable">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{IMAGE}">
  <meta property="og:image:alt" content="Constellation — governed automated work">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">
  <meta name="twitter:image" content="{IMAGE}">
  <title>{esc(title)}</title>
  <link rel="canonical" href="{esc(canonical)}">
  <link rel="stylesheet" href="base.css">
</head>'''


def update(path: Path, rendered: str) -> str:
    source = path.read_text()
    updated, count = re.subn(r"<head>.*?</head>", rendered, source, count=1, flags=re.DOTALL)
    if count != 1:
        raise ValueError(f"{path}: expected one head element")
    relative = path.name
    links = []
    for current_page, label, href in NAVIGATION:
        current = ' aria-current="page"' if current_page == relative else ""
        strong = relative == "index.html" and current_page == "index.html"
        link = f'<a href="{href}"{current}>{label}</a>'
        links.append(f"<strong>{link}</strong>" if strong else link)
    navigation = '<nav aria-label="Main navigation">' + "".join(links) + "</nav>"
    updated, count = re.subn(
        r'<nav aria-label="Main navigation">.*?</nav>',
        navigation,
        updated,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError(f"{path}: expected one main navigation")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for relative, values in PAGES.items():
        path = ROOT / "constellation" / relative
        updated = update(path, head(*values))
        if updated != path.read_text():
            stale.append(relative)
            if not args.check:
                path.write_text(updated)
    if args.check and stale:
        print("stale Constellation metadata: " + ", ".join(stale), file=sys.stderr)
        return 1
    print(f"Checked {len(PAGES)} mutable page metadata blocks; {len(stale)} updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
