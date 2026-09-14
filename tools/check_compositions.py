#!/usr/bin/env python3
"""Validate composition IDs against the public component inventory."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import re
import subprocess
import argparse

from check_constellation import local_problem

ROOT = Path(__file__).resolve().parent.parent
COMPOSITION_FIELDS = {"id", "summary", "capabilities", "lost_guarantees", "maturity", "public_examples", "recipe", "refusals"}
PIN = re.compile(r"^[0-9a-f]{40}$")
PRERELEASE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-[0-9a-z]+(?:[.-][0-9a-z]+)*$")


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
            if (not isinstance(entry, dict) or not set(entry) <= {"capability", "component_ids", "provided_by"}
                    or set(entry) < {"capability", "component_ids"}
                    or not isinstance(entry["capability"], str) or not entry["capability"]
                    or not isinstance(entry["component_ids"], list)
                    or entry.get("provided_by", "component") not in {"component", "deployment", "synthetic-fixture"}):
                raise ValueError("composition has invalid capability implementation")
            provided_by = entry.get("provided_by", "component")
            if ((provided_by == "component" and (not _nonempty_strings(entry["component_ids"])
                                                   or not set(entry["component_ids"]) <= component_ids))
                    or (provided_by != "component" and entry["component_ids"])):
                raise ValueError("composition capability has invalid provider reference")


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
            or not isinstance(data.get("version"), str)
            or not PRERELEASE.fullmatch(data["version"])
            or data.get("release_status") != "candidate"):
        raise ValueError("invalid integration profile header")
    seen = set()
    for profile in data.get("profiles", []):
        fields = {"id", "component_ids", "status", "guide"}
        if set(profile) not in (fields, fields | {"release_candidate"}, fields | {"release"}):
            raise ValueError("invalid integration profile fields")
        if profile["id"] in seen or not set(profile["component_ids"]) <= component_ids:
            raise ValueError("duplicate profile or unknown component")
        if local_problem(root / "constellation/integration-profiles.json", profile["guide"], root):
            raise ValueError("invalid integration profile guide")
        reference = "release" if "release" in profile else "release_candidate"
        if reference in profile:
            candidate = profile[reference]
            expected_status = "released-alpha" if reference == "release" else "qualified-public-reproduction-tag-pending"
            if (profile["status"] != expected_status
                    or not isinstance(candidate, dict)
                    or set(candidate) != {"suite_version", "guide", "manifest"}
                    or not PRERELEASE.fullmatch(candidate.get("suite_version", ""))
                    or not all(isinstance(candidate[field], str) and candidate[field]
                               for field in ("guide", "manifest"))):
                raise ValueError("invalid release-candidate reference")
            for field in ("guide", "manifest"):
                if local_problem(root / "constellation/integration-profiles.json",
                                 candidate[field], root):
                    raise ValueError("release-candidate link is invalid")
            manifest_path = root / "constellation" / candidate["manifest"]
            try:
                manifest = json.loads(manifest_path.read_text())
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError("release-candidate manifest is unreadable") from error
            if (manifest.get("schema") != "constellation.integration-release-manifest/v1"
                    or manifest.get("suite_version") != candidate["suite_version"]
                    or not any(isinstance(entry, dict) and entry.get("id") == profile["id"]
                               for entry in manifest.get("profiles", []))):
                raise ValueError("release-candidate does not match its immutable manifest")
        seen.add(profile["id"])
    return len(seen)


def _git_bytes(root: Path, commit: str, path: str) -> bytes:
    if path.startswith("/") or ".." in Path(path).parts:
        raise ValueError("release example path leaves its source tree")
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=root, check=False,
        capture_output=True,
    )
    if completed.returncode:
        raise ValueError("release example file is absent from its pinned source tree")
    return completed.stdout


def _git_text(root: Path, *arguments: str) -> str:
    completed = subprocess.run(["git", *arguments], cwd=root, check=False,
                               capture_output=True, text=True)
    if completed.returncode:
        raise ValueError("release verification checkout is not the required Git source")
    return completed.stdout.strip()


def _normalized_source(value: str) -> str:
    normalized = value.removesuffix(".git").rstrip("/")
    github_ssh = re.fullmatch(r"git@(github\.com|github-unpingable):([^/]+/[^/]+)", normalized)
    if github_ssh:
        return github_ssh.group(2)
    github = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)", normalized)
    return github.group(1) if github else normalized


def _git_common_dir(root: Path) -> Path:
    value = Path(_git_text(root, "rev-parse", "--git-common-dir"))
    return (root / value).resolve() if not value.is_absolute() else value.resolve()


def _validate_example_source(root: Path, example: object, components: list[dict],
                             source_head: str, verification_checkouts: dict[str, Path]) -> None:
    if not isinstance(example, dict) or not PIN.fullmatch(example.get("commit", "")):
        raise ValueError("release example source has invalid pin")
    external_fields = {"source_kind", "component_id", "commit", "example",
                       "example_sha256", "guide", "guide_sha256"}
    if example.get("source_kind") == "public_component":
        if set(example) != external_fields:
            raise ValueError("external release example has invalid fields")
        component = next((item for item in components
                          if item.get("id") == example.get("component_id")), None)
        # The kit and runtime are independently pinned snapshots of the same
        # public product. A later example commit does not upgrade the runtime;
        # qualification must exercise the exact pair recorded by the manifest.
        if (component is None
                or not isinstance(component.get("source"), str)
                or not component["source"].startswith("https://")):
            raise ValueError("external release example is not bound to a public component source")
        checkout = verification_checkouts.get(example["component_id"])
        if checkout is None or not checkout.is_absolute() or not checkout.is_dir():
            raise ValueError("external release example requires an explicit verification checkout")
        if _git_text(checkout, "rev-parse", "HEAD") != example["commit"]:
            raise ValueError("external release example checkout is not at the pinned commit")
        remote = _git_text(checkout, "remote", "get-url", "origin")
        if _normalized_source(remote) != _normalized_source(component["source"]):
            raise ValueError("external release example checkout has the wrong public source identity")
        if _git_common_dir(checkout) == _git_common_dir(root):
            raise ValueError("external release example cannot self-pin the site source")
        for stem in ("example", "guide"):
            path, expected = example[stem], example[f"{stem}_sha256"]
            if (not isinstance(path, str) or not path
                    or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)
                    or hashlib.sha256(_git_bytes(checkout, example["commit"], path)).hexdigest() != expected):
                raise ValueError("external release example hash does not match pinned component source")
        return
    legacy_fields = {"repository", "commit", "reader", "reader_sha256", "setup", "setup_sha256",
                     "requirements", "requirements_sha256"}
    if (set(example) != legacy_fields or example["commit"] == source_head
            or not isinstance(example["repository"], str)
            or not example["repository"].startswith("https://")):
        raise ValueError("release example source has invalid or circular self pin")
    for stem in ("reader", "setup", "requirements"):
        path, expected = example[stem], example[f"{stem}_sha256"]
        if (not isinstance(path, str) or not path
                or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)
                or hashlib.sha256(_git_bytes(root, example["commit"], path)).hexdigest() != expected):
            raise ValueError("release example hash does not match pinned source tree")


def validate_releases(root: Path = ROOT, verification_checkouts: dict[str, Path] | None = None) -> int:
    """Validate immutable release records separately from the mutable profile catalog."""
    releases = root / "constellation/releases"
    if not releases.is_dir():
        return 0
    inventory = json.loads((root / "constellation/components.json").read_text())
    components = inventory["components"]
    component_ids = {item["id"] for item in components}
    verification_checkouts = verification_checkouts or {}
    try:
        source_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as error:
        raise ValueError("release validation requires the source Git tree") from error
    count = 0
    for manifest_path in sorted(releases.glob("*/manifest.json")):
        raw = manifest_path.read_bytes()
        data = json.loads(raw)
        if (data.get("schema") != "constellation.integration-release-manifest/v1"
                or data.get("manifest_schema_version") != 1
                or data.get("suite_version") != manifest_path.parent.name
                or data.get("schema") == "constellation.integration-profiles/v1"):
            raise ValueError("invalid immutable release manifest header")
        profiles = data.get("profiles")
        components = data.get("components")
        if not isinstance(profiles, list) or not profiles or not isinstance(components, list) or not components:
            raise ValueError("release manifest lacks profiles or components")
        for profile in profiles:
            if (not isinstance(profile, dict) or not isinstance(profile.get("id"), str)
                    or not set(profile.get("required_components", [])) <= component_ids):
                raise ValueError("release profile has unknown component")
        for component in components:
            if (not isinstance(component, dict) or component.get("id") not in component_ids
                    or not isinstance(component.get("source"), str)
                    or not PIN.fullmatch(component.get("commit", ""))):
                raise ValueError("release component has invalid source pin")
        _validate_example_source(root, data.get("example_source"), components,
                                 source_head, verification_checkouts)
        documentation = data.get("documentation", {})
        qualification = data.get("qualification", {})
        guide = documentation.get("guide") if isinstance(documentation, dict) else None
        record = qualification.get("record") if isinstance(qualification, dict) else None
        if not isinstance(guide, str) or not isinstance(record, str):
            raise ValueError("release manifest lacks sibling guide or qualification record")
        guide_path, qualification_path = manifest_path.parent / guide, manifest_path.parent / record
        if not guide_path.is_file() or not qualification_path.is_file():
            raise ValueError("release manifest sibling record is missing")
        qualification_data = json.loads(qualification_path.read_text())
        if (qualification_data.get("schema") != "constellation.integration-qualification/v1"
                or qualification_data.get("suite_version") != data["suite_version"]
                or qualification_data.get("manifest_sha256") != hashlib.sha256(raw).hexdigest()):
            raise ValueError("qualification does not bind this manifest")
        count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--component-checkout", action="append", default=[], metavar="ID=/ABSOLUTE/PATH")
    arguments = parser.parse_args()
    checkouts = {}
    for binding in arguments.component_checkout:
        component_id, separator, path = binding.partition("=")
        if not separator or not component_id or not Path(path).is_absolute() or component_id in checkouts:
            parser.error("--component-checkout requires one unique ID=/ABSOLUTE/PATH binding")
        checkouts[component_id] = Path(path)
    print(f"Validated {validate()} compositions, {validate_profiles()} profiles and {validate_releases(verification_checkouts=checkouts)} releases")
