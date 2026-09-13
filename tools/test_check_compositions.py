import json
import tempfile
import unittest
from pathlib import Path

from check_compositions import validate, validate_profiles


class Compositions(unittest.TestCase):
    def composition(self, capability_ids=("a",), *, example_id="a"):
        return {
            "id": "x", "summary": "X", "maturity": "runnable", "recipe": "recipes.html#one",
            "lost_guarantees": ["No authority"], "refusals": ["Invalid input refuses"],
            "capabilities": {"required": [{"capability": "read", "component_ids": list(capability_ids)}], "optional": []},
            "public_examples": [{"implementation_id": example_id, "source": "https://example.test/source", "example": "recipes.html#one", "state": "fixture"}],
        }

    def test_references_inventory_and_recipe_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json",
                "compositions": [self.composition()]}))
            self.assertEqual(validate(root), 1)

    def test_unknown_component_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json",
                "compositions": [self.composition(("missing",), example_id="missing")]}))
            with self.assertRaises(ValueError): validate(root)

    def test_rejects_copied_catalog_field(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            composition = self.composition(); composition["name"] = "copied catalog field"
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json", "compositions": [composition]}))
            with self.assertRaises(ValueError): validate(root)

    def test_allows_explicit_deployment_capability_without_catalog_component(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            composition = self.composition()
            composition["capabilities"]["required"].append({
                "capability": "deployment executor", "component_ids": [], "provided_by": "deployment"})
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json", "compositions": [composition]}))
            self.assertEqual(validate(root), 1)

    def test_refuses_deployment_capability_that_claims_catalog_component(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            composition = self.composition()
            composition["capabilities"]["required"].append({
                "capability": "deployment executor", "component_ids": ["a"], "provided_by": "deployment"})
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json", "compositions": [composition]}))
            with self.assertRaises(ValueError): validate(root)

    def test_versioned_profiles_reference_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            (root / "constellation/integration-profiles.json").write_text(json.dumps({
                "schema": "constellation.integration-profiles/v1", "version": "0.1.0-alpha.1",
                "release_status": "candidate", "profiles": [{"id": "a", "component_ids": ["a"],
                "status": "runnable", "guide": "recipes.html#one"}]}))
            self.assertEqual(validate_profiles(root), 1)


if __name__ == "__main__": unittest.main()
