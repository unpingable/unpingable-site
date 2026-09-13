#!/usr/bin/env python3
"""Read one local Phosphor campaign index without changing it."""
from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

SCHEMA = "ag.operator-ui.campaign-index/v1"
MAX_BYTES = 4 * 1024 * 1024
ENDPOINT_PATH = "/api/v1/campaigns"


class RedirectRefused(HTTPRedirectHandler):
    """Keep the one read-only request on the selected loopback endpoint."""

    def redirect_request(self, request, fp, code, message, headers, newurl):  # type: ignore[no-untyped-def]
        raise HTTPError(request.full_url, code, "redirect refused", headers, fp)


def checked_url(value: str) -> str:
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("--url must have a valid Phosphor loopback port") from error
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "::1"}
        or port != 8417
        or parsed.path != ENDPOINT_PATH
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("--url must be the exact loopback Phosphor campaign-index endpoint")
    return value


def fetch(url: str) -> bytes:
    """Fetch one bounded index without proxy or redirect traversal."""
    opener = build_opener(ProxyHandler({}), RedirectRefused())
    request = Request(url, method="GET")
    try:
        with opener.open(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}")
            raw = response.read(MAX_BYTES + 1)
    except HTTPError as error:
        raise RuntimeError(f"HTTP {error.code}: {error.reason}") from error
    except URLError as error:
        raise RuntimeError(f"transport failure: {error.reason}") from error
    if len(raw) > MAX_BYTES:
        raise RuntimeError("Phosphor response exceeds 4194304-byte bound")
    return raw


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
            summary_source: dict[str, str] = {"availability": availability}
            if availability == "unavailable":
                error_kind = source.get("error_kind")
                if not isinstance(error_kind, str) or not error_kind:
                    raise ValueError(f"invalid {name} unavailable source")
                summary_source["error_kind"] = error_kind
            sources[name] = summary_source
        summary.append({"locator_token": item["locator_token"], "sources": sources})
    return {"schema": "constellation.phosphor-index-summary/v1", "campaigns": summary}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8417/api/v1/campaigns")
    args = parser.parse_args()
    try:
        raw = fetch(checked_url(args.url))
        print(json.dumps(summarize(json.loads(raw)), sort_keys=True, separators=(",", ":")))
    except (ValueError, json.JSONDecodeError, RuntimeError) as error:
        raise SystemExit(
            f"Phosphor index not accepted: {error}. Preserve the observed result; "
            "inspect the selected loopback server and its documented owner records before retrying."
        ) from error


if __name__ == "__main__":
    main()
