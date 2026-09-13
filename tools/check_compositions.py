#!/usr/bin/env python3
"""Validate composition IDs against the public component inventory."""
from __future__ import annotations

import json
from pathlib import Path

from check_constellation import local_problem

ROOT = Path(__file__).resolve().parent.parent
COMPOSITION_FIELDS = {"id", "summary", "capabilities", "lost_guarantees", "maturity", "public_examples", "recipe", "refusals"}


def _nonempty_strings(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item for item in value)


def _validate_capabilities(item: dict, component_ids: set[str]) -> None:
    capabilities = item["capabilities"]
    if not isinstance(capabilities, dict) or set(capabilities) != {"required", "optional"}:
        raise ValueError("invalid composition capabilities")
    for group in ("required", "optional"):
        entries = capabilities[group]
        if not isinstance(entries, list) or (group == "required" and not entries):
            raise ValueError("composition requires named required capabilities")
        for entry in entries:
            if (not isinstance(entry, dict) or set(entry) != {"capability", "component_ids"}
                    or not isinstance(entry["capability"], str) or not entry["capability"]
                    or not _nonempty_strings(entry["component_ids"])
                    or not set(entry["component_ids"]) <= component_ids):
                raise ValueError("composition has invalid capability implementation")


def _validate_examples(root: Path, item: dict, component_ids: set[str]) -> None:
    examples = item["public_examples"]
    if not isinstance(examples, list) or not examples:
        raise ValueError("composition requires public example disposition")
    for example in examples:
        if (not isinstance(example, dict) or set(example) != {"implementation_id", "source", "example", "state"}
                or example["implementation_id"] not in component_ids
                or not isinstance(example["state"], str) or not example["state"]
                or not (example["source"] is None or (isinstance(example["source"], str) and example["source"].startswith("https://")))):
            raise ValueError("invalid public example disposition")
        problem = local_problem(root / "constellation/compositions.json", example["example"], root)
        if problem:
            raise ValueError(f"invalid public example link: {problem}")


def validate(root: Path = ROOT) -> int:
    inventory = json.loads((root / "constellation/components.json").read_text())
    component_ids = {item["id"] for item in inventory["components"]}
    data = json.loads((root / "constellation/compositions.json").read_text())
    if data.get("schema") != "constellation.compositions/v1" or data.get("inventory") != "components.json":
        raise ValueError("invalid composition catalog header")
    seen: set[str] = set()
    for item in data.get("compositions", []):
        if not isinstance(item, dict) or set(item) != COMPOSITION_FIELDS:
            raise ValueError("composition fields must remain capability references, not copied inventory")
        if (not isinstance(item["id"], str) or not item["id"] or item["id"] in seen
                or not isinstance(item["summary"], str) or not item["summary"]
                or not isinstance(item["maturity"], str) or not item["maturity"]
                or not _nonempty_strings(item["lost_guarantees"])
                or not _nonempty_strings(item["refusals"])):
            raise ValueError("composition has duplicate identity or unknown component")
        problem = local_problem(root / "constellation/compositions.json", item["recipe"], root)
        if problem:
            raise ValueError(f"invalid recipe link: {problem}")
        _validate_capabilities(item, component_ids)
        _validate_examples(root, item, component_ids)
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
