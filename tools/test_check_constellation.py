import tempfile
import unittest
from pathlib import Path

from check_constellation import Page, local_problem, route_source_problems


class LocalLinks(unittest.TestCase):
    def test_parser_collects_navigation_assets_and_anchors(self):
        page = Page('<title>Front</title><h1>Heading</h1><nav><a href="start.html#demo">Start here</a></nav><img src="shot.png"><h2 id="demo">Demo</h2>')
        self.assertEqual(page.links, ["start.html#demo", "shot.png"])
        self.assertEqual(page.ids, {"demo"})
        self.assertEqual(page.title, "Front")
        self.assertEqual(page.h1, "Heading")
        self.assertEqual(page.nav_links, [("start.html#demo", "Start here")])

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

    def test_extensionless_shadow_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            front = root / "constellation" / "index.html"
            front.parent.mkdir()
            front.write_text('''<title>Front</title>
                <link rel="canonical" href="https://unpingable.com/constellation/">
                <nav><a href="start.html">Start</a></nav><h1>Front door</h1>''')
            self.assertEqual(route_source_problems(root), [])
            (root / "constellation.html").write_text("obsolete sibling")
            self.assertEqual(route_source_problems(root), [
                "constellation.html: shadows the constellation/ directory"
            ])

    def test_other_basename_collisions_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            front = root / "constellation" / "index.html"
            front.parent.mkdir()
            front.write_text('''<title>Front</title>
                <link rel="canonical" href="https://unpingable.com/constellation/">
                <nav><a href="start.html">Start</a></nav><h1>Front door</h1>''')
            (root / "docs").mkdir()
            (root / "docs.html").write_text("shadow")
            self.assertEqual(route_source_problems(root), [
                "docs.html: shadows the docs/ directory"
            ])


if __name__ == "__main__":
    unittest.main()
