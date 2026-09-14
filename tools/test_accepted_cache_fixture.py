import argparse
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import sqlite3

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "constellation/examples/connected_cache/accepted-plan"
sys.path.insert(0, str(FIXTURE_DIR))
from export_accepted_cache_fixture import export
from maude.plan.store import DraftStore

SOURCE_BUNDLE = Path(os.environ.get("ACCEPTED_FIXTURE_BUNDLE", str(FIXTURE_DIR / "accepted-bundle.json")))
SOURCE_STORE = Path(os.environ.get("ACCEPTED_FIXTURE_STORE", str(FIXTURE_DIR / "accepted-plan.sqlite")))
BUNDLE_SHA = "1fa0f621556484c916da8127083bf42e2a54646954de096a872d39d7d7abb441"
STORE_SHA = "a9ceed5a625dcbc8708301b4aaac58c2ef0a4b394127b7cae953316e0503f4de"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(SOURCE_BUNDLE.is_file() and SOURCE_STORE.is_file(),
                     "set ACCEPTED_FIXTURE_BUNDLE and ACCEPTED_FIXTURE_STORE")
class ExportTests(unittest.TestCase):
    def args(self, root, *, bundle=SOURCE_BUNDLE, store=SOURCE_STORE):
        return argparse.Namespace(
            bundle=bundle, store=store, output=root / "out",
            bundle_sha256=BUNDLE_SHA, store_sha256=STORE_SHA,
            draft_id="draft_synthetic_cache_platform",
            plan_digest="sha256:bae29715069c298263314057a8681e71903d49eb29b7536a25f69671baddd83e",
            lock_id="sha256:d2b6350eeab1fba4fa1265e13c7793a76991d1bf8478c1f267941dc447aca07d",
            acceptance_ref="sha256:98e3bf73b45e29d6098f1f0762babbcc71bb81391d2b188b95c81e241ba0295a",
        )

    def test_export_preserves_source_and_exact_bytes(self):
        before = (digest(SOURCE_BUNDLE), digest(SOURCE_STORE))
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); result = export(self.args(root))
            self.assertEqual(digest(root / "out/accepted-bundle.json"), BUNDLE_SHA)
            self.assertEqual(digest(root / "out/accepted-plan.sqlite"), STORE_SHA)
            self.assertEqual(result["authority"], "none")
        self.assertEqual((digest(SOURCE_BUNDLE), digest(SOURCE_STORE)), before)

    def test_wrong_bundle_hash_refuses_without_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); args = self.args(root); args.bundle_sha256 = "0" * 64
            with self.assertRaisesRegex(ValueError, "exact independently reviewed fixture hashes"):
                export(args)
            self.assertFalse(args.output.exists())

    def test_wrong_store_hash_refuses_without_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); args = self.args(root); args.store_sha256 = "0" * 64
            with self.assertRaisesRegex(ValueError, "exact independently reviewed fixture hashes"):
                export(args)
            self.assertFalse(args.output.exists())

    def test_wrong_plan_binding_refuses_without_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); args = self.args(root); args.plan_digest = "sha256:" + "0" * 64
            with self.assertRaisesRegex(ValueError, "bundle differs"):
                export(args)
            self.assertFalse(args.output.exists())

    def test_extra_record_store_refuses_even_with_its_recomputed_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); bundle = root / "bundle.json"; store = root / "store.sqlite"
            bundle.write_bytes(SOURCE_BUNDLE.read_bytes()); store.write_bytes(SOURCE_STORE.read_bytes())
            with sqlite3.connect(store) as db:
                db.execute("INSERT INTO drafts VALUES (?,?,?)", ("private-extra", "private-revision", "2026-01-01T00:00:00Z"))
            args = self.args(root, bundle=bundle, store=store)
            args.store_sha256 = digest(store)
            with self.assertRaisesRegex(ValueError, "exact independently reviewed fixture hashes"):
                export(args)
            self.assertFalse(args.output.exists())

    def test_content_mutation_during_validation_refuses_without_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); bundle = root / "bundle.json"; store = root / "store.sqlite"
            bundle.write_bytes(SOURCE_BUNDLE.read_bytes()); store.write_bytes(SOURCE_STORE.read_bytes())
            real_open = DraftStore.open_readonly

            class MutatingProjection:
                def __init__(self, wrapped): self.wrapped = wrapped
                def projection(self, draft_id):
                    result = self.wrapped.projection(draft_id)
                    with store.open("ab") as stream: stream.write(b"changed")
                    return result

            with mock.patch("export_accepted_cache_fixture.DraftStore.open_readonly",
                            side_effect=lambda path: MutatingProjection(real_open(path))):
                with self.assertRaisesRegex(ValueError, "source changed"):
                    export(self.args(root, bundle=bundle, store=store))
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
