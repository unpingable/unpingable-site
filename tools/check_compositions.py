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


if __name__ == "__main__":
    print(f"Validated {validate()} compositions")
