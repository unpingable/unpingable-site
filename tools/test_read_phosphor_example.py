import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).parent.parent / "constellation/examples/read_phosphor.py"
SPEC = importlib.util.spec_from_file_location("read_phosphor", PATH)
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class ReaderExample(unittest.TestCase):
    def test_preserves_independent_source_availability(self):
        value = {"schema": MODULE.SCHEMA, "campaigns": [{"locator_token": "aa",
            "inspect": {"availability": "available"}, "history": {"availability": "unavailable"},
            "refusals": {"availability": "available"}}]}
        self.assertEqual(MODULE.summarize(value)["campaigns"][0]["sources"]["history"], "unavailable")

    def test_refuses_foreign_shape(self):
        with self.assertRaises(ValueError): MODULE.summarize({"schema": "other", "campaigns": []})


if __name__ == "__main__": unittest.main()
