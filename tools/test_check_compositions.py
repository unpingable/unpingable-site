import json
import tempfile
import unittest
from pathlib import Path

from check_compositions import validate


class Compositions(unittest.TestCase):
    def test_references_inventory_and_recipe_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json",
                "compositions": [{"id": "x", "summary": "X", "component_ids": ["a"],
                                  "maturity": "runnable", "recipe": "recipes.html#one"}]}))
            self.assertEqual(validate(root), 1)

    def test_unknown_component_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json",
                "compositions": [{"id": "x", "summary": "X", "component_ids": ["missing"],
                                  "maturity": "runnable", "recipe": "recipes.html#one"}]}))
            with self.assertRaises(ValueError): validate(root)


if __name__ == "__main__": unittest.main()
