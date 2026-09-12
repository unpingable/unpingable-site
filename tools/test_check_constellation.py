import tempfile
import unittest
from pathlib import Path

from check_constellation import Page, local_problem


class LocalLinks(unittest.TestCase):
    def test_parser_collects_navigation_assets_and_anchors(self):
        page = Page('<a href="start.html#demo">Start</a><img src="shot.png"><h2 id="demo">Demo</h2>')
        self.assertEqual(page.links, ["start.html#demo", "shot.png"])
        self.assertEqual(page.ids, {"demo"})

    def test_destination_and_anchor_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text('<main id="main"></main>')
            self.assertIsNone(local_problem(page, "#main", root))
            self.assertEqual(local_problem(page, "#missing", root), "missing local anchor")
            self.assertEqual(local_problem(page, "absent.html", root), "missing local destination")
            self.assertEqual(local_problem(page, "../outside", root), "link leaves the site tree")
            self.assertIsNone(local_problem(page, "https://example.com/", root))


if __name__ == "__main__":
    unittest.main()
