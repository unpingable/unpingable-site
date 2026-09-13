#!/usr/bin/env python3
"""Read one local Phosphor campaign index without changing it."""
from __future__ import annotations

import argparse
import json
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SCHEMA = "ag.operator-ui.campaign-index/v1"
MAX_BYTES = 4 * 1024 * 1024


def summarize(document: object) -> dict[str, object]:
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ValueError("unexpected Phosphor schema")
    campaigns = document.get("campaigns")
    if not isinstance(campaigns, list):
        raise ValueError("campaigns is not a list")
    summary = []
    for item in campaigns:
        if not isinstance(item, dict) or not isinstance(item.get("locator_token"), str):
            raise ValueError("invalid campaign index entry")
        sources = {}
        for name in ("inspect", "history", "refusals"):
            source = item.get(name)
            availability = source.get("availability") if isinstance(source, dict) else None
            if availability not in {"available", "unavailable"}:
                raise ValueError(f"invalid {name} availability")
            sources[name] = availability
        summary.append({"locator_token": item["locator_token"], "sources": sources})
    return {"schema": "constellation.phosphor-index-summary/v1", "campaigns": summary}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8417/api/v1/campaigns")
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("--url must select a loopback HTTP Phosphor endpoint")
    with urlopen(Request(args.url, method="GET"), timeout=10) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise SystemExit("Phosphor response exceeds bound")
    print(json.dumps(summarize(json.loads(raw)), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
