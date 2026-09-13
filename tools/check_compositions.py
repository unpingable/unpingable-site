#!/usr/bin/env python3
"""Validate composition IDs against the public component inventory."""
from __future__ import annotations

import json
from pathlib import Path

from check_constellation import local_problem

ROOT = Path(__file__).resolve().parent.parent


def validate(root: Path = ROOT) -> int:
    inventory = json.loads((root / "constellation/components.json").read_text())
    component_ids = {item["id"] for item in inventory["components"]}
    data = json.loads((root / "constellation/compositions.json").read_text())
    if data.get("schema") != "constellation.compositions/v1" or data.get("inventory") != "components.json":
        raise ValueError("invalid composition catalog header")
    seen: set[str] = set()
    for item in data.get("compositions", []):
        if set(item) != {"id", "summary", "component_ids", "maturity", "recipe"}:
            raise ValueError("composition fields must remain references, not copied inventory")
        if item["id"] in seen or not item["component_ids"] or not set(item["component_ids"]) <= component_ids:
            raise ValueError("composition has duplicate identity or unknown component")
        problem = local_problem(root / "constellation/compositions.json", item["recipe"], root)
        if problem:
            raise ValueError(f"invalid recipe link: {problem}")
        seen.add(item["id"])
    if not seen:
        raise ValueError("composition catalog is empty")
    return len(seen)


def validate_profiles(root: Path = ROOT) -> int:
    component_ids = {item["id"] for item in json.loads(
        (root / "constellation/components.json").read_text())["components"]}
    data = json.loads((root / "constellation/integration-profiles.json").read_text())
    if (data.get("schema") != "constellation.integration-profiles/v1"
            or data.get("version") != "0.1.0-alpha.1" or data.get("release_status") != "candidate"):
        raise ValueError("invalid integration profile header")
    seen = set()
    for profile in data.get("profiles", []):
        if set(profile) != {"id", "component_ids", "status", "guide"}:
            raise ValueError("invalid integration profile fields")
        if profile["id"] in seen or not set(profile["component_ids"]) <= component_ids:
            raise ValueError("duplicate profile or unknown component")
        if local_problem(root / "constellation/integration-profiles.json", profile["guide"], root):
            raise ValueError("invalid integration profile guide")
        seen.add(profile["id"])
    return len(seen)


if __name__ == "__main__":
    print(f"Validated {validate()} compositions and {validate_profiles()} profiles")
